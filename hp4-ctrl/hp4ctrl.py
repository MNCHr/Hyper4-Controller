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

import code

class Controller(object):
  def __init__(self, args):
    self.slices = {} # slice name (str) : Slice
    self.devices = {} # device name (str) : Device
    self.host = args.host
    self.port = args.port
    self.debug = args.debug
    self.slicemgr_commands = ['create_virtual_device',
                              'migrate_virtual_device',
                              'remove_virtual_device',
                              'destroy_virtual_device']

  def handle_request(self, request):
    "Handle a request"
    if len(request) < 2:
      return "Request format: <slice name | admin> <command> [parameter list]"
    requester = request.split()[0]
    command = request.split()[1]
    parameters = [requester] + request.split()[2:]
    if requester not in self.slices and requester != 'admin':
      return "Denied; no slice " + requester
    if (requester != 'admin'
          and command not in self.slicemgr_commands):
      return "Denied; command not available to " + requester

    resp = ""
    try:
      resp = getattr(self, command)(parameters)
    except AttributeError:
      return "Command not found: " + command
    except:
      return "Unexpected error: " + str(sys.exc_info()[0])

    return resp

  def create_device(self, parameters):
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
        return "Error - create_device(" + dev_name + "): " + str(sys.exc_info()[0])

    json = '/home/ubuntu/hp4-src/hp4/hp4.json'
    runtime_CLI.load_json_config(hp4_client, json)
    rta = runtime_CLI.RuntimeAPI(pre, hp4_client)

    if dev_type == 'bmv2_SSwitch':
      self.devices[dev_name] = device.Bmv2_SSwitch(rta, num_entries, ports)
    elif dev_type == 'Agilio':
      self.devices[dev_name] = device.Agilio(rta, num_entries, ports)
    else:
      return 'Error - device type ' + dev_type + ' unknown'

    return "Added device: " + dev_name

  def create_slice(self, parameters):
    "Create a slice"
    hp4slice = parameters[1]
    self.slices[hp4slice] = Slice(hp4slice)
    return "Created slice: " + hp4slice

  def grant_lease(self, parameters):
    code.interact(local=locals())
    hp4slice = parameters[0]

  def create_virtual_device(self, parameters):
    return 'Not implemented yet'

  def migrate_virtual_device(self, parameters):
    return 'Not implemented yet'

  def remove_virtual_device(self, parameters):
    return 'Not implemented yet'

  def handle_translate(self, parameters):
    return 'Not implemented yet'

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
  def __init__(self, args):
    super(ChainController, self).__init__(args)
    self.slicemgr_commands.append('insert')
    self.slicemgr_commands.append('append')
    self.slicemgr_commands.append('remove')

  def handle_request(self, request):
    return super(ChainController, self).handle_request(request)
    
  def insert(self, parameters):
    return 'Not implemented yet'

  def append(self, parameters):
    return 'Not implemented yet'

  def remove(self, parameters):
    return 'Not implemented yet'

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
