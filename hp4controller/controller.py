#!/usr/bin/python

import argparse
import sys
import runtime_CLI
from sswitch_CLI import SimpleSwitchAPI
import socket
import os
import devices.device as device
from virtualdevice.virtualdevice import VirtualDevice, VirtualDeviceFactory
from virtualdevice.interpret import Interpretation
import virtualdevice.p4rule as p4rule
from p4command import P4Command
import textwrap
import leases.lease
from errors import AddRuleError, ModRuleError, DeleteRuleError

import code
# code.interact(local=dict(globals(), **locals()))

# TODO (Global): refactor to reduce degree of coupling
#  methods reach too deep into other class dependency trees to accomplish tasks

class Controller(object):
  def __init__(self, args):
    self.slices = {} # slice name (str) : Slice
    self.devices = {} # device name (str) : Device
    self.host = args.host
    self.port = args.port
    self.debug = args.debug
    self.admin_commands = ['create_device',
                           'list_devices',
                           'create_slice',
                           'list_slices',
                           'grant_lease',
                           'revoke_lease',
                           'reset_device',
                           'set_defaults']
    self.next_vdev_ID = 1
    self.vdev_factory = VirtualDeviceFactory()

  def assign_vdev_ID(self):
    vdev_ID = self.next_vdev_ID
    self.next_vdev_ID += 1
    return vdev_ID

  def handle_request(self, request):
    "Handle a request"
    if len(request) < 2:
      return "Request format: <slice name | admin> <command> [parameter list]"
    requester = request.split()[0]
    command = request.split()[1]
    self.dbugprint("Request: " + request)
    self.dbugprint("Command: " + command)
    parameters = [requester] + request.split()[2:]
    if ((requester not in self.slices) and (requester != 'admin')):
      return "Denied; no slice " + requester
    if ((requester != 'admin')
          and (command in self.admin_commands)):
      return "Denied; command not available to " + requester

    resp = ""

    if requester == 'admin':
      try:
        resp = getattr(self, command)(parameters)
      except AttributeError as e:
        return "AttributeError(handle_request - " + command + "): " + str(e)
      except Exception as e:
        return "Unexpected error: " + str(e)
    elif command == 'create_virtual_device':
      resp = self.create_virtual_device(parameters)
    else:
      resp = self.slices[requester].handle_request(request.split()[1:])

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
    max_entries = int(parameters[6])
    ports = parameters[7:]
    prelookup = {'None': runtime_CLI.PreType.None,
                 'SimplePre': runtime_CLI.PreType.SimplePre,
                 'SimplePreLAG': runtime_CLI.PreType.SimplePreLAG}

    services = runtime_CLI.RuntimeAPI.get_thrift_services(prelookup[pre])
    services.extend(SimpleSwitchAPI.get_thrift_services())

    try:
      std_client, mc_client, sswitch_client = runtime_CLI.thrift_connect(ip, port, services)
    except:
        return "Error - create_device(" + dev_name + "): " + str(sys.exc_info()[0])

    # TODO: fix this
    json = '/home/ubuntu/hp4-src/hp4/hp4.json'
    runtime_CLI.load_json_config(std_client, json)
    rta = SimpleSwitchAPI(prelookup[pre], std_client, mc_client, sswitch_client)

    # TODO: fix this; Controller must not be required to know every Device subclass
    if dev_type == 'bmv2_SSwitch':
      self.devices[dev_name] = device.Bmv2_SSwitch(rta, max_entries, ports, ip, port)
    elif dev_type == 'Agilio':
      self.devices[dev_name] = device.Agilio(rta, max_entries, ports, ip, port)
    else:
      return 'Error - device type ' + dev_type + ' unknown'

    self.dbugprint("Reached return statement")
    return "Added device: " + dev_name

  def create_slice(self, parameters):
    "Create a slice"
    hp4slice = parameters[1]
    self.slices[hp4slice] = Slice(hp4slice)
    return "Created slice: " + hp4slice

  def list_slices(self, parameters):
    "List slices"
    # parameters:
    # <'admin'> [-d for detail]
    message = ''
    ##first = True
    for hp4slice in self.slices:
      #if first == False:
      message += '\n'
      #else:
      #  first = False
      message += hp4slice
      first = True
      for dev in self.slices[hp4slice].leases:
        if first == True:
          message += '\n'
        else:
          first = False

        message += '  ' + dev + ':'
        leaseinfo = str(self.slices[hp4slice].leases[dev]).splitlines()
        for line in leaseinfo:
          message += '\n    ' + line

    return message

  def list_devices(self, parameters):
    "List devices"
    # parameters:
    # <'admin'>
    message = ''
    first = True
    for hp4devicename in self.devices:
      if first == False:
        message += '\n'
      else:
        first = False
      hp4device = self.devices[hp4devicename]
      message += hp4devicename
      for line in str(hp4device).splitlines():
        message += '\n  ' + line

    return message

  def grant_lease(self, parameters):
    # parameters:
    # <'admin'> <slice> <device> <memory limit> <compclassname> <ports>
    hp4slice = parameters[1]
    dev_name = parameters[2]
    entry_limit = int(parameters[3])
    leaseclassname = parameters[4]
    ports = parameters[5:]

    # verify request:
    if hp4slice not in self.slices:
      return 'Error: no slice ' + hp4slice

    if dev_name not in self.devices:
      return 'Error: no device ' + dev_name

    if (entry_limit > (self.devices[dev_name].max_entries
                       - self.devices[dev_name].reserved_entries)):
      return 'Error: memory request exceeds memory available'

    for port in ports:
      if port not in self.devices[dev_name].phys_ports_remaining:
        return 'Error: port ' + port + ' not available'
    # all ports available; reserve
    for port in ports:
      self.devices[dev_name].phys_ports_remaining.remove(port)
    self.devices[dev_name].reserved_entries += entry_limit

    leaseclass = getattr(leases.lease, leaseclassname)

    self.slices[hp4slice].leases[dev_name] = leaseclass(dev_name, self.devices[dev_name],
                                                   entry_limit, ports)

    return 'Lease granted; ' + hp4slice + ' given access to ' + dev_name

  def revoke_lease(self, parameters):
    # parameters:
    # <'admin'> <slice> <device>
    hp4slice = parameters[1]
    dev_name = parameters[2]
    lease = self.slices[hp4slice].leases[dev_name]

    lease.revoke()

    del self.slices[hp4slice].leases[dev_name]

    return 'Lease revoked: ' + hp4slice + ' lost access to ' + dev_name

  def reset_device(self, parameters):
    # parameters:
    # <'admin'> <device>
    dev_name = parameters[1]
    for hp4slice in self.slices:
      if dev_name in self.slices[hp4slice].leases:
        self.revoke_lease(['admin', hp4slice, dev_name])
    
    return 'Device reset: ' + dev_name

  def create_virtual_device(self, parameters):
    # invoke loader
    # parameters:
    # <slice_name> <program_path> <vdev_name>
    hp4slice = parameters[0]
    program_path = parameters[1]
    vdev_name = parameters[2]
    vdev_ID = self.assign_vdev_ID()

    vdev = self.vdev_factory.create_vdev(vdev_name, vdev_ID, program_path)
    self.slices[hp4slice].vdevs[vdev_name] = vdev
    
    return 'Virtual device ' + vdev_name + ' created'

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
        data = clientsocket.recv(4096)
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

