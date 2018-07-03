#!/usr/bin/python

from p4_hlir.main import HLIR
from p4_hlir.hlir.p4_parser import p4_parse_state
import p4_hlir
from compiler import HP4Compiler, CodeRepresentation
import argparse
import itertools
import code
from inspect import currentframe, getframeinfo
import sys
import math
import json

SEB = 320
METADATA_WIDTH = 256

PS_RET_TYPE = 0
PS_RET_CRITERIA = 1
PS_RET_BRANCHES = 2
PS_RET_IMM_STATE = 1
PS_CALL_TYPE = 0
PS_CALL_H_INST = 1
OFFSET = 0
WIDTH = 1
BRANCH_VALUES = 0
BRANCH_STATE = 1
VAL_TYPE = 0
VAL_VALUE = 1
MAX_BYTE = 100
T_NAME = 0
L_BOUND = 1
U_BOUND = 2
HIGHEST_PRIORITY = '0'
LOWEST_PRIORITY = '2147483646'
VBITS_WIDTH = 80

parse_select_table_boundaries = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100]

current_call = tuple

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))

def convert_to_builtin_type(obj):
  d = { '__class__':obj.__class__.__name__, '__module__':obj.__module__, }
  d.update(obj.__dict__)
  return d

class HP4_Command(object):
  def __init__(self, command='table_add',
                     table='',
                     action='',
                     match_params=[],
                     action_params=[]):
    self.command = command
    self.table = table
    self.action = action
    self.match_params = match_params
    self.action_params = action_params
  def __str__(self):
    """ assumes command is \'table_add\' """
    if self.command != 'table_add':
      raise Exception("Incorrect table command %s, table %s" % (self.command, self.table))
    ret = self.table + ' ' + self.action + ' :'
    ret += ' '.join(self.match_params)
    ret += ':'
    ret += ' '.join(self.action_params)
    return ret

class HP4_Match_Command(HP4_Command):
  def __init__(self, source_table='',
                     source_action='',
                     **kwargs):
    super(HP4_Match_Command, self).__init__(**kwargs)
    self.source_table = source_table
    self.source_action = source_action

class HP4_Primitive_Command(HP4_Command):
  def __init__(self, source_table, source_action, command, table, action, mparams, aparams, src_aparam_id):
    HP4_Command.__init__(self, command, table, action, mparams, aparams)
    self.source_table = source_table
    self.source_action = source_action
    self.src_aparam_id = src_aparam_id

class DAG_Topo_Sorter():
  def __init__(self, p4_tables):
    self.unmarked = []
    self.tempmarked = []
    self.permmarked = []
    self.L = []
    for key in p4_tables:
      self.unmarked.append(p4_tables[key])

  def visit(self, n):
    if n.control_flow_parent == 'egress':
      print("ERROR: Not yet supported: tables in egress (" + n.name + ")")
      exit()
    if n in self.tempmarked:
      print("ERROR: not a DAG")
      exit()
    if n in self.unmarked:
      self.unmarked.remove(n)
      self.tempmarked.append(n)
      for m in n.next_.values():
        if m != None:
          self.visit(m)
      self.permmarked.append(n)
      self.tempmarked.remove(n)
      self.L.insert(0, n)

  def sort(self):      
    while len(self.unmarked) > 0: # while there are unmarked nodes do
      n = self.unmarked[0]
      self.visit(n)
    return self.L

