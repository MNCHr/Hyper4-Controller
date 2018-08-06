#!/usr/bin/python

import argparse
import sys
import socket
import readline
import cmd
import atexit
import code
from inspect import currentframe, getframeinfo
from client import ChainSliceManager

def debug():
  """ Break and enter interactive method after printing location info """
  # written before I knew about the pdb module
  caller = currentframe().f_back
  method_name = caller.f_code.co_name
  line_no = getframeinfo(caller).lineno
  print(method_name + ": line " + str(line_no))
  code.interact(local=dict(globals(), **caller.f_locals))

BUFFSIZE = 4096

class VibrantManager(ChainSliceManager):
  def __init__(self, **kwargs):
    super(VibrantManager, self).__init__(**kwargs)
    self.devices = []
    self.dec_path = ""
    self.enc_path = ""
    self.h_width = 64
    self.k_width = 8
    self.keyset1 = []

"""
1 command to create vibrant vdevs & initialize
1 command to deploy decryptors to all switches
1 command to deploy encryptors to all switches
1 command to rotate keys via individual key rotations
- space to stop
1 command to rotate keys via vdev replacement
- space to stop
"""

  @staticmethod
  def gen_subkey(nbytes):
    ret = '0x'
    for i in range(nbytes):
      ret += hex(random.randint(0, 255)).split('0x')[1]
    return ret

  def gen_mask_and_keys(self):
    h_width = self.h_width
    k_width = self.k_width

    assert(h_width > 0)
    assert(h_width > k_width)

    bits = []
    mask = 0

    for i in range(k_width):
      done = False
      while(done == False):
        bit = random.randint(0, h_width - 1)
        if bit not in bits:
          bits.append(bit)
          done = True
  
    for bit in bits:
      mask = mask | (1 << bit)
    
    for i in range(2**k_width):
    # TODO: import remainder f method from key_rotator fro line 129 down

  def do_vib_ap_init(self, line):
    """Initialize VIBRANT address protection: vib_ap_init <decryptor p4_path>
     \r<enryptor p4_path> <list of devices>
    """
    minargs = 2
    self.devices = line[2:].split()
    dec_path = line[0]
    enc_path = line[1]
    for device in self.devices:
      name = device + '_vib_dec'
      vdev_create_line = dec_path + ' ' + name
      resp = self.send_request(self.user + ' vdev_create ' + vdev_create_line)
      name = device + '_vib_enc'
      vdev_create_line = enc_path + ' ' + name
      resp = self.send_request(self.user + ' vdev_create ' + vdev_create_line)


def client(args):
  if args.user == 'admin':
    c = Administrator(**vars(args))
  else:
    c = VibrantManager(**vars(args))
  if args.startup:
    with open(args.startup) as commands:
      for command in commands:
        c.onecmd(command)
  c.cmdloop()

def parse_args(args):
  parser = argparse.ArgumentParser(description='HyPer4 Client')
  parser.add_argument('--debug', help='turn on debug mode',
                      action='store_true')
  parser.add_argument('--ip', help='ip of Controller',
                      type=str, action="store", default="localhost")
  parser.add_argument('--port', help='port for Controller',
                      type=int, action="store", default=33333)
  parser.add_argument('--startup', help='file with commands to run at startup',
                      type=str, action="store")
  parser.add_argument('user', help='<slice name> | \'admin\'', type=str, action="store")
  parser.set_defaults(func=client)

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  args.func(args)

if __name__ == '__main__':
  main()
