Vagrant.configure("2") do |config| 
  
  # La Box base per tutte le VM (leggera e universale)
  BOX_NAME = "generic/debian12"
  
  # Definizioni delle Reti
  # Attacker Network: 192.168.20.0/24
  # Zombie Network: 192.168.4.0/24
  # Target Network: 192.168.5.0/24

  # --- CONFIGURAZIONE MACCHINE ---

  # 1. ROUTER (Interconnette le tre reti)
  config.vm.define "router" do |router|
    router.vm.box = BOX_NAME
    router.vm.hostname = "Router"
    
    # Router ha 3 interfacce private, una per ogni sottorete
    router.vm.network "private_network", ip: "192.168.20.254"	#Rete Attaccante
    router.vm.network "private_network", ip: "192.168.4.254"	#Rete Zombie
    router.vm.network "private_network", ip: "192.168.5.254"	#Rete Target
    
    # Provisioning: Abilita IP Forwarding e blocca ICMP Unreachable
    router.vm.provision "shell", inline: <<-SHELL
      echo "Configurazione Router..."
      sudo apt update && sudo apt install -y tcpdump net-tools iptables
      
      # 1. Abilita IP Forwarding
      sudo sysctl -w net.ipv4.ip_forward=1

      # 2. Regola IPTABLES: Blocca gli ICMP Host Unreachable
      # Questi pacchetti possono interferire con il test rivelando fallimenti di routing.
      # Utilizziamo la catena FORWARD che gestisce il traffico tra le interfacce.
      #sudo iptables -A FORWARD -p icmp --icmp-type host-unreachable -j DROP
      sudo iptables -A OUTPUT -p icmp --icmp-type host-unreachable -j DROP
      echo "Regola iptables (DROP ICMP Host Unreachable) applicata sul Router."
    SHELL
  end

  # 2. ZOMBIE (Kernel da testare)
  config.vm.define "zombie" do |zombie|
    zombie.vm.box = BOX_NAME
    zombie.vm.hostname = "Zombie" # <--- AGGIUNTO HOSTNAME
    zombie.vm.network "private_network", ip: "192.168.4.100"
    
    # Aumentiamo le risorse per una compilazione kernel più veloce (opzionale)
    zombie.vm.provider "libvirt" do |libvirt|
      libvirt.cpus = 2
      libvirt.memory = 2048
      libvirt.cpu_model = "host-model"
    end

    # Sync folder per la patch e gli script di compilazione
    zombie.vm.synced_folder "zombie_files/", "/home/vagrant/zombie_files", type: "rsync"
    
    zombie.vm.provision "shell", inline: <<-SHELL
      echo "Configurazione Zombie..."
      
      # Installazione strumenti
      sudo apt update && sudo apt install -y tcpdump net-tools screen build-essential rsync libncurses-dev bison flex libssl-dev libelf-dev bc dwarves
      
      # Configurazione Rotte Statica:
      #sudo ip route add 192.168.20.0/24 via 192.168.4.254 dev eth1
      #sudo ip route add 192.168.5.0/24 via 192.168.4.254 dev eth1
      sudo ip route add 192.168.20.0/24 via 192.168.4.254
      sudo ip route add 192.168.5.0/24 via 192.168.4.254
      
      echo "Rotte statiche configurate"
      
      #cd /home/vagrant/zombie_files/kernel
      #make clean
      #no '' | make localmodconfig
      #scripts/config --disable SYSTEM_TRUSTED_KEYS
      #scripts/config --disable SYSTEM_REVOCATION_KEYS
      #scripts/config --disable DEBUG_INFO
      #scripts/config --enable DEBUG_INFO_NONE
      #scripts/config --enable CONFIG_INET_DIAG
      #scripts/config --enable CONFIG_INET_TCP_DIAG
      #scripts/config --enable CONFIG_NETLINK_DIAG

      #make -j$(nproc)
      #sudo make modules_install
      #sudo make install
      #sudo reboot

      #echo "Compilazione kernel completata, procedere con il reboot della macchina"

    SHELL
    
    # Sync folder per la patch e gli script di compilazione
    #zombie.vm.synced_folder "zombie_files/", "/home/vagrant/zombie_files", type: "rsync"
    
    # Provisioning separato per la compilazione (da implementare)
    #zombie.vm.provision "shell", path: "provision/compile_zombie.sh"
  end

  # 3. TARGET (Server bersaglio della SYN queue)
  config.vm.define "target" do |target|
    target.vm.box = BOX_NAME
    target.vm.hostname = "Target"
    target.vm.network "private_network", ip: "192.168.5.100"
    
    target.vm.provision "shell", inline: <<-SHELL
      echo "Configurazione Target..."
      
      # Installazione di un tool per simulare un servizio in ascolto
      sudo apt update && sudo apt install -y tcpdump net-tools screen rsync iptables
      
      # Configurazione Rota Statica:
      #sudo ip route add 192.168.20.0/24 via 192.168.5.254 dev eth1
      #sudo ip route add 192.168.4.0/24 via 192.168.5.254 dev eth1
      sudo ip route add 192.168.20.0/24 via 192.168.5.254
      sudo ip route add 192.168.4.0/24 via 192.168.5.254
      
      echo "Configurazione target completata"
    SHELL

    # Sync folder per script specifici del target (se presenti)
    #target.vm.synced_folder "target_files/", "/home/vagrant/target_files", type: "rsync"
  end
  
  # Impostazione del provider KVM/Libvirt per tutte le VM
  config.vm.provider "libvirt" do |libvirt|
    libvirt.driver = "kvm"
    libvirt.connect_via_ssh = false
    # Lasciamo l'URI alla configurazione di default o user session per evitare errori
  end
  
  # 4. ATTACCANTE (Source of the spoofed traffic and RST drop)
  config.vm.define "attacker" do |attacker|
    attacker.vm.box = BOX_NAME
    attacker.vm.hostname = "Attacker"
    attacker.vm.network "private_network", ip: "192.168.20.100"
    
    attacker.vm.provision "shell", inline: <<-SHELL
      echo "Configurazione Attaccante..."
      
      # Installazione strumenti
      sudo apt update && sudo apt install -y tcpdump net-tools python3 python3-pip screen rsync iptables python3-scapy
      
      # 2. Configurazione Rotte Statiche:
      #sudo ip route add 192.168.4.0/24 via 192.168.20.254 dev eth1
      #sudo ip route add 192.168.5.0/24 via 192.168.20.254 dev eth1
      sudo ip route add 192.168.4.0/24 via 192.168.20.254
      sudo ip route add 192.168.5.0/24 via 192.168.20.254

      # 3. Regola IPTABLES Cruciale: Blocca i pacchetti RST (e ICMP se necessario)
      #sudo iptables -A INPUT -p tcp --tcp-flags RST RST -s 192.168.4.100 -j DROP # Blocca RST in arrivo dallo Zombie
      sudo iptables -A OUTPUT -p tcp --tcp-flags RST RST -d 192.168.4.100 -j DROP
      sudo iptables -A OUTPUT -p tcp --tcp-flags RST RST -d 192.168.5.100 -j DROP
      
      # 4. Abilita IP Spoofing (se necessario)
      # Nota: Di default è disabilitato se il router non lo blocca a livello Layer 2.
      # sudo sysctl -w net.ipv4.conf.eth1.rp_filter=0 
      
      echo "Ambiente Attaccante pronto. Scapy installato, rotte e regole iptables configurate."
    SHELL
    
    # Sync folder per gli script di attacco (usando rsync, come concordato)
    attacker.vm.synced_folder "attack_files/", "/home/vagrant/attack_files", type: "rsync"
  end
end
