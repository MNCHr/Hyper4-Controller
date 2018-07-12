#!/usr/bin/python

from p4_hlir.main import HLIR
from p4_hlir.hlir.p4_parser import p4_parse_state
import p4_hlir
from p4_hlir.hlir.p4_tables import p4_table
from compiler import HP4Compiler, CodeRepresentation
import argparse
import itertools
import code
from inspect import currentframe, getframeinfo
import sys
import math
from math import ceil
import json
import pkg_resources

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
MATCH_TYPE = 1
MATCH_FIELD = 0
PRIM_TYPE = 0
PRIM_SUBTYPE = 1
P4_CALL_PRIMITIVE = 0
P4_CALL_PARAMS = 1
PARAM = 0
PARAM_TYPE = 1
MATCH_OBJECT = 0
MATCH_TYPE = 1
EXT_FIRST_WIDTH = 40 # in bytes
EXT_START_INDEX = 2

parse_select_table_boundaries = [0, 20, 30, 40, 50, 60, 70, 80, 90, 100]

primitive_ID = {'modify_field': '[MODIFY_FIELD]',
                'add_header': '[ADD_HEADER]',
                'copy_header': '[COPY_HEADER]',
                'remove_header': '[REMOVE_HEADER]',
                'modify_field_with_hash_based_offset': '[MODIFY_FIELD_WITH_HBO]',
                'modify_field_rng_uniform': '[MODIFY_FIELD_RNG_U]',
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
                'add_to_field': '[MATH_ON_FIELD]',
                'bit_xor': '[BIT_XOR]'}

primitive_tnames = {'modify_field': 'mod',
                    'add_header': 'addh',
                    'copy_header': '',
                    'remove_header': 'removeh',
                    'modify_field_with_hash_based_offset': '',
                    'modify_field_rng_uniform': 'mod_rng',
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
                    'add_to_field': 'math_on_field',
                    'bit_xor': 'bit_xor'}

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
                      ('ext', 'meta'): '14'}

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
                          '14': 'mod_extracted_meta'}

a2f_prim_subtype_ID = {'add': '1', 'sub': '2'}

a2f_prim_subtype_action = {'1': 'a_add2f_extracted_const_u',
                           '2': 'a_subff_extracted_const_u'}

bx_prim_subtype_ID = {('meta', 'meta', 'const'): '1',
                      ('ext', 'ext', 'const'): '2',
                      ('meta', 'ext', 'const'): '3'}

bx_prim_subtype_action = {'1': 'bit_xor_meta_meta_const',
                          '2': 'bit_xor_extracted_extracted_const',
                          '3': 'bit_xor_meta_extracted_const'}

gen_prim_subtype_action = {'add_header': 'a_addh',
                           'copy_header': '',
                           'remove_header': 'a_removeh',
                           'modify_field_with_hash_based_offset': '',
                           'modify_field_rng_uniform': 'mod_extracted_rng',
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

current_call = tuple

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))

def unsupported(msg):
  print(msg)
  exit()

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
      unsupported("ERROR: Not yet supported: tables in egress (" + n.name + ")")

    if n in self.tempmarked:
      unsupported("ERROR: not a DAG")

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
          unsupported("Not supported: standard_metadata field %s" \
                                                % self.field_name)
      else:
        unsupported("Not supported: standard_metadata with %s match type" \
                                                        % self.match_type)

    elif self.source_type == 'metadata':
      if self.match_type == 'P4_MATCH_EXACT':
        return '[METADATA_EXACT]'
      elif self.match_type == 'P4_MATCH_TERNARY':
        return '[METADATA_TERNARY]'
      else:
        unsupported("Not supported: metadata with %s match type" \
                                               % self.match_type)
    elif self.source_type == 'extracted':
      if self.match_type == 'P4_MATCH_EXACT':
        return '[EXTRACTED_EXACT]'
      elif self.match_type == 'P4_MATCH_VALID':
        return '[EXTRACTED_VALID]'
      elif self.match_type == 'P4_MATCH_TERNARY':
        return '[EXTRACTED_TERNARY]'
      else:
        unsupported("Not supported: extracted with %s match type" \
                                                % self.match_type)
    elif self.source_type == '':
      if self.match_type == 'MATCHLESS':
        return '[MATCHLESS]'
      else:
        unsupported("Not supported: [no source] with %s match type" \
                                                  % self.match_type)
    else:
      unsupported("Not supported: source type %s, match type %s" \
                           % (self.source_type, self.match_type))

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

def collect_meta(headers):
  """ Classify headers (metadata | parsed representation)
      - For metadata: assign each field an offset into meta.data
      - NOTE: the same cannot be done for parsed representation headers
        until we traverse the parse tree, because each path through the
        parse tree potentially yields a distinct set of field offsets
        into pr.data.
  """
  meta_offsets = {}
  metadata_offset = 0

  for header_key in headers.keys():
    header = headers[header_key]

    if header.name == 'standard_metadata':
      continue

    if header.name == 'intrinsic_metadata':
      continue

    if header.metadata == True:

      for field in header.fields:
        fullname = header.name + '.' + field.name
        meta_offsets[fullname] = metadata_offset
        metadata_offset += field.width
        if metadata_offset > METADATA_WIDTH:
          unsupported("Error: out of metadata memory with %s" % fullname)

  return meta_offsets

