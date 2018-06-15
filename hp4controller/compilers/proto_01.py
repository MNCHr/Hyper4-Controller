#!/usr/bin/python

from p4_hlir.main import HLIR
from p4_hlir.hlir.p4_parser import p4_parse_state
import p4_hlir
import argparse
import code
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

parse_select_table_boundaries = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100]

current_call = tuple

# pc numbering: 0 = prior to start; 1 = ready for start
next_pc_id = 1

def get_next_pc_id():
  global next_pc_id
  ret = next_pc_id
  next_pc_id += 1
  return ret

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
  def __init__(self, hp4_bits_extracted=SEB,
                     p4_bits_extracted=0,
                     ps_path=[],
                     pcs_path=[],
                     pcs_id=0,
                     parse_state=None,
                     entry_table='tset_parse_control',
                     **kwargs):
    self.hp4_bits_extracted = hp4_bits_extracted
    self.p4_bits_extracted = p4_bits_extracted
    self.ps_path = ps_path
    self.pcs_path = pcs_path
    self.pcs_id = pcs_id
    self.parse_state = parse_state
    self.entry_table = entry_table
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
    print(cmd)
    code.interact(local=dict(globals(), **locals()))

    commands.append(cmd)

    for child in pcs.children:
      commands = gen_parse_control_entries(child, commands)

  return commands

def process_parse_tree_clr(pcs, h):
  print(str(pcs.pcs_id) + ' [' + pcs.parse_state.name + ']')
  for call in pcs.parse_state.call_sequence:
    if call[PS_CALL_TYPE] == p4_hlir.hlir.p4_parser.parse_call.extract:
      pcs.header_offsets[call[PS_CALL_H_INST].name] = pcs.p4_bits_extracted
      pcs.p4_bits_extracted += call[PS_CALL_H_INST].header_type.length * 8
      if pcs.hp4_bits_extracted < pcs.p4_bits_extracted:
        pcs.hp4_bits_extracted = pcs.p4_bits_extracted
    else:
      raise Exception('Unsupported parse call: %s' % call[PS_CALL_TYPE])

  def add_next(next_parse_state):
    next_pcs_pcs_path = list(pcs.pcs_path)
    next_pcs_pcs_path.append(pcs)
    next_pcs_ps_path = list(pcs.ps_path)
    next_pcs_ps_path.append(pcs.parse_state)
    next_pcs = PC_State(hp4_bits_extracted = pcs.hp4_bits_extracted,
                        p4_bits_extracted = pcs.p4_bits_extracted,
                        ps_path = next_pcs_ps_path,
                        pcs_path = next_pcs_pcs_path,
                        pcs_id = get_next_pc_id(),
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

def launch_process_parse_tree_clr(pcs, h):
  start_pcs = PC_State(pcs_path=[pcs],
                       pcs_id=get_next_pc_id(),
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
  pre_pcs = PC_State(parse_state=h.p4_parse_states['start'])
  launch_process_parse_tree_clr(pre_pcs, h)
  consolidate_parse_tree_clr(pre_pcs, h)
  commands = gen_parse_control_entries(pre_pcs)
  code.interact(local=dict(globals(), **locals()))

if __name__ == '__main__':
  main()
