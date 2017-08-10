#!/usr/bin/python

import argparse
import sys
import runtime_CLI
import socket
import hp4loader
import os
import virtualdevice
from hp4translator import VDevCommand_to_HP4Command

class Controller():
  def __init__(self):
    pass
  def handle_request(self, request):
    pass
  def handle_create_device(self, dev_name, ip_addr, port, num_ifaces, dev_type):
    pass
  def handle_create_slice(self):
    pass
  def handle_create_lease(self):
    pass
  def handle_create_vdev(self):
    pass
  def handle_migrate_vdev(self):
    pass
  def handle_delete_vdev(self):
    pass
  def handle_translate(self):
    pass

class ChainController(Controller):
  def handle_insert(self):
    pass
  def handle_append(self):
    pass
  def handle_remove(self):
    pass

class Slice():
  def __init__(self):
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}

class Lease():
  def __init__(self, dev, memory_limit):
    self.device = dev
    self.memory_limit = memory_limit
    self.memory_usage = 0
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}

  def send_command(self, p4cmd):
    return dev.send_command(dev.command_to_string(p4cmd))

print("Success!")
