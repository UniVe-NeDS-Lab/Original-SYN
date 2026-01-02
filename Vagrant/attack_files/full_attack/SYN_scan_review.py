#target finding and probabilitsic analysis

import scapy.all as scapy
import numpy as np
import random
import logging
from time import sleep

def backlog_syn_scan(bcklg_size, zombie_ip, zombie_port, target_ip):
    """
    Check whether the target machine is alive and reachable.
    
    :param bcklg_size: zombie's backlog size
    :param zombie_ip: zombie's IP address
    :param zombie_port: zombie's port number
    :param target_ip: target's IP address
    :return: p_value, represent the probability of the target machine to be alive 
    """
    packets = []

    packets_number = int(bcklg_size*3/4) # we want to fill only 3/4 of the whole backlog in order not to DoS the zombie
    syn_packets_number = int(packets_number/2) # we send half of the total size of packets as spoofed SYN packets
    canaries_number = packets_number - syn_packets_number # the other half is filled with canaries
    syn_ports = np.random.default_rng().choice([x for x in range(49151, 65535)], syn_packets_number, replace=False) # we use random ports, doesn't matter if they're open 
    canaries_ports = np.random.default_rng().choice([x for x in range(49151, 65535)], canaries_number, replace=False) # we use random ports, doesn't matter if they're open 
    
    # Creates the spoofed SYN packets
    for port in syn_ports:
        packet = scapy.IP(dst=zombie_ip, src=target_ip)/scapy.TCP(dport=zombie_port, sport=port, flags="S")
        packets.append(packet)
    
    # Creates the canaries
    for port in canaries_ports:
        packet = scapy.IP(dst=zombie_ip)/scapy.TCP(dport=zombie_port, sport=port, flags="S", seq=1)
        packets.append(packet)

    packets = random.sample(packets, len(packets)) # shuffle randomly the packets
            
    # Creates the probes
    probes = []
    for port in canaries_ports:
        packet = scapy.IP(dst=zombie_ip)/scapy.TCP(dport=zombie_port, sport=port, flags="S", seq=0) # probes are equal to canaries with seq-=1
        probes.append(packet)

    #answered_first, _ = scapy.sr(packets, inter=1/5, timeout=0) # sending SYN packets mixed with canaries 
    answered_first, _ = scapy.sr(packets, timeout=0)
    #loss = canaries_number - len(answered)

    print("SYN packet sent")

    sleep(15)

    answered, _ = scapy.sr(probes, timeout=5) # "pinging" the canaries by sending the probes

    print("Probes sent")
    ack = 0
    sa = 0
    for _, response in answered: # counting the number of ACKs and SYN-ACKs on the answers to the probes
        print(response)
        if response is not None:
            tcp_header = response.getlayer(scapy.TCP) if response.haslayer(scapy.TCP) else None
            if tcp_header is not None and tcp_header.flags == 0x10: # ACK received
                ack += 1
            elif tcp_header.flags == 0x12: # SYN-ACK received
                sa += 1
    print(canaries_ports)
    print(syn_ports)
                    
    logging.info(f"Total canaries: {canaries_number}, ACKs: {ack},  SYN-ACKs: {sa}") 
    
    if(ack == canaries_number):
        print("Target alive")
    else:
        print("Target not alive")
