from ..p4command import P4Command
from p4rule import P4Rule
from interpret import Interpretation, InterpretationGuide, Interpreter
from ..compilers import p4_hp4
from ..compilers.compiler import CodeRepresentation
import re

import code

class VirtualDevice():
  def __init__(self, virtual_device_ID, hp4code, guide):
    self.virtual_device_ID = virtual_device_ID
    self.guide = guide

    # from the elements in these lists, generate table_add commands when loading
    # onto a device
    self.hp4code = []  # representation of .p4
    self.hp4rules = [] # representation of table entries added (e.g., via CLI)
    # object_code format:
    #  <table> <action> :<mparams>:<aparams
    for line in hp4code:
      table = line.split()[0]
      action = line.split()[1]
      mparams = line.split(':')[1].split()
      aparams = line.split(':')[2].split()
      self.hp4code.append(P4Rule(table, action, mparams, aparams))

    self.origin_table_rules = {} # KEY: (table (str), user-facing handle (int))
                                 # VALUE: Interpretation
    self.hp4_code_and_rules = {} # KEY: (table (str), hp4-facing handle (int))
                                 # VALUE: P4Rule}
    self.t_virtnet_handles = {} # KEY: vegress_spec (int)
                                # VALUE: hp4-facing handle (int)
    self.t_egr_virtnet_handles = {} # KEY: vegress_spec (int)
                                    # VALUE: hp4-facing handle (int)
    self.dev_name = 'none'
    self.next_handle = {} # KEY: table (str)
                          # VALUE: next handle (int)

  def interpret(self, p4command):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::translate
    p4commands = []
    table = p4command.attributes['table']

    if p4command.command_type == 'table_add':
      match_ID = self.assign_handle(table)
      p4commands = Interpreter.table_add(self.guide, p4command, match_ID,
                                         self.virtual_device_ID)
      
    elif p4command.command_type == 'table_modify':
      p4commands = Interpeter.table_modify(self.guide, p4command)

    elif p4command.command_type == 'table_delete':
      p4commands = Interpreter.table_delete(self.guide, p4command)

    return p4commands

  def assign_handle(self, table):
    if table not in self.next_handle:
      self.next_handle[table] = 1
    handle = self.next_handle[table]
    self.next_handle[table] += 1
    return handle

class CompileError(Exception):
  pass

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
    sr['[PARSE_SELECT_SEB]'] = '1'
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
    sr['[MODIFY_FIELD]'] = '0'
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

      hp4code.append(line)

    f_ac.close()

    return hp4code

  def create_vdev(self, vdev_ID, program_path):
    if program_path not in self.compiled_programs:
      # compile
      if program_path.endswith('.p4'):
        try:
          out_path = program_path.split('.p4')[0] + '.hp4t'
          mt_out_path = program_path.split('.p4')[0] + '.hp4mt'
          seb = 20
          self.compiled_programs[program_path] = \
             self.hp4c.compile_to_hp4(program_path, out_path, mt_out_path, seb)
        except CompileError as e:
          return "Compile Error: " + str(e)
      else:
        raise CompileError('filetype not supported')

    object_code_path = self.compiled_programs[program_path].object_code_path
    ig_path = self.compiled_programs[program_path].interpretation_guide_path
   
    hp4code = self.link(object_code_path, vdev_ID)
    guide = InterpretationGuide(ig_path)

    return VirtualDevice(vdev_ID, hp4code, guide)

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
