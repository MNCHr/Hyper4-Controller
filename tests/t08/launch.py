#!/usr/bin/python

# Generate topo.txt and commands_s*.txt for n switches

import argparse
import sys
import os

import code
from inspect import currentframe, getframeinfo

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))

def parse_args(args):
  parser = argparse.ArgumentParser(description='VIBRANT Launcher')
  parser.add_argument('numdevices', type=int)
  parser.add_argument('--topo', help='name of mininet sim topo file',
                      type=str, default='topo.txt')
  return parser.parse_args(args)

def gen_topo(topofile, numdevices):
  with open(topofile, 'w') as f:
    f.write('switches ' + str(numdevices) + '\n')
    f.write('hosts 4\n')
    f.write('h1 s1\n')
    f.write('h2 s1\n')
    f.write('h3 s' + str(numdevices) + '\n')
    f.write('h4 s' + str(numdevices) + '\n')
    for i in range(numdevices - 1):
      f.write('s' + str(i + 1) + ' s' + str(i + 2) + '\n')

def gen_commands(numdevices):
  cfiles = []
  for i in range(numdevices):
    cfile = 'commands_s' + str(i + 1) + '.txt'
    with open(cfile, 'w') as f:
      # f.write('mc_mgrp_create 1\n')
      # f.write('mc_node_create 17 1 2 3 4\n')
      # f.write('mc_node_associate 1 0\n')
      f.write('table_add check_vibrant vibrant_present 1 =>\n')
      f.write('table_add check_vibrant vibrant_not_present 0 =>\n')
      f.write('table_add dmac broadcast 0xFFFFFFFFFFFF => 5\n')

      if i == 0:
        f.write('table_add dmac local 0x000400000000 => 1\n')
        f.write('table_add dmac2 local 0x000400000000 => 1\n')
      elif i == (numdevices - 1):
        f.write('table_add dmac not_local 0x000400000000 => 3\n')
        f.write('table_add dmac2 not_local 0x000400000000 => 3\n')
      else:
        f.write('table_add dmac not_local 0x000400000000 => 1\n')
        f.write('table_add dmac2 not_local 0x000400000000 => 1\n')

      if i == 0:
        f.write('table_add dmac not_local 0x000400000002 => 3\n')
        f.write('table_add dmac2 not_local 0x000400000002 => 3\n')
      elif i == (numdevices - 1):
        f.write('table_add dmac local 0x000400000002 => 1\n')
        f.write('table_add dmac2 local 0x000400000002 => 1\n')
      else:
        f.write('table_add dmac not_local 0x000400000002 => 2\n')
        f.write('table_add dmac2 not_local 0x000400000002 => 2\n')

      f.write('table_set_default strip_vibrant a_strip_vibrant\n')
      f.write('table_add dmac2 broadcast 0xFFFFFFFFFFFF => 5\n')
      f.write('table_add add_vibrant a_add_vibrant 1 =>\n')
      f.write('table_add add_vibrant _no_op 0 =>\n')
      # f.write('table_set_default filter_egress _drop\n')

    cfiles.append(cfile)
  return cfiles  

def main():
  args = parse_args(sys.argv[1:])
  gen_topo(args.topo, args.numdevices)
  gen_commands(args.numdevices)
      
if __name__ == '__main__':
  main()
