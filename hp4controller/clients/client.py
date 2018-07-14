#!/usr/bin/python

import argparse
import sys
import socket
import readline
import cmd
import atexit
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

BUFFSIZE = 4096

class Client(cmd.Cmd, object):
  
  prompt = 'HP4$ '
  intro = 'HP4 Controller Client'

  def __init__(self, user='admin', ip='localhost', port=33333,
                     debug=False, histfile=".client-history", **kwargs):
    cmd.Cmd.__init__(self)
    self.user = user
    self.host = ip
    self.port = port
    self.debug = debug
    self.syntax = {}
    self.syntax_msg = {}
    self.init_history(histfile)

  def init_history(self, histfile):
    readline.parse_and_bind("tab: complete")
    if hasattr(readline, "read_history_file"):
      try:
        readline.read_history_file(histfile)
      except IOError:
        pass
      atexit.register(self.save_history, histfile)

  def save_history(self, histfile):
    readline.set_history_length(1000)
    readline.write_history_file(histfile)

  def confirm_syntax(self, line, minargs, cmd_syntax):

    if not cmd_syntax:
      return True

    command = line.split()[0]
    numargs = len(line.split()) - 1

    if numargs < minargs:
      print(command + ': ' + self.syntax_msg[command])
      return False

    args = line.split()[1:]

    for i, arg in enumerate(args):
      # don't check args beyond cmd_syntax, e.g., vdev_interpret/f
      if i == len(cmd_syntax):
        return True
      if arg not in cmd_syntax[i]:
        if type(arg) not in cmd_syntax[i]:
          if int in cmd_syntax[i]:
            try:
              int(arg)
            except ValueError as e:
              print(command + ': ' + self.syntax_msg[command])
              return False
          else:
            print(command + ': ' + self.syntax_msg[command])
            return False

    return True


  def debug_print(self, s):
    if self.debug:
      print(s)

  def send_request(self, request):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
      s.connect((self.host, self.port))
    except socket.error as e:
      s.close()
      return 'Could not connect to ' + str(self.host) + ':' + str(self.port)
    s.send(request)
    resp = s.recv(BUFFSIZE)
    s.close()
    return resp

  def do_slice_dump(self, line):
    "Display leases and virtual devices in a slice: slice_dump <slice>"
    resp = self.send_request(line + ' slice_dump')
    self.debug_print(resp)
    
  def do_source(self, line):
    "Source a file: source <file>"
    with open(line, 'r') as f:
      for l in f:
        self.cmdqueue.append(l)

  def do_EOF(self, line):
    self.debug_print('')
    return True

