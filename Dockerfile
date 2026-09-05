FROM debian:bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Install KVM, libvirt, Vagrant, build dependencies, and make/gcc for gem native extensions
RUN apt-get update && apt-get install -y \
    qemu-kvm \
    libvirt-daemon-system \
    libvirt-clients \
    bridge-utils \
    virtinst \
    wget \
    curl \
    gnupg \
    lsb-release \
    sudo \
    iptables \
    net-tools \
    git \
    rsync \
    build-essential \
    libxslt-dev \
    libxml2-dev \
    libvirt-dev \
    zlib1g-dev \
    ruby-dev \
    kmod \
    && rm -rf /var/lib/apt/lists/*

# Add HashiCorp repository and install Vagrant
RUN wget -O - https://apt.releases.hashicorp.com/gpg | gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update && apt-get install -y vagrant \
    && rm -rf /var/lib/apt/lists/*

# Install vagrant-libvirt plugin with proper build tools present
RUN vagrant plugin install vagrant-libvirt

WORKDIR /workspace

COPY . /workspace/

CMD ["tail", "-f", "/dev/null"]


