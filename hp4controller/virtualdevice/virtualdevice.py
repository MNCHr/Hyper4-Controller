from hp4controller.p4command import P4Command
from p4rule import P4Rule
from interpret import Interpretation, InterpretationGuide, Interpreter
from hp4controller.compilers import p4_hp4
from hp4controller.compilers.compiler import CodeRepresentation
import re

import code
# code.interact(local=dict(globals(), **locals()))

"""
VirtualDevice::hp4code
- static code, the .hp4t but with vdev_ID and other tokens filled in
  - all values should be portable across physical devices
    - the only one that would cause concern is the vdev_ID, but the
      controller has been written to ensure this is unique to minimize
      the hassle involved in migrating a vdev from one device to another
- persists independent of host (endures for the lifetime of the vdev)

VirtualDevice::hp4rules
- dynamic hp4-facing ruleset generated/modified/filtered by interpret commands
- persists independent of host, unless slice manager takes explicit action

VirtualDevice::hp4_code_and_rules <-- 'hp4-facing'
- {(table (str), hp4-facing handle (int)): P4Rule}
- tracks rules in the host associated with the VirtualDevice - code + dynamic rules
- updated by Slice::interpret
- used by Lease::load_virtual_device
  - validate request
  - emptied and filled again via VirtualDevice::hp4code and VirtualDevice::hp4rules
  - used to back out if error occurs, tracking all hp4-facing (table, handle) pairs
    in order to issue table_deletes
- used by Lease::remove
  - issue table_deletes

VirtualDevice::nrules <-- 'user-facing'
- {(user-facing table (str), user-facing handle (int)): Interpretation}
- Interpretation:
  - native_rule
  - match_ID (syn. w/ native_handle)
  - hp4_rule_keys:
    list of hp4-facing (table, action, handle) tuples
CHANGE: need to restore original vision of nrules; hp4_rule_keys
was supposed to be keys looking up rules in hp4_code_and_rules
- but don't remove 'action' member of hp4_rule_keys; it is needed by
  Interpreter.table_modify

Whenever nrules is updated, hp4_code_and_rules should be also.

One entry in nrules corresponds to many entries in hp4_code_and_rules.
"""

