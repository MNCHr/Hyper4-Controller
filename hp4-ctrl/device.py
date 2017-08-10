import p4command

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


