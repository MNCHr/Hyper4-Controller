from ..p4command import P4Command
from ..virtualdevice.p4rule import P4Rule
from ..errors import AddRuleError, ModRuleError, DeleteRuleError

import re
import sys
from cStringIO import StringIO
import code
# code.interact(local=dict(globals(), **locals()))

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
  def __init__(self, rta, max_entries, phys_ports, ip, port):
    self.rta = rta
    self.max_entries = max_entries
    self.reserved_entries = 0
    self.phys_ports = phys_ports
    self.phys_ports_remaining = list(phys_ports)
    self.ip = ip # management iface
    self.port = port # management iface

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

  def __str__(self):
    ret = 'Type: ' + self.__class__.__name__ + '\n'
    ret += 'Address: ' + self.ip + ':' + self.port + '\n'
    ret += 'Entry max: ' + str(self.max_entries) + '\n'
    ret += 'Entries reserved: ' + str(self.reserved_entries) + '\n'
    ret += 'Physical ports: ' + str(self.phys_ports) + '\n'
    ret += 'Physical ports remaining: ' + str(self.phys_ports_remaining)
    return ret

class Bmv2_SSwitch(Device):

  def send_command(self, cmd_str_rep):
    "send bmv2-formatted command to P4 device"
    if cmd_str_rep.split()[0] == 'table_add':
      try:
        table = cmd_str_rep.split()[1]
        action = cmd_str_rep.split()[2]
        mparams = cmd_str_rep.split('=>')[0].split()[3:]
        aparams = cmd_str_rep.split('=>')[1].split()
        rule = P4Rule(table, action, mparams, aparams)
        handle = self.do_table_add(rule)
      except AddRuleError as e:
        print('AddRuleError exception: ' + str(e))
      except:
        raise
      return handle

    elif cmd_str_rep.split()[0] == 'table_modify':
      try:
        self.do_table_modify(cmd_str_rep.split('table_modify ')[1])
        handle = cmd_str_rep.split()[2]
      except ModRuleError as e:
        print('ModRuleError exception: ' + str(e))
      except:
        raise
      return handle

    elif cmd_str_rep.split()[0] == 'table_delete':
      try:
        self.do_table_delete(cmd_str_rep.split('table_delete ' )[1])
        handle = cmd_str_rep.split()[1]
      except DeleteRuleError as e:
        print('DeleteRuleError exception: ' + str(e))
      except:
          raise
      return handle

    else:
      print("ERROR: Bmv2_SSwitch::send_command: " + cmd_str_rep + ")")
      exit()

  def do_table_delete(self, rule_identifier):
    "rule_identifier: \'<table name> <entry handle>\'"
    with Capturing() as output:
      try:
        self.rta.do_table_delete(rule_identifier)
      except:
        raise DeleteRuleError("table_delete raised an exception (rule: " + rule_identifier + ")")
    for out in output:
      print(out)
      if ('Invalid' in out) or ('Error' in out):
        raise DeleteRuleError(out)

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
        raise AddRuleError("table_add raised an exception (rule: " + rule + ")")
    for out in output:
      print(out)
      if ('Invalid' in out) or ('Error' in out):
        raise AddRuleError(out)
      if 'Entry has been added' in out:
        return int(out.split('handle ')[1])

  def do_table_modify(self, rule_mod):
    "rule_mod: \'<table name> <action> <handle> <[aparams]>\'"
    with Capturing() as output:
      try:
        self.rta.do_table_modify(rule_mod)
      except:
        raise ModRuleError("table_modify raised an exception (rule_mod: " + rule_mod + ")")
    for out in output:
      print(out)
      if ('Invalid' in out) or ('Error' in out):
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
      command_str += ' => ' + ' '.join(cmd.attributes['aparams'])
    elif cmd.command_type == 'table_delete':
      command_str += ' ' + str(cmd.attributes['handle'])
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
      attributes['handle'] = int(command_str[0].split()[3])
    return P4Command(command_type, attributes)

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
