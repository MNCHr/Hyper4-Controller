from hp4controller.p4command import P4Command
from hp4controller.virtualdevice.p4rule import P4Rule
from hp4controller.errors import AddRuleError, ModRuleError, DeleteRuleError
from hp4controller.errors import MCastError, SendCommandError

from sswitch_CLI import SimpleSwitchAPI

import re
import sys
from cStringIO import StringIO
import code
from inspect import currentframe, getframeinfo

# CSR: Command String Representation
CSR_CMD_TYPE = 0

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))

# http://stackoverflow.com/questions/16571150/how-to-capture-stdout-output-from-a-python-function-call
class Capturing(list):
  def __enter__(self):
    self._stdout = sys.stdout
    sys.stdout = self._stringio = StringIO()
    return self
  def __exit__(self, *args):
    self.extend(self._stringio.getvalue().splitlines())
    del self._stringio
    sys.stdout = self._stdout

class Device():
  def __init__(self, rta, max_entries, phys_ports, ip, port, debug=False):
    self.rta = rta
    self.max_entries = max_entries
    self.reserved_entries = 0
    self.phys_ports = phys_ports
    self.phys_ports_remaining = list(phys_ports)
    self.ip = ip # management iface
    self.port = port # management iface
    self.next_mcast_grp_id = 1
    self.debug = debug

  def debug_print(self, s):
    if self.debug:
      print(s)

  def assign_mcast_grp_id(self):
    ret = self.next_mcast_grp_id
    self.next_mcast_grp_id += 1
    return ret

  def send_command(self, cmd_str_rep):
    # return handle (regardless of command type)
    pass

  def do_table_delete(self, rule_identifier):
    """ Implement w/ device-specific mechanism/syntax for deleting rules """
    pass

  def do_table_add(self, rule):
    """ Implement w/ device-specific mechanism/syntax for adding rules """
    pass

  def do_table_modify(self, rule):
    """ Implement w/ device-specific mechanism/syntax for modifying rules """
    pass

  @staticmethod
  def command_to_string(cmd):
    pass

  @staticmethod
  def string_to_command(string):
    pass

  def mcast_setup(self, mcast_grp_id, ports):
    pass

  def mcast_teardown(self, mcast_grp_id, node_handle):
    pass

  @staticmethod
  def get_mcast_attribs(vdev_ID, vegress, mcast_grp_id, filtered):
    attribs = {'table': 't_virtnet',
               'action': 'do_phys_fwd_only',
               'mparams': [str(vdev_ID), str(vegress)],
               'aparams': [str(mcast_grp_id), str(filtered)]}
    return attribs

  def __str__(self):
    ret = 'Type: ' + self.__class__.__name__ + '\n'
    ret += 'Address: ' + self.ip + ':' + self.port + '\n'
    ret += 'Entry max: ' + str(self.max_entries) + '\n'
    ret += 'Entries reserved: ' + str(self.reserved_entries) + '\n'
    ret += 'Physical ports: ' + str(self.phys_ports) + '\n'
    ret += 'Physical ports remaining: ' + str(self.phys_ports_remaining)
    return ret

