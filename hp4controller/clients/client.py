#!/usr/bin/python

import argparse
import sys
import socket
import cmd

BUFFSIZE = 1024

class Client(cmd.Cmd):
  prompt = 'HP4$ '
  intro = 'HP4 Controller Client'

  def __init__(self, args):
    cmd.Cmd.__init__(self)
    self.user = args.user
    self.host = args.ip
    self.port = args.port
    self.debug = args.debug

  def send_request(self, request):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((self.host, self.port))
    s.send(request)
    resp = s.recv(BUFFSIZE)
    s.close()
    return resp

  def do_EOF(self, line):
    print
    return True

class SliceManager(Client):

  def do_lease(self, line):
    "Call a lease method: lease <device> <method name> <virtual device> [args]"
    resp = self.send_request(self.user + ' lease ' + line)
    print(resp)

  def do_create_virtual_device(self, line):
    "Create virtual device: create_virtual_device <p4_path> <vdev_name>"
    resp = self.send_request(self.user + ' create_virtual_device ' + line)
    print(resp)

  """
  def do_migrate_virtual_device(self, line):
    "Migrate virtual device: migrate_virtual_device <virtual device> <destination device>"
    resp = self.send_request(self.user + ' migrate_virtual_device ' + line)
    print(resp)

  def do_withdraw_virtual_device(self, line):
    "Remove virtual device from current location: withdraw_virtual_device <virtual device>"
    resp = self.send_request(self.user + ' withdraw_virtual_device ' + line)
    print(resp)
  """

  def do_destroy_virtual_device(self, line):
    "Destroy virtual device (remove AND delete): destroy_virtual_device <virtual device>"
    resp = self.send_request(self.user + ' destroy_virtual_device ' + line)
    print(resp)

  def do_translate(self, line):
    "Translate API command: translate <virtual device> <\'bmv2\' | \'agilio\'> <command>"
    resp = self.send_request(self.user + ' translate ' + line)
    print(resp)

class ChainSliceManager(SliceManager):

  def do_lease(self, line):
    """insert|append|remove: lease <device> <insert|append|remove> <virtual device> [args]
     \rinsert args: <position> <egress handling mode>
     \rappend args: <egress handling mode: \'etrue\'|\'efalse\'|\'econd\'>
     \rremove args: N/A
    """
    resp = self.send_request(self.user + ' lease ' + line)
    print(resp)

  """
  def do_lease_insert(self, line):
    "Insert virtual device: insert <virtual device> <position> <egress handling mode>"
    # <slice name> lease <device name> insert
    resp = self.send_request(self.user + ' lease insert ' + line)
    print(resp)

  def do_append(self, line):
    "Append virtual device: append <virtual device> <egress handling mode>"
    resp = self.send_request(self.user + ' append ' + line)
    print(resp)

  def do_remove(self, line):
    "Remove virtual device: remove <virtual device>"
    resp = self.send_request(self.user + ' remove ' + line)
    print(resp)
  """

class Administrator(Client):
  prompt = 'HP4# '

  def do_create_device(self, line):
    """Create device: create_device <name> <ip_addr> <port>
     \r<dev_type: bmv2_SSwitch | Agilio> <pre: \'SimplePre\'|\'SimplePreLAG\'|\'None\'>
     \r<# entries> <ports>
    """
    resp = self.send_request(self.user + ' create_device ' + line)
    print(resp)

  def do_list_devices(self, line):
    """List devices: list_devices
     \rtest
    """
    resp = self.send_request(self.user + ' list_devices ' + line)
    print(resp)

  def do_create_slice(self, line):
    "Create slice: create_slice <slice>"
    resp = self.send_request(self.user + ' create_slice ' + line)
    print(resp)

  def do_list_slices(self, line):
    "List slices: list_slices [-d for detail]"
    resp = self.send_request(self.user + ' list_slices ' + line)
    print(resp)

  def do_grant_lease(self, line):
    "Grant lease (slice access to a device): grant_lease <slice> <device> <entry limit> <comp subclass> <ports>"
    resp = self.send_request(self.user + ' grant_lease ' + line)
    print(resp)

  def do_revoke_lease(self, line):
    "Revoke lease: revoke_lease <slice> <device>"
    resp = self.send_request(self.user + ' revoke_lease ' + line)
    print(resp)

  def do_reset_device(self, line):
    "Reset a device: reset_device <device>"
    resp = self.send_request(self.user + ' reset_device ' + line)
    print(resp)

  def do_set_defaults(self, line):
    "Set device defaults: set_defaults <device>"
    resp = self.send_request(self.user + ' set_defaults ' + line)
    print(resp)

def client(args):
  if args.user == 'admin':
    c = Administrator(args)
  else:
    c = ChainSliceManager(args)
  if args.startup:
    with open(args.startup) as commands:
      for command in commands:
        c.onecmd(command)
  c.cmdloop()

def parse_args(args):
  parser = argparse.ArgumentParser(description='HyPer4 Client')
  parser.add_argument('--debug', help='turn on debug mode',
                      action='store_true')
  parser.add_argument('--ip', help='ip of Controller',
                      type=str, action="store", default="localhost")
  parser.add_argument('--port', help='port for Controller',
                      type=int, action="store", default=33333)
  parser.add_argument('--startup', help='file with commands to run at startup',
                      type=str, action="store")
  parser.add_argument('user', help='<slice name> | \'admin\'', type=str, action="store")
  parser.set_defaults(func=client)

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  args.func(args)

if __name__ == '__main__':
  main()
