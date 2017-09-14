class P4Rule():
  def __init__(self, table, action, mparams, aparams):
    self.table = table
    self.action = action
    self.mparams = mparams
    self.aparams = aparams
  def __str__(self):
    ret = self.table + ' ' + self.action + ' '
    for mparam in self.mparams:
      ret += str(mparam) + ' '
    ret += '=> '
    for aparam in self.aparams:
      ret += str(aparam) + ' '
    return ret[0:-1]
