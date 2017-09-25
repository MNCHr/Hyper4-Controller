#!/usr/bin/python

import argparse
import sys
import random

parser = argparse.ArgumentParser(description='Generate topo.txt')
parser.add_argument('--seed', help='Seed for pseudorandom numbers',
                    type=int, action="store", default=None)
parser.add_argument('--numswitches', help='Number of switches',
                    type=int, action="store", default=3)
parser.add_argument('--numhosts', help='Total number of hosts',
                    type=int, action="store")
parser.add_argument('--hostsperswitch', help='Number of hosts per switch',
                    type=int, action="store")
parser.add_argument('--test', help='Name of test',
                    type=str, action="store", default="t0")

args = parser.parse_args(sys.argv[1:])

if args.numhosts and args.hostsperswitch:
  raise parser.error("--numhosts incompatible with --hostsperswitch")

if not args.numhosts and not args.hostsperswitch:
  raise parser.error("must supply either --numhosts or --hostsperswitch")

if args.numhosts:
  assert(args.numhosts % args.numswitches == 0)
  hps = args.numhosts / args.numswitches

else: #args.hostsperswitch:
  hps = args.hostsperswitch

output = []
output.append('switches %d\n' % args.numswitches)
output.append('hosts %d\n' % (hps * args.numswitches))

for i in range(1, args.numswitches + 1):
  for j in range(1, hps + 1):
    hid = j + (i - 1)*hps
    output.append("h%d s%d\n" % (hid, i))

for i in range(1, args.numswitches):
  for j in range(i + 1, args.numswitches + 1):
    output.append("s%d s%d\n" % (i, j))

with open("%s/topo.txt"%args.test, 'w') as out:
  for line in output:
    out.write(line)
