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
import signal
import errno
import traceback
from pathlib2 import Path
import getpass

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
BACKLOG = 5

# https://stackoverflow.com/questions/18499497/how-to-process-sigterm-signal-gracefully
class GracefulKiller(object):
  kill_now = False
  def __init__(self):
    signal.signal(signal.SIGINT, self.exit_gracefully)
    signal.signal(signal.SIGTERM, self.exit_gracefully)
  
  def exit_gracefully(self, signum, frame):
    self.kill_now = True

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
    if len(request.split()) < 2:
      return "Request format: <slice name | admin> <command> [parameter list]"
    requester = request.split()[0]
    command = request.split()[1]
    # self.dbugprint("Request: " + request)
    # self.dbugprint("Command: " + command)
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
      #except Exception as e:
      #  return "Unexpected error(" + command + "): " + str(e)
    elif command == 'vdev_create':
      resp = self.vdev_create(parameters)
    else:
      # self.dbugprint("SLICE TO HANDLE " + request)
      resp = self.slices[requester].handle_request(request.split()[1:])

    return resp

  def create_device(self, parameters):
    # parameters:
    # <'admin'> <name> <ip_addr> <port> <dev_type: 'bmv2_SSwitch' | 'Agilio'>
    # <pre: 'None' | 'SimplePre' | 'SimplePreLAG'> <# entries> <json path> <ports>
    dev_name = parameters[1]
    ip = parameters[2]
    port = parameters[3]
    dev_type = parameters[4]
    pre = parameters[5]
    max_entries = int(parameters[6])

    try:
      int(parameters[7])
    except ValueError:
      json = parameters[7]
      ports = parameters[8:]
    else:
      json = '/home/' + getpass.getuser() + '/hp4-src/hp4/hp4.json'
      hjp_check = Path('hp4controller/hp4_json_path')
      if hjp_check.is_file():
        with open('hp4controller/hp4_json_path', 'r') as hjp:
          json = hjp.readline()[:-1]
      ports = parameters[7:]

    json_check = Path(json)
    if json_check.is_file() == False:
      return 'Error - ' + json + ' not found'

    prelookup = {'None': runtime_CLI.PreType.None,
                 'SimplePre': runtime_CLI.PreType.SimplePre,
                 'SimplePreLAG': runtime_CLI.PreType.SimplePreLAG}

    services = runtime_CLI.RuntimeAPI.get_thrift_services(prelookup[pre])
    services.extend(SimpleSwitchAPI.get_thrift_services())

    #try:
    #  std_client, mc_client, sswitch_client = runtime_CLI.thrift_connect(ip, port, services)
    #except:
    #    return "Error - create_device(" + dev_name + "): " + str(sys.exc_info()[0])
    std_client, mc_client, sswitch_client = runtime_CLI.thrift_connect(ip, port, services)


    runtime_CLI.load_json_config(std_client, json)
    rta = SimpleSwitchAPI(prelookup[pre], std_client, mc_client, sswitch_client)

    # TODO: fix this; Controller must not be required to know every Device subclass
    if dev_type == 'bmv2_SSwitch':
      self.devices[dev_name] = device.Bmv2_SSwitch(rta, max_entries, ports, ip, port, debug=self.debug)
    elif dev_type == 'Agilio':
      self.devices[dev_name] = device.Agilio(rta, max_entries, ports, ip, port)
    else:
      return 'Error - device type ' + dev_type + ' unknown'

    self.dbugprint("Reached return statement")
    return "Added device: " + dev_name

  def create_slice(self, parameters):
    "Create a slice"
    hp4slice = parameters[1]
    self.slices[hp4slice] = Slice(hp4slice, self.debug)
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

  def vdev_create(self, parameters):
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
    serversocket.listen(BACKLOG)

    killer = GracefulKiller()

    while True:
      clientsocket = None
      try:
        clientsocket, addr = serversocket.accept()
        self.dbugprint("Got a connection from %s" % str(addr))
        data = clientsocket.recv(BUFFSIZE)
        self.dbugprint('Received: ' + data)
        response = self.handle_request(data)
        clientsocket.sendall(response)
        clientsocket.close()
      except KeyboardInterrupt:
        #if clientsocket:
        #  clientsocket.close()
        #serversocket.close()
        #self.dbugprint("Keyboard Interrupt, sockets closed")
        break
      except socket.error as (code, msg):
        if code != errno.EINTR:
          debug()
          raise
      if killer.kill_now:
        self.dbugprint("\rConViDa terminated")
        break

    if clientsocket:
      clientsocket.close()
      serversocket.close()
      self.dbugprint("sockets closed")

  def dbugprint(self, msg):
    if self.debug:
      print(msg)
      with open('controller_debug', 'a') as out:
        out.write(msg + '\n')

