import test2, SYN_scan_review
import sys
from time import sleep

def main(zombie_ip, zombie_port, target_ip):
    #open_connections.send_syn_packets(zombie_ip, zombie_port)
    backlog_size = test2.infer_backlog_size(zombie_ip, zombie_port)
    sleep(90)
    SYN_scan_review.backlog_syn_scan(backlog_size, zombie_ip, zombie_port, target_ip)
    #print(p_value)
    #print("fine")

if __name__ == "__main__":
    zombie_ip = sys.argv[1]
    zombie_port = int(sys.argv[2])
    target_ip = sys.argv[3]

    main(zombie_ip, zombie_port, target_ip)