class Table_Rep():
  def __init__(self, stage, match_type, source_type, field_name):
    self.stage = stage # int
    self.match_type = match_type
    self.source_type = source_type
    self.field_name = field_name
    self.name = 't' + str(self.stage) + '_'
    if source_type == 'standard_metadata':
      self.name += 'stdmeta_' + field_name + '_'
    elif source_type == 'metadata':
      self.name += 'metadata_'
    elif source_type == 'extracted':
      self.name += 'extracted_'
    if match_type == 'P4_MATCH_EXACT':
      self.name += 'exact'
    elif match_type == 'P4_MATCH_VALID':
      self.name += 'valid'
    elif match_type == 'P4_MATCH_TERNARY':
      self.name += 'ternary'
    elif match_type == 'MATCHLESS':
      self.name += 'matchless'
  def table_type(self):
    if self.source_type == 'standard_metadata':
      if self.match_type == 'P4_MATCH_EXACT':
        if self.field_name == 'ingress_port':
          return '[STDMETA_INGRESS_PORT_EXACT]'
        elif self.field_name == 'packet_length':
          return '[STDMETA_PACKET_LENGTH_EXACT]'
        elif self.field_name == 'instance_type':
          return '[STDMETA_INSTANCE_TYPE_EXACT]'
        elif self.field_name == 'egress_spec':
          return '[STDMETA_EGRESS_SPEC_EXACT]'
        else:
          print("Not supported: standard_metadata field %s" % self.field_name)
          exit()
      else:
        print("Not supported: standard_metadata with %s match type" % self.match_type)
        exit()
    elif self.source_type == 'metadata':
      if self.match_type == 'P4_MATCH_EXACT':
        return '[METADATA_EXACT]'
      elif self.match_type == 'P4_MATCH_TERNARY':
        return '[METADATA_TERNARY]'
      else:
        print("Not supported: metadata with %s match type" % self.match_type)
        exit()
    elif self.source_type == 'extracted':
      if self.match_type == 'P4_MATCH_EXACT':
        return '[EXTRACTED_EXACT]'
      elif self.match_type == 'P4_MATCH_VALID':
        return '[EXTRACTED_VALID]'
      elif self.match_type == 'P4_MATCH_TERNARY':
        return '[EXTRACTED_TERNARY]'
      else:
        print("Not supported: extracted with %s match type" % self.match_type)
        exit()
    elif self.source_type == '':
      if self.match_type == 'MATCHLESS':
        return '[MATCHLESS]'
      else:
        print("Not supported: [no source] with %s match type" % self.match_type)
        exit()
    else:
      print("Not supported: source type %s, match type %s" % (self.source_type, self.match_type))
      exit()
  def __str__(self):
    return self.name

class Action_Rep():
  def __init__(self):
    self.stages = set()
    self.tables = {} # {stage (int) : table_name (str)}
    self.next = {} # {table_name (str) : (next_stage (int), next_table_code (int))}
    self.call_sequence = []

class PC_State(object):
  newid = itertools.count().next
  def __init__(self, hp4_bits_extracted=SEB,
                     p4_bits_extracted=0,
                     ps_path=[],
                     pcs_path=[],
                     parse_state=None,
                     entry_table='tset_parse_control',
                     **kwargs):
    self.hp4_bits_extracted = hp4_bits_extracted
    self.p4_bits_extracted = p4_bits_extracted
    self.ps_path = ps_path
    self.pcs_path = pcs_path
    self.pcs_id = PC_State.newid()
    self.parse_state = parse_state
    self.entry_table = entry_table # TODO: Delete if we don't need this
    self.children = []
    self.header_offsets = {} # header name (str) : hp4 bit offset (int)
    for pcs in self.pcs_path:
      self.header_offsets.update(pcs.header_offsets)
    self.select_criteria = [] # list of (offset, width) tuples, each
                              #  element corresponding to a criteria in the
                              #  select statement, representing the hp4 view
    self.select_values = [] # list of lists: each member a list of values,
                            #  each value corresponding to a criteria in
                            #  select_criteria

  def __str__(self):
    ret = 'ID: ' + str(self.pcs_id) + '; ' + self.parse_state.name + '\n'
    ret += 'hp4_bits_extracted: ' + str(self.hp4_bits_extracted) + '\n'
    ret += 'p4_bits_extracted: ' + str(self.p4_bits_extracted) + '\n'
    ret += 'ps_path: ' + str(self.ps_path) + '\n'
    ret += 'pcs_path: ' 
    for pcs in self.pcs_path:
      ret += str(pcs.pcs_id) + '(' + pcs.parse_state.name + ') '
    ret += '\n'
    ret += 'children: '
    for child in self.children:
      ret += child.parse_state.name + ' '
    return ret

class P4_to_HP4(HP4Compiler):

  def collect_actions(self, actions):
    """ Uniquely number each action """
    action_ID = {}
    actionID = 1
    for action in actions:
      if action.lineno > 0: # is action from source (else built-in)?
        action_ID[action] = actionID
        actionID += 1
    return action_ID

  def build(self, h):

    self.action_ID = self.collect_actions(h.p4_actions.values())

    pre_pcs = PC_State(parse_state=h.p4_parse_states['start'])
    launch_process_parse_tree_clr(pre_pcs, h)
    consolidate_parse_tree_clr(pre_pcs, h)

    first_table = h.p4_ingress_ptr.keys()[0]
    self.commands = gen_parse_control_entries(pre_pcs) \
                  + gen_parse_select_entries(pre_pcs) \
                  + gen_pipeline_config_entries(pre_pcs, first_table)
    self.command_templates = gen_tX_templates(first_table)

  def compile_to_hp4(self, program_path, out_path, mt_out_path, numprimitives):
    self.out_path = out_path
    self.mt_out_path = mt_out_path
    numprimitives = numprimitives
    h = HLIR(program_path)
    h.build()
    do_support_checks(h)
    self.build(h)
    self.write_output()

    return CodeRepresentation(out_path, mt_out_path)

  def write_output(self):
    out = open(self.out_path, 'w')
    for command in self.commands:
      out.write(str(command) + '\n')
    out.close()
    out = open(self.mt_out_path, 'w')
    json.dump(self.command_templates, out, default=convert_to_builtin_type, indent=2)
    out.close()

