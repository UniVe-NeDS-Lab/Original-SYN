#!/bin/bash

# This is 100% pure AI slop, but is should make the setup faster

set -e

echo "=== Starting Custom Kernel Setup ==="

# 1. Prerequisites
echo "[*] Installing prerequisites..."
sudo apt-get update && sudo apt-get install -y \
    build-essential \
    libncurses-dev \
    bison \
    flex \
    libssl-dev \
    libelf-dev \
    bc \
    dwarves \
    rsync \
    wget \
    xz-utils \
    fakeroot \
    ncurses-dev \
    libssl-dev \
    elfutils \
    libaudit-dev \
    libcap-dev \
    libcap-ng-dev \
    kmod

# Navigate to kernel source directory if available, or download if needed
# (Assuming kernel source is located in zombie_files/kernel or similar based on tree)
KERNEL_DIR=""
if [ -d "/home/vagrant/zombie_files/kernel" ]; then
    KERNEL_DIR="/home/vagrant/zombie_files/kernel"
elif [ -d "./Vagrant/zombie_files/kernel" ]; then
    KERNEL_DIR="./Vagrant/zombie_files/kernel"
else
    echo "[*] Kernel source directory not found in default paths. Looking around..."
    KERNEL_DIR=$(find . -type d -name "kernel" | head -n 1)
fi

if [ -n "$KERNEL_DIR" ] && [ -f "$KERNEL_DIR/Makefile" ]; then
    echo "[*] Found kernel source at $KERNEL_DIR"
    cd "$KERNEL_DIR"
else
    echo "[!] Kernel source directory with Makefile not found. Checking current directory..."
    if [ ! -f "Makefile" ]; then
        echo "[*] Downloading Linux Kernel 5.16.9 source..."
        wget https://mirrors.edge.kernel.org/pub/linux/kernel/v5.x/linux-5.16.9.tar.xz
        wget https://mirrors.edge.kernel.org/pub/linux/kernel/v5.x/linux-5.16.9.tar.sign
        unxz -v linux-5.16.9.tar.xz
        tar xvf linux-5.16.9.tar
        cd linux-5.16.9
    fi
fi

echo "[*] Configuring kernel non-interactively..."

# If an existing .config is already present in the kernel source tree, preserve and reuse it.
# Otherwise, copy from /boot or /proc or fall back to defconfig.
if [ -f ".config" ]; then
    echo "[*] Existing .config found in kernel source tree, preserving and reusing it..."
else
    if [ -f "/boot/config-$(uname -r)" ]; then
        cp -v /boot/config-$(uname -r) .config
    elif [ -f /proc/config.gz ]; then
        zcat /proc/config.gz > .config
    else
        echo "[!] No existing kernel config found. Running make defconfig..."
        make defconfig
    fi
fi

# Use make olddefconfig to handle any new config symbols non-interactively with default answers
# instead of make localmodconfig which relies on host lsmod and prompts for new options interactively.
export KCONFIG_NOTIMEOUT=1
yes '' | make olddefconfig || echo "[!] olddefconfig warning encountered, continuing..."

# Disabilitazione chiavi fidate e info di debug non necessarie
scripts/config --disable SYSTEM_TRUSTED_KEYS || true
scripts/config --disable SYSTEM_REVOCATION_KEYS || true
scripts/config --disable DEBUG_INFO || true
scripts/config --enable DEBUG_INFO_NONE || true

# Abilitazione diagnostica di rete (TCP e Netlink)
scripts/config --enable CONFIG_INET_DIAG || true
scripts/config --enable CONFIG_INET_TCP_DIAG || true
scripts/config --enable CONFIG_NETLINK_DIAG || true

# Run olddefconfig again to cleanly apply changes non-interactively
yes '' | make olddefconfig || true

echo "[*] Compiling kernel -j$(nproc)... (NOTE: Must be run as non-root user)"
# Ensure we are not running as root for make, or use appropriate handling
if [ "$(id -u)" -eq 0 ]; then
    echo "[!] Warning: Running make as root is discouraged by kernel build system. Creating build user if needed..."
    useradd -ms /bin/bash builduser || true
    chown -R builduser:builduser .
    sudo -u builduser make -j$(nproc)
else
    make -j$(nproc)
fi

echo "=== Custom Kernel Built Successfully ==="
echo "In order to install it on a VM, move it and run"
echo "sudo make modules_install"
echo "sudo make install"

