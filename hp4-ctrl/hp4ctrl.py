#!/usr/bin/python

import argparse
import sys
import runtime_CLI
import socket
import hp4loader
import os
import device
import virtualdevice
from hp4translator import VDevCommand_to_HP4Command

class Controller():
  def __init__(self, args):
    self.slices = {} # slice name (str) : Slice
    self.devices = {} # device name (str) : Device
    self.host = args.host
    self.port = args.port
    self.debug = args.debug

  def handle_request(self, request):
    pass

  def handle_create_device(self, parameters):
    # parameters:
    # <'admin'> <name> <ip_addr> <port> <dev_type: 'bmv2_SSwitch' | 'Agilio'>
    # <pre: 'None' | 'SimplePre' | 'SimplePreLAG'> <# entries> <ports>
    dev_name = parameters[1]
    ip = parameters[2]
    port = parameters[3]
    dev_type = parameters[4]
    pre = parameters[5]
    num_entries = parameters[6]
    ports = parameters[7:]
    prelookup = {'None': 0, 'SimplePre': 1, 'SimplePreLAG': 2}
    
    try:
      hp4_client, mc_client = runtime_CLI.thrift_connect(ip, port,
                  runtime_CLI.RuntimeAPI.get_thrift_services(prelookup[pre]))
    except:
        return "Error - handle_create_device(" + dev_name + "): " + str(sys.exc_info()[0])

    json = '/home/ubuntu/hp4-src/hp4/hp4.json'
    runtime_CLI.load_json_config(hp4_client, json)
    rta = runtime_CLI.RuntimeAPI(pre, hp4_client)
    self.devices[dev_name] = Device(rta, num_entries, ports)
    return "Added device: " + dev_name

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

  def serverloop(self):
    serversocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    serversocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    serversocket.bind((self.host, self.port))
    serversocket.listen(5)

    while True:
      clientsocket = None
      try:
        clientsocket, addr = serversocket.accept()
        self.dbugprint("Got a connection from %s" % str(addr))
        data = clientsocket.recv(1024)
        self.dbugprint(data)
        response = self.handle_request(data)
        clientsocket.sendall(response)
        clientsocket.close()
      except KeyboardInterrupt:
        if clientsocket:
          clientsocket.close()
        serversocket.close()
        self.dbugprint("Keyboard Interrupt, sockets closed")
        break

  def dbugprint(self, msg):
    if self.debug:
      print(msg)

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
  ctrl.dbugprint('Starting server at %s:%d' % (args.host, args.port))
  ctrl.serverloop()

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
