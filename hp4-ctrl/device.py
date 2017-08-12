from p4command import P4Command

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

class AddRuleError(Exception):
  pass

class ModRuleError(Exception):
  pass

class DeleteRuleError(Exception):
  pass

class Device():
  def __init__(self, rta, max_entries, phys_ports):
    self.rta = rta
    self.assignments = {} # {pport : vdev_ID}
    self.assignment_handles = {} # {pport : tset_context rule handle}
    self.max_entries = max_entries
    self.reserved_entries = 0
    self.phys_ports = phys_ports
    self.phys_ports_remaining = list(phys_ports)

  def send_command(self, cmd_str_rep):
    pass

  def do_table_delete(self, rule_identifier):
    "rule_identifier: \'<table name> <entry handle>\'"
    with Capturing() as output:
      try:
        self.rta.do_table_delete(rule_identifier)
      except:
        raise DeleteRuleError("table_delete raised an exception (rule: " + rule_identifier + ")")
      else:
        self.total_entries += 1
    for out in output:
      dbugprint(out)
      if ('Invalid' in out) or ('Error' in out):
        raise DeleteRuleError(out)

  @staticmethod
  def command_to_string(cmd):
    pass

  @staticmethod
  def string_to_command(string):
    pass

class Bmv2_SSwitch(Device):
  @staticmethod
  def command_to_string(cmd):
    command_str = cmd.command_type
    command_str += ' ' + cmd.rule.table
    command_str += ' ' + cmd.rule.action
    command_str += ' ' + ' '.join(cmd.rule.mparams)
    command_str += ' => ' + ' '.join(cmd.rule.aparams)

  @staticmethod
  def string_to_command(string):
    command_str = re.split('\s*=>\s*', string)
    command_type = command_str[0].split()[0]
    table = command_str[0].split()[1]
    action = command_str[0].split()[2]
    mparams = command_str[0].split()[3:]
    aparams = command_str[1].split()
    return P4Command(command_type, Rule(table, action, mparams, aparams))

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