def collect_actions(actions):
  """ Uniquely number each action """
  action_ID = {}
  actionID = 1
  for action in actions:
    if action.lineno > 0: # is action from source (else built-in)?
      action_ID[action] = actionID
      actionID += 1
  return action_ID

def get_prim_subtype(p4_call):
  """ p4_call: (p4_action, [list of parameters])
  """
  primitive = p4_call[P4_CALL_PRIMITIVE]
  params = p4_call[P4_CALL_PARAMS]
  if (primitive.name == 'drop' or 
      primitive.name == 'add_header' or 
      primitive.name == 'remove_header' or
      primitive.name == 'modify_field_rng_uniform'):
    return '0'
  elif primitive.name == 'add_to_field':
    if type(params[0]) is p4_hlir.hlir.p4_headers.p4_field:
      if params[0].instance.metadata == True:
        unsupported("Not supported: metadata (%s) as dst field in \
                         add_to_field" %  params[0].instance.name)

      else:
        if type(params[1]) is int:
          if params[1] < 0:
            return(a2f_prim_subtype_ID['sub'])
          else:
            return(a2f_prim_subtype_ID['add'])
        else:
          unsupported("ERROR: Not supported: %s type for src field in \
                                      add_to_field" % type(params[1]))

    else:
      unsupported("ERROR: dst field type %s in add_to_field" % type(params[0]))

  elif primitive.name == 'bit_xor':
    first = 0
    second = 0
    third = 0
    if params[0].instance.metadata == True:
      first = 'meta' # user-defined metadata
    else: # parsed representation
      first = 'ext'
    if params[1].instance.metadata == True:
      second = 'meta' # user-defined metadata
    else: # parsed representation
      second = 'ext'
    if type(params[2]) in [int, long]:
      third = 'const'
    elif type(params[2]) is p4_hlir.hlir.p4_imperatives.p4_signature_ref:
      third = 'const'
    else:
      unsupported("ERROR: Unexpected type %s as third param in \
                    bit_xor call" % type(params[2]))

    return bx_prim_subtype_ID[(first, second, third)]

  elif primitive.name == 'modify_field':
    first = 0
    second = 0
    if params[0].instance.metadata == True:
      if params[0].instance.name == 'standard_metadata':
        if params[0].name == 'egress_spec':
          first = params[0].name
        else:
          unsupported("ERROR: Unexpected stdmeta field %s as dst in \
                           modify_field primitive" % params[0].name)

      elif params[0].instance.name == 'intrinsic_metadata':
        if params[0].name == 'mcast_grp':
          #first = params[0].name
          first = 'egress_spec'
        else:
          unsupported("ERROR: Unexpected intmeta field %s as dst in \
                        modify_field primitive" % params[0].name)

      else: # user-defined metadata
        first = 'meta'
    else: # parsed representation
      first = 'ext'
    if type(params[1]) in [int, long]:
      second = 'const'
    elif type(params[1]) is p4_hlir.hlir.p4_headers.p4_field:
      if params[1].instance.metadata == True:
        if params[1].instance.name == 'standard_metadata':
          second = params[1].name
        else:
          second = 'meta'
      else:
        second = 'ext'
    elif type(params[1]) is p4_hlir.hlir.p4_imperatives.p4_signature_ref:
      second = 'const'
    else:
      unsupported("ERROR: Unexpected type %s as src in \
                    modify_field call" % type(params[1]))

    return mf_prim_subtype_ID[first, second]

def gen_bitmask(fieldwidth, offset, maskwidth):
  """fieldwidth: bits; offset: bits; maskwidth: bytes"""
  mask = '0x'

  bytes_written = offset / 8
  bits_left = fieldwidth
  while bits_left > 0:
    byte = 0
    bit = 0b10000000 >> (offset % 8)
    if bits_left >= 8 - (offset % 8):
      for i in range(8 - (offset % 8)):
        byte = byte | bit
        bit = bit >> 1
      bits_left = bits_left - (8 - (offset % 8))
      offset = offset + 8 - (offset % 8)
    else:
      for i in range(bits_left):
        byte = byte | bit
        bit = bit >> 1
      bits_left = 0
    mask += hex(byte)[2:]
    bytes_written += 1

  mask += '[' + str(maskwidth - bytes_written) + 'x00s]'

  return mask

def gen_addremove_header_bitmask(offset, maskwidth):
  """offset: bits; maskwidth: bytes"""

  bytes_written = offset / 8
  return '0x[' + str(maskwidth - bytes_written) + 'xFFs]'

