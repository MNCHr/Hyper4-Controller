#!/usr/bin/python

import argparse
import sys
import random

parser = argparse.ArgumentParser(description='Generate t03 table commands')
parser.add_argument('--seed', help='Seed for pseudorandom numbers',
                    type=int, action="store", default=None)
parser.add_argument('--numswitches', help='Number of switches',
                    type=int, action="store", default=3)
parser.add_argument('--numhosts', help='Number of hosts',
                    type=int, action="store", default=24)

args = parser.parse_args(sys.argv[1:])

nb_switches = args.numswitches
nb_hosts = args.numhosts

assert((nb_hosts % nb_switches) == 0)
nb_hosts_per_switch = nb_hosts / nb_switches
nb_links_per_switch = nb_switches - 1 + nb_hosts_per_switch

assert((nb_links_per_switch % 2) == 0)

random.seed(args.seed)

for i in range(nb_switches):
  output = []
  ports = range(1, nb_links_per_switch + 1)
  rand_ports = random.sample(ports, nb_links_per_switch)
  pairs = []
  for j in range(0, len(rand_ports), 2):
    output.append("table_add init_meta_egress a_init_meta_egress %d => %d" \
                  % (rand_ports[j], rand_ports[j+1]))
    output.append("table_add init_meta_egress a_init_meta_egress %d => %d" \
                  % (rand_ports[j+1], rand_ports[j]))

  output.append("table_add check_arp present 1 =>")
  output.append("table_add check_arp send_packet 0 =>")
  output.append("table_add check_opcode arp_request 1 =>")
  output.append("table_set_default check_opcode send_packet")

  for j in range(1, nb_hosts+1):
    hex_id = hex(j).split('x')[-1]
    assert(len(hex_id) < 3)
    if len(hex_id) < 2:
      hex_id = '0' + hex_id
    dest_ip = "0x0A0000" + hex_id
    dest_mac = "0x0004000000" + hex_id
    output.append("table_add handle_arp_request arp_reply " + dest_ip \
                  + " => " + dest_mac)

  output.append("table_set_default handle_arp_request send_packet")

  with open("t03_arp_entries_test_%d"%(i+1), 'w') as out:
    for line in output:
      out.write(line + '\n')
