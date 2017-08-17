from ..p4command import P4Command
from p4rule import P4Rule
from interpret import Interpretation, InterpretationGuide
from ..compilers import compiler as hp4compiler
from ..compilers.compiler import CodeRepresentation

class VirtualDevice():
  def __init__(self, virtual_device_ID, code, guide):
    self.virtual_device_ID = virtual_device_ID
    self.guide = guide
    self.code = {} # {handle (int): p4cmd (P4Command)}
    self.origin_table_rules = {} # {handle (int): map (Origin_to_HP4Map)}
    self.hp4_table_rules = {} # {handle (int): p4r (P4Rule)}
    self.dev_name = 'none'
    self.next_handle = 0

  def interpret(self, p4command):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::translate
    p4commands = []
    # this may be problematic, reusing the origin rule handle as the match_ID
    match_ID = vdev.assign_handle()
    self.origin_table_rules[match_ID] # TODO...
    return p4commands

  def assign_handle(self):
    handle = self.next_handle
    self.next_handle += 1
    return handle

class CompileError(Exception):
  pass

class VirtualDeviceFactory():
  def __init__(self):
    compiled_programs = {} # {program_path (str) : cr (hp4compiler.CodeRepresentation)}
    hp4c = hp4compiler.P4_to_HP4()

  def link(self, object_code_path, vdev_ID):
    f_ac = open(object_code_path, 'r')
    code = []

    sr = {}
    sr['[vdev ID]'] = vdev_ID
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

      code.append(line)

    f_ac.close()

    return code

  def create_vdev(self, vdev_ID, program_path):
    if program_path not in compiled_programs:
      # compile
      if program_path.endswith('.p4'):
        try:
          self.compiled_programs[program_path] = self.hp4c.compile_to_hp4(program_path)
        except CompileError as e:
          return "Compile Error: " + str(e)
      else:
        raise CompileError('filetype not supported')
    
    object_code_path = self.compiled_programs[program_path].object_code_path
    ig_path = self.compiled_programs[program_path].rule_translation_guide_path
   
    code = link(object_code_path, vdev_ID)
    guide = InterpretationGuide(ig_path) # TODO: verify parameters

    return VirtualDevice(vdev_ID, code, guide)

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