class SliceManager(Client):

  def __init__(self, **kwargs):
    super(SliceManager, self).__init__(**kwargs)
    self.syntax_msg['lease_info'] = '<device>'
    self.syntax['lease_info'] = ([str],)
    self.syntax_msg['lease_dump'] = '<device>'
    self.syntax['lease_dump'] = ([str],)
    self.syntax_msg['lease_config_egress'] = '<device> <egress_spec value> ' \
                                           + 'mcast <filtered|unfiltered>'
    self.syntax['lease_config_egress'] = ([str], [int], ['mcast'],
                                          ['filtered', 'unfiltered'])
    self.syntax_msg['vdev_withdraw'] = '<virtual device>'
    self.syntax['vdev_withdraw'] = ([str],)
    self.syntax_msg['vdev_stage_flush'] = '<virtual device>'
    self.syntax['vdev_stage_flush'] = ([str],)
    self.syntax_msg['vdev_stage_dump'] = '<virtual device>'
    self.syntax['vdev_stage_dump'] = ([str],)
    self.syntax_msg['vdev_stage_clear'] = '<virtual device>'
    self.syntax['vdev_stage_clear'] = ([str],)
    self.syntax_msg['vdev_interpret'] = '<virtual device> ' \
                                      + '<\'bmv2\' | \'agilio\'> ' \
                                      + '[--stage|--stage_if_full] <command>'
    self.syntax['vdev_interpret'] = ([str], ['bmv2', 'agilio'],
                                     ['--stage', '--stage_if_full', str], [str])
    self.syntax_msg['vdev_interpretf'] = '<virtual device> ' \
                                       + '<\'bmv2\' | \'agilio\'> ' \
                                       + '[--stage|--stage_if_full] <file>'
    self.syntax['vdev_interpretf'] = ([str], ['bmv2', 'agilio'],
                                      ['--stage', '--stage_if_full', str], [str])
    self.syntax_msg['slice_dump'] = ''
    self.syntax['slice_dump'] = ()
    self.syntax_msg['vdev_create'] = '<p4_path> <vdev_name>'
    self.syntax['vdev_create'] = ([str], [str])
    self.syntax_msg['vdev_info'] = '<virtual device>'
    self.syntax['vdev_info'] = ([str],)
    self.syntax_msg['vdev_dump'] = '<virtual device>'
    self.syntax['vdev_dump'] = ([str],)
    self.syntax_msg['vdev_destroy'] = '<virtual device>'
    self.syntax['vdev_destroy'] = ([str],)
    self.syntax['list_vdev_hp4code'] = ([str],)
    self.syntax_msg['list_vdev_hp4code'] = '<virtual device>'
    self.syntax['list_vdev_hp4rules'] = ([str],)
    self.syntax_msg['list_vdev_hp4rules'] = '<virtual device>'
    self.syntax['list_vdev_hp4_code_and_rules'] = ([str],)
    self.syntax_msg['list_vdev_hp4_code_and_rules'] = '<virtual device>'

  def do_slice_dump(self, line):
    "Display leases and virtual devices in a slice: slice_dump"
    minargs = 0
    if self.confirm_syntax('slice_dump ' + line, minargs, self.syntax['slice_dump']):
      super(SliceManager, self).do_slice_dump(self.user)
    
  def do_vdev_create(self, line):
    "Create virtual device: vdev_create <p4_path> <vdev_name>"
    minargs = 2
    if self.confirm_syntax('vdev_create ' + line, minargs, self.syntax['vdev_create']):
      resp = self.send_request(self.user + ' vdev_create ' + line)
      self.debug_print(resp)

  def do_vdev_destroy(self, line):
    "Destroy virtual device (remove AND delete): vdev_destroy <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_destroy ' + line, minargs, self.syntax['vdev_destroy']):
      resp = self.send_request(self.user + ' vdev_destroy ' + line)
      self.debug_print(resp)

  def do_vdev_dump(self, line):
    "Display all pushed entries in a vdev: vdev_dump <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_dump ' + line, minargs, self.syntax['vdev_dump']):
      resp = self.send_request(self.user + ' vdev_dump ' + line)
      self.debug_print(resp)

  def do_vdev_info(self, line):
    "Show info about a vdev: vdev_info <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_info ' + line, minargs, self.syntax['vdev_info']):
     resp = self.send_request(self.user + ' vdev_info ' + line)
     self.debug_print(resp)

  def do_list_vdev_hp4code(self, line):
    "List a vdev's hp4code: list_vdev_hp4code <virtual device>"
    minargs = 1
    if self.confirm_syntax('list_vdev_hp4code ' + line, minargs, self.syntax['list_vdev_hp4code']):
      resp = self.send_request(self.user + ' list_vdev_hp4code ' + line)
      self.debug_print(resp)

  def do_list_vdev_hp4rules(self, line):
    "List a vdev's hp4rules: list_vdev_hp4rules <virtual device>"
    minargs = 1
    if self.confirm_syntax('list_vdev_hp4rules ' + line, minargs, self.syntax['list_vdev_hp4rules']):
      resp = self.send_request(self.user + ' list_vdev_hp4rules ' + line)
      self.debug_print(resp)

  def do_list_vdev_hp4_code_and_rules(self, line):
    "List a vdev's hp4 code and rules: list_vdev_hp4_code_and_rules <virtual device>"
    minargs = 1
    if self.confirm_syntax('list_vdev_hp4_code_and_rules ' + line, minargs, self.syntax['list_vdev_hp4_code_and_rules']):
      resp = self.send_request(self.user + ' list_vdev_hp4_code_and_rules ' + line)
      self.debug_print(resp)

  def help_vdev_interpret(self):
    print('Interpret API command: vdev_interpret <virtual device> ' \
          + '<\'bmv2\' | \'agilio\'> [--stage|--stage_if_full] <command>')

  def do_vdev_interpret(self, line):
    minargs = 3
    if self.confirm_syntax('vdev_interpret ' + line, minargs, self.syntax['vdev_interpret']):
      resp = self.send_request(self.user + ' vdev_interpret ' + line)
      self.debug_print(resp)

  def help_vdev_interpretf(self):
    print('Interpret API commands in file: vdev_interpretf ' + self.syntax_msg['vdev_interpretf'])

  def do_vdev_interpretf(self, line):
    minargs = 3
    if self.confirm_syntax('vdev_interpretf ' + line, minargs, self.syntax['vdev_interpretf']):
      resp = ''
      with open(line.split()[2]) as commands:
        pre = ''
        for command in commands:
          newline = ' '.join(line.split()[0:2]) + ' ' + command
          resp += pre + self.send_request(self.user + ' vdev_interpret ' + newline)
          pre = '\n'
      self.debug_print(resp)

  def do_vdev_stage_clear(self, line):
    "Clear staged entries: vdev_stage_clear <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_stage_clear ' + line, minargs, self.syntax['vdev_stage_clear']):
      resp = self.send_request(self.user + ' vdev_stage_clear ' + line)
      self.debug_print(resp)

  def do_vdev_stage_dump(self, line):
    "Display all staged entries in a vdev: vdev_stage_dump <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_stage_dump ' + line, minargs, self.syntax['vdev_stage_dump']):
      resp = self.send_request(self.user + ' vdev_stage_dump ' + line)
      self.debug_print(resp)

  def do_vdev_stage_flush(self, line):
    "Push all staged entries to physical device: vdev_stage_flush <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_stage_flush ' + line, minargs, self.syntax['vdev_stage_flush']):
      resp = self.send_request(self.user + ' vdev_stage_flush ' + line)
      self.debug_print(resp)

  def do_vdev_withdraw(self, line):
    "Stage pushed entries & pull virtual device: vdev_withdraw <virtual device>"
    minargs = 1
    if self.confirm_syntax('vdev_withdraw ' + line, minargs, self.syntax['vdev_withdraw']):
      resp = self.send_request(self.user + ' vdev_withdraw ' + line)
      self.debug_print(resp)

  def help_lease_config_egress(self):
    print("Configure lease egress: lease_config_egress <device> " \
          + "<egress_spec value> mcast <filtered|unfiltered>")

  def do_lease_config_egress(self, line):
    minargs = 4
    if self.confirm_syntax('lease_config_egress ' + line, minargs, self.syntax['lease_config_egress']):
      resp = self.send_request(self.user + ' lease_config_egress ' + line)
      self.debug_print(resp)

  def do_lease_dump(self, line):
    "Display vdev info for each resident vdev: lease_dump <device>"
    minargs = 1
    if self.confirm_syntax('lease_dump ' + line, minargs, self.syntax['lease_dump']):
      resp = self.send_request(self.user + ' lease_dump ' + line)
      self.debug_print(resp)

  def do_lease_info(self, line):
    "Show info about a lease: lease_info <device>"
    minargs = 1
    if self.confirm_syntax('lease_info ' + line, minargs, self.syntax['lease_info']):
      resp = self.send_request(self.user + ' lease_info ' + line)
      self.debug_print(resp)

