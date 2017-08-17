class P4Command():
  def __init__(self, command_type, attributes):
    self.command_type = command_type
    self.attributes = attributes # {<attrib_name>: <attribute}
                                 # standard attributes:
                                 #  table
                                 #  action
                                 #  mparams
                                 #  aparams
                                 #  handle
                                 #  src_table (for HP4 match commands)
                                 #  src_aparam_id (for HP4 primitive commands)