class P4_to_HP4(HP4Compiler):

  def walk_ingress_pipeline(self, tables):
    """ populate table_to_trep and action_to_arep data structures """
    table_to_trep = {}
    action_to_arep = {}
    stage = 1

    # 1) Do topological sort of tables
    tsorter = DAG_Topo_Sorter(tables)
    tsort = tsorter.sort()
    # 2) assign each one to a unique stage
    for i in range(len(tsort)):
      curr_table = tsort[i]
      source_type = ''
      match_type = 'MATCHLESS'
      field_name = ''
      if len(curr_table.match_fields) > 0:
        match = curr_table.match_fields[0]
        match_type = match[MATCH_TYPE].value
        field_name = match[MATCH_FIELD].name
        if (match_type == 'P4_MATCH_EXACT' or
            match_type == 'P4_MATCH_TERNARY'):
          # headers_hp4_type[<str>]: 'standard_metadata' | 'metadata' | 'extracted'
          source_type = get_hp4_type(match[MATCH_FIELD].instance)
        elif match_type == 'P4_MATCH_VALID':
          source_type = get_hp4_type(match[MATCH_FIELD])
      table_to_trep[curr_table] = Table_Rep(stage,
                                            match_type,
                                            source_type,
                                            field_name)

      for action in curr_table.actions:
        if action_to_arep.has_key(action) is False:
          action_to_arep[action] = Action_Rep()
          for call in action.call_sequence:
            prim_type = call[PRIM_TYPE].name
            prim_subtype = get_prim_subtype(call)
            action_to_arep[action].call_sequence.append((prim_type, prim_subtype))
        action_to_arep[action].stages.add(stage)
        action_to_arep[action].tables[stage] = curr_table.name

      stage += 1

    return table_to_trep, action_to_arep

  def gen_tX_templates(self, tables):
    command_templates = []

    for table in self.table_to_trep:
      tname = str(self.table_to_trep[table])
      aname = 'init_program_state'
      mparams = ['[vdev ID]']
      if len(table.match_fields) > 1:
        unsupported("Not yet supported: more than 1 match field (table: %s)" % table.name)

      # mparams_list = []
      if len(table.match_fields) == 1:      
        if table.match_fields[0][1].value == 'P4_MATCH_VALID':
          mp = '[valid]&&&'
          # self.vbits[(level, header_instance)]
          hinst = table.match_fields[0][0]
          for key in self.vbits.keys():
            if hinst.name == key[1]:
              mp += format(self.vbits[key], '#x')
              # temp_mparams = list(mparams)
              # temp_mparams.append(mp)
              # mparams_list.append(temp_mparams)
              mparams.append(mp)
        elif ((table.match_fields[0][1].value == 'P4_MATCH_EXACT') or
             (table.match_fields[0][1].value == 'P4_MATCH_TERNARY')):
          field = table.match_fields[0][0]
          mp = '[val]'
          if field.instance.name != 'standard_metadata':
            maskwidth = 100
            if field.instance.metadata:
              maskwidth = 32
            offset = self.field_offsets[str(field)]
            mp += '&&&' + gen_bitmask(field.width,
                                      offset,
                                      maskwidth)
          elif field.name != 'egress_spec' and field.name != 'ingress_port':
            mp += '&&&' + hex((1 << field.width) - 1)
          else: # egress_spec... rep'd by virt_egress_spec, which is 8 bits
            mp += '&&&0xFF'
          mparams.append(mp)

      # need a distinct template entry for every possible action
      for action in table.actions:
        # action_ID
        aparams = [str(self.action_ID[action])]
        # match_ID
        aparams.append('[match ID]')
        # next stage, next_table
        if 'hit' in table.next_:
          next_table_trep = self.table_to_trep[table.next_['hit']]
          aparams.append(str(next_table_trep.stage))
          aparams.append(next_table_trep.table_type())
        elif table.next_[action] == None:
          aparams.append('0')
          aparams.append('[DONE]')
        else:
          next_table_trep = self.table_to_trep[table.next_[action]]
          aparams.append(str(next_table_trep.stage))
          aparams.append(next_table_trep.table_type())
        # primitives
        idx = 0
        for call in action.call_sequence:
          prim_type = primitive_ID[call[P4_CALL_PRIMITIVE].name]
          prim_subtype = get_prim_subtype(call)
          if not prim_subtype:
            unsupported("Error: couldn't get the prim_subtype for " + prim_type)
          aparams.append(prim_type)
          aparams.append(prim_subtype)
          idx += 1

        if len(action.call_sequence) == 0:
          aparams.append(primitive_ID['no_op'])
          # subtype
          aparams.append('0')
          idx = 1

        # zeros for remaining type / subtype parameters of init_program_state
        for i in range(idx, self.numprimitives):
          aparams.append('0')
          aparams.append('0')

        # all matches are ternary, requiring priority
        # TODO: except matchless?
        aparams.append('[PRIORITY]')

        command_templates.append(HP4_Match_Command(source_table=table.name,
                                                   source_action=action.name,
                                                   command="table_add",
                                                   table=tname,
                                                   action=aname,
                                                   match_params=mparams,
                                                   action_params=aparams))
    return command_templates

  def gen_action_aparams(self, p4_call, call, field_offsets):
    aparams = []
    primtype = call[PRIM_TYPE]
    subtype = call[PRIM_SUBTYPE]
    p4_call_params = p4_call[P4_CALL_PARAMS]

    if primtype == 'drop':
      return aparams
    if primtype == 'add_to_field':
      if (a2f_prim_subtype_action[subtype] == 'a_add2f_extracted_const_u' or
          a2f_prim_subtype_action[subtype] == 'a_subff_extracted_const_u'):
        # aparams: leftshift, val
        dst_offset = field_offsets[str(p4_call_params[0])]
        leftshift = 800 - (dst_offset + p4_call_params[0].width)
        if type(p4_call_params[1]) is int:
          val = str(p4_call_params[1])
          if a2f_prim_subtype_action[subtype] == 'a_subff_extracted_const_u':
            val = str(p4_call_params[1]*-1)
        else:
          val = '[val]'
        aparams.append(str(leftshift))
        aparams.append(val)

    if primtype == 'add_header' or primtype == 'remove_header':

      hdr = p4_call_params[0]
      offset = self.header_offsets[hdr.name]
      byte_offset = int(ceil(offset / 8.0))
      sz = hdr.header_type.length

      vb = 0
      for key in self.vbits:
        if hdr.name == key[1]:
          vb = self.vbits[key]
          break
      if vb == 0:
        print('Fail: didn\'t find vbits entry for ' + hdr.name)
        exit()

      mask = gen_addremove_header_bitmask(offset, MAX_BYTE)

      if primtype == 'add_header':
        # aparams: sz, offset, msk, vbits    
        aparams.append(str(sz))
        aparams.append(str(byte_offset))
        aparams.append(mask)
        aparams.append('0x%x' % vb)
      else: # 'remove_header'
        # aparams: sz, msk, vbits
        aparams.append(str(sz))
        aparams.append(mask)
        vbinv = ~vb & (2**VBITS_WIDTH - 1)
        aparams.append('0x%x' % vbinv)

    if primtype == 'modify_field_rng_uniform':
      # aparams: leftshift, emask, lowerbound, upperbound
      if type(p4_call_params[1]) in [int, long]:
        val1 = str(p4_call_params[1])
      else:
        val1 = '[val]'
      if type(p4_call_params[2]) in [int, long]:
        val2 = str(p4_call_params[2])
      else:
        val2 = '[val]'

      fo = field_offsets[str(p4_call_params[0])]
      fw = p4_call_params[0].width
      maskwidthbits = 800
      leftshift = str(maskwidthbits - (fo + fw))
      mask = gen_bitmask(p4_call_params[0].width,
                              field_offsets[str(p4_call_params[0])],
                              maskwidthbits / 8)
      aparams.append(leftshift)
      aparams.append(mask)
      aparams.append(val1)
      aparams.append(val2)

    if primtype == 'bit_xor':
      # aparams: elshift, ershift, vlshift, dest_mask, src_mask, val
      fo_intermediate = field_offsets[str(p4_call_params[1])]
      fw_intermediate = p4_call_params[1].width
      fo_final = field_offsets[str(p4_call_params[0])]
      fw_final = p4_call_params[0].width
      if bx_prim_subtype_action[subtype] == 'bit_xor_meta_meta_const':
        unsupported("Not yet supported: bit_xor_meta_meta_const")
        dest_maskwidthbits = 256
        src_maskwidthbits = 256

      elif bx_prim_subtype_action[subtype] == 'bit_xor_extracted_extracted_const':
        dest_maskwidthbits = 800
        src_maskwidthbits = 800

      elif bx_prim_subtype_action[subtype] == 'bit_xor_meta_extracted_const':
        dest_maskwidthbits = 256
        src_maskwidthbits = 800

      elshift = 0
      ershift = 0
      dst_revo = dest_maskwidthbits - (fo_final + fw_final)
      src_revo = src_maskwidthbits - (fo_intermediate + fw_intermediate)
      if src_revo > dst_revo:
        ershift = src_revo - dst_revo
      else:
        elshift = dst_revo - src_revo

      vlshift = str(src_maskwidthbits - (fo_intermediate + fw_intermediate))

      dest_mask = gen_bitmask(fw_final, fo_final, dest_maskwidthbits / 8)
      src_mask = gen_bitmask(fw_intermediate, fo_intermediate, src_maskwidthbits / 8)
      src_mask = src_mask.split('[')[0]

      if type(p4_call_params[2]) in [int, long]:
        val = str(p4_call_params[2])
      else:
        val = '[val]'

      aparams.append(str(elshift))
      aparams.append(str(ershift))
      aparams.append(vlshift)
      aparams.append(dest_mask)
      aparams.append(src_mask)
      aparams.append(val)
      
    if primtype == 'modify_field':
      instance_name = p4_call_params[0].instance.name
      dst_field_name = p4_call_params[0].name
      if instance_name == 'intrinsic_metadata':
        if dst_field_name == 'mcast_grp':
          instance_name = 'standard_metadata'
          dst_field_name = 'egress_spec'
        else:
          unsupported("Not supported: modify_field(" + instance_name + '.' \
                + dst_field_name + ", *)")

      if type(p4_call_params[1]) is p4_hlir.hlir.p4_headers.p4_field:
        if p4_call_params[1].width > p4_call_params[0].width:
          dst = instance_name + '.' + dst_field_name
          src = p4_call_params[1].instance.name + '.' + p4_call_params[1].name
          print("WARNING: modify_field(%s, %s): %s width (%i) > %s width (%i)" \
              % (dst, src, src, p4_call_params[1].width, dst, p4_call_params[0].width))

      if mf_prim_subtype_action[subtype] == 'mod_meta_stdmeta_ingressport':
        unsupported("Not yet supported: %s" % mf_prim_subtype_action[subtype])

      elif mf_prim_subtype_action[subtype] == 'mod_meta_stdmeta_packetlength':
        unsupported("Not yet supported: %s" % mf_prim_subtype_action[subtype])

      elif mf_prim_subtype_action[subtype] == 'mod_meta_stdmeta_egressspec':
        unsupported("Not yet supported: %s" % mf_prim_subtype_action[subtype])

      elif mf_prim_subtype_action[subtype] == 'mod_meta_stdmeta_egressport':
        unsupported("Not yet supported: %s" % mf_prim_subtype_action[subtype])

      elif mf_prim_subtype_action[subtype] == 'mod_meta_stdmeta_egressinst':
        unsupported("Not yet supported: %s" % mf_prim_subtype_action[subtype])

      elif mf_prim_subtype_action[subtype] == 'mod_meta_stdmeta_insttype':
        unsupported("Not yet supported: %s" % mf_prim_subtype_action[subtype])

      elif mf_prim_subtype_action[subtype] == 'mod_stdmeta_egressspec_meta':
        # aparams: rightshift, tmask
        rshift = 256 - (field_offsets[str(p4_call_params[1])] + p4_call_params[1].width)
        mask = 0
        if p4_call_params[1].width < p4_call_params[0].width:
          mask = hex(int(math.pow(2, p4_call_params[1].width)) - 1)
        else:
          mask = hex(int(math.pow(2, p4_call_params[0].width)) - 1)
        aparams.append(str(rshift))
        aparams.append(mask)

      elif (mf_prim_subtype_action[subtype] == 'mod_meta_const' or
            mf_prim_subtype_action[subtype] == 'mod_extracted_const'):
        # aparams: leftshift, mask, val
        if type(p4_call_params[1]) in [int, long]:
          val = str(p4_call_params[1])
        else:
          val = '[val]'
        fo = field_offsets[str(p4_call_params[0])]
        fw = p4_call_params[0].width
        maskwidthbits = 800
        if mf_prim_subtype_action[subtype] == 'mod_meta_const':
          maskwidthbits = 256
        leftshift = str(maskwidthbits - (fo + fw))
        mask = gen_bitmask(p4_call_params[0].width,
                                field_offsets[str(p4_call_params[0])],
                                maskwidthbits / 8)
        aparams.append(leftshift)
        aparams.append(mask)
        aparams.append(val)

      elif (mf_prim_subtype_action[subtype] == 'mod_stdmeta_egressspec_const'):
        if type(p4_call_params[1]) is int:
          aparams.append(str(p4_call_params[1]))
        else:
          aparams.append('[val]')

      elif (mf_prim_subtype_action[subtype] == 'mod_intmeta_mcast_grp_const'):
        if type(p4_call_params[1]) is int:
          unsupported("Not yet supported: mod_intmeta_mcast_grp_const w/ explicit const")

        else:
          aparams.append('[MCAST_GRP]')

      #elif mf_prim_subtype_action[subtype] == 'mod_stdmeta_egressspec_stdmeta_ingressport':
      #  return aparams
      elif mf_prim_subtype_action[subtype] == 'mod_extracted_extracted':
        # aparams:
        # - leftshift (how far should src field be shifted to align w/ dst)
        # - rightshift (how far should src field be shifted to align w/ dst)
        # - msk (bitmask for dest field)
        dst_offset = field_offsets[str(p4_call_params[0])]
        src_offset = field_offsets[str(p4_call_params[1])]
        lshift = 0
        rshift = 0
        # *_revo = revised offset; right-aligned instead of left-aligned
        dst_revo = 800 - (dst_offset + p4_call_params[0].width)
        src_revo = 800 - (src_offset + p4_call_params[1].width)
        if src_revo > dst_revo:
          rshift = src_revo - dst_revo
        else:
          lshift = dst_revo - src_revo
        aparams.append(str(lshift))
        aparams.append(str(rshift))
        aparams.append(gen_bitmask(p4_call_params[0].width, dst_offset, 100))
      elif mf_prim_subtype_action[subtype] == 'mod_meta_extracted':
        dst_offset = field_offsets[str(p4_call_params[0])]
        src_offset = field_offsets[str(p4_call_params[1])]
        lshift = 0
        rshift = 0
        dstmaskwidthbits = 256
        srcmaskwidthbits = 800
        # *_revo = revised offset; right-aligned instead of left-aligned
        dst_revo = dstmaskwidthbits - (dst_offset + p4_call_params[0].width)
        src_revo = srcmaskwidthbits - (src_offset + p4_call_params[1].width)
        if src_revo > dst_revo:
          rshift = src_revo - dst_revo
        else:
          lshift = dst_revo - src_revo
        dstmask = gen_bitmask(p4_call_params[0].width, dst_offset,
                                   dstmaskwidthbits / 8)
        srcmask = dstmask
        if p4_call_params[1].width < p4_call_params[0].width:
          srcmask = gen_bitmask(p4_call_params[1].width, dst_offset,
                                     dstmaskwidthbits / 8)
        aparams.append(str(lshift))
        aparams.append(str(rshift))
        aparams.append(dstmask)
        aparams.append(srcmask)
      elif mf_prim_subtype_action[subtype] == 'mod_extracted_meta':
        dst_offset = field_offsets[str(p4_call_params[0])]
        src_offset = field_offsets[str(p4_call_params[1])]
        lshift = 0
        rshift = 0
        dstmaskwidthbits = 800
        srcmaskwidthbits = 256
        # *_revo = revised offset; right-aligned instead of left-aligned
        dst_revo = dstmaskwidthbits - (dst_offset + p4_call_params[0].width)
        src_revo = srcmaskwidthbits - (src_offset + p4_call_params[1].width)
        if src_revo > dst_revo:
          rshift = src_revo - dst_revo
        else:
          lshift = dst_revo - src_revo
        dstmask = gen_bitmask(p4_call_params[0].width, dst_offset,
                                   dstmaskwidthbits / 8)
        srcmask = dstmask
        if p4_call_params[1].width < p4_call_params[0].width:
          srcmask = gen_bitmask(p4_call_params[1].width, dst_offset,
                                     dstmaskwidthbits / 8)
        aparams.append(str(lshift))
        aparams.append(str(rshift))
        aparams.append(dstmask)
        aparams.append(srcmask)

    return aparams

  def gen_action_entries(self, action_to_arep, action_ID, field_offsets):
    commands = []
    command_templates = []
    for action in action_to_arep:
      for stage in action_to_arep[action].stages:
        table_name = action_to_arep[action].tables[stage]
        for p4_call in action.call_sequence:
          p4_call_params = p4_call[P4_CALL_PARAMS]
          istemplate = False
          idx = action.call_sequence.index(p4_call)
          call = action_to_arep[action].call_sequence[idx]
          primtype = call[PRIM_TYPE]
          subtype = call[PRIM_SUBTYPE]
          rank = idx + 1
          tname = 't_' + primitive_tnames[primtype] + '_' + str(stage) + str(rank)

          if primtype == 'modify_field':
            aname = mf_prim_subtype_action[subtype]
          elif primtype == 'add_to_field':
            aname = a2f_prim_subtype_action[subtype]
          elif primtype == 'bit_xor':
            aname = bx_prim_subtype_action[subtype]
          else:
            aname = gen_prim_subtype_action[primtype]
          mparams = ['[vdev ID]']
          if primtype != 'drop':
            if primtype in ['modify_field', 'add_to_field', 'bit_xor']:
              mparams.append( subtype )
            mparams.append(str(action_ID[action]))
            # If the parameter passed to the primitive in the source code is an
            # action parameter reference, the match_ID parameter should be
            # [val]&&&0x7FFFFF because each distinct match could have a different
            # value for the action parameter.  Otherwise, we don't care what the
            # match_ID is so use 0&&&0.
            match_ID_param = '0&&&0'
            for param in p4_call_params:
              if type(param) is p4_hlir.hlir.p4_imperatives.p4_signature_ref:
                match_ID_param = '[match ID]&&&0x7FFFFF'
                istemplate = True
                break
            mparams.append(match_ID_param)

          aparams = self.gen_action_aparams(p4_call, call, field_offsets)

          if istemplate == True:
            aparams.append('0') # meta_primitive_state.match_ID mparam matters
            idx = -1
            if type(p4_call_params[1]) is p4_hlir.hlir.p4_imperatives.p4_signature_ref:
              idx = p4_call_params[1].idx
            command_templates.append(HP4_Primitive_Command(table_name,
                                            action.name,
                                            "table_add",
                                            tname,
                                            aname,
                                            mparams,
                                            aparams,
                                            str(idx)))
          else:
            # meta_primitive_state.match_ID mparam does not matter
            # only append priority if the table involves ternary matching
            #  e.g., drop tables do not
            if len(mparams) > 0:
              for param in mparams:
                if '&&&' in param:
                  aparams.append(str(LOWEST_PRIORITY))
                  break
            commands.append(HP4_Command("table_add",
                                        tname,
                                        aname,
                                        mparams,
                                        aparams))

    return commands, command_templates


  def build(self, h):

    self.field_offsets = collect_meta(h.p4_header_instances)
    self.action_ID = collect_actions(h.p4_actions.values())

    pre_pcs = PC_State(parse_state=h.p4_parse_states['start'])
    launch_process_parse_tree_clr(pre_pcs, h)

    self.header_offsets = collect_header_offsets(pre_pcs)
    self.field_offsets.update(collect_field_offsets(self.header_offsets,
                                                    h.p4_header_instances))

    consolidate_parse_tree_clr(pre_pcs, h)

    ingress_pcs_list = collect_ingress_pcs(pre_pcs)
    self.vbits = get_vbits(ingress_pcs_list)

    first_table = h.p4_ingress_ptr.keys()[0]

    ps_entries = gen_parse_select_entries(pre_pcs)
    # post-process output of gen_parse_select_entries:
    #  parse_select_00_19, _20_29, and _30_39 use 320b field ext.first
    ps_entries = process_parse_select_entries(ps_entries)

    self.commands = gen_parse_control_entries(pre_pcs) \
                  + ps_entries \
                  + gen_pipeline_config_entries(pre_pcs, first_table,
                                                ingress_pcs_list, self.vbits)

    self.table_to_trep, self.action_to_arep = self.walk_ingress_pipeline(h.p4_tables)
    self.command_templates = self.gen_tX_templates(h.p4_tables)
    action_commands, action_templates = self.gen_action_entries(self.action_to_arep,
                                                               self.action_ID,
                                                               self.field_offsets)
    self.commands += action_commands
    self.command_templates += action_templates

    self.commands += gen_tmiss_entries(h.p4_tables,
                                       self.table_to_trep,
                                       h.p4_control_flows['ingress'],
                                       self.numprimitives)

    self.commands += gen_t_checksum_entries(h.calculated_fields,
                                            h.p4_field_list_calculations,
                                            self.field_offsets,
                                            self.vbits)

    self.commands += gen_t_resize_pr_entries()

  def compile_to_hp4(self, program_path, out_path, mt_out_path, numprimitives):
    self.out_path = out_path
    self.mt_out_path = mt_out_path
    self.numprimitives = numprimitives
    h = HLIR(program_path)
    h.add_primitives(json.loads(pkg_resources.resource_string('p4c_bm', 'primitives.json')))
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

    def getkey(command):
      return (command.table, command.source_action, command.action_params)
    sorted_ct = sorted(self.command_templates, key=getkey)

    json.dump(sorted_ct, out, default=convert_to_builtin_type, indent=2)
    out.close()

