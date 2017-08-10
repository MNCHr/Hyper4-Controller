#!/usr/bin/python

import argparse
import sys
import socket
import cmd

class Client(cmd.Cmd):
  prompt = 'HP4$ '
  intro = 'HP4 Controller Client'

  def __init__(self, args):
    cmd.Cmd.__init__(self)

  def send_request(self, request):
    pass

  def do_EOF(self, line):
    print
    return True

class SliceManager(Client):
  def __init__(self):
    pass
  def do_create_virtual_device(self, line):
    "Create virtual device"
    pass
  def do_migrate_virtual_device(self, line):
    "Migrate virtual device: migrate_virtual_device <virtual device> <destination device>"
    pass
  def do_delete_virtual_device(self, line):
    pass

class ChainSliceManager(SliceManager):
  def __init__(self):
    pass
  def do_insert(self, line):
    pass
  def do_append(self, line):
    pass
  def do_remove(self, line):
    pass

class Administrator(Client):
  prompt = 'HP4# '

  def do_create_device(self, line):
    pass
  def do_list_devices(self, line):
    "List devices"
    pass
  def do_create_slice(self, line):
    "Create slice"
    pass
  def do_list_slices(self, line):
    "List slices"
    pass
  def do_grant_lease(self, line):
    "Grant lease (slice access to a device): grant_lease <slice> <device> <memory limit> <ports>"
    pass
  def do_revoke_lease(self, line):
    "Revoke lease"
    pass
  def do_reset_device(self, line):
    "Reset a device: reset_device <device>"
    pass
  def do_set_defaults(self, line):
    "Set device defaults: set_defaults <device>"
    pass

def client(args):
  c = Administrator(args)
  c.cmdloop()

def parse_args(args):
  parser = argparse.ArgumentParser(description='HyPer4 Client')

  parser.set_defaults(func=client)

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  args.func(args)

if __name__ == '__main__':
  main()