class Slice():
  def __init__(self, name, debug):
    self.name = name
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}
    self.leases = {} # {dev_name (string): lease (Lease)}
    self.debug = debug

  def handle_request(self, parameters):
    # parameters:
    # <command> <command parameters>
    command = parameters[0]
    if 'lease' in command:
      dev_name = parameters[1]
      lease = self.leases[dev_name]
      if command == 'lease_config_egress':
        resp = lease.lease_config_egress(parameters[2:])
        return resp
      elif command == 'lease_replace':
        vdev = self.vdevs[parameters[2]]
        new_vdev = self.vdevs[parameters[3]]
        return lease.lease_replace(parameters[2:], vdev, new_vdev)
      elif command == 'lease_info':
        resp = str(lease)
        return resp
      elif command == 'lease_dump':
        return lease.lease_dump()
      else:
        try:
          vdev = self.vdevs[parameters[2]]
        except IndexError as e:
          print('IndexError: ' + str(e))
          print('controller.py::Slice::handle_request; parameters: ' + str(parameters))
          debug()
        try:
          resp = getattr(lease, command)(parameters[2:], vdev)
        except AttributeError as e:
          print(e)
          debug()
          return "AttributeError(handle_request - " + command + "): " + str(e)
        except Exception as e:
          print "Unexpected error(" + command + "): " + str(e)
          debug()
        #  return "Unexpected error(" + command + "): " + str(e)
        return resp
    else:
      try:
        resp = getattr(self, command)(parameters[1:])
      except AttributeError as e:
        print(e)
        debug()
        return "AttributeError(handle_request - " + command + "): " + str(e)
      except Exception as e:
        print(e)
        debug()
      #  return "Unexpected error(" + command + "): " + str(e)
      return resp

  def slice_dump(self, parameters):
    resp = ""
    for dev_name in self.leases:
      lease = self.leases[dev_name]
      resp += dev_name + '(' + str(lease.entry_usage) + '/' \
              + str(lease.entry_limit) + ') [' + str(lease.ports) + ']: \n'
      resp += lease.print_vdevs()
    resp += 'unassigned:\n'
    unassigned = [vdev for vdev in self.vdevs.values() if vdev.dev_name == 'none']
    unassigned.sort(key=lambda vdev: vdev.name)
    for vdev in unassigned:
      resp += '  ' + vdev.name + '\n'
    return resp[0:-1]

  """
  def list_vdevs(self, parameters):
    resp = ""
    for vdev_name in self.vdevs:
      vdev = self.vdevs[vdev_name]
      resp += vdev_name + '@' + vdev.dev_name + '\n'
    return resp
  """

  def dbug_print(self, msg):
    if self.debug:
      with open('controller_debug', 'a') as out:
        out.write(msg + '\n')
      print(msg)

  def vdev_dump(self, parameters):
    "Display all pushed entries"
    if parameters[0] not in self.vdevs:
      return parameters[0] + ' not recognized'
    msg = self.vdevs[parameters[0]].dump()
    self.dbug_print('vdev_dump: ' + parameters[0])
    self.dbug_print(msg)
    return msg

  def vdev_info(self, parameters):
    if parameters[0] not in self.vdevs:
      return parameters[0] + ' not recognized'
    return self.vdevs[parameters[0]].info()

  def list_vdev_hp4code(self, parameters):
    if parameters[0] not in self.vdevs:
      return parameters[0] + ' not recognized'
    vdev = self.vdevs[parameters[0]]
    msg = vdev.str_hp4code()
    self.dbug_print('list_vdev_hp4code: ' + parameters[0])
    self.dbug_print(msg)
    return msg

  def list_vdev_hp4rules(self, parameters):
    if parameters[0] not in self.vdevs:
      return parameters[0] + ' not recognized'
    vdev = self.vdevs[parameters[0]]
    msg = vdev.str_hp4rules()
    self.dbug_print('list_vdev_hp4rules: ' + parameters[0])
    self.dbug_print(msg)
    return msg

  def list_vdev_hp4_code_and_rules(self, parameters):
    if parameters[0] not in self.vdevs:
      return parameters[0] + ' not recognized'
    vdev = self.vdevs[parameters[0]]
    msg = vdev.str_hp4_code_and_rules()
    self.dbug_print('list_vdev_hp4_code_and_rules: ' + parameters[0])
    self.dbug_print(msg)
    return msg

  """
  def list_devs(self, parameters):
    resp = "device(used/allocated)\tvdev chain\n"
    for dev_name in self.leases:
      lease = self.leases[dev_name]
      resp += dev_name + '(' + str(lease.entry_usage) + '/' \
              + str(lease.entry_limit) + '): ' + str(lease) + '\n'
    return resp[0:-1]
  """

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

  def vdev_destroy(self, parameters):
    vdev_name = parameters[0]
    vdev = self.vdevs[vdev_name]
    if vdev.dev_name != 'none':
      lease = self.leases[vdev.dev_name]
      lease.lease_remove(parameters, vdev)
    del self.vdevs[vdev_name]
    return 'Virtual device ' + vdev_name + ' destroyed'
      
  def vdev_interpret(self, parameters):
    # parameters:
    # <slice name> <virtual device> <style: 'bmv2' | 'agilio'> <command>
    vdev_name = parameters[0]
    style = parameters[1]

    # reformat & sanity check
    vdev_command_str = ' '.join(parameters[2:])
    if style == 'bmv2':
      native_command = device.Bmv2_SSwitch.string_to_command(vdev_command_str)
    elif style == 'agilio':
      native_command = device.Agilio.string_to_command(vdev_command_str)
    else:
      return 'Error - ' + style + ' not one of (\'bmv2\', \'agilio\')'
    if vdev_name not in self.vdevs:
      return 'Error - ' + vdev_name + ' not a recognized virtual device'
    vdev = self.vdevs[vdev_name]

    """
    if (vdev_name == 's1_vib_enc' and
        parameters[2] == 'table_modify' and 
        parameters[4] == 'a_mod_epoch_and_encrypt' and 
        native_command.attributes['table'] == 'encrypt' and 
        native_command.attributes['handle'] == 1):
      debug()
    """
    #if vdev_name == 's1_vib_enc':
    #  debug()

    # intepret
    hp4commands = vdev.interpret(native_command)

    # destination
    dev_name = vdev.dev_name

    # prepare to track changes to ruleset
    hp4_rule_keys = [] # list of (table, action, handle) tuples

    #if vdev_name == 's1_vib_enc':
    #  debug()

    def get_table_action_rule(hp4command, hp4handle, dev_name):
      table = hp4command.attributes['table']
      try:
        action = hp4command.attributes['action']
      except Exception as e:
        print(e)
        debug()

      if hp4command.command_type == 'table_add':
        rule = p4rule.P4Rule(table, action,
                             hp4command.attributes['mparams'],
                             hp4command.attributes['aparams'])
      else: # 'table_modify'
        # TODO: fix this?  hp4rules should work whether vdev is loaded or not, right?
        if dev_name == 'none':
          mparams = vdev.hp4rules[(table, hp4handle)].mparams
        else:
          mparams = vdev.hp4_code_and_rules[(table, hp4handle)].mparams
          if mparams != vdev.hp4rules[(table, hp4handle)].mparams:
            print('Investigate why hp4rules and hp4_code_and_rules differ')
            debug()
        rule = p4rule.P4Rule(table, action,
                             mparams,
                             hp4command.attributes['aparams'])

      return table, action, rule

    #trap = False

    if dev_name == 'none':
      if native_command.command_type == 'table_set_default':
        # replace line in vdev.hp4_code
        if len(hp4commands) != 1:
          print("Slice::interpret: Unexpected length of hp4commands (" \
                + str(len(hp4commands)) + ")")
          exit()

        newrule = hp4commands[0]
        for rule in vdev.hp4code:
          if rule.table == newrule.attributes['table']:
            # replace 1st six elements, or all init_program_state parameters:
            #   action_ID, match_ID, next_stage, next_table, primitive,
            #   primitive_subtype
            # seventh element == priority, which should remain the same
            for i in range(6):
              rule.aparams[i] = newrule.attributes['aparams'][i]
            break
  
      else:
        # gather changes to ruleset
        for hp4command in hp4commands:
          if hp4command.command_type == 'table_add':
            hp4handle = vdev.assign_staged_hp4_handle(hp4command.attributes['table'])
            table, action, rule = get_table_action_rule(hp4command, hp4handle, dev_name)
            vdev.hp4rules[(table, hp4handle)] = rule
            hp4_rule_keys.append((table, action, hp4handle))
          elif hp4command.command_type == 'table_modify':
            hp4handle = int(hp4command.attributes['handle'])
            table, action, rule = get_table_action_rule(hp4command, hp4handle, dev_name)
            vdev.hp4rules[(table, hp4handle)] = rule
            hp4_rule_keys.append((table, action, hp4handle))
          else: # command_type == 'table_delete'
            table = hp4command.attributes['table']
            hp4handle = int(hp4command.attributes['handle'])
            del vdev.hp4rules[(table, hp4handle)]

      #if vdev_name == 's1_vib_enc':
      #  debug()

    else:
      # accounting
      entries_available = (self.leases[dev_name].entry_limit
                          - self.leases[dev_name].entry_usage)
      diff = 0
      for hp4command in hp4commands:
        if hp4command.command_type == 'table_add':
          diff += 1
        elif hp4command.command_type == 'table_delete':
          diff -= 1
      # abort if insufficient capacity
      if diff > entries_available:
        debug()
        return 'Error - entries net increase(' + str(diff) \
             + ') exceeds availability(' + str(entries_available) + ')'

      # push hp4 rules, collect handles, gather changes to ruleset
      for hp4command in hp4commands:
        # return value should be handle for all commands
        #if hp4command.attributes['table'] == 't_bit_xor_25' and hp4command.command_type == 'table_delete':
        #  debug()
        try:
          hp4handle = int(self.leases[dev_name].send_command(hp4command))
        except Exception as e:
          print(e)
          debug()
        if hp4command.command_type == 'table_add' or hp4command.command_type == 'table_modify':
          table, action, rule = get_table_action_rule(hp4command, hp4handle, dev_name)
        else: # command_type == 'table_delete'
          table = hp4command.attributes['table']

        if hp4command.command_type == 'table_add' or hp4command.command_type == 'table_modify':
          vdev.hp4rules[(table, hp4handle)] = rule
          vdev.hp4_code_and_rules[(table, hp4handle)] = rule
          hp4_rule_keys.append((table, action, hp4handle))
          if hp4command.command_type == 'table_add':
            self.leases[dev_name].entry_usage += 1
        else: # command_type == 'table_delete'
          del vdev.hp4_code_and_rules[(table, hp4handle)]
          del vdev.hp4rules[(table, hp4handle)]
          self.leases[dev_name].entry_usage -= 1

        #if hp4command.command_type == 'table_delete' and hp4command.attributes['table'] == 't_bit_xor_25' and hp4handle == 0 and vdev_name == 's1_vib_enc':
        #  debug()
        #  trap = True

      #if vdev_name == 's1_vib_enc':
      #  debug()

    # record changes to ruleset
    try:
      table = native_command.attributes['table']
    except Exception as e:
      print(e)
      debug()
    nhandle_str = ''
    if native_command.command_type == 'table_add':
      # new Origin_to_HP4Map w/ new hp4_rule_keys list
      try:
        rule = p4rule.P4Rule(table, native_command.attributes['action'],
                             native_command.attributes['mparams'],
                             native_command.attributes['aparams'])
      except Exception as e:
        print(e)
        debug()

      match_ID = int(hp4commands[0].attributes['aparams'][1])
      nhandle_str = '; handle: ' + str(match_ID)
      vdev.nrules[(table, match_ID)] = Interpretation(rule, match_ID, hp4_rule_keys)

    elif native_command.command_type == 'table_modify':

      #if vdev_name == 's1_vib_enc':
      #  debug()

      # update interpretation origin rule
      match_ID = native_command.attributes['handle']
      nhandle_str = '; handle: ' + str(match_ID)
      interpretation = vdev.nrules[(table, match_ID)]
      try:
        rule = p4rule.P4Rule(table, native_command.attributes['action'],
                             interpretation.native_rule.mparams,
                             native_command.attributes['aparams'])
      except Exception as e:
        print(e)
        debug()

      # retain match rule
      hp4_match_rule_key = vdev.nrules[(table, match_ID)].hp4_rule_keys[0]
      hp4_rule_keys.insert(0, hp4_match_rule_key)

      vdev.nrules[(table, match_ID)] = Interpretation(rule, match_ID, hp4_rule_keys)

    elif native_command.command_type == 'table_set_default':
      match_ID = 0
      try:
        rule = p4rule.P4Rule(table, native_command.attributes['action'],
                             [],
                             native_command.attributes['aparams'],
                             default=True)
      except Exception as e:
        print(e)
        debug()
      vdev.nrules[(table, match_ID)] = Interpretation(rule, match_ID, hp4_rule_keys)

    elif native_command.command_type == 'table_delete':
      handle = native_command.attributes['handle']
      del vdev.nrules[(table, handle)]

    """
    if (vdev_name == 's1_vib_enc' and
        parameters[2] == 'table_modify' and 
        parameters[4] == 'a_mod_epoch_and_encrypt' and 
        native_command.attributes['table'] == 'encrypt' and 
        native_command.attributes['handle'] == 1):
      debug()
    """
    #if vdev_name == 's1_vib_enc':
    #  debug()

    return 'Interpreted: ' + vdev_command_str + ' for ' + vdev_name + ' on ' \
                           + dev_name + ' ' + nhandle_str

class CompTypeException(Exception):
  pass

def server(args):
  ctrl = Controller(args)
  ctrl.dbugprint('ConViDa listening at %s:%d' % (args.host, args.port))
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