def do_support_checks(h):
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
    aparams.append(str(int(ceil(start_pcs.p4_bits_extracted / 8.0))))
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
    unsupported("select criteria (" + str(crit[OFFSET]) + ", " + str(crit[WIDTH]) \
                              + ") not divisible by 8")

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
      numbytes = int(ceil(next_pcs.hp4_bits_extracted / 8.0))
      aparams.append(str(numbytes))

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
        numbytes = int(ceil(next_pcs.hp4_bits_extracted / 8.0))
        aparams.append(str(numbytes))
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

def process_parse_select_entries(ps_entries):
  ret = []
  for command in ps_entries:
    strbounds = command.table.split('tset_parse_select_')[1].split('_')
    lower, upper = [int(x) for x in strbounds]
    if lower > EXT_FIRST_WIDTH:
      ret.append(command)

    new_mp_val = ''
    new_mp_mask = ''
    started = False
    for mp in command.match_params[EXT_START_INDEX:]:
      val, mask = [int(x, 0) for x in mp.split('&&&')]
      if started or mask != 0:
        started = True
        valstr, maskstr = ["0x{:02x}".format(x).split('0x')[1] for x in [val, mask]]
        new_mp_val += valstr
        new_mp_mask += maskstr

    # fill out remaining bytes until we have all 40
    for j in range(upper + 1, EXT_FIRST_WIDTH):
      new_mp_val += '00'
      new_mp_mask += '00'

    new_mp = command.match_params[0:EXT_START_INDEX]
    new_mp.append('0x' + new_mp_val + '&&&0x' + new_mp_mask)
    ret.append(HP4_Command(command='table_add',
                           table=command.table,
                           action=command.action,
                           match_params=new_mp,
                           action_params=command.action_params))
    
  return ret

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
    unsupported("Unhandled ps return_statement: " + ps.return_statement[PS_RET_TYPE])

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

