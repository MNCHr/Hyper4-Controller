import virtualdevice

class Composition():
  def __init__(self):
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}

  def remove(self, vdev_name):
    pass

class Chain(Composition):
  def __init__(self):
    self.vdev_chain = []
  def insert(self, vdev_name, pos):
    pass
  def append(self, vdev_name):
    pass

  def __str__(self):
    ret = ''
    for i in range(len(self.vdev_chain)):
      ret += ' -> ' + self.vdev_chain[i]
    return ret

class DAG(Composition):
  pass

class VirtualNetwork(Composition):
  pass