def do_support_checks(h):
  def unsupported(msg):
    print(msg)
    exit()

  # Not sure how this would happen in P4 but HLIR suggests the possibility:
  if len(h.p4_ingress_ptr.keys()) > 1:
    unsupported("Not supported: multiple entry points into the ingress pipeline")
  # Tables with multiple match criteria:
  for table in h.p4_tables.values():
    if len(table.match_fields) > 1:
      unsupported("Not supported: multiple field matches (table: %s)" % table.name)

def get_parse_select_table_code(first_byte):
  for i in range(len(parse_select_table_boundaries) - 1):
    lowerbound = parse_select_table_boundaries[i]
    upperbound = parse_select_table_boundaries[i+1]
    if first_byte >= lowerbound and first_byte < upperbound:
      ret = '[PARSE_SELECT_'
      ret += '%02d_%02d]' % (lowerbound, upperbound - 1)
      return ret
  raise Exception("Did not find parse_select table; first_byte: %d" % first_byte)

def get_pc_action(pcs):
  select_first_byte = MAX_BYTE
  for criteria in pcs.select_criteria:
    select_first_byte = min(criteria[OFFSET] / 8, select_first_byte)
  return get_parse_select_table_code(select_first_byte)

def gen_pc_entry_start(pcs):
  """ Generate parse_control entries for pc 0/1:
       We need an entry for pc 1 only if SEB is insufficient
       to handle 'start', in which case the action for pc 0
       must be extract_more
  """
  start_pcs = pcs.children[0] # pc 0 always has one child: pc 1
  mparams = ['[vdev ID]', str(pcs.pcs_id)]
  aparams = []
  act = 'set_next_action'
  if start_pcs.p4_bits_extracted > pcs.hp4_bits_extracted:
    act = 'extract_more'
    aparams.append(str(start_pcs.p4_bits_extracted))
  else:
    if not start_pcs.children:
      aparams.append('[PROCEED]')
    else:
      aparams.append(get_pc_action(start_pcs))

  aparams.append(str(start_pcs.pcs_id))

  cmd = HP4_Command(command='table_add',
                    table='tset_parse_control',
                    action=act,
                    match_params=mparams,
                    action_params=aparams)
  return cmd

def get_p_ps_tables(pcs):
  # sort
  sorted_criteria, sorted_branches, default_branch = sort_return_select(pcs)

  # revise branch_values, select_criteria per parse_select table boundaries
  revised_criteria, revised_branches = revise_return_select(pcs,
                                                            sorted_criteria,
                                                            sorted_branches)
  return get_parse_select_tables(revised_criteria)

def did_rewind(pcs):
  if not pcs.children:
    return False
  first_criteria = sort_return_select(pcs)[0][0]
  j = 0
  while parse_select_table_boundaries[j+1] * 8 <= first_criteria[OFFSET]:
    j += 1
  p_ps_tables = get_p_ps_tables(pcs.pcs_path[-1])
  if parse_select_table_boundaries[j] <= p_ps_tables[-1][L_BOUND]:
    return True
  return False

def gen_parse_control_entries(pcs, commands=[]):
  if pcs.pcs_id == 0:
    cmd = gen_pc_entry_start(pcs)
    commands.append(cmd)
    if cmd.action == 'extract_more':
      commands = gen_parse_control_entries(pcs.children[0], commands)
    else:
      for child in pcs.children[0].children:
        commands = gen_parse_control_entries(child, commands)
  
  else:
    if (pcs.pcs_path[-1].hp4_bits_extracted < pcs.hp4_bits_extracted or
        did_rewind(pcs)):
      mparams = ['[vdev ID]', str(pcs.pcs_id)]
      aparams = []
      act = 'set_next_action'
      if not pcs.children:
        aparams.append('[PROCEED]')
      else:
        aparams.append(get_pc_action(pcs))
      aparams.append(str(pcs.pcs_id))

      cmd = HP4_Command(command='table_add',
                        table='tset_parse_control',
                        action=act,
                        match_params=mparams,
                        action_params=aparams)

      commands.append(cmd)

    for child in pcs.children:
      commands = gen_parse_control_entries(child, commands)

  return commands