def get_vbits(ingress_pcs_list):
  headerset, maxdepth = get_headerset_and_maxdepth(ingress_pcs_list)
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

  match = table.match_fields[0] # supporting only one match field
  match_type = match[MATCH_TYPE]

  if match_type.value == 'P4_MATCH_EXACT':
    field = match[MATCH_OBJECT]
    header = field.instance
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
        unsupported("ERROR: Unsupported: match on stdmetadata field %s" % field.name)

    elif header_hp4_type == 'metadata':
      return '[METADATA_EXACT]'
    elif header_hp4_type == 'extracted':
      return '[EXTRACTED_EXACT]'
  elif match_type.value == 'P4_MATCH_VALID':
    return '[EXTRACTED_VALID]'
  else:
    unsupported("Not yet supported: " + match_type.value)
  
def gen_pipeline_config_entries(pcs, first_table, ingress_pcs_list, vbits):
  if pcs.pcs_id == 0:
    return gen_pipeline_config_entries(pcs.children[0],
                                       first_table,
                                       ingress_pcs_list,
                                       vbits)

  commands = []

  aparam_table_ID = get_aparam_table_ID(first_table)  

  for pcs in ingress_pcs_list:
    val = 0
    for i, header in enumerate( sorted(pcs.header_offsets,
                                       key=pcs.header_offsets.get) ):
      val = val | vbits[(i, header)]

    valstr = '0x' + '%x' % val
    commands.append(HP4_Command('table_add',
                                'tset_pipeline_config',
                                'a_set_pipeline',
                                ['[vdev ID]', str(pcs.pcs_id)],
                                [aparam_table_ID, valstr, HIGHEST_PRIORITY]))

  return commands

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
  #print(str(pcs.pcs_id) + ' [' + pcs.parse_state.name + ']')
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

