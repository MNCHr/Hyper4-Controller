from ..virtualdevice.virtualdevice import VirtualDevice
from ..p4command import P4Command

import code

class Lease(object):
  def __init__(self, dev, entry_limit, ports):
    self.device = dev
    self.entry_limit = entry_limit
    self.entry_usage = 0
    self.ports = ports
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}
    self.assignments = {} # {pport : vdev_ID}
    self.assignment_handles = {} # {pport : tset_context rule handle}
    vegress_val = 1
    self.egress_map = {} # {vegress_spec (int): egress_spec (int)}
    # note, following assumes port id == egress_spec
    for port in ports:
      self.egress_map[vegress_val] = port
      vegress_val += 1

  def revoke(self):
    # delete rules for tset_context
    for port in self.assignments.keys():
      table = 'tset_context'
      handle = self.assignment_handles[port]
      rule_identifier = table + ' ' + str(handle)
      self.device.do_table_delete(rule_identifier)
    self.assignments = {}
    self.assignment_handles = {}

    for port in self.ports:
      self.device.phys_ports_remaining.append(port)

    self.device.reserved_entries -= self.entry_limit

  def load_vdev(self, vdev_name, vdev):
    "Load virtual device onto physical device"
    for rule in vdev.hp4code:
      try:
        table = rule.table
        handle = self.device.do_table_add(rule)
        vdev.hp4_table_rules[(table, handle)] = rule
      except AddRuleError as e:
        # remove all entries already added
        for table, h in vdev.hp4_table_rules.keys():
          rule_identifier = table + ' ' + str(h)
          self.device.do_table_delete(rule_identifier)
          del vdev.hp4_table_rules[(table, h)]
        raise AddRuleError('Lease::load_vdev failed for ' + vdev_name)

    self.entry_usage += len(vdev.hp4code)
    self.vdevs[vdev_name] = vdev

  def withdraw_vdev(self, vdev_name):
    "Remove virtual device from Lease (does not destroy virtual device)"
    num_entries = len(self.vdevs[vdev_name].hp4_table_rules)
    # pull all virtual device related rules from device
    for table, handle in self.vdevs[vdev_name].hp4_table_rules.keys():
      rule_identifier = table + ' ' + str(handle)
      self.device.do_table_delete(rule_identifier)
    self.vdevs[vdev_name].hp4_table_rules = {}

    self.entry_usage -= num_entries
    # if applicable, remove vdev from composition
    if vdev_name in self.vdevs:
      self.remove(vdev_name)

    # make lease forget about it (Lease's owning Slice still has it)
    del self.vdevs[vdev_name]

  def handle_request(self, parameters):
    command = parameters[0]
    resp = ""
    try:
      resp = getattr(self, command)(parameters[1:])
    except AttributeError as e:
      return "AttributeError(handle_request - " + command + "): " + str(e)
    except Exception as e:
      return "Unexpected error: " + str(e)
    return resp

  def send_command(self, p4cmd):
    return self.device.send_command(self.device.command_to_string(p4cmd))

  def remove(self, vdev_name):
    pass

  def __str__(self):
    ret = 'entry usage/limit: ' + str(self.entry_usage) + '/' \
                                + str(self.entry_limit) + '\n'
    ret += 'ports:' + str(self.ports) + '\n'
    ret += 'virtual devices:\n'
    for vdev in self.vdevs:
      ret += ' ' + vdev + '\n'
    #ret += 'composition: ' + str(self.composition)
    return ret

