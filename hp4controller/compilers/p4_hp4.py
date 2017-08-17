#!/usr/bin/python

from compiler import HP4Compiler, CodeRepresentation
from p4_hlir.main import HLIR
import p4_hlir
from p4_hlir.hlir.p4_core import p4_enum
from collections import OrderedDict
import argparse
import code
import sys
import math
import json

RETURN_TYPE = 0
CRITERIA = 1
NEXT_PARSE_STATE = 1
CASE_ENTRIES = 2

MAX_PRIORITY = 2147483646

primitive_ID = {'modify_field': '[MODIFY_FIELD]',
                'add_header': '[ADD_HEADER]',
                'copy_header': '[COPY_HEADER]',
                'remove_header': '[REMOVE_HEADER]',
                'modify_field_with_hash_based_offset': '[MODIFY_FIELD_WITH_HBO]',
                'truncate': '[TRUNCATE]',
                'drop': '[DROP]',
                'no_op': '[NO_OP]',
                'push': '[PUSH]',
                'pop': '[POP]',
                'count': '[COUNT]',
                'execute_meter': '[METER]',
                'generate_digest': '[GENERATE_DIGEST]',
                'recirculate': '[RECIRCULATE]',
                'resubmit': '[RESUBMIT]',
                'clone_ingress_pkt_to_egress': '[CLONE_INGRESS_EGRESS]',
                'clone_egress_pkt_to_egress': '[CLONE_EGRESS_EGRESS]',
                'multicast': '[MULTICAST]',
                'add_to_field': '[MATH_ON_FIELD]'}

primitive_tnames = {'modify_field': 'mod',
                    'add_header': 'addh',
                    'copy_header': '',
                    'remove_header': '',
                    'modify_field_with_hash_based_offset': '',
                    'truncate' : 'truncate',
                    'drop' : 'drop',
                    'no_op' : '',
                    'push' : '',
                    'pop' : '',
                    'count' : '',
                    'execute_meter': '',
                    'generate_digest': '',
                    'recirculate': '',
                    'resubmit': '',
                    'clone_ingress_pkt_to_egress': '',
                    'clone_egress_pkt_to_egress': '',
                    'multicast': 'multicast',
                    'add_to_field': 'math_on_field'}

mf_prim_subtype_ID = {('meta', 'ingress_port'): '1',
                      ('meta', 'packet_length'): '2',
                      ('meta', 'egress_spec'): '3',
                      ('meta', 'egress_port'): '4',
                      ('meta', 'egress_instance'): '5',
                      ('meta', 'instance_type'): '6',
                      ('egress_spec', 'meta'): '7',
                      ('meta', 'const'): '8',
                      ('egress_spec', 'const'): '9',
                      ('ext', 'const'): '10',
                      ('egress_spec', 'ingress_port'): '11',
                      ('ext', 'ext'): '12',
                      ('meta', 'ext'): '13',
                      ('ext', 'meta'): '14',
                      ('mcast_grp', 'const'): '80'}

mf_prim_subtype_action = {'1': 'mod_meta_stdmeta_ingressport',
                          '2': 'mod_meta_stdmeta_packetlength',
                          '3': 'mod_meta_stdmeta_egressspec',
                          '4': 'mod_meta_stdmeta_egressport',
                          '5': 'mod_meta_stdmeta_egressinst',
                          '6': 'mod_meta_stdmeta_insttype',
                          '7': 'mod_stdmeta_egressspec_meta',
                          '8': 'mod_meta_const',
                          '9': 'mod_stdmeta_egressspec_const',
                          '10': 'mod_extracted_const',
                          '11': 'mod_stdmeta_egressspec_stdmeta_ingressport',
                          '12': 'mod_extracted_extracted',
                          '13': 'mod_meta_extracted',
                          '14': 'mod_extracted_meta',
                          '80': 'mod_intmeta_mcast_grp_const'}

a2f_prim_subtype_ID = {'add': '1', 'sub': '2'}

a2f_prim_subtype_action = {'1': 'a_add2f_extracted_const_u',
                           '2': 'a_subff_extracted_const_u'}

gen_prim_subtype_action = {'add_header': 'a_addh',
                           'copy_header': '',
                           'remove_header': '',
                           'modify_field_with_hash_based_offset': '',
                           'truncate': 'a_truncate',
                           'drop': 'a_drop',
                           'no_op': '',
                           'push': '',
                           'pop': '',
                           'count': '',
                           'execute_meter': '',
                           'recirculate': '',
                           'resubmit': '',
                           'clone_ingress_pkt_to_egress': '',
                           'clone_egress_pkt_to_egress': '',
                           'multicast': 'a_multicast'}

def convert_to_builtin_type(obj):
  d = { '__class__':obj.__class__.__name__, '__module__':obj.__module__, }
  d.update(obj.__dict__)
  return d

class MatchParam():
  def __init__(self):
    self.value = 0
    self.mask = 0
  def __str__(self):
    return format(self.value, '#04x') + '&&&' + format(self.mask, '#04x')

class DAG_Topo_Sorter():
  def __init__(self, p4_tables):
    self.unmarked = []
    self.tempmarked = []
    self.permmarked = []
    self.L = []
    for key in p4_tables:
      self.unmarked.append(p4_tables[key])

  def visit(self, n):
    if n in self.tempmarked:
      print("ERROR: not a DAG")
      exit()
    if n in self.unmarked:
      self.unmarked.remove(n)
      self.tempmarked.append(n)
      for m in n.next_.values():
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
    self.stage = stage
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
      else:
        print("Not supported: metadata with %s match type" % self.match_type)
        exit()
    elif self.source_type == 'extracted':
      if self.match_type == 'P4_MATCH_EXACT':
        return '[EXTRACTED_EXACT]'
      elif self.match_type == 'P4_MATCH_VALID':
        return '[EXTRACTED_VALID]'
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
    self.tables = {}
    self.call_sequence = []


class P4_to_HP4(HP4Compiler):
  def compile_to_hp4(self, program_path, args):
    self.h = HLIR(program_path)
    self.headers_hp4_type = {}
    self.action_ID = {}
    self.actionID = 1
    self.pc_bits_extracted = {}
    self.pc_action = {}
    self.field_offsets = {}
    self.offset = 0
    self.ps_to_pc = {}
    self.pc_to_ps = {}
    self.pc_to_preceding_pcs = {}
    self.vbits = {}
    self.tics_match_offsets = {}
    self.tics_table_names = {}
    self.tics_list = []
    self.stage = 1
    self.table_to_trep = {}
    self.action_to_arep = {}
    self.commands = []
    self.command_templates = []
    # Resume: line 268 of ~/hp4-src/p4c-hp4.py

    # TODO implement all necessary steps above
    return CodeRepresentation(object_code_path, interpretation_guide_path)

  def build(self):
    pass

  def write_output(self):
    pass

def parse_args(args):
  parser = argparse.ArgumentParser(description='P4->HP4 Compiler')
  parser.add_argument('input', help='path for input .p4',
                    type=str)
  parser.add_argument('-o', '--output', help='path for output .hp4t file',
                    type=str, action="store", required=True)
  parser.add_argument('-m', '--mt_output', help='path for match template output',
                    type=str, action="store", default='output.hp4mt')
  parser.add_argument('-s', '--seb', help='set standard extracted bytes',
                    type=int, action="store", default=20)
  parser.add_argument('--egress_filter', help='enable egress filtering',
                      action='store_true')
  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  hp4c = P4_to_HP4(args.input, args)
  hp4c.build()
  hp4c.write_output()

if __name__ == '__main__':
  main()