def collect_header_offsets(pcs, header_offsets={}):
  for header in pcs.header_offsets:
    if header in header_offsets:
      if pcs.header_offsets[header] != header_offsets[header]:
        unsupported("Unsupported: %s has multiple potential offsets; %db and %db" \
                    % (header, pcs.header_offsets[header], header_offsets[header]))
  header_offsets.update(pcs.header_offsets)
  for child in pcs.children:
    header_offsets = collect_header_offsets(child, header_offsets)

  return header_offsets

def collect_field_offsets(header_offsets, header_instances):
  field_offsets = {}
  for header in header_offsets:
    hinst = header_instances[header]
    for field in hinst.fields:
      field_offsets[header + '.' + field.name] = field.offset + header_offsets[header]

  return field_offsets

def get_table_from_cs(control_statement):
    if type(control_statement) is p4_table:
      return control_statement
    elif type(control_statement) is tuple:
      return control_statement[0]
    else:
      unsupported("Error (get_table_from_cs): unsupported control statement type: " \
            + str(type(control_statement)))

def walk_control_block(control_block, table):
    for control_statement in control_block:
      cs_idx = control_block.index(control_statement)
      if type(control_statement) is p4_table:
        # apply_table_call
        if control_statement == table:
          if cs_idx == len(control_block) - 1:
            return True, None
          return True, get_table_from_cs(control_block[cs_idx + 1])
      elif type(control_statement) is tuple:
        # apply_and_select_block
        if control_statement[0] == table:
          if cs_idx == len(control_block) - 1:
            return True, None
          return True, get_table_from_cs(control_block[cs_idx + 1])
        else:
          for case in control_statement[1]:
            found, next_table = walk_control_block(case[1], table)
            if found:
              if next_table != None:
                return True, next_table
              elif cs_idx < len(control_block) - 1:
                return True, get_table_from_cs(control_block[cs_idx + 1])
              else:
                return True, None
      else:
        unsupported("Error: unsupported call_sequence entry type: " + str(type(entry)))

    return False, None

