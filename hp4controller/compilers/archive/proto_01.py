#!/usr/bin/python

from p4_hlir.main import HLIR
from p4_hlir.hlir.p4_parser import p4_parse_state
import p4_hlir
import argparse
import itertools
import code
from inspect import currentframe, getframeinfo
# code.interact(local=dict(globals(), **locals()))
import sys

SEB = 320

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

class HP4_Parse_Select_Command(HP4_Command):
  def __init__(self, curr_pc_state = 0,
                     next_pc_state = 0,
                     next_parse_state = '',
                     priority = 0,
                     **kwargs):
    super(HP4_Parse_Select_Command, self).__init__(**kwargs)
    self.curr_pc_state = curr_pc_state
    self.next_pc_state = next_pc_state
    self.next_parse_state = next_parse_state
    self.priority = priority

class HP4_Match_Command(HP4_Command):
  def __init__(self, source_table='',
                     source_action='',
                     **kwargs):
    super(HP4_Match_Command, self).__init__(**kwargs)
    self.source_table = source_table
    self.source_action = source_action

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
    next = [child for child in pcs.children \
                   if child.parse_state.name == branch[BRANCH_STATE]][0]
    if next.hp4_bits_extracted > pcs.hp4_bits_extracted:
      action = 'extract_more'
      aparams.append(str(next.hp4_bits_extracted))
    else: # another select statement in next pcs - need to rewind?
      n_first_criteria = sort_return_select(next)[0][0]
      j = 0
      while parse_select_table_boundaries[j+1] * 8 <= n_first_criteria[OFFSET]:
        j += 1
      if parse_select_table_boundaries[j] <= parse_select_tables[pst_count][L_BOUND]:
        # rewind
        action = 'extract_more'
        aparams.append(str(next.hp4_bits_extracted))
      else:
        act = 'set_next_action'
        next_ps_table = get_parse_select_table(n_first_criteria)
        aparams.append(get_ps_action(next_ps_table[T_NAME]))

    aparams.append(str(next.pcs_id))

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

def get_pipeline_config_entries(level):
  commands = []
  # TODO
  return commands

  """ I don't think we will output the commands here
      Rather we just need to look at the headers
  """

def gen_pipeline_config_entries(pcs):
  commands = []
  """ This approach seems incorrect:
  pcs_levels = collect_pcs_levels(pcs)
  for level in pcs_levels:
    commands += get_pipeline_config_entries(level)
  """
  debug()
  # pcs_headers = 
  return commands

""" This method evidently is worthless:
def collect_pcs_levels(pcs, levellist = [], level=0):
  if pcs.pcs_id == 0:
    return collect_pcs_levels(pcs.children[0], [[pcs.children[0]]])

  if pcs.children:
    if len(levellist) < level + 2:
      levellist.append([])
    levellist[level + 1] += [child for child in pcs.children]

  for child in pcs.children:
    levellist = collect_pcs_levels(child, levellist, level+1)
  return levellist
"""

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
  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  h = HLIR(args.input)
  h.build()
  do_support_checks(h)
  pre_pcs = PC_State(parse_state=h.p4_parse_states['start'])
  launch_process_parse_tree_clr(pre_pcs, h)
  consolidate_parse_tree_clr(pre_pcs, h)
  parse_control_commands = gen_parse_control_entries(pre_pcs)
  parse_select_commands = gen_parse_select_entries(pre_pcs)
  pipeline_config_commands = gen_pipeline_config_entries(pre_pcs)
  debug()

if __name__ == '__main__':
  main()
