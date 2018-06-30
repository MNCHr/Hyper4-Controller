#!/usr/bin/python

from compiler import HP4Compiler, CodeRepresentation
from p4_hlir.main import HLIR
import p4_hlir
from p4_hlir.hlir.p4_core import p4_enum
from p4_hlir.hlir.p4_tables import p4_table
from collections import OrderedDict
import argparse
import code
# code.interact(local=dict(globals(), **locals()))
import sys
import math
import json

RETURN_TYPE = 0
CRITERIA = 1
NEXT_PARSE_STATE = 1
CASE_ENTRIES = 2
METADATA_WIDTH = 256

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
                    'remove_header': 'removeh',
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
                      ('ext', 'meta'): '14'} #,
                      #('mcast_grp', 'const'): '80'}

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
                          '14': 'mod_extracted_meta'} #,
                           #'80': 'mod_intmeta_mcast_grp_const'}

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

class HP4_Command:
  def __init__(self, command, table, action, mparams, aparams):
    self.command = command
    self.table = table
    self.action = action
    self.match_params = mparams
    self.action_params = aparams
  def __str__(self):
    """ assumes command is \'table_add\' """
    if self.command != 'table_add':
      print("ERROR: incorrect table command %s, table %s" % (self.command, self.table))
      exit()
    ret = self.table + ' ' + self.action + ' :'
    ret += ' '.join(self.match_params)
    ret += ':'
    ret += ' '.join(self.action_params)
    return ret

class HP4_Parse_Select_Command(HP4_Command):
  def __init__(self):
    HP4_Command.__init__(self, '', '', '', [], [])
    self.curr_pc_state = 0
    self.next_pc_state = 0
    self.next_parse_state = ''
    self.priority = 0

class HP4_Match_Command(HP4_Command):
  def __init__(self, source_table, source_action, command, table, action, mparams, aparams):
    HP4_Command.__init__(self, command, table, action, mparams, aparams)
    self.source_table = source_table
    self.source_action = source_action

class HP4_Primitive_Command(HP4_Command):
  def __init__(self, source_table, source_action, command, table, action, mparams, aparams, src_aparam_id):
    HP4_Command.__init__(self, command, table, action, mparams, aparams)
    self.source_table = source_table
    self.source_action = source_action
    self.src_aparam_id = src_aparam_id

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


