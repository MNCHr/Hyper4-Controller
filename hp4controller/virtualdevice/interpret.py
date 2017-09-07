import virtualdevice
from ..p4command import P4Command
from p4rule import P4Rule

import json
import copy
import code

class Interpreter(object):
  @staticmethod
  def table_add(guide, p4command, match_ID):
    p4commands = []
    rule = P4Rule(p4command.attributes['table'],
                  p4command.attributes['action'],
                  p4command.attributes['mparams'],
                  p4command.attributes['aparams'])
    key = (rule.table, rule.action)
    mrule = copy.copy(guide.templates[key]['match'])

    # TODO ...

    p4commands.append(mrule)

    for entry in guide.templates[key]['primitives']:
      arule = copy.copy(entry)

      # TODO ...

      p4commands.append(arule)

    return p4commands

  @staticmethod
  def table_modify(guide, p4command):
    pass

  @staticmethod
  def table_delete(guide, p4command):
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
