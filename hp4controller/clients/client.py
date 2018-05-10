#!/usr/bin/python

import argparse
import sys
import socket
import cmd
import code
# code.interact(local=dict(globals(), **locals()))

BUFFSIZE = 4096

class Client(cmd.Cmd, object):
  prompt = 'HP4$ '
  intro = 'HP4 Controller Client'

  def __init__(self, user='admin', ip='localhost', port=33333, debug=False, **kwargs):
    cmd.Cmd.__init__(self)
    self.user = user
    self.host = ip
    self.port = port
    self.debug = debug

  def send_request(self, request):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((self.host, self.port))
    s.send(request)
    resp = s.recv(BUFFSIZE)
    s.close()
    return resp

  def do_slice_dump(self, line):
    "Display leases and virtual devices in a slice: slice_dump <slice>"
    resp = self.send_request(line + ' slice_dump')
    print(resp)
    
  def do_source(self, line):
    "Source a file: source <file>"
    with open(line, 'r') as f:
      for l in f:
        self.cmdqueue.append(l)

  def do_EOF(self, line):
    print
    return True

class SliceManager(Client):

  def do_slice_dump(self, line):
    "Display leases and virtual devices in a slice: slice_dump"
    resp = super(SliceManager, self).do_slice_dump(self.user)
    print(resp)
    
  def do_vdev_create(self, line):
    "Create virtual device: vdev_create <p4_path> <vdev_name>"
    resp = self.send_request(self.user + ' vdev_create ' + line)
    print(resp)

  def do_vdev_destroy(self, line):
    "Destroy virtual device (remove AND delete): vdev_destroy <virtual device>"
    resp = self.send_request(self.user + ' vdev_destroy ' + line)
    print(resp)

  def do_vdev_dump(self, line):
    "Display all pushed entries in a vdev: vdev_dump <virtual device>"
    resp = self.send_request(self.user + ' vdev_dump ' + line)
    print(resp)

  def do_vdev_info(self, line):
    "Show info about a vdev: vdev_info <virtual device>"
    resp = self.send_request(self.user + ' vdev_info ' + line)
    print(resp)

  def help_vdev_interpret(self):
    print('Interpret API command: vdev_interpret <virtual device> ' \
          + '<\'bmv2\' | \'agilio\'> [--stage|--stage_if_full] <command>')

  def do_vdev_interpret(self, line):
    resp = self.send_request(self.user + ' vdev_interpret ' + line)
    print(resp)

  def help_vdev_interpretf(self):
    print('Interpret API commands in file: interpret_file <virtual device> ' \
          + '<\'bmv2\' | \'agilio\'> [--stage|--stage_if_full] <file>')

  def do_vdev_interpretf(self, line):
    resp = ''
    with open(line.split()[2]) as commands:
      pre = ''
      for command in commands:
        newline = ' '.join(line.split()[0:2]) + ' ' + command
        resp += pre + self.send_request(self.user + ' vdev_interpret ' + newline)
        pre = '\n'
    print(resp)

  def do_vdev_stage_clear(self, line):
    "Clear staged entries: vdev_stage_clear <virtual device>"
    resp = self.send_request(self.user + ' vdev_stage_clear ' + line)
    print(resp)

  def do_vdev_stage_dump(self, line):
    "Display all staged entries in a vdev: vdev_stage_dump <virtual device>"
    resp = self.send_request(self.user + ' vdev_stage_dump ' + line)
    print(resp)

  def do_vdev_stage_flush(self, line):
    "Push all staged entries to physical device: vdev_stage_flush <virtual device>"
    resp = self.send_request(self.user + ' vdev_stage_flush ' + line)
    print(resp)

  def do_vdev_withdraw(self, line):
    "Stage pushed entries & pull virtual device: vdev_withdraw <virtual device>"
    resp = self.send_request(self.user + ' vdev_withdraw ' + line)
    print(resp)

  def help_lease_config_egress(self):
    print("Configure lease egress: lease_config_egress <device> " \
          + "<egress_spec value> mcast <filtered|unfiltered>")

  def do_lease_config_egress(self, line):
    resp = self.send_request(self.user + ' lease_config_egress ' + line)
    print(resp)

  def do_lease_dump(self, line):
    "Display vdev info for each resident vdev: lease_dump <device>"
    resp = self.send_request(self.user + ' lease_dump ' + line)
    print(resp)

  def do_lease_info(self, line):
    "Show info about a lease: lease_info <device>"
    resp = self.send_request(self.user + ' lease_info ' + line)
    print(resp)

  """
  def do_lease(self, line):
    "Call a lease method: lease <device> <method name> <virtual device> [args]"
    resp = self.send_request(self.user + ' lease ' + line)
    print(resp)

  def do_create_virtual_device(self, line):
    "Create virtual device: create_virtual_device <p4_path> <vdev_name>"
    resp = self.send_request(self.user + ' create_virtual_device ' + line)
    print(resp)

  def do_migrate_virtual_device(self, line):
    "Migrate virtual device: migrate_virtual_device <virtual device> <destination device>"
    resp = self.send_request(self.user + ' migrate_virtual_device ' + line)
    print(resp)

  def do_withdraw_virtual_device(self, line):
    "Remove virtual device from current location: withdraw_virtual_device <virtual device>"
    resp = self.send_request(self.user + ' withdraw_virtual_device ' + line)
    print(resp)

  def do_destroy_virtual_device(self, line):
    "Destroy virtual device (remove AND delete): destroy_virtual_device <virtual device>"
    resp = self.send_request(self.user + ' destroy_virtual_device ' + line)
    print(resp)

  def do_interpret(self, line):
    "Interpret API command: interpret <virtual device> <\'bmv2\' | \'agilio\'> <command>"
    resp = self.send_request(self.user + ' interpret ' + line)
    print(resp)

  def do_interpret_file(self, line):
    "Interpret API commands in file: interpret_file <virtual device> <\'bmv2\' | \'agilio\'> <file>"  
    resp = ''
    with open(line.split()[2]) as commands:
      pre = ''
      for command in commands:
        newline = ' '.join(line.split()[0:2]) + ' ' + command
        resp += pre + self.send_request(self.user + ' interpret ' + newline)
        pre = '\n'
    print(resp)

  def do_list_vdevs(self, line):
    "List virtual devices: list_vdevs"
    resp = self.send_request(self.user + ' list_vdevs ' + line)
    print(resp)

  def do_list_vdev(self, line):
    "List details about a virtual device: list_vdev <virtual device>"
    resp = self.send_request(self.user + ' list_vdev ' + line)
    print(resp)

  def do_list_devs(self, line):
    "List devices: list_devs"
    resp = self.send_request(self.user + ' list_devs ' + line)
    print(resp)

  def do_list_vdev_hp4code(self, line):
    resp = self.send_request(self.user + ' list_vdev_hp4code ' + line)
    print(resp)

  def do_list_vdev_hp4rules(self, line):
    resp = self.send_request(self.user + ' list_vdev_hp4rules ' + line)
    print(resp)

  def do_list_vdev_hp4_code_and_rules(self, line):
    resp = self.send_request(self.user + ' list_vdev_hp4_code_and_rules ' + line)
    print(resp)
  """

