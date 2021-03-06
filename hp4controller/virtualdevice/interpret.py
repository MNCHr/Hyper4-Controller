import virtualdevice
from hp4controller.p4command import P4Command
from hp4controller.errors import InterpretError
from p4rule import P4Rule

import json
import copy
import re
import code
from inspect import currentframe, getframeinfo

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))


MAX_PRIORITY = 2147483646

match_types = {'[DONE]':'0',
               '[EXTRACTED_EXACT]':'1',
               '[METADATA_EXACT]':'2',
               '[STDMETA_EXACT]':'3',
               '[EXTRACTED_VALID]':'4',
               '[STDMETA_INGRESS_PORT_EXACT]':'5',
               '[STDMETA_PACKET_LENGTH_EXACT]':'6',
               '[STDMETA_INSTANCE_TYPE_EXACT]':'7',
               '[STDMETA_EGRESS_SPEC_EXACT]':'8',
               '[METADATA_TERNARY]':'9',
               '[EXTRACTED_TERNARY]':'10',
               '[MATCHLESS]':'99'}

primitive_types = {'[ADD_HEADER]':'1',
									 '[COPY_HEADER]':'2',
									 '[REMOVE_HEADER]':'3',
									 '[MODIFY_FIELD_WITH_HBO]':'4',
									 '[TRUNCATE]':'5',
									 '[DROP]':'6',
									 '[NO_OP]':'7',
									 '[PUSH]':'8',
									 '[POP]':'9',
									 '[COUNT]':'10',
									 '[METER]':'11',
									 '[GENERATE_DIGEST]':'12',
									 '[RECIRCULATE]':'13',
									 '[RESUBMIT]':'14',
									 '[CLONE_INGRESS_INGRESS]':'15',
									 '[CLONE_EGRESS_INGRESS]':'16',
									 '[CLONE_INGRESS_EGRESS]':'17',
									 '[CLONE_EGRESS_EGRESS]':'18',
									 '[MULTICAST]':'19',
									 '[MATH_ON_FIELD]':'20',
                   '[MODIFY_FIELD]':'21',
                   '[MODIFY_FIELD_RNG_U]': '22',
                   '[BIT_XOR]': '23'}