def gen_tmiss_entries(tables, table_to_trep, ingress, numprimitives):
  commands = []

  for table_name in tables:

    table = tables[table_name]
    trep = table_to_trep[table]
    tname = trep.name
    stage = trep.stage # int
    aname = 'init_program_state'
    mparams = ['[vdev ID]']
    if 'matchless' not in tname:
      mparams.append('0&&&0')
                 
    # identify next_table so we can look up stage for aparams[0]
    #   aparams[0]: 'next_stage' parameter in finish_action (stages.p4/p4t)
    if 'miss' in table.next_:
      next_table = table.next_['miss']
    else:
      found, next_table = walk_control_block(ingress.call_sequence, table)

    if next_table == None:
      next_stage = '0'
      next_table_type = '0'
    else:
      next_stage = str(table_to_trep[next_table].stage)
      next_table_type = table_to_trep[next_table].table_type()

    aparams = ['0', # action_ID
               '0', # match_ID
               next_stage,
               next_table_type]
      
    # zeros for remaining type / subtype parameters of init_program_state
    for i in range(numprimitives):
      aparams.append('0')
      aparams.append('0')

    if 'matchless' not in tname:
      aparams.append(str(LOWEST_PRIORITY))

    commands.append(HP4_Command(command="table_add",
                                table=tname,
                                action=aname,
                                match_params=mparams,
                                action_params=aparams))

  return commands

