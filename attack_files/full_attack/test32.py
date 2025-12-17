#from scapy.all import IP, TCP, send, sniff, sr
from scapy.all import *
import logging
import sys
import time
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
#spoofeds = [None for _ in range(256)]

def send_syn_packets(target_ip, target_port, num_packets):
    """
    Send SYN packets to a target to potentially fill its SYN backlog.
    
    :param target_ip: IP address of the target machine
    :param target_port: Port number on the target machine
    :param num_packets: Number of SYN packets to send
    """
    #logging.info(f"Sending {num_packets} SYN packets to {target_ip}:{target_port}")

    for i in range(num_packets):
        ip = IP(dst=target_ip)
        tcp = TCP(sport=40000 + i, dport=target_port, flags='S', seq=1000 + i)
        packet = ip / tcp
        recieved = sr1(packet, timeout=0, verbose=0)
        
        #time.sleep(1/10)
        #logging.info(f"Sent TCP packet from port {40000 + i}")
    
    #logging.info("SYN packets sent.")

def check_eviction(target_ip, target_port, original_seq_num, original_sport):
    """
    Check whether a SYN entry has been evicted from the backlog by sending a duplicate SYN.
    
    :param target_ip: IP address of the target machine
    :param target_port: Port number on the target machine
    :param original_seq_num: Sequence number used for the original SYN
    :param original_sport: Source port used for the original SYN
    :return: 'ACK' if the original SYN is still in the backlog, 'SYN-ACK' if evicted, None if no response
    """
    # Send a duplicate SYN packet with the same sequence number and source port
    ip = IP(dst=target_ip)
    tcp = TCP(sport=original_sport, dport=target_port, flags='S', seq=original_seq_num-1)
    duplicate_syn = ip / tcp
    ans, _ = sr(duplicate_syn, verbose=0, timeout=4)

    eviction = False
    if ans:
        for _, packet in ans:
            tcp_layer = packet.getlayer(TCP)
            #logging.info(f"{original_sport} has flags: {tcp_layer.flags}")
            
            if tcp_layer.flags == 0x12:  # SYN-ACK flag
                #logging.info(f"{original_sport} recieved SYN-ACK")
                eviction = True
    
    return eviction


def infer_backlog_size(target_ip, target_port):
    """
    Infer the SYN backlog size of a target Linux machine.

    :param target_ip: IP address of the target machine
    :param target_port: Port number on the target machine
    :return: Estimated SYN backlog size
    """
    min_backlog = 12
    max_backlog = 32
    backlog_size = min_backlog
    j = -1
    while backlog_size <= max_backlog:
        logging.info(f"Testing backlog size: {backlog_size}")
        j += 1
        # Send SYN packets to fill the backlog
        send_syn_packets(target_ip, target_port, int(3/4*backlog_size))
        
        time.sleep(8)

        # Check for eviction
        eviction_detected = False
        response = []
        for i in range(int(3/4 * backlog_size)):
            # Use the same source port and sequence number for checking eviction
            response.append(check_eviction(target_ip, target_port, 1000 + i, 40000 + i))
            if True in response:
                eviction_detected = True
#                break

        if eviction_detected:
            break
        else:
            backlog_size += 1

        time.sleep(80)

    return backlog_size

def main(target_ip, target_port):
    inferred_size = infer_backlog_size(target_ip, target_port)

    if inferred_size:
        print(f"backlog size infeered = {inferred_size}")
    else:
        print("-1")
        
    return inferred_size

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <target_ip> <target_port>")
        sys.exit(1)

    target_ip = sys.argv[1]
    target_port = int(sys.argv[2])
    main(target_ip, target_port)
