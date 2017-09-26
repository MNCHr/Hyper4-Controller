#!/usr/bin/python

import argparse
import sys

parser = argparse.ArgumentParser(description='Generate pingall mininet script')
parser.add_argument('--numswitches', help='Number of switches',
                    type=int, action="store", default=3)
parser.add_argument('--numhosts', help='Number of hosts',
                    type=int, action="store")
parser.add_argument('--hostsperswitch', help='Number of hosts',
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
  nb_hosts = args.numhosts

else: #args.hostsperswitch:
  nb_hosts = args.hostsperswitch * args.numswitches

nb_switches = args.numswitches
assert(nb_hosts % nb_switches == 0)

with open("%s/%s_pairpings"%(args.test, args.test), 'w') as out:
  for i in range(1, nb_hosts):
    for j in range(i + 1, nb_hosts + 1):
      out.write('h%d ping h%d -c 1 -W 1 &\n' % (i, j))
      out.write('h%d ping h%d -c 1 -W 1 &\n' % (j, i))