# gen_t_checksum_entries(h.calculated_fields)
def gen_t_checksum_entries(calculated_fields, p4_field_list_calculations,
                           field_offsets, vbits):
    """ detect and handle ipv4 checksum """
    commands = []

    cf_none_types = 0
    cf_valid_types = 0
    checksum_detected = False
    for cf in calculated_fields:
      for statement in cf[1]:
        if statement[0] == 'update':
          flc = p4_field_list_calculations[statement[1]]
          for fl in flc.input:
            count = 0
            max_field_offset = 0
            max_field = None
            for field in fl.fields:
              count += field.width
              if field.offset > max_field_offset:
                max_field_offset = field.offset
                max_field = field
            if count == 144:
              if flc.algorithm == 'csum16' and flc.output_width == 16:
                # Calculate rshift_base parameter
                #  This is the amount to R-shift extracted.data such
                #  that the ipv4 header is right aligned
                key = max_field.instance.name + '.' + max_field.name
                # TODO: remove assumption that extracted.data is 800 bits
                aparam = str(800 - field_offsets[key] - max_field.width)
                if statement[2] == None:
                  cf_none_types += 1
                  if (cf_none_types + cf_valid_types) > 1:
                    print("ERROR: Unsupported: multiple checksums")
                    exit()
                  else:
                    checksum_detected = True
                    commands.append(HP4_Command("table_add",
                                                "t_checksum",
                                                "a_ipv4_csum16",
                                                ['[vdev ID]', '0&&&0'],
                                                [aparam, str(LOWEST_PRIORITY)]))
                else:
                  if statement[2].op == 'valid':
                    cf_valid_types += 1
                    if (cf_none_types + cf_valid_types) > 1:
                      print("ERROR: Unsupported: multiple checksums")
                      exit()
                    else:
                      # TODO: reduce entries by isolating relevant bit
                      for key in vbits.keys():
                        if statement[2].right == key[1]:
                          mparams = ['[vdev ID]']
                          val = format(vbits[key], '#x')
                          mparams.append(val + '&&&' + val)
                          checksum_detected = True
                          commands.append(HP4_Command("table_add",
                                                      "t_checksum",
                                                      "a_ipv4_csum16",
                                                       mparams,
                                                       [aparam, '0']))
                  else:
                    unsupported("ERROR: Unsupported if_cond op " \
                                + "in calculated field: %s" % statement[2].op)

              else:
                unsupported("ERROR: Unsupported checksum (%s, %i)" \
                            % (flc.algorithm, flc.output_width))

            else:
              unsupported("ERROR: Unsupported checksum - field list of %i bits" \
                          % count)

        else:
          unsupported("WARNING: Unsupported update_verify_spec " \
                      + "for calculated field: %s" % statement[0])

    if checksum_detected == False:
      commands.append(HP4_Command("table_add",
                                      "t_checksum",
                                      "_no_op",
                                      ['[vdev ID]', '0&&&0'],
                                      [str(LOWEST_PRIORITY)]))

    return commands

def gen_t_resize_pr_entries():
    commands = []
    # TODO: full implementation as the following primitives get support:
    # - add_header | remove_header | truncate | push | pop | copy_header*
    # * maybe (due to possibility of making previously invalid header
    #   valid)
    # default entry handled by controller

    return commands

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

if __name__ == '__main__':
  main()
