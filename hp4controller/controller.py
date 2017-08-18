#!/usr/bin/python

import argparse
import sys
import runtime_CLI
import socket
import os
import devices.device as device
from virtualdevice.virtualdevice import VirtualDevice, VirtualDeviceFactory
from virtualdevice.interpret import Interpretation
from p4command import P4Command
#import p4rule
import textwrap
from compositions.composition import Chain
from errors import AddRuleError, ModRuleError, DeleteRuleError

import code

class Lease():
  def __init__(self, dev, entry_limit, ports, comp_type):
    self.device = dev
    self.entry_limit = entry_limit
    self.entry_usage = 0
    self.ports = ports
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}
    if comp_type == 'chain':
      self.composition = Chain()
    elif comp_type == 'dag':
      pass
    elif comp_type == 'virtualnetwork':
      pass
    else:
      raise CompTypeException("invalid comp type: " + comp_type)

  def load_vdev(self, vdev_name, vdev):
    "Load virtual device onto physical device"
    for rule in vdev.hp4code:
      try:
        table = rule.table
        handle = self.device.do_table_add(rule)
        vdev.hp4_table_rules[(table, handle)] = rule
      except AddRuleError as e:
        # remove all entries already added
        code.interact(local=locals())
        for table, h in vdev.hp4_table_rules.keys():
          rule_identifier = table + ' ' + str(h)
          self.device.do_table_delete(rule_identifier)
          del vdev.hp4_table_rules[(table, h)]
        raise AddRuleError('Lease::load_vdev failed for ' + vdev_name)

    self.entry_usage += len(vdev.hp4code)
    self.vdevs[vdev_name] = vdev

  def withdraw_vdev(self, vdev_name):
    "Remove virtual device from Lease (does not destroy virtual device)"
    num_entries = len(self.vdevs[vdev_name].hp4_table_rules)

    # pull all virtual device related rules from device
    for table, handle in self.vdevs[vdev_name].hp4_table_rules.keys():
      rule_identifier = table + ' ' + str(handle)
      self.device.do_table_delete(rule_identifier)
    self.vdevs[vdev_name].hp4_table_rules = {}

    self.entry_usage -= num_entries

    # if applicable, remove vdev from composition
    if vdev_name in self.composition.vdevs:
      self.composition.remove(vdev_name)

    # update vdev.dev_name
    self.vdevs[vdev_name].dev_name = 'none'
    # make lease forget about it (Lease's owning Slice still has it)
    del self.vdevs[vdev_name]

  def send_command(self, p4cmd):
    return dev.send_command(dev.command_to_string(p4cmd))

  def __str__(self):
    ret = 'entry usage/limit: ' + str(self.entry_usage) + '/' \
                                + str(self.entry_limit) + '\n'
    ret += 'ports:' + str(self.ports) + '\n'
    ret += 'virtual devices:\n'
    for vdev in self.vdevs:
      ret += ' ' + vdev + '\n'
    ret += 'composition: ' + str(self.composition)
    return ret

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
    parameters = [requester] + request.split()[2:]
    if requester not in self.slices and requester != 'admin':
      return "Denied; no slice " + requester
    if (requester != 'admin'
          and command not in self.slicemgr_commands):
      return "Denied; command not available to " + requester

    resp = ""
    try:
      resp = getattr(self, command)(parameters)
    except AttributeError as e:
      return "AttributeError(handle_request - " + command + "): " + str(e)
    except Exception as e:
      return "Unexpected error: " + str(e)

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
    # <'admin'> <slice> <device> <memory limit> <ports>
    hp4slice = parameters[1]
    dev_name = parameters[2]
    entry_limit = int(parameters[3])
    ports = parameters[4:]

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

    self.slices[hp4slice].leases[dev_name] = Lease(self.devices[dev_name],
                                                   entry_limit, ports, 'chain')

    return 'Lease granted; ' + hp4slice + ' given access to ' + dev_name

  def revoke_lease(self, parameters):
    # parameters:
    # <'admin'> <slice> <device>
    hp4slice = parameters[1]
    dev_name = parameters[2]
    lease = self.slices[hp4slice].leases[dev_name]

    for vdev in lease.vdevs.keys():
      lease.withdraw_vdev(vdev)

    for port in lease.ports:
      self.devices[dev_name].phys_ports_remaining.append(port)

    self.devices[dev_name].reserved_entries -= lease.entry_limit

    del self.slices[hp4slice].leases[dev_name]

    return 'Lease revoked: ' + hp4slice + ' lost access to ' + dev_name

  def reset_device(self, parameters):
    # parameters:
    # <'admin'> <device>
    dev_name = parameters[1]
    for hp4slice in self.slices:
      if dev_name in self.slices[hp4slice].leases:
        self.revoke_lease(['admin', hp4slice, dev_name])
    hp4device = self.devices[dev_name]
    # delete rules for tset_context
    for port in hp4device.assignments.keys():
      table = 'tset_context'
      handle = hp4device.assignments_handles[port]
      rule_identifier = table + ' ' + str(handle)
      hp4device.do_table_delete(rule_identifier)
    hp4device.assignments = {}
    hp4device.assignments_handles = {}
    
    return 'Device reset: ' + dev_name

  def create_virtual_device(self, parameters):
    # invoke loader
    # parameters:
    # <slice_name> <program_path> <vdev_name>
    hp4slice = parameters[0]
    program_path = parameters[1]
    vdev_name = parameters[2]
    vdev_ID = self.assign_vdev_ID()

    self.slices[hp4slice].vdevs[vdev_name] = \
                           self.vdev_factory.create_vdev(vdev_ID, program_path)
    
    return 'Virtual device ' + vdev_name + ' created'

  def migrate_virtual_device(self, parameters):
    # parameters:
    # <slice_name> <vdev_name> <dest device>
    hp4slice = parameters[0]
    vdev_name = parameters[1]
    dest_dev_name = parameters[2]

    # validate request
    # - validate slice
    if hp4slice not in self.slices:
      return 'Error - ' + hp4slice + ' not a valid slice'
    # - validate vdev_name
    if vdev_name not in self.slices[hp4slice].vdevs:
      return 'Error - ' + vdev_name + ' not a valid virtual device'
    # - validate dest_dev_name
    if dest_dev_name not in self.devices:
      return 'Error - ' + dest_dev_name + ' not a valid device'
    # - validate lease
    if dest_dev_name not in self.slices[hp4slice].leases:
      return 'Error - ' + dest_dev_name + ' not among leases owned by ' + hp4slice
    # - validate lease has sufficient entries
    vdev = self.slices[hp4slice].vdevs[vdev_name]
    vdev_entries = len(vdev.hp4code) + len(vdev.hp4_table_rules)
    entries_available = (self.slices[hp4slice].leases[dest_dev_name].entry_limit
                       - self.slices[hp4slice].leases[dest_dev_name].entry_usage)
    if (vdev_entries > entries_available):
      return 'Error - request(' + str(vdev_entries) + ') exceeds entries \
              available(' + entries_available + ') for lease on ' + dest_dev_name

    src_dev_name = self.slices[hp4slice].vdevs[vdev_name].dev_name
    if src_dev_name in self.devices:
      self.slices[hp4slice].leases[src_dev_name].withdraw_vdev(vdev_name)
    self.slices[hp4slice].leases[dest_dev_name].load_vdev(vdev_name, vdev)

    return 'Virtual device ' + vdev_name + ' migrated to ' + dest_dev_name

  def withdraw_virtual_device(self, parameters):
    hp4slice = parameters[0]
    vdev_name = parameters[1]
    dev_name = self.slices[hp4slice].vdevs[vdev_name].dev_name
    if dev_name not in self.devices:
      return 'Error - ' + vdev_name + ' not at a known device'
    self.slices[hp4slice].leases[dev_name].withdraw_vdev(vdev_name)
    return 'Virtual device ' + vdev_name + ' withdrawn from ' + dev_name

  def interpret(self, parameters):
    # TODO: Fix the native -> hp4 rule handle confusion.  Need to track
    #  virtual (native) rule handles to support table_delete and table_modify
    #  commands.
    # parameters:
    # <slice name> <virtual device> <style: 'bmv2' | 'agilio'> <command>
    hp4slice = parameters[0]
    vdev_name = parameters[1]
    style = parameters[2]
    vdev_command_str = ' '.join(parameters[3:])
    if style == 'bmv2':
      p4command = Bmv2_SSwitch.string_to_command(vdev_command_str)
    elif style == 'agilio':
      p4command = Agilio.string_to_command(vdev_command_str)
    else:
      return 'Error - ' + style + ' not one of (\'bmv2\', \'agilio\')'
    if hp4slice not in self.slices:
      return 'Error - ' + hp4slice + ' not a valid slice'
    if vdev_name not in self.slices[hp4slice].vdevs:
      return 'Error - ' + vdev_name + ' not a virtual device in ' + hp4slice
    vdev = self.slices[hp4slice].vdevs[vdev_name]
    hp4commands = Interpreter.interpret(vdev, p4command)

    # accounting
    entries_available = (self.slices[hp4slice].leases[vdev.dev_name].entry_limit
                       - self.slices[hp4slice].leases[vdev.dev_name].entry_usage)
    diff = 0
    for hp4command in hp4commands:
      if hp4command.command_type == 'table_add':
        diff += 1
      elif hp4command.command_type == 'table_delete':
        diff -= 1
    if diff > entries_available:
      return 'Error - entries net increase(' + str(diff) \
           + ') exceeds availability(' + str(entries_available) + ')'

    # push hp4 rules, collect handles
    hp4_rule_handles = []
    for hp4command in hp4commands:
      # return value should be handle for all commands
      hp4handle = self.slices[hp4slice].leases[vdev.dev_name].send_command(hp4command)
      table = hp4command.attribs['table']
      if hp4command.command_type == 'table_add' or hp4command.command_type == 'table_modify':
        vdev.hp4_table_rules[(table, hp4handle)] = hp4command.rule
      else: # command_type == 'table_delete'
        del vdev.hp4_table_rules[(table, hp4handle)]
      # accounting
      if hp4command.command_type == 'table_add':
        self.slices[hp4slice].leases[vdev.dev_name].entry_usage += 1
        hp4_rule_handles.append(hp4handle)
      elif hp4command.command_type == 'table_modify':
        hp4_rule_handles.append(hp4handle)
      elif hp4command.command_type == 'table_delete':
        self.slices[hp4slice].leases[vdev.dev_name].entry_usage -= 1

    # account for origin rule: handle, hp4 rules & hp4 handles
    table = p4command.attributes['table']
    if p4command.command_type == 'table_add':
      # new Origin_to_HP4Map w/ new hp4_rule_handles list
      rule = p4rule.P4Rule(table, p4command.attributes['action'],
                           p4command.attributes['mparams'],
                           p4command.attributes['aparams'])
      vdev.origin_table_rules[(table, vdev.assign_handle())] = \
                         virtualdevice.Interpretation(rule, hp4_rule_handles)

    elif p4command.command_type == 'table_modify':
      # replace Origin_to_HP4Map w/ one with new rule, new hp4_rules_handles list
      handle = p4command.attributes['handle']
      oldrule = vdev.origin_table_rules[(table, handle)].origin_rule
      action = p4command.attributes['action']
      mparams = oldrule.mparams
      aparams = p4command.attributes['aparams']
      rule = p4rule.P4Rule(table, action, mparams, aparams)
      vdev.origin_table_rules[(table, handle)] = \
                         virtualdevice.Interpretation(rule, hp4_rule_handles)

    elif p4command.command_type == 'table_delete':
      handle = p4command.attributes['handle']
      del vdev.origin_table_rules[(table, handle)]

    return 'Translated: ' + vdev_command_str + ' for ' + vdev_name + ' on ' + vev.dev_name

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
    self.leases = {} # {dev_name (string): lease (Lease)}

class CompTypeException(Exception):
  pass

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
