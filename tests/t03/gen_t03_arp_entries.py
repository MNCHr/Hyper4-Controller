#!/usr/bin/python

import argparse
import sys
import random
import os
import code

parser = argparse.ArgumentParser(description='Generate t03 table commands')
parser.add_argument('--seed', help='Seed for pseudorandom numbers',
                    type=int, action="store", default=None)
parser.add_argument('--numswitches', help='Number of switches',
                    type=int, action="store", default=3)
parser.add_argument('--numhosts', help='Number of hosts',
                    type=int, action="store")
parser.add_argument('--hostsperswitch', help='Number of hosts',
                    type=int, action="store")

args = parser.parse_args(sys.argv[1:])

if args.numhosts and args.hostsperswitch:
  raise parser.error("--numhosts incompatible with --hostsperswitch")

if not args.numhosts and not args.hostsperswitch:
  raise parser.error("must supply either --numhosts or --hostsperswitch")

if args.numhosts:
  assert(args.numhosts % args.numswitches == 0)
  nb_hosts = args.numhosts

else: #args.hostsperswitch:
  nb_hosts = args.hostsperswitch * args.numswitches

nb_switches = args.numswitches

assert((nb_hosts % nb_switches) == 0)
nb_hosts_per_switch = nb_hosts / nb_switches
nb_links_per_switch = nb_switches - 1 + nb_hosts_per_switch

assert((nb_links_per_switch % 2) == 0)

random.seed(args.seed)
ip_addrs = range(1, 255)
assigned_addrs = []
for h in xrange(nb_hosts):
  assigned_addrs.append(ip_addrs.pop(random.randint(0, len(ip_addrs) - 1)))

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

  output.append("table_add check_arp arp_present 1 =>")
  output.append("table_add check_arp send_packet 0 =>")
  output.append("table_add check_opcode arp_request 1 =>")
  output.append("table_set_default check_opcode send_packet")

  for j in range(1, nb_hosts+1):
    hex_macid = hex(j).split('x')[-1]
    assert(len(hex_macid) < 3)
    if len(hex_macid) < 2:
      hex_macid = '0' + hex_macid
    dest_mac = "0x0004000000" + hex_macid
    hex_ipid = hex(assigned_addrs[j-1]).split('x')[-1]
    assert(len(hex_ipid) < 3)
    if len(hex_ipid) < 2:
      hex_ipid = '0' + hex_ipid
    dest_ip = "0x0A0000" + hex_ipid
    output.append("table_add handle_arp_request arp_reply " + dest_ip \
                  + " => " + dest_mac)

  output.append("table_set_default handle_arp_request send_packet")

  fname = os.path.dirname(os.path.realpath(__file__)) + '/t03_arp_entries_s%d'%(i+1)
  with open(fname, 'w') as out:
    for line in output:
      out.write(line + '\n')