class Chain(Lease):
  def __init__(self, dev, entry_limit, ports):
    super(Chain, self).__init__(dev, entry_limit, ports)
    self.vdev_chain = [] # vdev_names (strings)

  def handle_request(self, parameters):
    return super(Chain, self).handle_request(parameters)

  def insert(self, parameters):
    # parameters:
    # <virtual device name> <position> <egress handling mode>
    vdev_name = parameters[0]
    position = int(parameters[1])
    egress_mode = parameters[2]

    # validate request
    # - validate vdev_name
    if vdev_name not in self.vdevs:
      return 'Error - ' + vdev_name + ' not found'

    vdev = self.vdevs[vdev_name]
    vdev_ID = vdev.virtual_device_ID

    commands = []    
    chain = self.vdev_chain
    
    if position == 0:
      if len(chain) > 0:
        # entry point: table_modify
        for port in self.assignments:
          handle = self.assignment_handles[port]
          command_type = 'table_modify'
          attribs = {'table': 'tset_context',
                     'action': 'a_set_context',
                     'handle': str(handle),
                     'aparams': [str(vdev_ID)]}
          commands.append(P4Command(command_type, attribs))
      else:
        # entry point: table_add
        for port in self.ports:
          command_type = 'table_add'
          attribs = {'table': 'tset_context',
                     'action': 'a_set_context',
                     'mparams': [str(port)],
                     'aparams': [str(vdev_ID)]}
          commands.append(P4Command(command_type, attribs))
          # TODO: ensure self.assignments is updated

    elif len(chain) > 0:
      # link left vdev to new vdev
      # this involves modifying all t_virtnet and t_egr_virtnet rules for the leftvdev
      leftvdev_name = chain[position - 1]
      leftvdev = self.vdevs[leftvdev_name]
      # modify rules referenced by leftvdev.t_virtnet_handles,
      # leftvdev.t_egr_virtnet_handles
      for handle in leftvdev.t_virtnet_handles:
        command_type = 'table_modify'
        attribs = {'table': 't_virtnet',
                   'action': 'do_virt_fwd',
                   'handle': str(handle),
                   'aparams': []}
        commands.append(P4Command(command_type, attribs))
      for handle in leftvdev.t_egr_virtnet_handles:
        command_type = 'table_modify'
        attribs = {'table': 't_egr_virtnet',
                   'action': 'vfwd',
                   'handle': str(handle),
                   'aparams': [str(vdev_ID), str(len(self.ports) + vdev_ID)]}
        commands.append(P4Command(command_type, attribs))

      if position < len(chain):
        # link new vdev to next vdev
        rightvdev_name = chain[position]
        rightvdev = self.vdevs[rightvdev_name]
        rightvdev_vingress = str(len(self.ports) + rightvdev.virtual_device_ID)
        for vegress in self.egress_map:
          command_type = 'table_add'
          attribs = {'table': 't_virtnet',
                     'action': 'do_virt_fwd',
                     'mparams': [str(vdev_ID), str(vegress)],
                     'aparams': []}
          commands.append(P4Command(command_type, attribs))
          attribs = {'table': 't_egr_virtnet',
                     'action': 'vfwd',
                     'mparams': [str(vdev_ID), str(vegress)],
                     'aparams': [str(rightvdev.virtual_device_ID),
                                 rightvdev_vingress]}
          commands.append(P4Command(command_type, attribs))

    if position == len(chain):
      # link new instance to physical ports
      for vegress in self.egress_map:
        # TODO: add support for multicast groups.
        #  Involves inserting an 'if' clause:
        #   if type(self.device) == Bmv2_SSwitch and vegress in self.multicast_specs
        #      t_virtnet do_phys_mcast VDEV VEGRESS_SPEC => map[VEGRESS_SPEC]
        command_type = 'table_add'
        attribs = {'table': 't_virtnet',
                   'action': 'do_phys_fwd_only',
                   'mparams': [str(vdev_ID), str(vegress)],
                   'aparams': [self.egress_map[vegress]]}
        commands.append(P4Command(command_type, attribs))

    chain.insert(position, vdev_name)

    for command in commands:
      # TODO: update assignments / assignment_handles
      self.send_command(command)
    
    return 'Virtual Device ' + vdev_name + ' inserted at position ' + str(position)

  def append(self, vdev_name):
    pass
  def remove(self, vdev_name):
    pass

  def __str__(self):
    ret = ''
    for i in range(len(self.vdev_chain)):
      ret += ' -> ' + self.vdev_chain[i]
    return ret

class DAG(Lease):
  pass

class VirtualNetwork(Lease):
  pass
