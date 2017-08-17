from p4command import P4Command

attribs = {'table': 'mytable'}

thing = P4Command('table_add', attribs)

print(thing.command_type)