class Slice():
  def __init__(self, name):
    self.name = name
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}
    self.leases = {} # {dev_name (string): lease (Lease)}

  def handle_request(self, parameters):
    # parameters:
    # <command> <command parameters>
    command = parameters[0]
    if command == 'lease':
      dev_name = parameters[1]
      lease = self.leases[dev_name]
      if parameters[2] == 'config_egress':
        return lease.handle_request(parameters[2:])
      elif parameters[2] == 'replace':
        vdev_name = parameters[3]
        new_vdev_name = parameters[4]
        args = (self.vdevs[vdev_name], self.vdevs[new_vdev_name])
        return lease.handle_request(parameters[2:], *args)
      else:
        vdev_name = parameters[3]
        args = (self.vdevs[vdev_name],)
        return lease.handle_request(parameters[2:], *args)
    else:
      try:
        resp = getattr(self, command)(parameters[1:])
      except AttributeError as e:
        return "AttributeError(handle_request - " + command + "): " + str(e)
      except Exception as e:
        return "Unexpected error: " + str(e)
      return resp

  def list_vdevs(self, parameters):
    resp = ""
    for vdev_name in self.vdevs:
      vdev = self.vdevs[vdev_name]
      resp += vdev_name + '@' + vdev.dev_name + '\n'
    return resp

  def list_vdev(self, parameters):
    return str(self.vdevs[parameters[0]])

  def list_vdev_hp4code(self, parameters):
    vdev = self.vdevs[parameters[0]]
    return vdev.str_hp4code()

  def list_vdev_hp4rules(self, parameters):
    vdev = self.vdevs[parameters[0]]
    return vdev.str_hp4rules()

  def list_vdev_hp4_code_and_rules(self, parameters):
    vdev = self.vdevs[parameters[0]]
    return vdev.str_hp4_code_and_rules()

  def list_devs(self, parameters):
    resp = "device(used/allocated)\tvdev chain\n"
    for dev_name in self.leases:
      lease = self.leases[dev_name]
      resp += dev_name + '(' + str(lease.entry_usage) + '/' \
              + str(lease.entry_limit) + '): ' + str(lease) + '\n'
    return resp[0:-1]

  """
  def migrate_virtual_device(self, parameters):
    # parameters:
    # <vdev_name> <dest device>
    vdev_name = parameters[0]
    dest_dev_name = parameters[1]

    # validate request
    # - validate vdev_name
    if vdev_name not in self.vdevs:
      return 'Error - ' + vdev_name + ' not a valid virtual device'
    # - validate dest_dev_name
    if dest_dev_name not in self.leases:
      return 'Error - no lease for ' + dest_dev_name

    # - validate lease has sufficient entries
    vdev = self.vdevs[vdev_name]
    vdev_entries = len(vdev.hp4code) + len(vdev.hp4_code_and_rules)
    entries_available = (self.leases[dest_dev_name].entry_limit
                       - self.leases[dest_dev_name].entry_usage)
    if (vdev_entries > entries_available):
      return 'Error - request(' + str(vdev_entries) + ') exceeds entries \
              available(' + entries_available + ') for lease on ' + dest_dev_name

    src_dev_name = self.vdev_locations[vdev_name]
    if src_dev_name in self.leases:
      self.leases[src_dev_name].withdraw_vdev(vdev_name)
    # self.leases[dest_dev_name].load_vdev(vdev_name, vdev)
    self.vdev_locations[vdev_name] = dest_dev_name

    return 'Virtual device ' + vdev_name + ' migrated to ' + dest_dev_name
  """

  """
  def withdraw_virtual_device(self, parameters):
    vdev_name = parameters[0]
    dev_name = self.vdev[vdev_name].dev_name
    self.leases[dev_name].withdraw_vdev(vdev_name)

    return 'Virtual device ' + vdev_name + ' withdrawn from ' + dev_name
  """

  def destroy_virtual_device(self, parameters):
    pass

  def interpret(self, parameters):
    # TODO: Fix the native -> hp4 rule handle confusion.  Need to track
    #  virtual (native) rule handles to support table_delete and table_modify
    #  commands.
    # parameters:
    # <slice name> <virtual device> <style: 'bmv2' | 'agilio'> <command>
    print(parameters)
    vdev_name = parameters[0]
    style = parameters[1]
    vdev_command_str = ' '.join(parameters[2:])
    if style == 'bmv2':
      p4command = device.Bmv2_SSwitch.string_to_command(vdev_command_str)
    elif style == 'agilio':
      p4command = device.Agilio.string_to_command(vdev_command_str)
    else:
      return 'Error - ' + style + ' not one of (\'bmv2\', \'agilio\')'
    if vdev_name not in self.vdevs:
      return 'Error - ' + vdev_name + ' not a recognized virtual device'
    vdev = self.vdevs[vdev_name]
    hp4commands = vdev.interpret(p4command)
    #print("CHECKPOINT ALPHA")

    dev_name = vdev.dev_name

    # accounting
    entries_available = (self.leases[dev_name].entry_limit
                       - self.leases[dev_name].entry_usage)
    diff = 0
    for hp4command in hp4commands:
      if hp4command.command_type == 'table_add':
        diff += 1
      elif hp4command.command_type == 'table_delete':
        diff -= 1
    if diff > entries_available:
      return 'Error - entries net increase(' + str(diff) \
           + ') exceeds availability(' + str(entries_available) + ')'

    #print("CHECKPOINT BRAVO")

    # push hp4 rules, collect handles, update hp4-facing ruleset
    hp4_rule_keys = [] # list of (table, action, handle) tuples
    for hp4command in hp4commands:
      # return value should be handle for all commands
      hp4handle = int(self.leases[dev_name].send_command(hp4command))
      table = hp4command.attributes['table']
      if hp4command.command_type == 'table_add' or hp4command.command_type == 'table_modify':
        action = hp4command.attributes['action']
        if hp4command.command_type == 'table_add':
          rule = p4rule.P4Rule(table, action,
                               hp4command.attributes['mparams'],
                               hp4command.attributes['aparams'])
        else: # 'table_modify'
          mparams = vdev.hp4_code_and_rules[(table, hp4handle)].mparams
          rule = p4rule.P4Rule(table, action,
                               mparams,
                               hp4command.attributes['aparams'])
        vdev.hp4rules[(table, hp4handle)] = rule
        vdev.hp4_code_and_rules[(table, hp4handle)] = rule
      else: # command_type == 'table_delete'
        del vdev.hp4_code_and_rules[(table, hp4handle)]
        del vdev.hp4rules[(table, hp4handle)]
      # accounting
      if hp4command.command_type == 'table_add':
        self.leases[dev_name].entry_usage += 1
        hp4_rule_keys.append((table, action, hp4handle))
      elif hp4command.command_type == 'table_modify':
        hp4_rule_keys.append((table, action, hp4handle))
      elif hp4command.command_type == 'table_delete':
        self.leases[dev_name].entry_usage -= 1

    #print("CHECKPOINT CHARLIE")

    # account for origin rule: handle, hp4 rules & hp4 handles
    table = p4command.attributes['table']
    if p4command.command_type == 'table_add':
      # new Origin_to_HP4Map w/ new hp4_rule_keys list
      rule = p4rule.P4Rule(table, p4command.attributes['action'],
                           p4command.attributes['mparams'],
                           p4command.attributes['aparams'])
      # TODO: redo this properly
      match_ID = int(hp4commands[0].attributes['aparams'][1])
      vdev.origin_table_rules[(table, match_ID)] = \
                                         Interpretation(rule, match_ID, hp4_rule_keys)

    elif p4command.command_type == 'table_modify':
      # update interpretation origin rule
      match_ID = p4command.attributes['handle']
      interpretation = vdev.origin_table_rules[(table, match_ID)]
      rule = p4rule.P4Rule(table, p4command.attributes['action'],
                           interpretation.origin_rule.mparams,
                           p4command.attributes['aparams'])

      vdev.origin_table_rules[(table, match_ID)] = \
                                        Interpretation(rule, match_ID, hp4_rule_keys)

    elif p4command.command_type == 'table_delete':
      handle = p4command.attributes['handle']
      del vdev.origin_table_rules[(table, handle)]

    #print("CHECKPOINT DELTA")

    return 'Interpreted: ' + vdev_command_str + ' for ' + vdev_name + ' on ' + dev_name

class CompTypeException(Exception):
  pass

def server(args):
  ctrl = Controller(args)
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
