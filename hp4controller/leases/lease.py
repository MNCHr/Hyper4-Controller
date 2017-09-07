from ..virtualdevice.virtualdevice import VirtualDevice
from ..p4command import P4Command
from ..errors import AddRuleError, LoadError, VirtnetError

import code
# code.interact(local=dict(globals(), **locals()))

class Lease(object):
  def __init__(self, dev_name, dev, entry_limit, ports):
    self.dev_name = dev_name
    self.device = dev
    self.entry_limit = entry_limit
    self.entry_usage = 0
    self.ports = ports
    self.vdevs = {} # {vdev_name (string): vdev (VirtualDevice)}
    self.assignments = {} # {pport : vdev_ID}
    self.assignment_handles = {} # {pport : tset_context rule handle}
    vegress_val = 1
    self.egress_map = {} # {vegress_spec (int): egress_spec (int)}
    self.ingress_map = {} # {pport (int): virt_ingress_port (int)}
    # note, following assumes port id == egress_spec
    for port in ports:
      self.egress_map[vegress_val] = port
      self.ingress_map[port] = vegress_val
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

  def load_virtual_device(self, vdev_name, vdev, egress_mode):
    # validate request
    # - validate vdev_name
    if vdev_name in self.vdevs:
      raise LoadError(vdev_name + ' already present')

    # - validate lease has sufficient entries
    entries_available = self.entry_limit - self.entry_usage
    if (len(vdev.hp4_code_and_rules) > entries_available):
      raise LoadError('request('+ str(len(vdev.hp4_code_and_rules)) + ') \
              exceeds entries available(' + str(entries_available) + ')')

    # - validate virtual device not already somewhere else
    if vdev.dev_name != 'none':
      raise LoadError('first remove ' + vdev_name + ' from ' + vdev.dev_name)

    vdev.hp4_code_and_rules = {}

    for ruleset in [vdev.hp4code, vdev.hp4rules]:
      for rule in ruleset:
        try:
          table = rule.table
          command_type = 'table_add'
          action = rule.action
          aparams = list(rule.aparams)

          if egress_mode == 'efalse':
            if ('t_mod_' in table) and ('mod_stdmeta_egressspec' in rule.action):
              action = '_no_op'

          elif egress_mode == 'econd':
            if (table == 'tset_pipeline_config'):
              aparams[2] = '1'

          elif egress_mode != 'etrue':
            raise LoadError('Invalid egress handling mode: ' + egress_mode)

          attribs = {'table': table,
                     'action': action,
                     'mparams': rule.mparams,
                     'aparams': aparams}
          handle = self.send_command(P4Command(command_type, attribs))
          vdev.hp4_code_and_rules[(table, handle)] = rule
          
        except AddRuleError as e:
          # remove all entries already added
          for table, handle in vdev.hp4_code_and_rules.keys():
            rule_identifier = table + ' ' + str(handle)
            self.device.do_table_delete(rule_identifier)
            del vdev.hp4_code_and_rules[(table, handle)]
          raise LoadError('Lease::insert: ' + str(e))

    self.entry_usage += len(vdev.hp4code) + len(vdev.hp4rules)

  def handle_request(self, parameters, vdev):
    command = parameters[0]
    resp = ""
    try:
      resp = getattr(self, command)(parameters[1:], vdev)
    except AttributeError as e:
      return "AttributeError(handle_request - " + command + "): " + str(e)
    except Exception as e:
      return "Unexpected error: " + str(e)
    return resp

  def send_command(self, p4cmd):
    "Send command to associated device, return handle"
    return self.device.send_command(self.device.command_to_string(p4cmd))

  def remove(self, parameters, vdev):
    "Remove virtual device from Lease (does not destroy virtual device)"
    vdev_name = parameters[0]
    num_entries = len(vdev.hp4_code_and_rules)
    # pull all virtual device related rules from device
    for table, handle in vdev.hp4_code_and_rules.keys():
      rule_identifier = table + ' ' + str(handle)
      self.device.do_table_delete(rule_identifier)
    vdev.hp4_code_and_rules = {}

    self.entry_usage -= num_entries

    vdev.dev_name = 'none'

    # make lease forget about it (Lease's owning Slice still has it)
    del self.vdevs[vdev_name]

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
  def __init__(self, dev_name, dev, entry_limit, ports):
    super(Chain, self).__init__(dev_name, dev, entry_limit, ports)
    self.vdev_chain = [] # vdev_names (strings)

  def handle_request(self, parameters, vdev):
    return super(Chain, self).handle_request(parameters, vdev)

  def p2vdev(self, vdev):
    "Connect physical interfaces to virtual device"
    vdev_ID = vdev.virtual_device_ID
    if len(self.assignments) > 0:
      # table_modify
      for port in self.assignments:
        handle = self.assignment_handles[port]
        command_type = 'table_modify'
        attribs = {'table': 'tset_context',
                   'action': 'a_set_context',
                   'handle': str(handle),
                   'aparams': [str(vdev_ID), str(self.ingress_map[port])]}
        command = P4Command(command_type, attribs)
        self.assignments[port] = vdev_ID
        # self.assignments_handles[port] =  <- handle doesn't change
        self.send_command(command)
    else:
      # table_add
      for port in self.ports:
        command_type = 'table_add'
        attribs = {'table': 'tset_context',
                   'action': 'a_set_context',
                   'mparams': [str(port)],
                   'aparams': [str(vdev_ID), str(self.ingress_map[port])]}
        command = P4Command(command_type, attribs)
        self.assignments[port] = vdev_ID
        self.assignment_handles[port] = self.send_command(command)

  def vdev2p(self, vdev):
    "Connect virtual device to physical interfaces"
    vdev_ID = vdev.virtual_device_ID
    # t_virtnet
    # t_egr_virtnet
    if len(vdev.t_virtnet_handles) > 0:
      # table_modify
      # self.t_virtnet_handles = {} # KEY: vegress_spec (int)
                                    # VALUE: hp4-facing handle (int)
      for vegress in vdev.t_virtnet_handles:
        command_type = 'table_modify'
        attribs = {'table': 't_virtnet',
                   'action': 'do_phys_fwd_only',
                   'handle': str(vdev.t_virtnet_handles[vegress]),
                   'aparams': [self.egress_map[vegress]]}
        self.send_command(P4Command(command_type, attribs))

      if len(vdev.t_egr_virtnet_handles) > 0:
        # eliminate
        command_type = 'table_delete'
        for vegress in vdev.t_egr_virtnet_handles.keys():
          attribs = {'table': 't_egr_virtnet',
                     'handle': str(vdev.t_egr_virtnet_handles[vegress])}
          self.send_command(P4Command(command_type, attribs))
          del vdev.t_egr_virtnet_handles[vegress]
        
    else:
      if len(vdev.t_egr_virtnet_handles) > 0:
        raise VirtnetError('vdev2p: t_egr_virtnet has entries when t_virtnet doesn\'t')
      # table_add
      for vegress in self.egress_map:
        command_type = 'table_add'
        attribs = {'table': 't_virtnet',
                   'action': 'do_phys_fwd_only',
                   'mparams': [str(vdev_ID), str(vegress)],
                   'aparams': [self.egress_map[vegress]]}
        handle = self.send_command(P4Command(command_type, attribs))
        vdev.t_virtnet_handles[vegress] = handle

  def vdev2vdev(self, src_vdev, dest_vdev):
    "Connect source virtual device to destination virtual device"
    src_vdev_ID = src_vdev.virtual_device_ID
    dest_vdev_ID = dest_vdev.virtual_device_ID
    vingress = str(len(self.ports) + dest_vdev_ID)
    # t_virtnet src -> dest
    # t_egr_virtnet src -> dest
    if len(src_vdev.t_virtnet_handles) > 0:
      # table_modify
      for vegress in src_vdev.t_virtnet_handles:
        # self.t_virtnet_handles = {} # KEY: vegress_spec (int)
                                      # VALUE: hp4-facing handle (int)
        command_type = 'table_modify'
        attribs = {'table': 't_virtnet',
                   'action': 'do_virt_fwd',
                   'handle': str(src_vdev.t_virtnet_handles[vegress]),
                   'aparams': []}
        self.send_command(P4Command(command_type, attribs))
      if len(src_vdev.t_egr_virtnet_handles) > 0:
        # table_modify
        for vegress in src_vdev.t_virtnet_handles:
          command_type = 'table_modify'
          attribs = {'table': 't_egr_virtnet',
                     'action': 'vfwd',
                     'handle': str(src_vdev.t_egr_virtnet_handles[vegress]),
                     'aparams': [str(dest_vdev_ID), vingress]}
          self.send_command(P4Command(command_type, attribs))
      else:
        # table_add
        for vegress in src_vdev.t_virtnet_handles:
          command_type = 'table_add'
          attribs = {'table': 't_egr_virtnet',
                     'action': 'vfwd',
                     'mparams': [str(src_vdev_ID), str(vegress)],
                     'aparams': [str(dest_vdev_ID), vingress]}
          handle = self.send_command(P4Command(command_type, attribs))
          src_vdev.t_egr_virtnet_handles[vegress] = handle
        
    else:
      # table_add
      if len(src_vdev.t_egr_virtnet_handles) > 0:
        raise VirtnetError('vdev2vdev: t_egr_virtnet has entries when t_virtnet doesn\'t')
      for vegress in self.egress_map:
        command_type = 'table_add'
        attribs = {'table': 't_virtnet',
                   'action': 'do_virt_fwd',
                   'mparams': [str(src_vdev_ID), str(vegress)],
                   'aparams': []}
        handle = self.send_command(P4Command(command_type, attribs))
        src_vdev.t_virtnet_handles[vegress] = handle
        attribs = {'table': 't_egr_virtnet',
                   'action': 'vfwd',
                   'mparams': [str(src_vdev_ID), str(vegress)],
                   'aparams': [str(dest_vdev_ID), vingress]}
        handle = self.send_command(P4Command(command_type, attribs))
        src_vdev.t_egr_virtnet_handles[vegress] = handle

  def insert(self, parameters, vdev):
    # parameters:
    # <virtual device name> <position> <egress handling mode>
    vdev_name = parameters[0]
    position = int(parameters[1])
    egress_mode = parameters[2]

    vdev_ID = vdev.virtual_device_ID

    try:
      self.load_virtual_device(vdev_name, vdev, egress_mode)
    except LoadError as e:
      return 'Error - could not load ' + vdev_name + '; ' + str(e)

    chain = self.vdev_chain

    if position == 0:
      self.p2vdev(vdev)
    if position >= len(chain):
      self.vdev2p(vdev)
    if len(chain) > 0 and position < len(chain):
      rightvdev_name = chain[position]
      rightvdev = self.vdevs[rightvdev_name]
      self.vdev2vdev(vdev, rightvdev)
    if len(chain) > 0 and position > 0:
      leftvdev_name = chain[position - 1]
      leftvdev = self.vdevs[leftvdev_name]
      self.vdev2vdev(leftvdev, vdev)

    chain.insert(position, vdev_name)

    vdev.dev_name = self.dev_name
    self.vdevs[vdev_name] = vdev
    
    return 'Virtual Device ' + vdev_name + ' inserted at position ' + str(position)

  def append(self, parameters, vdev):
    # parameters:
    # <virtual device name> <egress handling mode>

    parameters.insert(1, len(self.vdev_chain))

    return self.insert(parameters, vdev)

  def remove(self, parameters, vdev):
    vdev_name = parameters[0]

    # delete vdev's t_virtnet/t_egr_virtnet entries
    for vegress in vdev.t_virtnet_handles.keys():
      handle = vdev.t_virtnet_handles[vegress]
      attribs = {'table': 't_virtnet',
                 'handle': str(handle)}
      self.send_command(P4Command('table_delete', attribs))
      del vdev.t_virtnet_handles[vegress]
    for vegress in vdev.t_egr_virtnet_handles.keys():
      handle = vdev.t_egr_virtnet_handles[vegress]
      attribs = {'table': 't_egr_virtnet',
                 'handle': str(handle)}
      self.send_command(P4Command('table_delete', attribs))
      del vdev.t_egr_virtnet_handles[vegress]

    chain = self.vdev_chain
    position = chain.index(vdev_name)

    if position == 0:
      if len(chain) > 1:
        # rightvdev exists; modify tset_context rules
        rightvdev_name = chain[1]
        rightvdev = self.vdevs[rightvdev_name]
        self.p2vdev(rightvdev)

      else:
        # no rightvdev; delete tset_context rules
        command_type = 'table_delete'
        for port in self.assignments.keys():
          attribs = {'table': 'tset_context',
                     'handle': str(self.assignment_handles[port])}
          self.send_command(P4Command(command_type, attribs))
          del self.assignments[port]
          del self.assignment_handles[port]
    else:
      leftvdev_name = chain[position - 1]
      leftvdev = self.vdevs[leftvdev_name]
      if position < (len(chain) - 1):
        rightvdev_name = chain[position + 1]
        rightvdev = self.vdevs[rightvdev_name]
        self.vdev2vdev(leftvdev, rightvdev)
      else:
        self.vdev2p(leftvdev)
          
    super(Chain, self).remove(parameters, vdev)
    chain.remove(vdev_name)

    return 'Virtual device ' + vdev_name + ' removed'

  def __str__(self):
    ret = ''
    for i in range(len(self.vdev_chain)):
      ret += ' -> ' + self.vdev_chain[i]
    return ret

class DAG(Lease):
  pass

class VirtualNetwork(Lease):
  pass
