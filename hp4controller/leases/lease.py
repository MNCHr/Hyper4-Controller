from hp4controller.virtualdevice.virtualdevice import VirtualDevice
from hp4controller.virtualdevice.p4rule import P4Rule
from hp4controller.virtualdevice.interpret import Interpretation
from hp4controller.p4command import P4Command
from hp4controller.errors import AddRuleError, LoadError, VirtnetError

import copy

import code
from inspect import currentframe, getframeinfo

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))

FILTERED = 1
UNFILTERED = 0

filteredlookup = {'filtered': FILTERED, 'unfiltered': UNFILTERED}

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
    self.egress_map[0] = 0
    # note, following assumes port id == egress_spec
    for port in ports:
      self.egress_map[vegress_val] = port
      self.ingress_map[port] = vegress_val
      vegress_val += 1
    # get mcast_grp_id from device
    self.mcast_grp_id = self.device.assign_mcast_grp_id()
    # create/associate mcast_grp, mcast_node
    self.mcast_node_handle = self.device.mcast_setup(self.mcast_grp_id, self.ports)
    self.mcast_egress_specs = {} # {vegress_spec (int): FILTERED|UNFILTERED (int)}

  def revoke(self):
    for vdev_name in self.vdevs.keys():
      vdev = self.vdevs[vdev_name]
      vdev.dev_name = 'none'
      self.lease_remove([vdev_name], vdev)

    # delete rules for tset_context
    for port in self.assignments.keys():
      table = 'tset_context'
      handle = self.assignment_handles[port]
      rule_identifier = table + ' ' + str(handle)
      self.device.do_table_delete(rule_identifier)
    self.assignments = {}
    self.assignment_handles = {}

    # delete mcast group and node
    self.device.mcast_teardown(self.mcast_grp_id, self.mcast_node_handle)

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

    if 'vib_dec' in vdev_name:
      debug()

    vdev.hp4_code_and_rules = {}

    def func(rule):
      table = rule.table
      command_type = 'table_add'
      action = rule.action
      aparams = list(rule.aparams)

      if egress_mode == 'efalse':
        if ('t_mod_' in table) and ('mod_stdmeta_egressspec' in rule.action):
          action = '_no_op'
          aparams = aparams[-1]

      elif egress_mode == 'econd':
        if (table == 'tset_pipeline_config'):
          aparams[2] = '1'

      elif egress_mode != 'etrue':
        raise LoadError('Invalid egress handling mode: ' + egress_mode)

      if action == 'mod_intmeta_mcast_grp_const':
        aparams[0] = str(self.mcast_grp_id)

      attribs = {'table': table,
                 'action': action,
                 'mparams': rule.mparams,
                 'aparams': aparams}

      debug()
      handle = self.send_command(P4Command(command_type, attribs))
      return table, handle

    def addRuleErrorHandler(e):
      # remove all entries already added
      for table, handle in vdev.hp4_code_and_rules.keys():
        rule_identifier = table + ' ' + str(handle)
        self.device.do_table_delete(rule_identifier)
        del vdev.hp4_code_and_rules[(table, handle)]
      raise LoadError('Lease::insert: ' + str(e))
     
    for rule in vdev.hp4code:
      try:
        table, handle = func(rule)
        vdev.hp4_code_and_rules[(table, handle)] = rule
          
      except AddRuleError as e:
        addRuleErrorHandler(e)

    new_hp4rules = {}
    for nrule in vdev.nrules:
      interp = vdev.nrules[nrule]
      new_hp4_rule_keys = []
      for key in interp.hp4_rule_keys:
        rule = vdev.hp4rules[(key[0], key[2])]

        try:
          table, handle = func(rule)
          vdev.hp4_code_and_rules[(table, handle)] = rule
          new_hp4_rules[(table, handle)] = rule

        except AddRuleError as e:
          addRuleErrorHandler(e)
        if key[2] < 0:
          new_hp4_rule_keys.append((key[0], key[1], key[2] * -1))
        else:
          new_hp4_rule_keys.append(key)

      interp.hp4_rule_keys = new_hp4_rule_keys

    vdev.hp4rules = new_hp4rules

    self.entry_usage += len(vdev.hp4code) + len(vdev.hp4rules)

  def send_command(self, p4cmd):
    "Send command to associated device, return handle"
    return self.device.send_command(self.device.command_to_string(p4cmd))

  def lease_remove(self, parameters, vdev):
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

  def lease_config_egress(self, parameters):
    egress_spec = int(parameters[0])
    command_type = parameters[1]
    self.mcast_egress_specs[egress_spec] = filteredlookup[parameters[2]]

    return 'Egress ' + str(egress_spec) + ' configured'

  def lease_dump(self):
    ret = ''
    for vdev in self.vdevs:
      ret += self.vdevs[vdev].info()
    return ret[:-1]

  def print_vdevs(self):
    ret = ''
    for vdev in self.vdevs:
      ret += '  ' + vdev + '\n'
    return ret

  def __str__(self):
    ret = 'entry usage/limit: ' + str(self.entry_usage) + '/' \
                                + str(self.entry_limit) + '\n'
    ret += 'ports:' + str(self.ports) + '\n'
    ret += 'virtual devices:\n'
    ret += self.print_vdevs()
    #ret += 'composition: ' + str(self.composition)
    return ret