def get_new_val(val, width, offset, new_width):
  mask = 0
  bitpos = offset
  while bitpos < (offset + new_width):
    mask += 2**(width - bitpos - 1)
    bitpos += 1
  newval = val & mask
  newval = newval >> (width - (offset + new_width))
  return newval

def sort_return_select(pcs):
  if pcs.parse_state.return_statement[PS_RET_TYPE] == 'immediate':
    return [], [], None

  sorted_indices = sorted(range(len(pcs.select_criteria)),
                          key=pcs.select_criteria.__getitem__)
  sorted_criteria = []
  for i in sorted_indices:
    sorted_criteria.append(pcs.select_criteria[i])
  sorted_branches = []
  default_branch = None

  for branch in pcs.parse_state.return_statement[PS_RET_BRANCHES]:
    if branch[BRANCH_VALUES][0][VAL_TYPE] == 'value':
      sorted_values = []
      for i in sorted_indices:
        sorted_values.append(branch[BRANCH_VALUES][i][VAL_VALUE])
      sorted_branches.append((sorted_values, branch[BRANCH_STATE]))
    elif branch[BRANCH_VALUES][0][VAL_TYPE] == 'default':
      default_branch = branch
  return sorted_criteria, sorted_branches, default_branch

def revise_value(val, crit, j):
  curr_offset = crit[OFFSET]
  ret = []
  while curr_offset < (crit[OFFSET] + crit[WIDTH]):
    # setup
    diff = parse_select_table_boundaries[j+1] * 8 - curr_offset
    if diff > crit[WIDTH]:
      diff = crit[OFFSET] + crit[WIDTH] - curr_offset
    # rev_branch_values
    ret.append(get_new_val(val,
                           crit[WIDTH],
                           curr_offset - crit[OFFSET],
                           diff))
    # cleanup
    curr_offset += diff
    j += 1
  return ret

def revise_criteria(crit, j):
  ret = []
  curr_offset = crit[OFFSET]
  while curr_offset < (crit[OFFSET] + crit[WIDTH]):
    # setup
    diff = parse_select_table_boundaries[j+1] * 8 - curr_offset
    if diff > crit[WIDTH]:
      diff = crit[OFFSET] + crit[WIDTH] - curr_offset
    # update
    ret.append((curr_offset, diff))
    # cleanup
    curr_offset += diff
    j += 1
  return ret

def revise_return_select(pcs, sorted_criteria, sorted_branches):
  revised_criteria = []
  revised_branches = [[] for count in xrange(len(sorted_branches))]

  i = 0
  for crit in sorted_criteria:
    j = 0
    while parse_select_table_boundaries[j+1] * 8 <= crit[OFFSET]:
      j += 1

    # detect and handle broken boundary
    if parse_select_table_boundaries[j+1] * 8 <= (crit[OFFSET] + crit[WIDTH]):    
      revised_criteria += revise_criteria(crit, j)
      k = 0
      for branch in sorted_branches:
        val = branch[BRANCH_VALUES][i]
        revised_branches[k] += revise_value(val, crit, j)
        k += 1

    else:
      revised_criteria.append(crit)
      k = 0
      for branch in sorted_branches:
        val = branch[BRANCH_VALUES][i]
        revised_branches[k].append(val)
        k += 1

    i += 1

  return revised_criteria, revised_branches

def do_split_criteria(crit):
  try:
    assert(crit[WIDTH] % 8 == 0)
  except AssertionError as e:
    print(e)
    print("select criteria (" + str(crit[OFFSET]) + ", " + str(crit[WIDTH]) \
                              + ") not divisible by 8")
    exit()
  curr_offset = crit[OFFSET]
  split_crit = []
  while curr_offset < crit[OFFSET] + crit[WIDTH]:
    split_crit.append((curr_offset, 8))
    curr_offset += 8
  return split_crit

def do_split_val(val, width):
  ret = []
  mask = 0
  bitpos = 0
  offset = 0

  while offset < width:
    mask = 0
    while bitpos < offset + 8:
      mask += 2**(width - bitpos - 1)
      bitpos += 1
    ret.append((val & mask) >> (width - bitpos))
    offset += 8
  return ret  

