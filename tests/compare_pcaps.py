#!/usr/bin/python

from scapy.all import rdpcap
from scapy.packet import NoPayload

from datetime import datetime
import argparse
import sys

import code


ECHO_REQUEST = 8
ECHO_REPLY = 0
ARP_REQUEST = 1
ARP_REPLY = 2

pkt_types = {('ARP', ARP_REQUEST): 'request',
            ('ARP', ARP_REPLY): 'reply',
            ('ICMP', ECHO_REQUEST): 'request',
            ('ICMP', ECHO_REPLY): 'reply'}

parser = argparse.ArgumentParser(description='Compare pcaps for different sessions')
#parser.add_argument('-t', '--test', help='Test id (e.g., t0X)',
#                    type=str, action=store)
parser.add_argument('-r1', '--run1', help='Path for first run pcap',
                    type=str, action="store")
parser.add_argument('-r2', '--run2', help='Path for second run pcap',
                    type=str, action="store")

args = parser.parse_args(sys.argv[1:])

r1_pkts = rdpcap(args.run1)
r2_pkts = rdpcap(args.run2)

r1_endpoints = {} # {(A (str), B(str)) : [packet_dict]}
r2_endpoints = {} # {(A (str), B(str)) : [packet_dict]}

r1_other = []
r2_other = []

# populate endpoints
for pkts, endpoints in [(r1_pkts, r1_endpoints), (r2_pkts, r2_endpoints)]:
  for pkt in pkts:
    l2_src = pkt.getfieldval('src')
    l2_dst = pkt.getfieldval('dst')

    if pkt.payload.name == 'ARP':
      op = pkt.payload.getfieldval('op')
      pkt_type = pkt_types[('ARP', op)]
      payload_type = 'ARP'
      l3_src = pkt.payload.getfieldval('psrc')
      l3_dst = pkt.payload.getfieldval('pdst')

    elif pkt.payload.name == 'IP':
      payload_type = pkt.payload.payload.name
      if payload_type == 'ICMP':
        op = pkt.payload.payload.getfieldval('type')
        pkt_type = pkt_types[('ICMP', op)]
        l3_src = pkt.payload.getfieldval('src')
        l3_dst = pkt.payload.getfieldval('dst')
      else:
        r1_other.append(pkt)
        continue

    else:
      r1_other.append(pkt)
      continue

    if pkt_type == 'request':
      key = (l3_src, l3_dst)
    elif pkt_type == 'reply':
      key = (l3_dst, l3_src)
    else:
      raise Exception("Error pkt_type: %s" % pkt_type)

    if key not in endpoints:
      endpoints[key] = []
    
    entry = {'t': pkt.time,
             'l3_src': l3_src,
             'l3_dst': l3_dst,
             'type': payload_type,
             'pkt_type': pkt_type}
  
    endpoints[key].append(entry)

mismatches = []

for endpoint_key in r1_endpoints.keys():
  if endpoint_key in r2_endpoints.keys():
    pkts1 = r1_endpoints[endpoint_key]
    pkts2 = r2_endpoints[endpoint_key]
    if len(pkts1) != len(pkts2):
      mismatches.append(str(endpoint_key) + " number of packets: pkts1: %d;" \
                        " pkts2: %d" % (len(pkts1), len(pkts2)))
      del r1_endpoints[endpoint_key]
      del r2_endpoints[endpoint_key]
      continue
    for i in range(len(pkts1)):
      pkt1 = pkts1[i]
      pkt2 = pkts2[i]
      for pktkey in pkt1.keys():
        if pktkey == 't':
          continue
        if pktkey not in pkt2.keys():
          mismatches.append(str(endpoint_key) + "[" + pktkey + " not found in pkt2")
          continue
        if pkt1[pktkey] != pkt2[pktkey]:
          mismatches.append(str(endpoint_key) + "[" + pktkey + "]: pkt1: %s;" \
                            " pkt2: %s" % (pkt1[pktkey], pkt2[pktkey]))
      
    del r1_endpoints[endpoint_key]
    del r2_endpoints[endpoint_key]

for endpoints, fname in [(r1_endpoints, args.run1), (r2_endpoints, args.run2)]:
  for endpoint_key in endpoints.keys():
    mismatches.append(str(endpoint_key) + ' found only in %s' % fname)

if len(mismatches) == 0:
  print('found no mismatches')
else:
  for mismatch in mismatches:
    print(mismatch)
