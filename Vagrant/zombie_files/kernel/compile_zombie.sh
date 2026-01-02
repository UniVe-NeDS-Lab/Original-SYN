#!/bin/bash

# Usciamo al primo errore
set -e


#yes '' | make localmodconfig
scripts/config --disable SYSTEM_TRUSTED_KEYS
scripts/config --disable SYSTEM_REVOCATION_KEYS
scripts/config --disable DEBUG_INFO
scripts/config --enable DEBUG_INFO_NONE
scripts/config --enable CONFIG_INET_DIAG
scripts/config --enable CONFIG_INET_TCP_DIAG
scripts/config --enable CONFIG_NETLINK_DIAG


echo "Forzatura driver VirtIO built-in..."
scripts/config --enable CONFIG_VIRTIO
scripts/config --enable CONFIG_VIRTIO_PCI
scripts/config --enable CONFIG_VIRTIO_BLK    # <--- Fondamentale per il disco
scripts/config --enable CONFIG_VIRTIO_NET    # <--- Fondamentale per la rete (SSH)
scripts/config --enable CONFIG_VIRTIO_CONSOLE
scripts/config --enable CONFIG_SCSI_VIRTIO

sed -i 's/CONFIG_VIRTIO_BLK=m/CONFIG_VIRTIO_BLK=y/' .config
sed -i 's/CONFIG_VIRTIO_NET=m/CONFIG_VIRTIO_NET=y/' .config
sed -i 's/CONFIG_VIRTIO_PCI=m/CONFIG_VIRTIO_PCI=y/' .config

yes '' | make localmodconfig

echo "--- Compilazione ---"
# Compilazione del kernel (vmlinuz) e dei moduli

make -j$(nproc)
make modules -j$(nproc)

sudo make modules_install
sudo make install

sudo update-grub

sudo reboot
