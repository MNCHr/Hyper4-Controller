import virtualdevice
import json
from ..p4command import P4Command
from p4rule import P4Rule

class Interpreter():
  @staticmethod
  def table_add(self):
    pass

  @staticmethod
  def table_modify(self):
    pass

  @staticmethod
  def table_delete(self):
    pass

class Interpretation():
  def __init__(self, rule, handles):
    self.origin_rule = rule
    self.hp4_rule_handles = handles

class InterpretationGuide():
  def __init__(self, ig_path):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::parse_json
    self.templates_match = {}
    self.templates_prims = {}
    with open(ig_path) as json_data:
      d = json.load(json_data)
      for hp4_command in d:
        attributes = {}
        attributes['src_table'] = hp4_command['source_table']
        src_table = hp4_command['source_table']
        src_action = hp4_command['source_action']
        key = (src_table, src_action)
        command_type = hp4_command['command']
        attributes['src_table'] = src_table
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
          if self.templates_prims.has_key(key) == False:
            self.templates_prims[key] = []
          self.templates_prims[key].append(P4Command(command_type, attributes))
        else:
          print("ERROR: Unrecognized class: %s" % hp4_command['__class__'])
    self.templates = {}
    for key in self.templates_match:
      self.templates[key] = {'match': self.templates_match[key], 'primitives': []}
      if self.templates_prims.has_key(key):
        self.templates[key]['primitives'] = self.templates_prims[key]

  #def get_templates(self, table, action):
  #  return self.templates[(table, action)]
