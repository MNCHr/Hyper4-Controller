#!/usr/bin/python

import argparse
import sys
import runtime_CLI
import socket
import hp4loader
import os
import virtualdevice
from hp4translator import VDevCommand_to_HP4Command

class Controller():
  def __init__(self):
    self.slices = {} # slice name (str) : Slice
    self.devices = {} # device name (str) : Device

  def handle_request(self, request):
    pass

  def handle_create_device(self, parameters):
    # parameters: dev_name, ip_addr, port, num_ifaces, dev_type
    #"Create device: create_device <ip_addr> <port> <dev_type: bmv2_SSwitch | Agilio> <ports>"
    dev_name = parameters[1]
    ip = parameters[2]
    port = parameters[3]
    dev_type = parameters[4]
    

  def handle_create_slice(self, parameters):
    "Create a slice"
    hp4slice = parameters[1]
    self.slices[hp4slice] = Slice(hp4slice)
    return "Added slice: " + hp4slice

  def handle_create_lease(self):
    pass

  def handle_create_vdev(self):
    pass

  def handle_migrate_vdev(self):
    pass

  def handle_delete_vdev(self):
    pass

  def handle_translate(self):
    pass

class ChainController(Controller):
  def handle_insert(self):
    pass
  def handle_append(self):
    pass
  def handle_remove(self):
    pass

class Slice():
  def __init__(self, name):
    self.name = name
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}

class Lease():
  def __init__(self, dev, memory_limit):
    self.device = dev
    self.memory_limit = memory_limit
    self.memory_usage = 0
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}

  def send_command(self, p4cmd):
    return dev.send_command(dev.command_to_string(p4cmd))

def server(args):
  ctrl = ChainController(args)
  ctrl.add_user([])
  ctrl.serverloop(args.host, args.port)

def parse_args(args):
  class ActionToPreType(argparse.Action):
    def __init__(self, option_strings, dest, nargs=None, **kwargs):
      if nargs is not None:
        raise ValueError("nargs not allowed")
      super(ActionToPreType, self).__init__(option_strings, dest, **kwargs)

    def __call__(self, parser, namespace, values, option_string=None):
      assert(type(values) is str)
      setattr(namespace, self.dest, PreType.from_str(values))

  parser = argparse.ArgumentParser(description='HyPer4 Control')
  parser.add_argument('--debug', help='turn on debug mode',
                      action='store_true')

  parser.add_argument('--host', help='host/ip for Controller',
                      type=str, action="store", default='localhost')
  parser.add_argument('--port', help='port for Controller',
                      type=int, action="store", default=33333)

  parser.set_defaults(func=server)

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  args.func(args)

if __name__ == '__main__':
  main()