class ChainSliceManager(SliceManager):

  def __init__(self, **kwargs):
    super(ChainSliceManager, self).__init__(**kwargs)

    self.syntax_msg['lease_append'] = '<device> <virtual device> ' \
                                    + '<etrue|efalse|econd>'
    self.syntax['lease_append'] = ([str], [str], ['etrue', 'efalse', 'econd'])

    self.syntax_msg['lease_insert'] = '<device> <virtual device> <position> ' \
                                    + '<etrue|efalse|econd>'
    self.syntax['lease_insert'] =     ([str], [str], [int], ['etrue', 'efalse', 'econd'])

    self.syntax_msg['lease_remove'] = '<device> <virtual device>'
    self.syntax['lease_remove'] =      ([str], [str])

    self.syntax_msg['lease_replace'] = '<device> <virtual device> ' \
                                     + '<new virtual device> <etrue|efalse|econd>'
    self.syntax['lease_replace'] = ([str], [str], [str], ['etrue', 'efalse', 'econd'])

  def help_lease_append(self):
    print("Append virtual device to end of chain: lease_append " + self.syntax_msg['lease_append'])

  def do_lease_append(self, line):
    minargs = 3
    if self.confirm_syntax('lease_append ' + line, minargs, self.syntax['lease_append']):
      resp = self.send_request(self.user + ' lease_append ' + line)
      self.debug_print(resp)

  def help_lease_insert(self):
    print("Insert virtual device in chain: lease_insert " + self.syntax_msg['lease_insert'])

  def do_lease_insert(self, line):
    minargs = 4
    if self.confirm_syntax('lease_insert ' + line, minargs, self.syntax['lease_insert']):
      resp = self.send_request(self.user + ' lease_insert ' + line)
      self.debug_print(resp)

  def help_lease_remove(self):
    print("Remove virtual device from chain: lease_remove " + self.syntax_msg['lease_remove'])

  def do_lease_remove(self, line):
    minargs = 2
    if self.confirm_syntax('lease_remove ' + line, minargs, self.syntax['lease_remove']):
      resp = self.send_request(self.user + ' lease_remove ' + line)
      self.debug_print(resp)

  def help_lease_replace(self):
    print("Replace virtual device in chain: lease_replace " + self.syntax_msg['lease_replace'])

  def do_lease_replace(self, line):
    minargs = 4
    if self.confirm_syntax('lease_replace ' + line, minargs, self.syntax['lease_replace']):
      resp = self.send_request(self.user + ' lease_replace ' + line)
      self.debug_print(resp)