def split_return_select(revised_criteria, revised_branches):
  split_criteria = []
  split_branches = [[] for count in xrange(len(revised_branches))]

  i = 0
  for crit in revised_criteria:
    split_crits = do_split_criteria(crit)
    for split_crit in split_crits:
      split_criteria.append(split_crit)
    j = 0
    for branch in revised_branches:
      val = branch[i]
      split_vals = do_split_val(val, crit[WIDTH])
      for split_val in split_vals:
        split_branches[j].append(split_val)
      j += 1
    i += 1

  return split_criteria, split_branches

def get_parse_select_table(crit):
  j = 0
  while parse_select_table_boundaries[j+1] * 8 <= crit[OFFSET]:
    j += 1
  lowerbound = parse_select_table_boundaries[j]
  upperbound = parse_select_table_boundaries[j+1]
  table_name = 'tset_parse_select_%02d_%02d' % (lowerbound, upperbound - 1)
  return table_name, lowerbound * 8, upperbound * 8

def get_parse_select_tables(revised_criteria):
  parse_select_tables = []
  for crit in revised_criteria:
    parse_select_table = get_parse_select_table(crit)
    if parse_select_table not in parse_select_tables:
      parse_select_tables.append(parse_select_table)
  return parse_select_tables

def get_mparam_indices(table, crits):
  mparam_indices = []
  for crit in crits:
    curr_offset = crit[OFFSET]
    while curr_offset < crit[OFFSET] + crit[WIDTH]:
      mparam_indices.append((curr_offset - table[L_BOUND]) / 8)
      curr_offset += 8
  return mparam_indices

def get_branch_mparams(branch_mparams, branch, mparam_indices):
  for index in mparam_indices:
    branch_mparams[index] = hex(branch.pop(0)) + '&&&0xFF'
  return branch_mparams

def get_ps_action(tablename):
  return '[' + tablename.split('tset_')[1].upper() + ']'

def get_branch_action(pcs, pst_count, parse_select_tables, branch):
  action = ''
  aparams = []

  if branch[BRANCH_STATE] == 'ingress':
    action = 'set_next_action'
    aparams.append('[PROCEED]')
    aparams.append(str(pcs.pcs_id))
    return action, aparams

  # set_next_action or extract_more
  if pst_count != len(parse_select_tables) - 1:
    action = 'set_next_action'
    aparams.append(get_ps_action(parse_select_tables[pst_count + 1][T_NAME]))
    aparams.append(str(pcs.pcs_id))
  else:
    next_pcs = [child for child in pcs.children \
                       if child.parse_state.name == branch[BRANCH_STATE]][0]

    if next_pcs.hp4_bits_extracted > pcs.hp4_bits_extracted:
      action = 'extract_more'
      aparams.append(str(next_pcs.hp4_bits_extracted))
    else:
      if not next_pcs.children:
        action = 'set_next_action'
        aparams.append('[PROCEED]')
        aparams.append(str(next_pcs.pcs_id))
        return action, aparams
      # another select statement in next pcs - need to rewind?
      n_first_criteria = sort_return_select(next_pcs)[0][0]
      j = 0
      while parse_select_table_boundaries[j+1] * 8 <= n_first_criteria[OFFSET]:
        j += 1
      if parse_select_table_boundaries[j] <= parse_select_tables[pst_count][L_BOUND]:
        # rewind
        action = 'extract_more'
        aparams.append(str(next_pcs.hp4_bits_extracted))
      else:
        action = 'set_next_action'
        next_ps_table = get_parse_select_table(n_first_criteria)
        aparams.append(get_ps_action(next_ps_table[T_NAME]))

    aparams.append(str(next_pcs.pcs_id))

  return action, aparams

