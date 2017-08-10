import p4command

class Device():
  def __init__(self, ip_addr, port):
    self.ip_addr = ip_addr
    self.port = port
  def send_command(self, cmd_str_rep):
    pass
  def command_to_string(cmd):
    pass
  def string_to_command(string):
    pass

class Bmv2_SSwitch(Device):
  def command_to_string(cmd):
    pass
  def string_to_command(string):
    pass

class Agilio(Device):
  def command_to_string(cmd):
    pass
  def string_to_command(string):
    pass

d = Device(...)
l = Lease(...)
l.send_command(<P4Command>)