class ChainSliceManager(SliceManager):

  """
  def do_lease(self, line):
  """
  """insert|append|remove: lease <device> <insert|append|remove|replace> <virtual device> [args]
     \rinsert args: <position> <egress handling mode>
     \rappend args: <egress handling mode: \'etrue\'|\'efalse\'|\'econd\'>
     \rremove args: N/A
     \rreplace args: <new virtual device> <egress handling mode>
     \rconfig_egress: lease <device> config_egress <egress_spec value> mcast <filtered|unfiltered>
     \rinfo: lease <device> info
  """
  """
    resp = self.send_request(self.user + ' lease ' + line)
    print(resp)
  """

  def help_lease_append(self):
    print("Append virtual device to end of chain: lease_append <device> " \
          + "<virtual device> <etrue|efalse|econd>")

  def do_lease_append(self, line):
    resp = self.send_request(self.user + ' lease_append ' + line)
    print(resp)

  def help_lease_insert(self):
    print("Insert virtual device in chain: lease_insert <device> " \
           + "<virtual device> <position> <etrue|efalse|econd>")

  def do_lease_insert(self, line):
    resp = self.send_request(self.user + ' lease_insert ' + line)
    print(resp)

  def help_lease_remove(self):
    print("Remove virtual device from chain: lease_remove <device> " \
          + "<virtual device>")

  def do_lease_remove(self, line):
    resp = self.send_request(self.user + ' lease_remove ' + line)
    print(resp)

  def help_lease_replace(self):
    print("Replace virtual device in chain: lease_replace <device> " \
          + "<virtual device> <new virtual device> <etrue|efalse|econd>")

  def do_lease_replace(self, line):
    resp = self.send_request(self.user + ' lease_replace ' + line)
    print(resp)

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
    c = Administrator(**vars(args))
  else:
    c = ChainSliceManager(**vars(args))
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