def get_parse_select_entries(pcs,
                             parse_select_tables,
                             split_criteria,
                             split_branches_with_dests,
                             default_branch):
  commands = []
  # for each parse_select table:
  # - pop all queue items that belong to the table
  # - generate table entry
  for pst_count, table in enumerate(parse_select_tables):
    crits = []
    while (split_criteria[0][OFFSET] >= table[L_BOUND] and
           split_criteria[0][OFFSET] < table[U_BOUND]):
      crits.append(split_criteria.pop(0))
      if not split_criteria:
        break
    mparam_indices = get_mparam_indices(table, crits)
    mparams = ['0&&&0' for count in xrange((table[U_BOUND] - table[L_BOUND]) / 8)]
    for branch in split_branches_with_dests:
      branch_mparams = ['[vdev ID]', str(pcs.pcs_id)]
      branch_mparams += get_branch_mparams(list(mparams), branch[BRANCH_VALUES], mparam_indices)
      # determine action and action_params
      branch_action, branch_aparams = get_branch_action(pcs,
                                                        pst_count,
                                                        parse_select_tables,
                                                        branch)
      # priority
      branch_aparams.append(HIGHEST_PRIORITY)
      commands.append(HP4_Command(command='table_add',
                                  table=table[T_NAME],
                                  action=branch_action,
                                  match_params=branch_mparams,
                                  action_params=branch_aparams))
    # default branch
    default_mparams = ['[vdev ID]', str(pcs.pcs_id)]
    default_mparams += list(mparams)
    default_action, default_aparams = get_branch_action(pcs,
                                                        pst_count,
                                                        parse_select_tables,
                                                        default_branch)
    default_aparams.append(LOWEST_PRIORITY)
    commands.append(HP4_Command(command='table_add',
                                table=table[T_NAME],
                                action=default_action,
                                match_params=default_mparams,
                                action_params=default_aparams))

  return commands

def gen_parse_select_entries(pcs, commands=[]):
  # base cases
  if pcs.pcs_id == 0:
    return gen_parse_select_entries(pcs.children[0])
  if pcs.parse_state.return_statement[PS_RET_TYPE] == 'immediate':
    return commands

  # sort
  sorted_criteria, sorted_branches, default_branch = sort_return_select(pcs)

  # revise branch_values, select_criteria per parse_select table boundaries
  revised_criteria, revised_branches = revise_return_select(pcs,
                                                            sorted_criteria,
                                                            sorted_branches)

  split_criteria, split_branches = split_return_select(revised_criteria,
                                                       revised_branches)

  parse_select_tables = get_parse_select_tables(revised_criteria)

  dests = [branch[BRANCH_STATE] for branch in sorted_branches]

  commands += get_parse_select_entries(pcs,
                                       parse_select_tables,
                                       split_criteria,
                                       zip(split_branches, dests),
                                       default_branch)

  for child in pcs.children:
    commands = gen_parse_select_entries(child, commands)

  return commands

"""
def get_parse_state_maps(pcs, ps_to_pcs={}):
  if pcs.pcs_id == 0:
    return get_parse_state_maps(pcs.children[0])

  if ps_to_pcs.has_key(pcs.parse_state) is False:
    ps_to_pcs[pcs.parse_state] = set()

  ps_to_pcs[pcs.parse_state].add(pcs)
  
  for child in pcs.children:
    ps_to_pcs.update(get_parse_state_maps(child, ps_to_pcs))

  return ps_to_pcs
"""

def collect_ingress_pcs(pcs, ingress_pcs_list=[]):
  if pcs.pcs_id == 0:
    return collect_ingress_pcs(pcs.children[0])

  ps = pcs.parse_state

  if ps.return_statement[PS_RET_TYPE] == 'select':
    for branch in ps.return_statement[PS_RET_BRANCHES]:
      if branch[BRANCH_STATE] == 'ingress':
        ingress_pcs_list.append(pcs)
        break
  elif ps.return_statement[PS_RET_TYPE] == 'immediate':
    if ps.return_statement[PS_RET_IMM_STATE] == 'ingress':
      ingress_pcs_list.append(pcs)
  else:
    print("Unhandled ps return_statement: " + ps.return_statement[PS_RET_TYPE])
    exit()

  for child in pcs.children:
    ingress_pcs_list = collect_ingress_pcs(child, ingress_pcs_list)

  return ingress_pcs_list

def get_headerset_and_maxdepth(ingress_pcs_list):
  pcs_headers = {}
  longest = 0
  for pcs in ingress_pcs_list:
    if len(pcs.header_offsets) > longest:
      longest = len(pcs.header_offsets)
  headerset = [set() for count in xrange(longest)]
  for j in range(longest):
    for pcs in ingress_pcs_list:
      if len(pcs.header_offsets) > j:
        pcs_headers = sorted(pcs.header_offsets, key=pcs.header_offsets.get)
        headerset[j].add(pcs_headers[j])

  return headerset, longest

def get_vbits(headerset, maxdepth):
  vbits = {}
  lshift = VBITS_WIDTH
  for j in range(maxdepth):
    numbits = len(headerset[j])
    lshift = lshift - numbits
    i = 1
    for header in headerset[j]:
      vbits[(j, header)] = i << lshift
      i = i << 1
  return vbits

def get_hp4_type(header):
  if header.name == 'standard_metadata':
    return 'standard_metadata'
  if header.metadata == True:
    return 'metadata'
  return 'extracted'