class Interpreter(object):
  @staticmethod
  def table_set_default(guide, p4command, mrule_handle, hp4_rule_keys, vdev_ID, mcast_grp_id):
    p4commands = []
    rule = P4Rule(p4command.attributes['table'],
                  p4command.attributes['action'],
                  [],
                  p4command.attributes['aparams'],
                  default=True)
    key = (rule.table, rule.action)

    mrule = copy.deepcopy(guide.templates[key]['match'])

    mrule.command_type = 'table_modify'
    mrule.attributes['handle'] = mrule_handle

    ## match parameters
    mrule_match_params = mrule.attributes['mparams']

    for i in range(len(mrule_match_params)):
      if mrule_match_params[i] == '[vdev ID]':
        mrule_match_params[i] = str(vdev_ID)

      if '[val]' in mrule_match_params[i]:
        mrule_match_params[i] = '0&&&0'

    ## action parameters
    mrule_action_params = mrule.attributes['aparams']
    for i in range(len(mrule_action_params)):
      if mrule_action_params[i] == '[match ID]':
        mrule_action_params[i] = '0'
      elif mrule_action_params[i] == '[PRIORITY]':
        mrule_action_params[i] = ''
      elif mrule_action_params[i] in match_types:
        mrule_action_params[i] = match_types[mrule_action_params[i]]
      elif mrule_action_params[i] in primitive_types:
        mrule_action_params[i] = primitive_types[mrule_action_params[i]]

    p4commands.append(mrule)
    
    # handle the primitives rules
    #   delete existing rules
    #   add new rules

    #   delete existing rules
    for table, action, handle in hp4_rule_keys:
      # delete everything but the match rule
      if table != mrule.attributes['table']:
        attribs = {'table': table,
                   'handle': handle}
        p4commands.append(P4Command('table_delete', attribs))

    #   add new rules
    for entry in guide.templates[key]['primitives']:
      arule = copy.deepcopy(entry)
      ## match parameters
      arule_match_params = arule.attributes['mparams']
      for i in range(len(arule_match_params)):
        if arule_match_params[i] == '[vdev ID]':
          arule_match_params[i] = str(vdev_ID)
        elif '[match ID]' in arule_match_params[i]:
          arule_match_params[i] = arule_match_params[i].replace('[match ID]',
                                                                 '0')
      ## action parameters
      arule_action_params = arule.attributes['aparams']
      for i in range(len(arule_action_params)):
        if arule_action_params[i] == '[val]':
          a_idx = int(arule.attributes['src_aparam_id'])
          arule_action_params[i] = str(rule.aparams[a_idx])
        if arule_action_params[i] == '[MCAST_GRP]':
          arule_action_params[i] = str(mcast_grp_id)
        if re.search("\[[0-9]*x00s\]", arule_action_params[i]):
          to_replace = re.search("\[[0-9]*x00s\]", arule_action_params[i]).group()
          numzeros = int(re.search("[0-9]+", to_replace).group())
          replace = ""
          for j in range(numzeros):
            replace += "00"   
          arule_action_params[i] = \
                            arule_action_params[i].replace(to_replace, replace)

      p4commands.append(arule)

    return p4commands
    
  @staticmethod
  def table_add(guide, p4command, match_ID, vdev_ID, mcast_grp_id):
    p4commands = []
    rule = P4Rule(p4command.attributes['table'],
                  p4command.attributes['action'],
                  p4command.attributes['mparams'],
                  p4command.attributes['aparams'])
    key = (rule.table, rule.action)

    # handle the match rule
    mrule = copy.deepcopy(guide.templates[key]['match'])
    ## match parameters
    mrule_match_params = mrule.attributes['mparams']

    for i in range(len(mrule_match_params)):
      if mrule_match_params[i] == '[vdev ID]':
        mrule_match_params[i] = str(vdev_ID)
      if '[val]' in mrule_match_params[i]:

        if '0x' in rule.mparams[0]:
          leftside = rule.mparams[0]
        elif ':' in rule.mparams[0]:
          print("Not yet supported: %s" % rule.mparams[0])
          exit()
        else:
          leftside = format(int(rule.mparams[0]), '#x')

        if '&&&' in leftside:
          leftside, mask = leftside.split('&&&')
          if re.search("\[[0-9]*x00s\]", mrule_match_params[i]):
            to_replace = re.search("\[[0-9]*x00s\]", mrule_match_params[i]).group()
            numzeros = int(re.search("[0-9]+", to_replace).group())
            replace = ""
            for j in range(numzeros):
              replace += "00"
            mrule_match_params[i] = mask + to_replace
            mrule_match_params[i] = \
                    mrule_match_params[i].replace(to_replace, replace)
            leftside += replace
            mrule_match_params[i] = \
                    leftside + '&&&' + mrule_match_params[i]

        else:
          if re.search("\[[0-9]*x00s\]", mrule_match_params[i]):
            to_replace = re.search("\[[0-9]*x00s\]", mrule_match_params[i]).group()
            numzeros = int(re.search("[0-9]+", to_replace).group())
            replace = ""
            for j in range(numzeros):
              replace += "00"
            mrule_match_params[i] = \
                    mrule_match_params[i].replace(to_replace, replace)
            leftside += replace
          mrule_match_params[i] = \
                  mrule_match_params[i].replace('[val]', leftside)

      elif '[valid]' in mrule_match_params[i]:
        # handle valid matching; 0 = 0, 1 = everything right of &&&
        if rule.mparams[0] == '1':
          mrule_match_params[i] = \
                  mrule_match_params[i].replace('[valid]',
                                       mrule_match_params[i].split('&&&')[1])
        elif rule.mparams[0] == '0':
          mrule_match_params[i] = \
                  mrule_match_params[i].replace('[valid]', '0x0')
        else:
          print("ERROR: Unexpected value in rule.mparams[0]: %s" % rule.mparams[0])
          exit()

    ## action parameters
    mrule_action_params = mrule.attributes['aparams']
    for i in range(len(mrule_action_params)):
      if mrule_action_params[i] == '[match ID]':
        mrule_action_params[i] = str(match_ID)
      elif mrule_action_params[i] == '[PRIORITY]':
        mrule_action_params[i] = '0'
      elif mrule_action_params[i] in match_types:
        mrule_action_params[i] = match_types[mrule_action_params[i]]
      elif mrule_action_params[i] in primitive_types:
        mrule_action_params[i] = primitive_types[mrule_action_params[i]]

    p4commands.append(mrule)

    # handle the primitives rules
    for entry in guide.templates[key]['primitives']:
      arule = copy.deepcopy(entry)
      ## match parameters
      arule_match_params = arule.attributes['mparams']
      for i in range(len(arule_match_params)):
        if arule_match_params[i] == '[vdev ID]':
          arule_match_params[i] = str(vdev_ID)
        elif '[match ID]' in arule_match_params[i]:
          arule_match_params[i] = arule_match_params[i].replace('[match ID]',
                                                                 str(match_ID))
      ## action parameters
      arule_action_params = arule.attributes['aparams']
      for i in range(len(arule_action_params)):
        if arule_action_params[i] == '[val]':
          a_idx = int(arule.attributes['src_aparam_id'])
          arule_action_params[i] = str(rule.aparams[a_idx])
        if arule_action_params[i] == '[MCAST_GRP]':
          arule_action_params[i] = str(mcast_grp_id)
        if re.search("\[[0-9]*x00s\]", arule_action_params[i]):
          to_replace = re.search("\[[0-9]*x00s\]", arule_action_params[i]).group()
          numzeros = int(re.search("[0-9]+", to_replace).group())
          replace = ""
          for j in range(numzeros):
            replace += "00"   
          arule_action_params[i] = \
                            arule_action_params[i].replace(to_replace, replace)

      p4commands.append(arule)

    return p4commands

  @staticmethod
  def table_modify(guide, p4command, interpretation, match_ID, vdev_ID, mcast_grp_id):
    p4commands = []
    # p4command attributes:
    #  'action': str
    #  'table': str
    #  'handle': int
    #  'aparams': [str]
    key = (p4command.attributes['table'], p4command.attributes['action'])

    if p4command.attributes['action'] == interpretation.native_rule.action:

      # PROBLEM: code below shouldn't be here - we might not end up committing the changes
      # UPDATE: this task was already in controller; suspect having it here was
      #  not only wrong but redundant
      # update interpretation origin rule
      #interpretation.native_rule = P4Rule(interpretation.native_rule.table,
      #                                    p4command.attributes['action'],
      #                                    interpretation.native_rule.mparams,
      #                                    p4command.attributes['aparams'])

      # table_modifies
      # TODO: revise to be less 'hacky' - this quality arises from lack of separation
      # in Interpretation class between the match rule and the primitive rules
      for i in range(1, len(interpretation.hp4_rule_keys)):
        table, action, handle = interpretation.hp4_rule_keys[i]
        # the 'i-1' is because the Interpretation has a match-rule-related P4Command first:
        arule = copy.deepcopy(guide.templates[key]['primitives'][i-1])
        if (arule.attributes['table'] != table) or (arule.attributes['action'] != action):
          print("Error: Interpret::table_modify observed interpretation out-of-sync w/ guide")
          debug()
          exit()
        arule_action_params = arule.attributes['aparams']
        del arule_action_params[len(arule_action_params)-1] # last is tern priority
        for i in range(len(arule_action_params)):
          if arule_action_params[i] == '[val]':
            a_idx = int(arule.attributes['src_aparam_id'])
            arule_action_params[i] = str(p4command.attributes['aparams'][a_idx])
          elif arule_action_params[i] == '[MCAST_GRP]':
            arule_action_params[i] = str(mcast_grp_id) # pass as parameter?
          elif re.search("\[[0-9]*x00s\]", arule_action_params[i]):
            to_replace = re.search("\[[0-9]*x00s\]", arule_action_params[i]).group()
            numzeros = int(re.search("[0-9]+", to_replace).group())
            replace = ""
            for j in range(numzeros):
              replace += "00"
            arule_action_params[i] = \
                              arule_action_params[i].replace(to_replace, replace)
        arule.command_type = 'table_modify'
        arule.attributes['handle'] = str(handle)
        p4commands.append(arule)

    else:
      # table_deletes, table_adds
      # skip match-related entry (don't want to delete it)
      for i in range(1, len(interpretation.hp4_rule_keys)):
        table, action, handle = interpretation.hp4_rule_keys[i]
        attribs = {'table': table,
                   'handle': handle}
        p4commands.append(P4Command('table_delete', attribs))

      for entry in guide.templates[key]['primitives']:
        arule = copy.deepcopy(entry)
        ## match parameters
        arule_match_params = arule.attributes['mparams']
        for i in range(len(arule_match_params)):
          if arule_match_params[i] == '[vdev ID]':
            arule_match_params[i] = str(vdev_ID)
          elif '[match ID]' in arule_match_params[i]:
            arule_match_params[i] = arule_match_params[i].replace('[match ID]',
                                                                 str(match_ID))
        ## action parameters
        arule_action_params = arule.attributes['aparams']
        for i in range(len(arule_action_params)):
          if arule_action_params[i] == '[val]':
            a_idx = int(arule.attributes['src_aparam_id'])
            arule_action_params[i] = str(p4command.attributes['aparams'][a_idx])
          if arule_action_params[i] == '[MCAST_GRP]':
            arule_action_params[i] = str(mcast_grp_id)
          if re.search("\[[0-9]*x00s\]", arule_action_params[i]):
            to_replace = re.search("\[[0-9]*x00s\]", arule_action_params[i]).group()
            numzeros = int(re.search("[0-9]+", to_replace).group())
            replace = ""
            for j in range(numzeros):
              replace += "00"   
            arule_action_params[i] = \
                            arule_action_params[i].replace(to_replace, replace)

        p4commands.append(arule)

    return p4commands

  @staticmethod
  def table_delete(p4command, hp4_rule_keys):
    p4commands = []
    for table, action, handle in hp4_rule_keys:
      attribs = {'table': table,
                 'handle': handle}
      p4commands.append(P4Command('table_delete', attribs))
    return p4commands

class Interpretation():
  def __init__(self, rule, match_ID, hp4_rule_keys):
    self.native_rule = rule
    self.match_ID = match_ID # int
    self.hp4_rule_keys = hp4_rule_keys # [(table (str), action (str), handle (int))]

class InterpretationGuide():
  def __init__(self, ig_path):
    # key method: ~/hp4-src/p4c-hp4/controller.py::DPMUServer::parse_json
    self.templates_match = {} # {(native_table, native_action): P4Command}
    self.templates_prims = {} # {(native_table, native_action): [P4Command]}
    with open(ig_path) as json_data:
      d = json.load(json_data)
      for hp4_command in d:
        attributes = {}
        src_table = hp4_command['source_table']
        src_action = hp4_command['source_action']
        key = (src_table, src_action)
        command_type = hp4_command['command']
        attributes['src_table'] = src_table
        attributes['src_action'] = src_action
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
