import argparse

class HP4Compiler():
  def compile_to_hp4(self, program_path, out_path, mt_out_path, seb):
    self.program_path = program_path
    self.out_path = out_path
    self.mt_out_path = mt_out_path
    self.seb = seb

class CodeRepresentation():
  def __init__(self, object_code_path, interpretation_guide_path):
    self.object_code_path = object_code_path
    self.interpretation_guide_path = interpretation_guide_path