class Bmv2_SSwitch(Device):

  def parse_table_add(self, cmd_str_rep):
    left = cmd_str_rep.split('=>')[0]
    right = cmd_str_rep.split('=>')[1]
    table = left.split()[1]
    action = left.split()[2]
    mparams = left.split()[3:]
    aparams = right.split()
    return table, action, mparams, aparams

  def parse_table_modify(self, cmd_str_rep):
    tm_cmd = cmd_str_rep.split('table_modify ')[1]
    handle = tm_cmd.split()[2]
    return tm_cmd, handle

  def parse_table_delete(self, cmd_str_rep):
    td_cmd = cmd_str_rep.split('table_delete ')[1]
    handle = td_cmd.split()[2]
    return td_cmd, handle

  def send_command(self, cmd_str_rep):
    "send bmv2-formatted command to P4 device"
    csr_cmd = cmd_str_rep.split()[CSR_CMD_TYPE]
    if csr_cmd == 'table_add':
      table, action, mparams, aparams = self.parse_table_add(cmd_str_rep)
      rule = P4Rule(table, action, mparams, aparams)
      try:
        handle = self.do_table_add(rule)
      except AddRuleError as e:
        print('AddRuleError exception: ' + str(e) + ' :: ' + cmd_str_rep)
        debug()
        raise
      except:
        debug()
        raise
      return handle

    elif csr_cmd == 'table_modify':
      tm_cmd, handle = self.parse_table_modify(cmd_str_rep)
      try:
        self.do_table_modify(tm_cmd)
      except ModRuleError as e:
        print('ModRuleError exception: ' + str(e) + ' :: ' + cmd_str_rep)
        debug()
        raise
      except:
        debug()
        raise
      return handle

    elif csr_cmd == 'table_delete':
      td_cmd, handle = self.parse_table_delete(cmd_str_rep)
      try:
        self.do_table_delete(td_cmd)
      except DeleteRuleError as e:
        print('DeleteRuleError exception: ' + str(e) + ' :: ' + cmd_str_rep)
        debug()
        raise
      except:
        debug()
        raise
      return handle

    else:
      print("ERROR: Bmv2_SSwitch::send_command: " + cmd_str_rep + ")")
      debug()
      raise SendCommandError("Not understood: " + cmd_str_rep)

  def do_table_delete(self, rule_identifier):
    "rule_identifier: \'<table name> <entry handle>\'"
    with Capturing() as output:
      try:
        self.rta.do_table_delete(rule_identifier)
      except:
        debug()
        raise DeleteRuleError("table_delete raised an exception (rule: " + rule_identifier + ")")
    for out in output:
      self.debug_print(out)
      if ('Invalid' in out) or ('Error' in out):
        debug()
        raise DeleteRuleError(out)
      #if ('Deleting entry 0 from t_bit_xor_25' in out) and (self.port == 9090):
      #  print(rule_identifier)
      #  print("Device on port " + str(self.port))
      #  debug()

  def do_table_add(self, rule):
    """ rule: P4Rule
        output: handle or error
    """
    # rta.do_table_add expects '<table> <action> <[mparams]> => <[aparams]>'
    bmv2_rule = rule.table + ' ' + rule.action + ' ' + ' '.join(rule.mparams) \
                           + ' => ' + ' '.join(rule.aparams)

    with Capturing() as output:
      try:
        self.rta.do_table_add(bmv2_rule)
      except:
        debug()
        raise AddRuleError("table_add raised an exception (rule: " + rule + ")")

    for out in output:
      self.debug_print(out)
      if ('Invalid' in out) or ('Error' in out):
        debug()
        raise AddRuleError(out)
      if 'Entry has been added' in out:
        return int(out.split('handle ')[1])

  def do_table_modify(self, rule_mod):
    "rule_mod: \'<table name> <action> <handle> <[aparams]>\'"

    # Bug in current version of bmv2/tools/run_CLI.sh: <-- what?  runtime_CLI.py?
    #  if no aparams, crashes unless '=>' present on the end
    if len(rule_mod.split()) == 3:
      rule_mod += ' =>'

    with Capturing() as output:
      try:
        self.rta.do_table_modify(rule_mod)
      except:
        raise ModRuleError("table_modify raised an exception (rule_mod: " + rule_mod + ")")

    for out in output:
      self.debug_print(out)
      if ('Invalid' in out) or ('Error' in out):
        debug()
        raise ModRuleError(out)

  @staticmethod
  def command_to_string(cmd):
    command_str = cmd.command_type
    command_str += ' ' + cmd.attributes['table']
    if cmd.command_type == 'table_add':
      command_str += ' ' + cmd.attributes['action']
      command_str += ' ' + ' '.join(cmd.attributes['mparams'])
      command_str += ' => ' + ' '.join(cmd.attributes['aparams'])
    elif cmd.command_type == 'table_modify':
      command_str += ' ' + cmd.attributes['action']
      command_str += ' ' + str(cmd.attributes['handle'])
      command_str += ' ' + ' '.join(cmd.attributes['aparams'])
    elif cmd.command_type == 'table_delete':
      command_str += ' ' + str(cmd.attributes['handle'])
    elif cmd.command_type == 'table_set_default':
      command_str += ' ' + cmd.attributes['action']
      command_str += ' ' + ' '.join(cmd.attribtes['aparams'])
    return command_str

  @staticmethod
  def string_to_command(string):
    command_str = re.split('\s*=>\s*', string)
    command_type = command_str[0].split()[0]
    attributes = {}
    attributes['table'] = command_str[0].split()[1]
    if command_type == 'table_add':
      # table_add <table name> <action name> <match fields> => <action parameters> [priority]
      attributes['action'] = command_str[0].split()[2]
      attributes['mparams'] = command_str[0].split()[3:]
      attributes['aparams'] = command_str[1].split()
    elif command_type == 'table_modify':
      # table_modify <table name> <action name> <entry handle> [action parameters]
      attributes['action'] = command_str[0].split()[2]
      attributes['handle'] = int(command_str[0].split()[3])
      attributes['aparams'] = command_str[0].split()[4:]
    elif command_type == 'table_delete':
      # table_delete <table name> <entry handle>
      attributes['handle'] = int(command_str[0].split()[2])
    elif command_type == 'table_set_default':
      # table_set_default <table name> <action name> <action parameters> [priority]
      attributes['action'] = command_str[0].split()[2]
      attributes['aparams'] = command_str[0].split()[3:]
    return P4Command(command_type, attributes)

  def mcast_setup(self, mcast_grp_id, ports):
    "Set up multicast group"
    # mc_mgrp_create
    with Capturing() as output:
      try:
        self.rta.do_mc_mgrp_create(str(mcast_grp_id))
      except:
        debug()
        raise MCastError("mc_mgrp_create raised an exception:" + str(sys.exc_info()[0]))
    for out in output:
      self.debug_print(out) 

    # mc_node_create
    with Capturing() as output:
      try:
        self.rta.do_mc_node_create("1 " + ' '.join(str(port) for port in ports))
      except:
        debug()
        raise MCastError("mc_node_create raised an exception")
    node_handle = -1
    for out in output:
      self.debug_print(out)
      if 'was created with handle' in out:
        node_handle = int(out.split('handle ')[1])
    if node_handle == -1:
      debug()
      raise MCastError("mc_node_create error - node_handle not assigned \
                       (did not receive success message?)")

    # mc_node_associate
    with Capturing() as output:
      try:
        self.rta.do_mc_node_associate(str(mcast_grp_id) + ' ' + str(node_handle))
      except:
        debug()
        raise MCastError("mc_node_associate raised an exception")
    for out in output:
      self.debug_print(out)

    return node_handle

  @staticmethod
  def get_mcast_attribs(vdev_ID, vegress, mcast_grp_id, filtered):
    attribs = {'table': 't_virtnet',
               'action': 'do_bmv2_mcast',
               'mparams': [str(vdev_ID), str(vegress)],
               'aparams': [str(mcast_grp_id), str(filtered)]}
    return attribs

  def mcast_teardown(self, mcast_grp_id, node_handle):
    with Capturing() as output:
      try:
        self.rta.do_mc_node_destroy(str(node_handle))
      except:
        debug()
        raise MCastError("mc_node_destroy raised an exception")
    for out in output:
      self.debug_print(out)
    with Capturing() as output:
      try:
        self.rta.do_mc_mgrp_destroy(str(mcast_grp_id))
      except:
        debug()
        raise MCastError("mc_mgrp_destroy raised an exception")
    for out in output:
      self.debug_print(out)

class Agilio(Device):
  @staticmethod
  def command_to_string(cmd):
    pass
  @staticmethod
  def string_to_command(string):
    pass

# usage
# d = Device(...)
# l = Lease(...)
# l.send_command(<P4Command>)
