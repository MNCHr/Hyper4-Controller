class P4Rule():
  def __init__(self, table, action, mparams, aparams, default=False):
    self.table = table
    self.action = action
    self.mparams = mparams
    self.aparams = aparams
    self.default = default
  def __str__(self):
    ret = self.table 
    if self.default:
      ret += '*'
    ret += ' ' + self.action + ' '
    for mparam in self.mparams:
      ret += str(mparam) + ' '
    ret += '=> '
    for aparam in self.aparams:
      ret += str(aparam) + ' '
    return ret[0:-1]
