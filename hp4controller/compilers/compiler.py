import argparse

class HP4Compiler():
  def compile_to_hp4(self, program_path, args):
    self.args = args

class CodeRepresentation():
  def __init__(self, object_code_path, interpretation_guide_path):
    self.object_code_path = object_code_path
    self.interpretation_guide_path = interpretation_guide_path