class Administrator(Client):
  prompt = 'HP4# '

  def __init__(self, **kwargs):
    super(Administrator, self).__init__(**kwargs)

  def do_create_device(self, line):
    """Create device: create_device <name> <ip_addr> <port>
     \r<dev_type: bmv2_SSwitch | Agilio> <pre: \'SimplePre\'|\'SimplePreLAG\'|\'None\'>
     \r<# entries> <ports>
    """
    resp = self.send_request(self.user + ' create_device ' + line)
    self.debug_print(resp)

  def do_list_devices(self, line):
    """List devices: list_devices
     \rtest
    """
    resp = self.send_request(self.user + ' list_devices ' + line)
    self.debug_print(resp)

  def do_create_slice(self, line):
    "Create slice: create_slice <slice>"
    resp = self.send_request(self.user + ' create_slice ' + line)
    self.debug_print(resp)

  def do_list_slices(self, line):
    "List slices: list_slices [-d for detail]"
    resp = self.send_request(self.user + ' list_slices ' + line)
    self.debug_print(resp)

  def do_grant_lease(self, line):
    "Grant lease (slice access to a device): grant_lease <slice> <device> <entry limit> <comp subclass> <ports>"
    resp = self.send_request(self.user + ' grant_lease ' + line)
    self.debug_print(resp)

  def do_revoke_lease(self, line):
    "Revoke lease: revoke_lease <slice> <device>"
    resp = self.send_request(self.user + ' revoke_lease ' + line)
    self.debug_print(resp)

  def do_reset_device(self, line):
    "Reset a device: reset_device <device>"
    resp = self.send_request(self.user + ' reset_device ' + line)
    self.debug_print(resp)

  def do_set_defaults(self, line):
    "Set device defaults: set_defaults <device>"
    resp = self.send_request(self.user + ' set_defaults ' + line)
    self.debug_print(resp)

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
