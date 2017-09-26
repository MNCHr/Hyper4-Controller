#!/usr/bin/python

from datetime import datetime
import argparse
import sys

import code

parser = argparse.ArgumentParser(description='Compare pcaps for different sessions')
#parser.add_argument('-t', '--test', help='Test id (e.g., t0X)',
#                    type=str, action=store)
parser.add_argument('-r1', '--run1', help='Path for first run pcap',
                    type=str, action="store")
parser.add_argument('-r2', '--run2', help='Path for second run pcap',
                    type=str, action="store")

args = parser.parse_args(sys.argv[1:])

r1_packets = []

r1_endpoints = {} # {(A (str), B(str)) : [packet_dict]}

def parse_packet(line, endpoints):
  packet = {'t': datetime.strptime(line.split()[0], '%H:%M:%S.%f'),
            'l2_src': line.split()[1],
            'l2_dst': line.split()[3][:-1],
            'ethertype': line.split()[5]}
  if packet['l2_src'] <= packet['l2_dst']:
    key = (packet['l2_src'], packet['l2_dst'])
  else:
    key = (packet['l2_dst'], packet['l2_src'])
  if key not in endpoints:
    endpoints[key] = []
  endpoints[key].append(packet)

with open(args.run1, 'r') as r1:
  for line in r1:
    parse_packet(line, r1_endpoints)

with open(args.run2, 'r') as r2:
  for line in r2:
    parse_packet(line, r2_endpoints)

code.interact(local=dict(globals(), **locals()))
