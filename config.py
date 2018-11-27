#!/usr/bin/python

import argparse
import sys
import subprocess

def parse_manifest(args):

  nodes = []

  with open(args.manifest, "r") as m:
     for line in m:
       if "<emulab:vnode name=" in line:
         node_num = line.split("\"")[1].split("pc")[1]
         nodes.append(node_num)

  return nodes

def parse_args(args):
  
  parser = argparse.ArgumentParser(description='Configure HyPer4/ConViDa evaluation')
  parser.add_argument('--user', help='cloudlab username',
                      type=str, action="store")
  parser.add_argument('--manifest', help='path to cloudlab manifest',
                      type=str, action="store", default="manifest")

  parser.set_defaults(func=parse_manifest)

  return parser.parse_args(args)


def main():
  args = parse_args(sys.argv[1:])
  config_args = ['./config.sh']
  if args.user:
    nodes = args.func(args)
    config_args.append(args.user)
    config_args += nodes
  elif args.manifest:
    print("Error: missing cloudlab username")
    exit()
  
  subprocess.call(config_args)

if __name__ == '__main__':
  main()