def get_aparam_table_ID(table):
  if len(table.match_fields) == 0:
    return '[MATCHLESS]'

  field_match = table.match_fields[0] # supporting only one match field
  field = field_match[0]
  header = field.instance
  match_type = field_match[1]

  if match_type.value == 'P4_MATCH_EXACT':
    header_hp4_type = get_hp4_type(header)
    if header_hp4_type == 'standard_metadata':
      if field.name == 'ingress_port':
        return '[STDMETA_INGRESS_PORT_EXACT]'
      elif field.name == 'packet_length':
        return '[STDMETA_PACKET_LENGTH_EXACT]'
      elif field.name == 'instance_type':
        return '[STDMETA_INSTANCE_TYPE_EXACT]'
      elif field.name == 'egress_spec':
        return '[STDMETA_EGRESS_SPEC_EXACT]'
      else:
        print("ERROR: Unsupported: match on stdmetadata field %s" % field.name)
        exit()
    elif header_hp4_type == 'metadata':
      return '[METADATA_EXACT]'
    elif header_hp4_type == 'extracted':
      return '[EXTRACTED_EXACT]'
  elif match_type.value == 'P4_MATCH_VALID':
    return '[EXTRACTED_VALID]'
  else:
    print("Not yet supported: " + match_type.value)
    exit()
  
def gen_pipeline_config_entries(pcs, first_table):
  if pcs.pcs_id == 0:
    return gen_pipeline_config_entries(pcs.children[0], first_table)

  commands = []

  ingress_pcs_list = collect_ingress_pcs(pcs)
  headerset, maxdepth = get_headerset_and_maxdepth(ingress_pcs_list)
  vbits = get_vbits(headerset, maxdepth)
  aparam_table_ID = get_aparam_table_ID(first_table)  

  for pcs in ingress_pcs_list:
    val = 0
    for i, header in enumerate(pcs.header_offsets):
      val = val | vbits[(i, header)]
    valstr = '0x' + '%x' % val
    commands.append(HP4_Command('table_add',
                                'tset_pipeline_config',
                                'a_set_pipeline',
                                ['[vdev ID]', str(pcs.pcs_id)],
                                [aparam_table_ID, valstr, HIGHEST_PRIORITY]))

  return commands

def gen_tX_templates(first_table):
  pass

def process_extract_statements(pcs):
  for call in pcs.parse_state.call_sequence:
    if call[PS_CALL_TYPE] == p4_hlir.hlir.p4_parser.parse_call.extract:
      pcs.header_offsets[call[PS_CALL_H_INST].name] = pcs.p4_bits_extracted
      pcs.p4_bits_extracted += call[PS_CALL_H_INST].header_type.length * 8
      if pcs.hp4_bits_extracted < pcs.p4_bits_extracted:
        pcs.hp4_bits_extracted = pcs.p4_bits_extracted
    else:
      raise Exception('Unsupported parse call: %s' % call[PS_CALL_TYPE])

