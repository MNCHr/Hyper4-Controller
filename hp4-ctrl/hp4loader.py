from virtualdevice import VirtualDevice
import hp4compiler

class CompileError(Exception):
  pass

class HP4Loader():
  def __init__(self):
    compiled_programs = {} # {program_path (str) : cr (hp4compiler.CodeRepresentation)}
    hp4c = hp4compiler.P4_to_HP4()

  def load(self, vdev_name, vdev_ID, program_path):
    if program_path not in compiled_programs:
      # compile
      if program_path.endswith('.p4'):
        try:
          self.compiled_programs[program_path] = self.hp4c.compile_to_hp4(program_path)
        except CompileError as e:
          return "Compile Error: " + str(e)
      else:
        raise CompileError('filetype not supported')
    # self.link
    
    #code = 
    #guide = 
    #return VirtualDevice(vdev_ID, code, guide)
    pass