class VirtualDevice():
  def __init__(self, name, virtual_device_ID, hp4code, guide, program_path):
    self.name = name
    self.virtual_device_ID = virtual_device_ID
    self.guide = guide
    self.program_path = program_path

    # from the elements in these lists, generate table_add commands when loading
    # onto a device
    self.hp4code = []  # representation of .p4
    self.hp4rules = {} # {(hp4-facing table (str), hp4-facing handle (int)): P4Rule}
    self.nrules = {} # KEY: (table (str), user-facing handle / match ID (int))
                     # VALUE: Interpretation
    # object_code format:
    #  <table> <action> :<mparams>:<aparams
    for line in hp4code:
      table = line.split()[0]
      action = line.split()[1]
      mparams = line.split(':')[1].split()
      aparams = line.split(':')[2].split()
      self.hp4code.append(P4Rule(table, action, mparams, aparams))

      # store handle for default rule for native match table
      if action == 'init_program_state' and aparams[1] == '0':
        for key in self.guide.templates_match:
          if self.guide.templates_match[key].attributes['table'] == table:
            native_table = key[0]
            init_default_rule = P4Rule(native_table, 'init_default',
                                       [],
                                       [])

            hp4_rule_keys = [(table, action, 0)]
            self.nrules[(native_table, 0)] = Interpretation(init_default_rule,
                                                            0,
                                                            hp4_rule_keys)
            break

    self.hp4_code_and_rules = {} # KEY: (table (str), hp4-facing handle (int))
                                 # VALUE: P4Rule}
    self.t_virtnet_handles = {} # KEY: vegress_spec (int)
                                # VALUE: hp4-facing handle (int)
    self.t_egr_virtnet_handles = {} # KEY: vegress_spec (int)
                                    # VALUE: hp4-facing handle (int)
    self.dev_name = 'none'
    self.mcast_grp_id = -1
    self.next_handle = {} # KEY: table (str)
                          # VALUE: next handle (int)
    self.next_staged_hp4_handle = {} # KEY: table (str)
                                     # VALUE: next handle (int)

  def str_hp4code(self):
    #ret = 'HP4 Code:\n'
    ret = ''
    for rule in self.hp4code:
      ret += str(rule) + '\n'
    return ret[:-1]

  def str_hp4rules(self):
    ret = ''
    for table, handle in self.hp4rules:
      rule = self.hp4rules[(table, handle)]
      ret += str(rule) + '\n'
    return ret[:-1]

  def str_hp4_code_and_rules(self):
    ret = ''
    for table, handle in self.hp4_code_and_rules:
      rule = self.hp4_code_and_rules[(table, handle)]
      ret += table + ':' + str(handle) + ': ' + str(rule) + '\n'
    return ret[:-1]

  def dump(self):
    indent = '  '
    ret = self.name + '@' + self.dev_name + '\n'
    ret += indent + 'handle\trule\n'
    indent += '  '
    sorted_rules = sorted(self.nrules.keys(),
                          key=lambda entry: entry[0] + str(entry[1]))
    for table, handle in sorted_rules:
      interpretation = self.nrules[(table, handle)]
      ret += indent + str(handle) + '\t\t' + str(interpretation.native_rule) + '\n'
    return ret[:-1]

  def info(self):
    ret = self.name + '(ID: ' + str(self.virtual_device_ID) + ')@' + self.dev_name + '\n'
    ret += self.program_path + '\n'
    ret += 'pushed (user-facing : hp4-facing): (' + str(len(self.nrules)) + ' : ' \
            + str(len(self.hp4rules)) + ')\n'
    #ret += 'staged (user-facing : hp4-facing): (' + str(len(self.staged_hp4rules)) \
    #        + ' : ' + str(len(self.staged_nrules)) + ')'
    return ret

  """
  def __str__(self):
    indent = '  '
    ret = self.name + '@' + self.dev_name + '\n'
    ret += indent + 'vdev_ID: ' + str(self.virtual_device_ID) + '\n'
    ret += indent + 'handle\trule\n'
    indent += '  '
    sorted_rules = sorted(self.nrules.keys(),
                          key=lambda entry: entry[0] + str(entry[1]))
    for table, handle in sorted_rules:
      interpretation = self.nrules[(table, handle)]
      ret += indent + str(handle) + '\t\t' + str(interpretation.native_rule) + '\n'
    return ret[:-1] # remove trailing '\n'
  """

  def interpret(self, p4command):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::translate
    p4commands = []
    native_table = p4command.attributes['table']

    if p4command.command_type == 'table_add':
      match_ID = self.assign_handle(native_table)
      p4commands = Interpreter.table_add(self.guide, p4command, match_ID,
                                         self.virtual_device_ID, self.mcast_grp_id)
    elif p4command.command_type == 'table_set_default':
      #print("breakpoint: VirtualDevice::interpret: table_set_default")
      #code.interact(local=dict(globals(), **locals()))

      hp4_rule_keys = self.nrules[(native_table, 0)].hp4_rule_keys
      _, _, handle = hp4_rule_keys[0]

      p4commands = Interpreter.table_set_default(self.guide,
                                                 p4command,
                                                 handle,
                                                 hp4_rule_keys,
                                                 self.virtual_device_ID,
                                                 self.mcast_grp_id)
    else:
      native_handle = p4command.attributes['handle']
      if native_handle == 0:
        print("Error(VirtualDevice::interpret) - table_modify / table_delete using native handle 0")
        exit()
      interpretation = self.nrules[(native_table, native_handle)]
      if p4command.command_type == 'table_modify':
        p4commands = Interpreter.table_modify(self.guide,
                                              p4command,
                                              interpretation,
                                              native_handle,
                                              self.virtual_device_ID,
                                              self.mcast_grp_id)
      elif p4command.command_type == 'table_delete':
        p4commands = Interpreter.table_delete(self.guide,
                                              p4command,
                                              interpretation.hp4_rule_keys)

    return p4commands

  def assign_handle(self, table):
    if table not in self.next_handle:
      self.next_handle[table] = 1
    handle = self.next_handle[table]
    self.next_handle[table] += 1
    return handle

  def assign_staged_hp4_handle(self, table):
    if table not in self.next_staged_hp4_handle:
      self.next_staged_hp4_handle[table] = -1
    handle = self.next_staged_hp4_handle[table]
    self.next_staged_hp4_handle[table] -= 1
    return handle

class CompileError(Exception):
  pass

STANDARD_EXTRACTION = 40