def process_parse_tree_clr(pcs, h):
  print(str(pcs.pcs_id) + ' [' + pcs.parse_state.name + ']')
  process_extract_statements(pcs)

  def add_next(next_parse_state):
    next_pcs_pcs_path = list(pcs.pcs_path)
    next_pcs_pcs_path.append(pcs)
    next_pcs_ps_path = list(pcs.ps_path)
    next_pcs_ps_path.append(pcs.parse_state)
    next_pcs = PC_State(hp4_bits_extracted = pcs.hp4_bits_extracted,
                        p4_bits_extracted = pcs.p4_bits_extracted,
                        ps_path = next_pcs_ps_path,
                        pcs_path = next_pcs_pcs_path,
                        parse_state = next_parse_state)
    pcs.children.append(next_pcs)
    return next_pcs

  if pcs.parse_state.return_statement[PS_RET_TYPE] == 'select':
    for criteria in pcs.parse_state.return_statement[PS_RET_CRITERIA]:
      if isinstance(criteria, current_call):
        curr_reqmt = criteria[OFFSET] + criteria[WIDTH]
        if pcs.p4_bits_extracted + curr_reqmt > pcs.hp4_bits_extracted:
          pcs.hp4_bits_extracted += curr_reqmt
        hp4_criteria_offset = criteria[OFFSET] + pcs.p4_bits_extracted
        pcs.select_criteria.append((hp4_criteria_offset, criteria[WIDTH]))
      else:
        hdr_name, fld_name = criteria.split('.')
        hp4_criteria_offset = h.p4_fields[criteria].offset + pcs.header_offsets[hdr_name]
        pcs.select_criteria.append((hp4_criteria_offset, h.p4_fields[criteria].width))

    next_parse_states = []
    for branch in pcs.parse_state.return_statement[PS_RET_BRANCHES]:
      # e.g., ([('value', 1108152157446)], 'parse_A')
      values = []
      for value in branch[BRANCH_VALUES]:
        if value[VAL_TYPE] != 'value' and value[VAL_TYPE] != 'default':
          raise Exception('Unsupported branch value type: %s' % value[VAL_TYPE])
        if value[VAL_TYPE] == 'default':
          values.append('default')
        else:
          values.append(value[VAL_VALUE])
      pcs.select_values.append( values )
      if branch[BRANCH_STATE] != 'ingress':
        next_parse_state = h.p4_parse_states[branch[BRANCH_STATE]]
        if next_parse_state not in next_parse_states:
          next_parse_states.append(next_parse_state)
          next_pcs = add_next(next_parse_state)
          process_parse_tree_clr(next_pcs, h)
  elif pcs.parse_state.return_statement[PS_RET_TYPE] == 'immediate':
      next_parse_state_name = pcs.parse_state.return_statement[PS_RET_IMM_STATE]
      if next_parse_state_name != 'ingress':
        next_parse_state = h.p4_parse_states[next_parse_state_name]
        next_pcs = add_next(next_parse_state)
        process_parse_tree_clr(next_pcs, h)
  else:
    raise Exception('Unsupported return type: %s' % \
                    pcs.parse_state.return_statement[PS_RET_TYPE])

def consolidate_parse_tree_clr(pcs, h):
  if pcs.parse_state.return_statement[PS_RET_TYPE] == 'immediate':
    next_parse_state_name = pcs.parse_state.return_statement[PS_RET_IMM_STATE]
    if next_parse_state_name != 'ingress':
      next_pc_state = pcs.children[0]
      next_parse_state = next_pc_state.parse_state
      old_ps_name = pcs.parse_state.name
      new_ps_name = pcs.parse_state.name + '-' + next_parse_state.name
      new_ps_call_sequence = list(pcs.parse_state.call_sequence)
      new_ps_call_sequence += next_parse_state.call_sequence
      new_ps = p4_parse_state(h,
                              new_ps_name,
                              call_sequence=new_ps_call_sequence,
                              return_statement=next_parse_state.return_statement)
      hp4_bits_diff = next_pc_state.hp4_bits_extracted - pcs.hp4_bits_extracted
      pcs.hp4_bits_extracted += hp4_bits_diff
      p4_bits_diff = next_pc_state.p4_bits_extracted - pcs.p4_bits_extracted
      pcs.p4_bits_extracted += p4_bits_diff
      pcs.parse_state = new_ps
      pcs.children = list(next_pc_state.children)
      prev_ps = pcs.ps_path[-1]
      for i, branch in enumerate(prev_ps.return_statement[PS_RET_BRANCHES]):
        if branch[BRANCH_STATE] == old_ps_name:
          prev_ps.return_statement[PS_RET_BRANCHES][i] = (branch[BRANCH_VALUES], new_ps_name)
  for child in pcs.children:
    consolidate_parse_tree_clr(child, h)

def print_processed_parse_tree(pcs, level=0):
  for line in str(pcs).split('\n'):
    print '\t' * level + line
  for child in pcs.children:
    print_processed_parse_tree(child, level+1)

def print_commands(commands):
  for command in commands:
    print(command)

def launch_process_parse_tree_clr(pcs, h):
  start_pcs = PC_State(pcs_path=[pcs],
                       parse_state=pcs.parse_state)
  pcs.children.append(start_pcs)
  process_parse_tree_clr(start_pcs, h)

def parse_args(args):
  parser = argparse.ArgumentParser(description='Recursive Parse Tree Processing')
  parser.add_argument('input', help='path for input .p4', type=str)
  parser.add_argument('-o', '--output', help='path for output .hp4t file',
                    type=str, action="store", default='output.hp4t')
  parser.add_argument('-m', '--mt_output', help='path for match template output',
                    type=str, action="store", default='output.hp4mt')
  parser.add_argument('--numprimitives', help='maximum number of primitives \
                       for which HyPer4 is configured',
                      type=int, action="store", default=9)

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  hp4c = P4_to_HP4()
  hp4c.compile_to_hp4(args.input, args.output, args.mt_output, args.numprimitives)
  debug()

if __name__ == '__main__':
  main()
