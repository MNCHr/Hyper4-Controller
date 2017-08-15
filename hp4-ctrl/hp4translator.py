import virtualdevice
import json
from p4command import P4Command

class Translator():
  @staticmethod
  def translate(self, vdev, p4command):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::translate
    pass

class RuleTranslationGuide():
  def __init__(self, rtg_path):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::parse_json
    self.templates_match = {}
    self.templates_prims = {}
    with open(rtg_path) as json_data:
      d = json.load(json_data)
      for hp4_command in d:
        attributes = {}
        attributes['src_table'] = hp4_command['source_table']
        #src_action = hp4_command['source_action']
        key = (src_table, src_action)
        command_type = hp4_command['command']
        attributes['table'] = hp4_command['table']
        attributes['action'] = hp4_command['action']
        attributes['mparams'] = hp4_command['match_params']
        attributes['aparams'] = hp4_command['action_params']

        if hp4_command['__class__'] == 'HP4_Match_Command':
          #templates_match[key] = HP4_Match_Command(src_table, src_action,
          #                                         command, table, action,
          #                                         match_params, action_params)
          self.templates_match[key] = P4Command(command_type, attributes)
        elif hp4_command['__class__'] == 'HP4_Primitive_Command':
          attributes['src_aparam_id'] = hp4_command['src_aparam_id']
          if templates_prims.has_key(key) == False:
            templates_prims[key] = []
          self.templates_prims[key].append(P4Command(command_type, attributes)
        else:
          print("ERROR: Unrecognized class: %s" % hp4_command['__class__'])
    self.templates = {}
    for key in self.templates_match:
      self.templates[key] = {'match': self.templates_match[key], 'primitives': []}
      if self.templates_prims.has_key(key):
        self.templates[key]['primitives'] = self.templates_prims[key]

  #def get_templates(self, table, action):
  #  return self.templates[(table, action)]
