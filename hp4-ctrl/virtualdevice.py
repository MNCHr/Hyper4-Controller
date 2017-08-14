from p4command import P4Command
from p4rule import P4Rule

class VirtualDevice():
  def __init__(self, virtual_device_ID, code, guide):
    self.virtual_device_ID = virtual_device_ID
    self.guide = guide
    self.code = {} # {handle (int): p4cmd (P4Command)}
    self.origin_table_rules = {} # {handle (int): map (Origin_to_HP4Map)}
    self.hp4_table_rules = {} # {handle (int): p4r (P4Rule)}
    self.dev_name = 'none'

class Origin_to_HP4Map():
  def __init__(self, rule, handles):
    self.origin_rule = rule
    self.hp4_rule_handles = handles