class P4_to_HP4(HP4Compiler):

  def collect_headers(self):
    """ Classify headers (metadata | parsed representation)
        - For metadata: assign each field an offset into meta.data
        - NOTE: the same cannot be done for parsed representation headers
          until we traverse the parse tree, because each path through the
          parse tree potentially yields a distinct set of field offsets
          into pr.data.
    """
    metadata_offset = 0
    for header_key in self.h.p4_header_instances.keys():
      header = self.h.p4_header_instances[header_key]
      if header.name == 'standard_metadata':
        self.headers_hp4_type[header_key] = 'standard_metadata'
        continue
      if header.metadata == True:
        self.headers_hp4_type[header_key] = 'metadata'
        for field in header.fields:
          fullname = header.name + '.' + field.name
          self.field_offsets[fullname] = metadata_offset
          metadata_offset += field.width
          if metadata_offset > METADATA_WIDTH:
            print("Error: out of metadata memory with %s" % fullname)
            exit()
      else:
        self.headers_hp4_type[header_key] = 'extracted'
    metadata_offset = 0

  def collect_actions(self):
    """ Uniquely number each action """
    for action in self.h.p4_actions.values():
      if action.lineno > 0: # is action from source (else built-in)?
        self.action_ID[action] = self.actionID
        self.actionID += 1

  def update_parse_state_maps(self, parse_state, pc_state):
    """ Track associations between parse states and parse control states """
    if self.ps_to_pc.has_key(parse_state) is False:
      self.ps_to_pc[parse_state] = set()
    if pc_state == 0:
      self.ps_to_pc[parse_state].add(1)
      self.pc_to_ps[1] = parse_state
    else:
      self.ps_to_pc[parse_state].add(pc_state)
      self.pc_to_ps[pc_state] = parse_state

  def process_parse_state(self, parse_state, pc_state):
    """ Analyze a parse control state
        - Examine associated parse state's calls
          - extract calls affect field offsets
          - extract calls and 'current' statements affect the
            number of bytes that should be extracted prior to entering
            the parse control state
            - but 'current' statements do not advance the pointer; this
              must be taken into account when looking at next parse control
              states
          - Identify byte range XX-YY in return statements of type 'select',
            requiring tset_parse_select_XX_YY entries
    """
    self.update_parse_state_maps(parse_state, pc_state)

    # numbits: Total number of bits that must have been extracted for hp4
    #          to handle this pc state.
    numbits = self.offset # measures how far into the packet we are already

    # handle extract statements
    for call in parse_state.call_sequence:
      if call[0].value != 'extract':
        print("ERROR: unsupported call %s" % call[0].value)
        exit()
      # update field_offsets, numbits
      for field in call[1].fields:
        self.field_offsets[call[1].name + '.' + field.name] = self.offset
        self.offset += field.width # advance offset
        numbits += field.width     # update requirement

    #code.interact(local=dict(globals(), **locals()))

    # establish required number of bits for hp4 to handle the pc state
    if numbits > self.seb * 8:
      self.pc_bits_extracted[pc_state] = numbits
    else:
      self.pc_bits_extracted[pc_state] = self.seb * 8
    self.pc_bit_offsets[pc_state] = self.offset
    if pc_state == 0: # TODO: proper implementation vs. this hack
      self.pc_bit_offsets[1] = self.offset

    # shouldn't we delay the preceding statements until we've processed
    #  the return_statement?

    if parse_state.return_statement[RETURN_TYPE] == 'immediate':
      if parse_state.return_statement[NEXT_PARSE_STATE] == 'ingress':
        self.pc_action[pc_state] = '[PROCEED]'
    elif parse_state.return_statement[RETURN_TYPE] == 'select':
      # The parse_select_* tables follow parse_control and read the
      #  pc_state.  Following parse_control, pc_state will == 1 if
      #  the node is parse 'start'.  Track value of pc_state as
      #  read by parse_select_* tables with parse_select_pc_state:
      if pc_state == 0:
        parse_select_pc_state = 1
      else:
        parse_select_pc_state = pc_state

      # account for 'current' instances
      maxcurr = 0
      # identify range of bytes to examine
      startbytes = 100
      endbytes = 0
      self.parse_select_match_offsets[parse_select_pc_state] = []
      for criteria in parse_state.return_statement[CRITERIA]:
        if isinstance(criteria, tuple): # tuple indicates use of 'current'
          # criteria[0]: start offset from current position
          # criteria[1]: width of 'current' call
          if maxcurr < criteria[0] + criteria[1]:
            maxcurr = criteria[0] + criteria[1]
          if (startbytes * 8) > self.offset + criteria[0]:
            startbytes = (self.offset + criteria[0]) / 8
          if (endbytes * 8) < self.offset + maxcurr:
            endbytes = int(math.ceil((self.offset + maxcurr) / 8.0))
        else: # single field
          offset_width = (self.field_offsets[criteria],
                          self.h.p4_fields[criteria].width)
          self.parse_select_match_offsets[parse_select_pc_state].append(offset_width)
          fieldstart = self.field_offsets[criteria] / 8
          fieldend = int(math.ceil((fieldstart * 8
                                    + self.h.p4_fields[criteria].width) / 8.0))
          if startbytes > fieldstart:
            startbytes = fieldstart
          if endbytes < fieldend:
            endbytes = fieldend

      #print(str(parse_state) + ': maxcurr = ' + str(maxcurr) + '; offset = ' \
      #    + str(self.offset))
      #print('pc_bits_extracted[' + str(pc_state) + ']: ' \
      #    + str(self.pc_bits_extracted[pc_state]))
      if (maxcurr + self.offset) > self.pc_bits_extracted[pc_state]:
        self.pc_bits_extracted[pc_state] = self.offset + maxcurr
  
      # pc_action[pc_state] = 'parse_select_XX_YY'
      if startbytes >= endbytes:
        print("ERROR: startbytes(%i) > endbytes(%i)" % (startbytes, endbytes))
        print("parse_state: %s" % parse_state)
        exit()
      def unsupported(sbytes, ebytes):
        print("ERROR: Not yet supported: startbytes(%i) and endbytes(%i) cross \
               boundaries"  % (sbytes, ebytes))
        exit()
      if startbytes < 20:
        if endbytes >= 20:
          unsupported(startbytes, endbytes)
        else:
          self.pc_action[pc_state] = '[PARSE_SELECT_00_19]'
          self.parse_select_table_names[parse_select_pc_state] = 'tset_parse_select_00_19'
      else:
        bound = 30
        while bound <= 100:
          if startbytes < bound:
            if endbytes >= bound:
              unsupported(startbytes, endbytes)
            else:
              namecore = 'parse_select_' + str(bound - 10) + '_' + str(bound - 1)
              self.pc_action[pc_state] = '[' + namecore.upper() + ']'
              self.parse_select_table_names[parse_select_pc_state] = 'tset_' + namecore
              break
          bound += 10
      if pc_state not in self.pc_action:
        print("ERROR: did not find parse_select_XX_YY function for \
               startbytes(%i) and endbytes(%i)" % (startbytes, endbytes))
        exit()

  def fill_parse_select_match_params(self, criteria_fields, values, pc_state):
    if len(criteria_fields) != len(values):
      print("ERROR: criteria_fields(%i) not same length as values(%i)" \
            % (len(criteria_fields),len(values)))
      exit()
    # looking at a single criteria field is sufficient to determine the byte
    #  range for the inspection, which affects the size of the match

    #  parameters string (20 bytes for the first parse_select table, 10 bytes
    #  for all others)
    mparams = []
    bitoffset = 0
    if isinstance(criteria_fields[0], str):
      # not 'current'
      bitoffset = self.field_offsets[criteria_fields[0]]
    elif isinstance(criteria_fields[0], tuple):
      # using 'current'
      bitoffset = criteria_fields[0][0]
      if pc_state in self.pc_bits_extracted:
        bitoffset += self.pc_bits_extracted[pc_state]
    #print('fill_parse_select_match_params')
    #code.interact(local=dict(globals(), **locals()))
    if bitoffset / 8 < 40:
      mparams = self.fill_parse_select_match_params_under40(criteria_fields, values, pc_state)
    else:
      mparams = self.fill_parse_select_match_params_40_99(criteria_fields, values, pc_state)

    ret = ['[vdev ID]', str(pc_state)]
    for mparam in mparams:
      ret.append(str(mparam))
    return ret

  def fill_parse_select_match_params_under40(self, criteria_fields, values, pc_state):
    mparam = MatchParam()
    for i in range(len(criteria_fields)):
      if values[i][0] != 'value' and values[i][0] != 'default':
        print("Not yet supported: type %s in case entry" % values[i][0])
        exit()
      fo = 0
      width = 0
      if isinstance(criteria_fields[i], str): # not 'current' tuple
        fo = self.field_offsets[criteria_fields[i]]
        width = self.h.p4_fields[criteria_fields[i]].width
      elif isinstance(criteria_fields[i], tuple): # 'current' tuple
        fo = criteria_fields[i][0] + self.pc_bit_offsets[pc_state]
        width = criteria_fields[i][1]
      fieldend = fo + width
      value = 0
      val = 0
      mask = 0
      if values[i][0] == 'value':
        value = values[i][1]
        mask = 0x00000000000000000000000000000000000000000000000000000000000000000000000000000000
        pos = fo
        while pos < fieldend:
          bit = 0x80000000000000000000000000000000000000000000000000000000000000000000000000000000 >> pos
          mask = mask | bit
          pos += 1
        try:
          val = value << (320 - fieldend)
        except ValueError as e:
          print(e)
          code.interact(local=dict(globals(), **locals()))
          exit()
      mparam.mask = mparam.mask | mask
      mparam.value = mparam.value | val
    return [mparam]

  def fill_parse_select_match_params_40_99(self, criteria_fields, values, pc_state):
    # create our return value, a list of MatchParams for tset_parse_select_40_49
    #  each initialized to '0&&&0' (value 0, mask 0 = don't care)
    mparams = [MatchParam() for count in xrange(10)]
    for i in range(len(criteria_fields)):
      # get field offset and width
      if isinstance(criteria_fields[i], tuple): # current
        fo = criteria_fields[i][0] + self.pc_bit_offsets[pc_state]
        width = criteria_fields[i][1]
      else: # field
        fo = self.field_offsets[criteria_fields[i]]
        width = self.h.p4_fields[criteria_fields[i]].width

      # set index of starting match parameter
      j = (fo / 8) % len(mparams)

      # set position of next bit after field
      fieldend = fo + width

      # set index of ending match parameter
      end_j = (int(math.ceil(fieldend / 8.0)) - 1) % len(mparams)

      value = 0
      if values[i][0] == 'value':
        value = values[i][1]
      while j <= end_j:
        mask = 0b00000000
        pos = fo % 8
        end = min(pos + width, 8)
        if values[i][0] == 'value':
          bit = 128 >> pos
          while pos < end:
            mask = mask | bit
            bit = bit >> 1
            pos += 1
        # truncate bits outside current byte boundary
        val = value >> (((fo % 8) + width) - end)
        # lshift to place value in correct position within current byte
        val = val << (8 - end)
        
        mparams[j].mask = mparams[j].mask | mask
        mparams[j].value = mparams[j].value | val
        j += 1
        if j <= end_j: # prepare for next iteration
          advance = 8 - (fo % 8)
          # advance fo
          fo = fo + advance
          # reduce width
          width = width - advance
          # change values[i]
          if width > 0:
            value = value % (1 << width)
    return mparams

  def walk_ingress_pipeline(self, curr_table):
    """ populate table_to_trep and action_to_arep data structures """

    # 1) Do topological sort of tables
    tsorter = DAG_Topo_Sorter(self.h.p4_tables)
    tsort = tsorter.sort()
    # 2) assign each one to a unique stage
    for i in range(len(tsort)):
      curr_table = tsort[i]
      source_type = ''
      match_type = 'MATCHLESS'
      field_name = ''
      if len(curr_table.match_fields) > 0:
        match_type = curr_table.match_fields[0][1].value
        field_name = curr_table.match_fields[0][0].name
        if (match_type == 'P4_MATCH_EXACT' or
            match_type == 'P4_MATCH_TERNARY'):
          # headers_hp4_type[<str>]: 'standard_metadata' | 'metadata' | 'extracted'
          source_type = self.headers_hp4_type[curr_table.match_fields[0][0].instance.name]
        elif match_type == 'P4_MATCH_VALID':
          source_type = self.headers_hp4_type[curr_table.match_fields[0][0].name]
      self.table_to_trep[curr_table] = Table_Rep(self.stage,
                                                 match_type,
                                                 source_type,
                                                 field_name)

      for action in curr_table.actions:
        if self.action_to_arep.has_key(action) is False:
          self.action_to_arep[action] = Action_Rep()
          for call in action.call_sequence:
            prim_type = call[0].name
            prim_subtype = self.get_prim_subtype(call)
            self.action_to_arep[action].call_sequence.append((prim_type, prim_subtype))
        self.action_to_arep[action].stages.add(self.stage)
        self.action_to_arep[action].tables[self.stage] = curr_table.name

      self.stage += 1

  def walk_parse_tree(self, parse_state, pc_state):
    """ parse_state: the HLIR object representing a parse node
        pc_state: A parse_control state representing a (possibly partial) path
                  through the parse tree
        - Collect parse control states, each uniquely numbered and associated
          with a list of parse states representing a (possibly partial) path
          through the parse tree.
        - Analyze each parse control state to identify its byte extraction
          requirements (to know when/how we should invoke the extract_more
          action)
    """ 
    # TODO: resolve concern that direct jumps not merged properly
    self.process_parse_state(parse_state, pc_state)

    curr_pc_state = pc_state
    if curr_pc_state == 0:
      curr_pc_state += 1
      self.pc_to_preceding_pcs[curr_pc_state] = []

    # traverse parse tree
    next_states = []
    next_states_pcs = {}
    if parse_state.return_statement[RETURN_TYPE] == 'immediate':
      if parse_state.return_statement[NEXT_PARSE_STATE] != 'ingress':
        next_state = self.h.p4_parse_states[parse_state.return_statement[1]]
        self.walk_parse_tree(next_state, pc_state)
      else:
        return
    elif parse_state.return_statement[RETURN_TYPE] == 'select':
      # return_statement[CASE_ENTRIES]: list of tuples (see case_entry below)
      for case_entry in parse_state.return_statement[CASE_ENTRIES]:
        t = HP4_Parse_Select_Command()
        t.command = "table_add"
        t.curr_pc_state = curr_pc_state
        t.table = self.parse_select_table_names[curr_pc_state]
        t.match_params = self.fill_parse_select_match_params(parse_state.return_statement[CRITERIA], case_entry[0], t.curr_pc_state)
        if case_entry[0][0][0] == 'default':
          t.priority = MAX_PRIORITY
        # case_entry: (list of values, next parse_state)
        if case_entry[1] != 'ingress':
          next_state = self.h.p4_parse_states[case_entry[1]]
          t.next_parse_state = next_state
          if next_state not in next_states:
            if pc_state == 0:
              pc_state += 1
            pc_state += 1
            next_states_pcs[next_state] = pc_state

            # track preceding pc_states
            if self.pc_to_preceding_pcs.has_key(curr_pc_state) is False:
              self.pc_to_preceding_pcs[curr_pc_state] = []
            self.pc_to_preceding_pcs[pc_state] = self.pc_to_preceding_pcs[curr_pc_state] + [curr_pc_state]

            # TODO: verify this line is correct; does it account for 'current'?
            # I think these lines are unnecessary - should be handled in process_parse_state
            #if self.offset > self.seb * 8:
            #  self.pc_bits_extracted[pc_state] = self.offset
            #else:
            #  self.pc_bits_extracted[pc_state] = self.seb * 8

            next_states.append(next_state)
            t.next_pc_state = pc_state
          else:
            t.next_pc_state = next_states_pcs[next_state]
        else:
          t.next_parse_state = 'ingress'
          t.next_pc_state = t.curr_pc_state
          t.action = 'set_next_action'
          t.action_params = ['[PROCEED]', str(t.next_pc_state), str(t.priority)]
        self.parse_select_list.append(t)
    else:
      print("ERROR: Unknown directive in return statement: %s" \
            % parse_state.return_statement[0])
      exit()

    save_offset = self.offset
    for next_state in next_states:
      self.walk_parse_tree(next_state, next_states_pcs[next_state])
      self.offset = save_offset

  def gen_tset_parse_control_entries(self):
    self.walk_parse_tree(self.h.p4_parse_states['start'], 0)
    for key in self.pc_action.keys():
      # special handling for pc_state 0
      if key == 0:
        if self.pc_bits_extracted[0] > (self.seb * 8):
          self.commands.append(HP4_Command("table_add",
                                           "tset_parse_control",
                                           "extract_more",
                                           ["[vdev ID]", "0"],
                                           [str(self.pc_bits_extracted[0]), "1"]))
          self.commands.append(HP4_Command("table_add",
                                           "tset_parse_control",
                                           "set_next_action",
                                           ["[vdev ID]", "1"],
                                           [self.pc_action[0], "1"]))
        else:
          self.commands.append(HP4_Command("table_add",
                                           "tset_parse_control",
                                           "set_next_action",
                                           ["[vdev ID]", "0"],
                                           [self.pc_action[0], "1"]))
          self.pc_bits_extracted[0] = self.seb * 8

        self.pc_bits_extracted[1] = self.pc_bits_extracted[0]
        self.pc_bits_extracted[0] = self.seb * 8
        self.pc_action[1] = self.pc_action[0]

      else:
        self.commands.append(HP4_Command("table_add",
                                         "tset_parse_control",
                                         "set_next_action",
                                         ["[vdev ID]", str(key)],
                                         [self.pc_action[key], str(key)]))

  def gen_tset_parse_select_entries(self):
    for t in self.parse_select_list:
      if t.next_parse_state != 'ingress':
        if self.pc_bits_extracted[t.next_pc_state] > self.pc_bits_extracted[t.curr_pc_state]:
          t.action = "extract_more"
          bytes = int(math.ceil(self.pc_bits_extracted[t.next_pc_state] / 8.0))
          t.action_params = [str(bytes), str(t.next_pc_state), str(t.priority)]
        else:
          t.action = "set_next_action"
          if t.next_pc_state in self.parse_select_table_names:
            next_action = "[" + self.parse_select_table_names[t.next_pc_state].split('tset_')[1].upper() + "]"
          else:
            next_action = "[PROCEED]"
          t.action_params = [next_action, str(t.next_pc_state), str(t.priority)]
      self.commands.append(t)

  def gen_tset_pipeline_config_entries(self):
    # USEFUL DATA STRUCTURES:
    # self.ps_to_pc = {p4_parse_state : pc_state}
    # self.pc_to_ps = {pc_state : p4_parse_state}
    # self.pc_to_preceding_pcs = {pc_state : [pc_state, ..., pc_state]}
    # self.h.p4_ingress_ptr = {p4_table: set([p4_parse_state, ..., p4_parse_state])}
    # self.h.p4_ingress_ptr.keys()[0].match_fields: (p4_field, MATCH_TYPE, None)
    #    MATCH_TYPE: P4_MATCH_EXACT | ? (no doubt P4_MATCH_VALID, others)
    #    third is probably mask
    if len(self.h.p4_ingress_ptr.keys()) > 1:
      print("Not yet supported: multiple entry points into ingress pipeline")
      exit()
    first_table = self.h.p4_ingress_ptr.keys()[0]
    if len(first_table.match_fields) > 1:
      print("Not yet supported: multiple field matches (table: %s)" % first_table.name)
      exit()

    # create all the valid values for extracted.validbits
    pc_headers = {}
    longest = 0
    for ingress_ps in self.h.p4_ingress_ptr[first_table]:
      for pc_state in self.ps_to_pc[ingress_ps]:
        pc_headers[pc_state] = []
        for prec_pc in self.pc_to_preceding_pcs[pc_state]:
          ps = self.pc_to_ps[prec_pc]
          for call in ps.call_sequence:
            if call[0].value != 'extract':
              print("ERROR (gen_tset_pipeline_config_entries): unsupported call %s" % call[0].value)
              exit()
            pc_headers[pc_state].append(call[1])
        for call in ingress_ps.call_sequence:
          if call[0].value != 'extract':
            print("ERROR (gen_tset_pipeline_config_entries): unsupported call %s" % call[0].value)
            exit()
          pc_headers[pc_state].append(call[1])

        if len(pc_headers[pc_state]) > longest:
          longest = len(pc_headers[pc_state])

    headerset = []
    for j in range(longest):
      headerset.append(set())
      
      for pc_state in pc_headers.keys():
        if len(pc_headers[pc_state]) > j:
          headerset[j].add(pc_headers[pc_state][j])

    # extracted.validbits is 80b wide
    # vbits: {(level (int), header name (str)): number (binary)}
    lshift = 80
    for j in range(longest):
      numbits = len(headerset[j])
      lshift = lshift - numbits
      i = 1
      for header in headerset[j]:
        self.vbits[(j, header)] = i << lshift
        i = i << 1

    # handle table_ID
    if len(first_table.match_fields) > 1:
      print("Not yet supported: multiple match fields (%s)" % first_table.name)
      exit()
    if len(first_table.match_fields) == 0:
      aparam_table_ID = '[MATCHLESS]'
    else:
      field_match = first_table.match_fields[0]
      field = field_match[0]
      match_type = field_match[1]

      if match_type.value == 'P4_MATCH_EXACT':
        if self.headers_hp4_type[field.instance.name] == 'standard_metadata':
          if field.name == 'ingress_port':
            aparam_table_ID = '[STDMETA_INGRESS_PORT_EXACT]'
          elif field.name == 'packet_length':
            aparam_table_ID = '[STDMETA_PACKET_LENGTH_EXACT]'
          elif field.name == 'instance_type':
            aparam_table_ID = '[STDMETA_INSTANCE_TYPE_EXACT]'
          elif field.name == 'egress_spec':
            aparam_table_ID = '[STDMETA_EGRESS_SPEC_EXACT]'
          else:
            print("ERROR: Unsupported: match on stdmetadata field %s" % field.name)
            exit()
        elif self.headers_hp4_type[field.instance.name] == 'metadata':
          aparam_table_ID = '[METADATA_EXACT]'
        elif self.headers_hp4_type[field.instance.name] == 'extracted':
          aparam_table_ID = '[EXTRACTED_EXACT]'
      elif match_type.value == 'P4_MATCH_VALID':
        aparam_table_ID = '[EXTRACTED_VALID]'
      else:
        print("Not yet supported: " + match_type.value)
        exit()
        # code.interact(local=dict(globals(), **locals()))

    for ps in self.h.p4_ingress_ptr[first_table]:
      for pc_state in self.ps_to_pc[ps]:
        val = 0
        for i in range(len(pc_headers[pc_state])):
          val = val | self.vbits[(i, pc_headers[pc_state][i])]
        valstr = '0x' + '%x' % val

        self.commands.append(HP4_Command("table_add",
                                         "tset_pipeline_config",
                                         "a_set_pipeline",
                                         ['[vdev ID]', str(pc_state)],
                                         [aparam_table_ID, valstr, '0']))

  def gen_bitmask(self, fieldwidth, offset, maskwidth):
    """fieldwidth: bits; offset: bits; maskwidth: bytes"""
    mask = '0x'
    # offset = self.field_offsets[str(field)]
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
    # maskwidth = 100
    # if field.instance.metadata:
    #  maskwidth = 32
    mask += '[' + str(maskwidth - bytes_written) + 'x00s]'
    #while bytes_written < 100:
    #  mask += '00'
    #  bytes_written += 1
    return mask

  def gen_bitmask2(self, fieldwidth, offset, maskwidthbits):
    mask = '0x'
    bits_written = offset
    bits_left = fieldwidth
    while bits_left > 0:
      bit = 0b10000000 >> offset

  def gen_tX_templates(self):
    self.walk_ingress_pipeline(self.h.p4_ingress_ptr.keys()[0])
    for table in self.table_to_trep:
      tname = str(self.table_to_trep[table])
      aname = 'init_program_state'
      match_params = ['[vdev ID]']
      if len(table.match_fields) > 1:
        print("Not yet supported: more than 1 match field (table: %s)" % table.name)
        exit()
      # match_params_list = []
      if len(table.match_fields) == 1:      
        if table.match_fields[0][1].value == 'P4_MATCH_VALID':
          mp = '[valid]&&&'
          # self.vbits[(level, header_instance)]
          hinst = table.match_fields[0][0]
          for key in self.vbits.keys():
            if hinst == key[1]:
              mp += format(self.vbits[key], '#x')
              # temp_match_params = list(match_params)
              # temp_match_params.append(mp)
              # match_params_list.append(temp_match_params)
              match_params.append(mp)
        elif ((table.match_fields[0][1].value == 'P4_MATCH_EXACT') or
             (table.match_fields[0][1].value == 'P4_MATCH_TERNARY')):
          field = table.match_fields[0][0]
          mp = '[val]'
          if field.instance.name != 'standard_metadata':
            maskwidth = 100
            if field.instance.metadata:
              maskwidth = 32
            mp += '&&&' + self.gen_bitmask(field.width,
                                           self.field_offsets[str(field)],
                                           maskwidth)
          elif field.name != 'egress_spec' and field.name != 'ingress_port':
            mp += '&&&' + hex((1 << field.width) - 1)
          else: # egress_spec... rep'd by virt_egress_spec, which is 8 bits
            mp += '&&&0xFF'
          match_params.append(mp)

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
          prim_type = primitive_ID[call[0].name]
          prim_subtype = self.get_prim_subtype(call)
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
        self.command_templates.append(HP4_Match_Command(table.name,
                                          action.name,
                                          "table_add",
                                          tname,
                                          aname,
                                          match_params,
                                          aparams))

  # primitive_call: (p4_action, [list of parameters])
  def get_prim_subtype(self, call):
    if call[0].name == 'drop':
      return '0'
    elif call[0].name == 'add_to_field':
      if type(call[1][0]) is p4_hlir.hlir.p4_headers.p4_field:
        if call[1][0].instance.metadata == True:
          print("Not supported: metadata (%s) as dst field in add_to_field" %  call[1][0].instance.name)
          exit()
        else:
          if type(call[1][1]) is int:
            if call[1][1] < 0:
              return(a2f_prim_subtype_ID['sub'])
            else:
              return(a2f_prim_subtype_ID['add'])
          else:
            print("ERROR: Not supported: %s type for src field in add_to_field" % type(call[1][1]))
            exit()
      else:
        print("ERROR: dst field type %s in add_to_field" % type(call[1][0]))
        exit()
    elif call[0].name == 'modify_field':
      first = 0
      second = 0
      if call[1][0].instance.metadata == True:
        if call[1][0].instance.name == 'standard_metadata':
          if call[1][0].name == 'egress_spec':
            first = call[1][0].name
          else:
            print("ERROR: Unexpected stdmeta field %s as dst in modify_field primitive" % call[1][0].name)
            exit()
        elif call[1][0].instance.name == 'intrinsic_metadata':
          if call[1][0].name == 'mcast_grp':
            #first = call[1][0].name
            first = 'egress_spec'
          else:
            print("ERROR: Unexpected intmeta field %s as dst in modify_field primitive" % call[1][0].name)
            exit()
        else: # user-defined metadata
          first = 'meta'
      else: # parsed representation
        first = 'ext'
      if type(call[1][1]) is int:
        second = 'const'
      elif type(call[1][1]) is p4_hlir.hlir.p4_headers.p4_field:
        if call[1][1].instance.metadata == True:
          if call[1][1].instance.name == 'standard_metadata':
            second = call[1][1].name
          else:
            second = 'meta'
        else:
          second = 'ext'
      elif type(call[1][1]) is p4_hlir.hlir.p4_imperatives.p4_signature_ref:
        second = 'const'
      else:
        print("ERROR: Unexpected type %s as src in modify_field call" % type(call[1][1]))
        exit()
      return mf_prim_subtype_ID[first, second]

  def print_action_to_arep(self):
    for action in self.action_to_arep:
      print("Action: " + str(action))
      print("  stages: " + str(self.action_to_arep[action].stages))
      print("  call_sequence: " + str(self.action_to_arep[action].call_sequence))

  def gen_action_entries(self):
    for action in self.action_to_arep:
      for stage in self.action_to_arep[action].stages:
        table_name = self.action_to_arep[action].tables[stage]
        for p4_call in action.call_sequence:
          istemplate = False
          idx = action.call_sequence.index(p4_call)
          call = self.action_to_arep[action].call_sequence[idx]
          rank = idx + 1
          tname = 't_' + primitive_tnames[call[0]] + '_' + str(stage) + str(rank)

          if call[0] == 'modify_field':
            aname = mf_prim_subtype_action[call[1]]
          elif call[0] == 'add_to_field':
            aname = a2f_prim_subtype_action[call[1]]
          else:
            aname = gen_prim_subtype_action[call[0]]
          mparams = ['[vdev ID]']
          if call[0] != 'drop':
            if call[0] == 'modify_field' or call[0] == 'add_to_field':
              mparams.append( call[1] )
            mparams.append(str(self.action_ID[action]))
            # If the parameter passed to the primitive in the source code is an
            # action parameter reference, the match_ID parameter should be
            # [val]&&&0x7FFFFF because each distinct match could have a different
            # value for the action parameter.  Otherwise, we don't care what the
            # match_ID is so use 0&&&0.
            match_ID_param = '0&&&0'
            for param in p4_call[1]:
              if type(param) == p4_hlir.hlir.p4_imperatives.p4_signature_ref:
                match_ID_param = '[match ID]&&&0x7FFFFF'
                istemplate = True
                break
            mparams.append(match_ID_param)
          aparams = self.gen_action_aparams(p4_call, call)
          if istemplate == True:
            aparams.append('0') # meta_primitive_state.match_ID mparam matters
            idx = -1
            if type(p4_call[1][1] == p4_hlir.hlir.p4_imperatives.p4_signature_ref):
              idx = p4_call[1][1].idx
            self.command_templates.append(HP4_Primitive_Command(table_name,
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
                  aparams.append(str(MAX_PRIORITY))
                  break
            self.commands.append(HP4_Command("table_add",
                                         tname,
                                         aname,
                                         mparams,
                                         aparams))

  # focus: mod, drop, math
  def gen_action_aparams(self, p4_call, call):
    aparams = []
    if call[0] == 'drop':
      return aparams
    if call[0] == 'add_to_field':
      if (a2f_prim_subtype_action[call[1]] == 'a_add2f_extracted_const_u' or
          a2f_prim_subtype_action[call[1]] == 'a_subff_extracted_const_u'):
        # aparams: leftshift, val
        dst_offset = self.field_offsets[str(p4_call[1][0])]
        leftshift = 800 - (dst_offset + p4_call[1][0].width)
        if type(p4_call[1][1]) == int:
          val = str(p4_call[1][1])
          if a2f_prim_subtype_action[call[1]] == 'a_subff_extracted_const_u':
            val = str(p4_call[1][1]*-1)
        else:
          val = '[val]'
        aparams.append(str(leftshift))
        aparams.append(val)
    if call[0] == 'modify_field':
      instance_name = p4_call[1][0].instance.name
      dst_field_name = p4_call[1][0].name
      if instance_name == 'intrinsic_metadata':
        if dst_field_name == 'mcast_grp':
          instance_name = 'standard_metadata'
          dst_field_name = 'egress_spec'
        else:
          print("Not supported: modify_field(" + instance_name + '.' \
                + dst_field_name + ", *)")
          exit()
      if isinstance(p4_call[1][1], p4_hlir.hlir.p4_headers.p4_field):
        if p4_call[1][1].width > p4_call[1][0].width:
          dst = instance_name + '.' + dst_field_name
          src = p4_call[1][1].instance.name + '.' + p4_call[1][1].name
          print("WARNING: modify_field(%s, %s): %s width (%i) > %s width (%i)" \
              % (dst, src, src, p4_call[1][1].width, dst, p4_call[1][0].width))
      if mf_prim_subtype_action[call[1]] == 'mod_meta_stdmeta_ingressport':
        print("Not yet supported: %s" % mf_prim_subtype_action[call[1]])
        exit()
      elif mf_prim_subtype_action[call[1]] == 'mod_meta_stdmeta_packetlength':
        print("Not yet supported: %s" % mf_prim_subtype_action[call[1]])
        exit()
      elif mf_prim_subtype_action[call[1]] == 'mod_meta_stdmeta_egressspec':
        print("Not yet supported: %s" % mf_prim_subtype_action[call[1]])
        exit()
      elif mf_prim_subtype_action[call[1]] == 'mod_meta_stdmeta_egressport':
        print("Not yet supported: %s" % mf_prim_subtype_action[call[1]])
        exit()
      elif mf_prim_subtype_action[call[1]] == 'mod_meta_stdmeta_egressinst':
        print("Not yet supported: %s" % mf_prim_subtype_action[call[1]])
        exit()
      elif mf_prim_subtype_action[call[1]] == 'mod_meta_stdmeta_insttype':
        print("Not yet supported: %s" % mf_prim_subtype_action[call[1]])
        exit()
      elif mf_prim_subtype_action[call[1]] == 'mod_stdmeta_egressspec_meta':
        # aparams: rightshift, tmask
        rshift = 256 - (self.field_offsets[str(p4_call[1][1])] + p4_call[1][1].width)
        mask = 0
        if p4_call[1][1].width < p4_call[1][0].width:
          mask = hex(int(math.pow(2, p4_call[1][1].width)) - 1)
        else:
          mask = hex(int(math.pow(2, p4_call[1][0].width)) - 1)
        aparams.append(str(rshift))
        aparams.append(mask)
      elif (mf_prim_subtype_action[call[1]] == 'mod_meta_const' or
            mf_prim_subtype_action[call[1]] == 'mod_extracted_const'):
        # aparams: leftshift, mask, val
        if type(p4_call[1][1]) == int:
          val = str(p4_call[1][1])
        else:
          val = '[val]'
        fo = self.field_offsets[str(p4_call[1][0])]
        fw = p4_call[1][0].width
        maskwidthbits = 800
        if mf_prim_subtype_action[call[1]] == 'mod_meta_const':
          maskwidthbits = 256
        leftshift = str(maskwidthbits - (fo + fw))
        mask = self.gen_bitmask(p4_call[1][0].width,
                                self.field_offsets[str(p4_call[1][0])],
                                maskwidthbits / 8)
        aparams.append(leftshift)
        aparams.append(mask)
        aparams.append(val)
      elif (mf_prim_subtype_action[call[1]] == 'mod_stdmeta_egressspec_const'):
        if type(p4_call[1][1]) == int:
          aparams.append(str(p4_call[1][1]))
        else:
          aparams.append('[val]')
      elif (mf_prim_subtype_action[call[1]] == 'mod_intmeta_mcast_grp_const'):
        if type(p4_call[1][1]) == int:
          print("Not yet supported: mod_intmeta_mcast_grp_const w/ explicit const")
          exit()
        else:
          aparams.append('[MCAST_GRP]')

      #elif mf_prim_subtype_action[call[1]] == 'mod_stdmeta_egressspec_stdmeta_ingressport':
      #  return aparams
      elif mf_prim_subtype_action[call[1]] == 'mod_extracted_extracted':
        # aparams:
        # - leftshift (how far should src field be shifted to align w/ dst)
        # - rightshift (how far should src field be shifted to align w/ dst)
        # - msk (bitmask for dest field)
        dst_offset = self.field_offsets[str(p4_call[1][0])]
        src_offset = self.field_offsets[str(p4_call[1][1])]
        lshift = 0
        rshift = 0
        # *_revo = revised offset; right-aligned instead of left-aligned
        dst_revo = 800 - (dst_offset + p4_call[1][0].width)
        src_revo = 800 - (src_offset + p4_call[1][1].width)
        if src_revo > dst_revo:
          rshift = src_revo - dst_revo
        else:
          lshift = dst_revo - src_revo
        aparams.append(str(lshift))
        aparams.append(str(rshift))
        aparams.append(self.gen_bitmask(p4_call[1][0].width, dst_offset, 100))
      elif mf_prim_subtype_action[call[1]] == 'mod_meta_extracted':
        dst_offset = self.field_offsets[str(p4_call[1][0])]
        src_offset = self.field_offsets[str(p4_call[1][1])]
        lshift = 0
        rshift = 0
        dstmaskwidthbits = 256
        srcmaskwidthbits = 800
        # *_revo = revised offset; right-aligned instead of left-aligned
        dst_revo = dstmaskwidthbits - (dst_offset + p4_call[1][0].width)
        src_revo = srcmaskwidthbits - (src_offset + p4_call[1][1].width)
        if src_revo > dst_revo:
          rshift = src_revo - dst_revo
        else:
          lshift = dst_revo - src_revo
        dstmask = self.gen_bitmask(p4_call[1][0].width, dst_offset,
                                   dstmaskwidthbits / 8)
        srcmask = dstmask
        if p4_call[1][1].width < p4_call[1][0].width:
          srcmask = self.gen_bitmask(p4_call[1][1].width, dst_offset,
                                     dstmaskwidthbits / 8)
        aparams.append(str(lshift))
        aparams.append(str(rshift))
        aparams.append(dstmask)
        aparams.append(srcmask)
      elif mf_prim_subtype_action[call[1]] == 'mod_extracted_meta':
        dst_offset = self.field_offsets[str(p4_call[1][0])]
        src_offset = self.field_offsets[str(p4_call[1][1])]
        lshift = 0
        rshift = 0
        dstmaskwidthbits = 800
        srcmaskwidthbits = 256
        # *_revo = revised offset; right-aligned instead of left-aligned
        dst_revo = dstmaskwidthbits - (dst_offset + p4_call[1][0].width)
        src_revo = srcmaskwidthbits - (src_offset + p4_call[1][1].width)
        if src_revo > dst_revo:
          rshift = src_revo - dst_revo
        else:
          lshift = dst_revo - src_revo
        dstmask = self.gen_bitmask(p4_call[1][0].width, dst_offset,
                                   dstmaskwidthbits / 8)
        srcmask = dstmask
        if p4_call[1][1].width < p4_call[1][0].width:
          srcmask = self.gen_bitmask(p4_call[1][1].width, dst_offset,
                                     dstmaskwidthbits / 8)
        aparams.append(str(lshift))
        aparams.append(str(rshift))
        aparams.append(dstmask)
        aparams.append(srcmask)

    return aparams

  def get_table_from_cs(self, control_statement):
    if type(control_statement) == p4_hlir.hlir.p4_tables.p4_table:
      return control_statement
    elif type(control_statement) == tuple:
      return control_statement[0]
    else:
      print("Error (get_table_from_cs): unsupported control statement type: " \
            + str(type(control_statement)))
      exit()

  def walk_control_block(self, control_block, table):
    for control_statement in control_block:
      cs_idx = control_block.index(control_statement)
      if type(control_statement) == p4_table:
        # apply_table_call
        if control_statement == table:
          if cs_idx == len(control_block) - 1:
            return True, None
          return True, self.get_table_from_cs(control_block[cs_idx + 1])
      elif type(control_statement) == tuple:
        # apply_and_select_block
        if control_statement[0] == table:
          if cs_idx == len(control_block) - 1:
            return True, None
          return True, self.get_table_from_cs(control_block[cs_idx + 1])
        else:
          for case in control_statement[1]:
            found, next_table = self.walk_control_block(case[1], table)
            if found:
              if next_table != None:
                return True, next_table
              elif cs_idx < len(control_block) - 1:
                return True, self.get_table_from_cs(control_block[cs_idx + 1])
              else:
                return True, None
      else:
        print("Error: unsupported call_sequence entry type: " + str(type(entry)))
        exit()
    return False, None

  def gen_tmiss_entries(self):
    for table_name in self.h.p4_tables:

      table = self.h.p4_tables[table_name]
      trep = self.table_to_trep[table]
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
        ingress = self.h.p4_control_flows['ingress']
        found, next_table = self.walk_control_block(ingress.call_sequence, table)

      if next_table == None:
        next_stage = '0'
        next_table_type = '0'
      else:
        next_stage = str(self.table_to_trep[next_table].stage)
        next_table_type = self.table_to_trep[next_table].table_type()

      aparams = ['0', # action_ID
                 '0', # match_ID
                 next_stage,
                 next_table_type]
      
      # zeros for remaining type / subtype parameters of init_program_state
      for i in range(self.numprimitives):
        aparams.append('0')
        aparams.append('0')

      if 'matchless' not in tname:
        aparams.append(str(MAX_PRIORITY))

      self.commands.append(HP4_Command("table_add",
                                            tname,
                                            aname,
                                            mparams,
                                            aparams))

  def gen_t_checksum_entries(self):
    """ detect and handle ipv4 checksum """
    cf_none_types = 0
    cf_valid_types = 0
    checksum_detected = False
    for cf in self.h.calculated_fields:
      for statement in cf[1]:
        if statement[0] == 'update':
          flc = self.h.p4_field_list_calculations[statement[1]]
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
                aparam = str(800 - self.field_offsets[key] - max_field.width)
                if statement[2] == None:
                  cf_none_types += 1
                  if (cf_none_types + cf_valid_types) > 1:
                    print("ERROR: Unsupported: multiple checksums")
                    exit()
                  else:
                    checksum_detected = True
                    self.commands.append(HP4_Command("table_add",
                                                      "t_checksum",
                                                      "a_ipv4_csum16",
                                                      ['[vdev ID]', '0&&&0'],
                                                      [aparam, str(MAX_PRIORITY)]))
                else:
                  if statement[2].op == 'valid':
                    cf_valid_types += 1
                    if (cf_none_types + cf_valid_types) > 1:
                      print("ERROR: Unsupported: multiple checksums")
                      exit()
                    else:
                      # TODO: reduce entries by isolating relevant bit
                      for key in self.vbits.keys():
                        if statement[2].right == key[1]:
                          mparams = ['[vdev ID]']
                          val = format(self.vbits[key], '#x')
                          mparams.append(val + '&&&' + val)
                          checksum_detected = True
                          self.commands.append(HP4_Command("table_add",
                                                            "t_checksum",
                                                            "a_ipv4_csum16",
                                                            mparams,
                                                            [aparam, '0']))
                  else:
                    print("ERROR: Unsupported if_cond op in calculated field: \
                           %s" % statement[2].op)
                    exit()
              else:
                print("ERROR: Unsupported checksum (%s, %i)" \
                      % (flc.algorithm, flc.output_width))
                exit()
            else:
              print("ERROR: Unsupported checksum - field list of %i bits" \
                     % count)
              exit()
        else:
          print("WARNING: Unsupported update_verify_spec for calculated field: \
                 %s" % statement[0])

    if checksum_detected == False:
      self.commands.append(HP4_Command("table_add",
                                      "t_checksum",
                                      "_no_op",
                                      ['[vdev ID]', '0&&&0'],
                                      [str(MAX_PRIORITY)]))

  def gen_t_resize_pr_entries(self):
    # TODO: full implementation as the following primitives get support:
    # - add_header | remove_header | truncate | push | pop | copy_header*
    # * maybe (due to possibility of making previously invalid header
    #   valid)

    # default entry handled by dpmu
    pass

  def build(self):
    self.collect_headers()
    self.collect_actions()
    self.gen_tset_parse_control_entries()
    self.gen_tset_parse_select_entries()
    self.gen_tset_pipeline_config_entries()
    self.gen_tX_templates()
    self.gen_action_entries()
    self.gen_tmiss_entries()
    self.gen_t_checksum_entries()
    self.gen_t_resize_pr_entries()

  def compile_to_hp4(self, program_path, out_path, mt_out_path, seb, numprimitives):
    self.program_path = program_path
    self.out_path = out_path
    self.mt_out_path = mt_out_path
    self.seb = seb
    self.numprimitives = numprimitives
    self.h = HLIR(program_path)
    self.h.build()
    if len(self.h.p4_ingress_ptr) > 1:
      print("ERROR: multiple ingress entry points:")
      for node in h.p4_ingress_ptr.keys():
        print('  ' + node)
      exit()
    self.headers_hp4_type = {}
    self.action_ID = {}
    self.actionID = 1

    self.pc_bits_extracted = {} # num bits HP4 must have extracted prior to handling
                                #  the associated parser function; viewpoint = hp4
    self.pc_bit_offsets = {} # pc_state : offset into the packet; viewpoint = native

    self.pc_action = {}
    self.field_offsets = {}
    self.offset = 0
    self.ps_to_pc = {}
    self.pc_to_ps = {}
    self.pc_to_preceding_pcs = {}
    self.vbits = {}
    self.parse_select_match_offsets = {}
    self.parse_select_table_names = {}
    self.parse_select_list = []
    self.stage = 1
    self.table_to_trep = {}
    self.action_to_arep = {}
    self.commands = []
    self.command_templates = []
    self.build()
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

def parse_args(args):
  parser = argparse.ArgumentParser(description='P4->HP4 Compiler')
  parser.add_argument('input', help='path for input .p4',
                    type=str)
  parser.add_argument('-o', '--output', help='path for output .hp4t file',
                    type=str, action="store", required=True)
  parser.add_argument('-m', '--mt_output', help='path for match template output',
                    type=str, action="store", default='output.hp4mt')
  parser.add_argument('-s', '--seb', help='set standard extracted bytes',
                    type=int, action="store", default=40)
  parser.add_argument('--numprimitives', help='maximum number of primitives \
                       for which HyPer4 is configured',
                      type=int, action="store", default=9)

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  hp4c = P4_to_HP4()
  hp4c.compile_to_hp4(args.input, args.output, args.mt_output, args.seb, args.numprimitives)
  #code.interact(local=dict(globals(), **locals()))

if __name__ == '__main__':
  main()