class VirtualDeviceFactory():
  def __init__(self):
    self.compiled_programs = {} # {program_path (str) : cr (hp4compiler.CodeRepresentation)}
    self.hp4c = p4_hp4.P4_to_HP4()

  def link(self, object_code_path, vdev_ID):
    f_ac = open(object_code_path, 'r')
    hp4code = []

    sr = {}
    sr['[vdev ID]'] = str(vdev_ID)
    sr['[PROCEED]'] = '0'
    sr['[PARSE_SELECT_00_19]'] = '1'
    sr['[PARSE_SELECT_20_29]'] = '2'
    sr['[PARSE_SELECT_30_39]'] = '3'
    sr['[PARSE_SELECT_40_49]'] = '4'
    sr['[PARSE_SELECT_50_59]'] = '5'
    sr['[PARSE_SELECT_60_69]'] = '6'
    sr['[PARSE_SELECT_70_79]'] = '7'
    sr['[PARSE_SELECT_80_89]'] = '8'
    sr['[PARSE_SELECT_90_99]'] = '9'
    sr['[EXTRACT_MORE]'] ='10'
    sr['[DONE]'] = '0'
    sr['[EXTRACTED_EXACT]'] = '1'
    sr['[METADATA_EXACT]'] = '2'
    sr['[STDMETA_EXACT]'] = '3'
    sr['[EXTRACTED_VALID]'] = '4'
    sr['[STDMETA_INGRESS_PORT_EXACT]'] = '5'
    sr['[STDMETA_PACKET_LENGTH_EXACT]'] = '6'
    sr['[STDMETA_INSTANCE_TYPE_EXACT]'] = '7'
    sr['[STDMETA_EGRESS_SPEC_EXACT]'] =	'8'
    sr['[MATCHLESS]'] = '99'
    sr['[COMPLETE]'] = '1'
    sr['[CONTINUE]'] = '2'
    sr['[ADD_HEADER]'] = '1'
    sr['[COPY_HEADER]'] = '2'
    sr['[REMOVE_HEADER]'] = '3'
    sr['[MODIFY_FIELD_WITH_HBO]'] = '4'
    sr['[TRUNCATE]'] = '5'
    sr['[DROP]'] = '6'
    sr['[NO_OP]'] = '7'
    sr['[PUSH]'] = '8'
    sr['[POP]'] = '9'
    sr['[COUNT]'] = '10'
    sr['[METER]'] = '11'
    sr['[GENERATE_DIGEST]'] = '12'
    sr['[RECIRCULATE]'] = '13'
    sr['[RESUBMIT]'] = '14'
    sr['[CLONE_INGRESS_INGRESS]'] = '15'
    sr['[CLONE_EGRESS_INGRESS]'] = '16'
    sr['[CLONE_INGRESS_EGRESS]'] = '17'
    sr['[CLONE_EGRESS_EGRESS]'] = '18'
    sr['[MULTICAST]'] = '19'
    sr['[MATH_ON_FIELD]'] = '20'
    sr['[MODIFY_FIELD]'] = '21'
    sr['[MODIFY_FIELD_RNG_U]'] = '22'

    found_sr = False

    for line in f_ac:
      if line == '# SEARCH AND REPLACE\n':
        found_sr = True
        break

    if(found_sr):
      line = f_ac.next()
      while line != '\n':
        linetoks = line.split()
        sr[linetoks[1]] = linetoks[3]
        line = f_ac.next()

    f_ac.seek(0)

    for line in f_ac:
      # strip out comments and white space
      if line[0] == '#' or line[0] == '\n':
        continue
      i = line.find('#')
      if i != -1:
        line = line[0:i]
        while line.endswith(' '):
          line = line[0:-1]
        line += '\n'

      for key in sr.keys():
        line = line.replace(key, sr[key])
      for token in re.findall("\[.*?\]", line):
        replace = ""
        if re.search("\[[0-9]*x00s\]", token):
          numzeros = int(re.search("[0-9]+", token).group())
          for i in range(numzeros):
            replace += "00"   
          line = line.replace(token, replace)
        elif re.search("\[[0-9]*xFFs\]", token):
          numFFs = int(re.search("[0-9]+", token).group())
          for i in range(numFFs):
            replace += "FF"
          line = line.replace(token, replace)

      hp4code.append(line)

    f_ac.close()

    return hp4code

  def create_vdev(self, vdev_name, vdev_ID, program_path):
    if program_path not in self.compiled_programs:
      # compile
      if program_path.endswith('.p4'):
        try:
          out_path = program_path.split('.p4')[0] + '.hp4t'
          mt_out_path = program_path.split('.p4')[0] + '.hp4mt'
          # TODO: replace the '9' (max primitives / action for which HP4 is configured
          self.compiled_programs[program_path] = \
             self.hp4c.compile_to_hp4(program_path, out_path, mt_out_path, 9)
        except CompileError as e:
          return "Compile Error: " + str(e)
      else:
        raise CompileError('filetype not supported')

    object_code_path = self.compiled_programs[program_path].object_code_path
    ig_path = self.compiled_programs[program_path].interpretation_guide_path
   
    hp4code = self.link(object_code_path, vdev_ID)
    guide = InterpretationGuide(ig_path)

    return VirtualDevice(vdev_name, vdev_ID, hp4code, guide, program_path)

  def writefile(self, program_path, outfile):
    pass

def produce_vdev(args):
  vdf = VirtualDeviceFactory()
  vdf.load(args.output, args.vdevID, args.input)
  vdf.writefile(args.input, args.output)

def parse_args(args):
  parser = argparse.ArgumentParser(description='HP4-targeting Compiler / Linker')
  parser.add_argument('--input', help='Annotated hp4 commands file',
                      type=str, action="store", required=True)
  parser.add_argument('--output', help='Where to write hp4-ready commands file',
                      type=str, action="store", required=True)
  parser.add_argument('--vdevID', help='Virtual Device ID',
                      type=str, action="store", default='1')

  parser.set_defaults(func=produce_vdev)

  return parser.parse_args()

def main():
  args = parse_args(sys.argv[1:])
  args.func(args)

if __name__ == '__main__':
  main()
