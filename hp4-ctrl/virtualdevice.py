from p4command import P4Command

class VirtualDevice():
  def __init__(self, virtual_device_ID, code, guide):
    self.virtual_device_ID = virtual_device_ID
    self.code = code # [P4Command]
    self.table_rules = [] # [P4Rule]
    self.guide = guide
    self.code_handles = {} # {handle (int): p4cmd (P4Command)}
    self.table_rules_handles = {} # {handle (int): p4r (P4Rule)}
