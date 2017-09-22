#!/usr/bin/python

import argparse
import sys
import re

import code

parser = argparse.ArgumentParser(description='Pcap Digest Processor')
parser.add_argument('file', help='file to process', type=str, action="store")
args = parser.parse_args(sys.argv[1:])

p = re.compile('id\s[0-9]*')

out = []
idmap = {} # {IPv4 ID field value (int) : remapped integer}
count = 0

with open(args.file) as f:
  for line in f:
    if 'ethertype' in line:
      out.append(p.sub('X', line))
      #m = re.search('id\s[0-9]*', line)
      #pkt_id = int(m.group(0).split()[1])
    else:
      m = re.search('id\s[0-9]*', line)
      pkt_id = int(m.group(0).split()[1])
      if idmap.has_key(pkt_id):
        pass
      else:
        idmap[pkt_id] = count
        count += 1
      out.append(p.sub('id ' + str(idmap[pkt_id]), line))

for line in out:
  print(line)