class Chain(Lease):
  def __init__(self, dev_name, dev, entry_limit, ports):
    super(Chain, self).__init__(dev_name, dev, entry_limit, ports)
    self.vdev_chain = [] # vdev_names (strings)

  def handle_request(self, parameters, *args):
    return super(Chain, self).handle_request(parameters, args)

  def print_vdevs(self):
    ret = ''
    for vdev in self.vdev_chain:
      ret += '  ' + vdev + '\n'
    return ret

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

  def install_mcast_rules(self, vdev, vegress):
    vdev_ID = vdev.virtual_device_ID
    command_type = 'table_add'
    filtered = self.mcast_egress_specs[vegress]
    attribs = self.device.get_mcast_attribs(vdev_ID,
                                            vegress,
                                            self.mcast_grp_id,
                                            filtered)
    handle = self.send_command(P4Command(command_type, attribs))
    vdev.t_virtnet_handles[vegress] = handle

  def vdev2p(self, vdev):
    "Connect virtual device to physical interfaces"
    vdev_ID = vdev.virtual_device_ID
    # t_virtnet
    # t_egr_virtnet
    if len(vdev.t_virtnet_handles) > 0:
      # table_delete
      # self.t_virtnet_handles = {} # KEY: vegress_spec (int)
                                    # VALUE: hp4-facing handle (int)
      for vegress in vdev.t_virtnet_handles.keys():
        attribs = {'table': 't_virtnet',
                   'handle': str(vdev.t_virtnet_handles[vegress])}
        self.send_command(P4Command('table_delete', attribs))
        del vdev.t_virtnet_handles[vegress]

      if len(vdev.t_egr_virtnet_handles) > 0:
        # eliminate
        for vegress in vdev.t_egr_virtnet_handles.keys():
          attribs = {'table': 't_egr_virtnet',
                     'handle': str(vdev.t_egr_virtnet_handles[vegress])}
          self.send_command(P4Command('table_delete', attribs))
          del vdev.t_egr_virtnet_handles[vegress]
        
    else:
      if len(vdev.t_egr_virtnet_handles) > 0:
        raise VirtnetError('vdev2p: t_egr_virtnet has entries when t_virtnet doesn\'t')

    for vegress in self.mcast_egress_specs:
      self.install_mcast_rules(vdev, vegress)

    for vegress in self.egress_map:
      command_type = 'table_add'
      attribs = {'table': 't_virtnet',
                 'action': 'do_phys_fwd_only',
                 'mparams': [str(vdev_ID), str(vegress)],
                 'aparams': [str(self.egress_map[vegress]), str(UNFILTERED)]}
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

      for vegress in src_vdev.t_virtnet_handles:
        # self.t_virtnet_handles = {} # KEY: vegress_spec (int)
                                      # VALUE: hp4-facing handle (int)
        command_type = 'table_modify'
        attribs = {'table': 't_virtnet',
                   'action': 'do_virt_fwd',
                   'handle': str(src_vdev.t_virtnet_handles[vegress]),
                   'aparams': []}
        self.send_command(P4Command(command_type, attribs))
        
    else:
      # table_add
      if len(src_vdev.t_egr_virtnet_handles) > 0:
        raise VirtnetError('vdev2vdev: t_egr_virtnet has entries when t_virtnet doesn\'t')

      command_type = 'table_add'
      for vegress in self.egress_map:
        attribs = {'table': 't_egr_virtnet',
                   'action': 'vfwd',
                   'mparams': [str(src_vdev_ID), str(vegress)],
                   'aparams': [str(dest_vdev_ID), vingress]}
        handle = self.send_command(P4Command(command_type, attribs))
        src_vdev.t_egr_virtnet_handles[vegress] = handle
      for vegress in self.egress_map:
        attribs = {'table': 't_virtnet',
                   'action': 'do_virt_fwd',
                   'mparams': [str(src_vdev_ID), str(vegress)],
                   'aparams': []}
        handle = self.send_command(P4Command(command_type, attribs))
        src_vdev.t_virtnet_handles[vegress] = handle

  def lease_replace(self, parameters, vdev, new_vdev):
    # parameters:
    # <old virtual device name> <new virtual device name> <egress mode>
    vdev_name = parameters[0]
    new_vdev_name = parameters[1]
    egress_mode = parameters[2]

    try:
      self.load_virtual_device(new_vdev_name, new_vdev, egress_mode)
    except LoadError as e:
      if 'already present' in str(e):
        pass
      else:
        return 'Error - could not load ' + new_vdev_name + '; ' + str(e)

    chain = self.vdev_chain
    position = chain.index(vdev_name)

    if position >= len(chain) - 1:
      self.vdev2p(new_vdev)
    if (len(chain) > 0) and (position < len(chain) - 1):
      rightvdev_name = chain[position + 1]
      rightvdev = self.vdevs[rightvdev_name]
      self.vdev2vdev(new_vdev, rightvdev)
    if len(chain) > 0 and position > 0:
      leftvdev_name = chain[position - 1]
      leftvdev = self.vdevs[leftvdev_name]
      self.vdev2vdev(leftvdev, new_vdev)
    if position == 0:
      self.p2vdev(new_vdev)

    # update vdev_chain
    chain.remove(vdev_name)
    chain.insert(position, new_vdev_name)
    return 'Virtual device ' + vdev_name + ' replaced with ' + new_vdev_name

  def lease_insert(self, parameters, vdev):
    # parameters:
    # <virtual device name> <position> <egress handling mode>
    vdev_name = parameters[0]
    position = int(parameters[1])
    egress_mode = parameters[2]

    vdev_ID = vdev.virtual_device_ID

    try:
      self.load_virtual_device(vdev_name, vdev, egress_mode)
    except LoadError as e:
      if 'already present' in str(e):
        pass
      else:
        return 'Error - could not load ' + vdev_name + '; ' + str(e)

    chain = self.vdev_chain

    #debug()

    if position >= len(chain):
      self.vdev2p(vdev)
    if (len(chain) > 0) and (position < len(chain)):
      rightvdev_name = chain[position]
      rightvdev = self.vdevs[rightvdev_name]
      self.vdev2vdev(vdev, rightvdev)
    if len(chain) > 0 and position > 0:
      leftvdev_name = chain[position - 1]
      leftvdev = self.vdevs[leftvdev_name]
      self.vdev2vdev(leftvdev, vdev)
    if position == 0:
      self.p2vdev(vdev)

    chain.insert(position, vdev_name)

    vdev.dev_name = self.dev_name
    self.vdevs[vdev_name] = vdev

    vdev.mcast_grp_id = self.mcast_grp_id
    
    return 'Virtual Device ' + vdev_name + ' inserted at position ' + str(position)

  def lease_append(self, parameters, vdev):
    # parameters:
    # <virtual device name> <egress handling mode>

    parameters.insert(1, len(self.vdev_chain))

    return self.lease_insert(parameters, vdev)

  def lease_remove(self, parameters, vdev):
    vdev_name = parameters[0]

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

          
    super(Chain, self).lease_remove(parameters, vdev)
    chain.remove(vdev_name)

    return 'Virtual device ' + vdev_name + ' removed'

  def lease_config_egress(self, parameters):
    super(Chain, self).lease_config_egress(parameters)
    vegress = int(parameters[0])
    if len(self.vdev_chain) > 0:
      end_vdev_name = self.vdev_chain[-1]
      end_vdev = self.vdevs[end_vdev_name]
      self.install_mcast_rules(end_vdev, vegress)
    return 'Chain: Egress ' + str(vegress) + ' configured'

  def __str__(self):
    ret = super(Chain, self).__str__()
    ret += 'Chain: \n'
    for i in range(len(self.vdev_chain)):
      ret += ' -> ' + self.vdev_chain[i]
    return ret

class DAG(Lease):
  pass

class VirtualNetwork(Lease):
  pass
