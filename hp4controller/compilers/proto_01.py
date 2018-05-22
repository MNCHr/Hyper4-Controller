#!/usr/bin/python

from p4_hlir.main import HLIR
import p4_hlir
import argparse
import code
# code.interact(local=dict(globals(), **locals()))
import sys

SEB = 320

PS_RET_TYPE = 0
PS_RET_CRITERIA = 1
PS_RET_BRANCHES = 2
PS_CALL_TYPE = 0
PS_CALL_H_INST = 1
PS_CURR_OFFSET = 0
PS_CURR_WIDTH = 1
BRANCH_VALUES = 0
BRANCH_STATE = 1
VAL_TYPE = 0
VAL_VALUE = 1

current_call = tuple

#TODO: implement proper pc numbering; 0 = prior to start; 1 = ready for start

next_pc_id = 0

def get_next_pc_id():
  global next_pc_id
  ret = next_pc_id
  next_pc_id += 1
  return ret

class PC_State(object):
  def __init__(self, hp4_bits_extracted=SEB,
                     p4_bits_extracted=0,
                     ps_path=[],
                     pcs_path=[],
                     pcs_id=0,
                     parse_state=None,
                     **kwargs):
    self.hp4_bits_extracted = hp4_bits_extracted
    self.p4_bits_extracted = p4_bits_extracted
    self.ps_path = ps_path
    self.pcs_path = pcs_path
    self.pcs_id = pcs_id
    self.parse_state = parse_state
    self.children = []

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

def clr_traverse(pcs, h):
  print(str(pcs.pcs_id) + ' [' + pcs.parse_state.name + ']')
  for call in pcs.parse_state.call_sequence:
    if call[PS_CALL_TYPE] == p4_hlir.hlir.p4_parser.parse_call.extract:
      pcs.p4_bits_extracted += call[PS_CALL_H_INST].header_type.length * 8
      if pcs.hp4_bits_extracted < pcs.p4_bits_extracted:
        pcs.hp4_bits_extracted = pcs.p4_bits_extracted
    else:
      raise Exception('Unsupported parse call: %s' % call[PS_CALL_TYPE])

  if pcs.parse_state.return_statement[PS_RET_TYPE] == 'select':
    for criteria in pcs.parse_state.return_statement[PS_RET_CRITERIA]:
      if isinstance(criteria, current_call):
        curr_reqmt = criteria[PS_CURR_OFFSET] + criteria[PS_CURR_WIDTH]
        if pcs.p4_bits_extracted + curr_reqmt > pcs.hp4_bits_extracted:
          pcs.hp4_bits_extracted += curr_reqmt
    next_parse_states = []
    for branch in pcs.parse_state.return_statement[PS_RET_BRANCHES]:
      # e.g., ([('value', 1108152157446)], 'parse_A')
      for value in branch[BRANCH_VALUES]:
        if value[VAL_TYPE] != 'value' and value[VAL_TYPE] != 'default':
          raise Exception('Unsupported branch value type: %s' % value[VAL_TYPE])
      if branch[BRANCH_STATE] != 'ingress':
        next_parse_state = h.p4_parse_states[branch[BRANCH_STATE]]
        if next_parse_state not in next_parse_states:
          next_parse_states.append(next_parse_state)
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
          clr_traverse(next_pcs, h)

def parse_args(args):
  parser = argparse.ArgumentParser(description='Recursive Parse Tree Processing')
  parser.add_argument('input', help='path for input .p4', type=str)
  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  h = HLIR(args.input)
  h.build()
  start_pcs = PC_State(pcs_id=get_next_pc_id(), parse_state=h.p4_parse_states['start'])
  clr_traverse(start_pcs, h)
  code.interact(local=dict(globals(), **locals()))

if __name__ == '__main__':
  main()
