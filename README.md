# Quick Reference & Command Cheat Sheet

Repository per la riproduzione dell'attacco side-channel con SYN, la gestione delle relative mitigazioni e la compilazione personalizzata del Kernel Linux.

---

## 1. Setup e Gestione Vagrant

### Installazione di Vagrant e Libvirt

```bash
# Installazione dipendenze KVM e Libvirt
sudo apt update && sudo apt install -y qemu-kvm libvirt-daemon-system libvirt-clients bridge-utils virtinst

# Abilitazione e avvio del servizio libvirtd
sudo systemctl enable --now libvirtd

# Aggiunta dell'utente corrente al gruppo libvirt
sudo usermod -aG libvirt $(whoami)

# Aggiunta repository ufficiale HashiCorp
wget -O - https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(grep -oP '(?<=UBUNTU_CODENAME=).*' /etc/os-release || lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list

# Installazione Vagrant
sudo apt update && sudo apt install -y vagrant

```

### Plugin Vagrant

```bash
# Provider Libvirt (obbligatorio)
vagrant plugin install vagrant-libvirt

# Trasferimento file via SCP (opzionale)
vagrant plugin install vagrant-scp

```

### Comandi Utili Vagrant

```bash
# Avvio macchine virtuali con provider Libvirt
vagrant up --provider=libvirt

# Stato delle istanze
vagrant status

# Accesso SSH alla macchina target
vagrant ssh <machine_name>

# Ricarica configurazione macchina
vagrant reload <machine_name>

# Spegnimento istanze
vagrant halt

# Sincronizzazione cartelle host -> guest (ATTENZIONE: le modifiche locali sul guest verranno perse)
vagrant rsync

# Copia file dalla macchina guest al sistema locale
vagrant scp <machine_name>:/home/vagrant/attack_files/capture.pcap ./local/path

# Eliminazione completa delle istanze (distruttivo)
vagrant destroy -f

```

---

## 2. Compilazione e Installazione Kernel Linux

> **Nota:** La compilazione del kernel (`make`) **deve essere eseguita da un utente non-root**. Il provider Vagrant esegue i comandi da `root`, perciò il kernel va compilato manualmente.
> 
> 

### Prerequisiti

```bash
sudo apt-get install -y build-essential libncurses-dev bison flex libssl-dev libelf-dev bc dwarves
```

### Download e Verifica Sorgenti

(I sorgenti del kernel sono disponibili su [mirrors.edge.kernel.org](https://mirrors.edge.kernel.org/pub/linux/kernel/))

```bash
# Decompressione archivio
unxz -v linux-5.16.9.tar.xz

# Importazione chiave PGP e verifica della firma
gpg --recv-keys <KEY_ID>
gpg --verify linux-5.16.9.tar.sign linux-5.16.9.tar

# Estrazione sorgenti
tar xvf linux-5.16.9.tar
cd linux-5.16.9/

```

### Configurazione e Compilazione

```bash
# Copia configurazione del kernel attuale
cp -v /boot/config-$(uname -r) .config

# Generazione configurazione locale ridotta
yes '' | make localmodconfig

# Disabilitazione chiavi fidate e info di debug non necessarie
scripts/config --disable SYSTEM_TRUSTED_KEYS
scripts/config --disable SYSTEM_REVOCATION_KEYS
scripts/config --disable DEBUG_INFO
scripts/config --enable DEBUG_INFO_NONE

# Abilitazione diagnostica di rete (TCP e Netlink)
scripts/config --enable CONFIG_INET_DIAG
scripts/config --enable CONFIG_INET_TCP_DIAG
scripts/config --enable CONFIG_NETLINK_DIAG

# Personalizzazione versione (General setup -> Local Version -> Nome custom del kernel)
make menuconfig

# Compilazione sorgenti (ESEGUIRE DA UTENTE NON-ROOT)
make -j$(nproc)

```

### Installazione e Riavvio

```bash
# Installazione moduli e immagine kernel (richiede root)
sudo make modules_install
sudo make install

# Riavvio sistema per caricare il nuovo kernel
sudo reboot

```

> **Nota:** Per la procedura di rimozione di un kernel compilato, consultare la guida su [AskUbuntu](https://askubuntu.com/questions/594443/how-can-i-remove-compiled-kernel).
> 
> 

---

## 4. Setup e Esecuzione con Docker Compose e Vagrant

Questo repository include una configurazione docker compose per avviare l'ambiente con il supporto a `libvirt`/`KVM` e `Vagrant`


### Avvio dello Stack Docker Compose
Per buildare e avviare il container in background:
```bash
docker compose up -d --build
```

### Utilizzo del Container e di Vagrant
Accesso alla shell del container:
```bash
docker exec -it original-syn-vagrant bash
```

Esecuzione di Vagrant per avviare le VM:
```bash
cd Vagrant
vagrant up --provider=libvirt
```


**Solamente nel caso in cui i servizi sulla VM zombie non fossero partiti,** eseguire i comandi riportati qui sotto
```bash
vagrant ssh zombie
cd zombie_files/test_backlog
./compile_run.sh
```

### Installazione del Kernel Personalizzato

Dato che il kernel compilato deve essere installato e avviato all'interno della VM dello zombie, di seguiro gli step da fare per installare il kernel modificato

1. Accedi alla VM zombie tramite SSH con Vagrant
```bash
vagrant ssh zombie
```

2. Vai nella cartella con il kernel e compilalo con lo script
```bash
cd zombie_files/kernel/
./setup_kernel.sh
```

3. Installa il kernel e riavvia
```bash
sudo make modules_install
sudo make install

sudo reboot
```

4. Check post-riavvio, gisuto per essere sicuri
```bash
vagrant ssh zombie
uname -r
```

## 6. Eseguire i Test

Prima di eseguire i test:
- configura Vagrant come descritto precedentemente (quindi anche il kernel sullo zombie, se necessario)
- usano o meno il kernel modificato, in base al test da fare

Per eseguire l'intera serie di test si può usare il seguente script:
```bash
cd /home/vagrant/attack_files/repeted_test_part2
./run.sh
```

## 5. Altri comandi utili

```bash
# Conteggio connessioni in stato SYN-RECV per una porta specifica (es. 8084)
ss -ant | grep SYN-RECV | grep :8084 | wc -l

# Ignorare gli update alla cartella Vagrant/zombie_files/kernel/, così git non deve gestirsi migliaia di cambiamenti ogni compilazione
git update-index --assume-unchanged Vagrant/zombie_files/kernel/
```

