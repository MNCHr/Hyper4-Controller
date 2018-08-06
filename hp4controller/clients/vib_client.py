#!/usr/bin/python

import random
import argparse
import sys
import socket
import readline
import cmd
import atexit
import thread
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
    self.dec_vdevs = []
    self.enc_vdevs = []
    self.dec_path = ""
    self.enc_path = ""
    self.h_width = 64
    self.key_index_width = 8
    self.keys = {} # {key index (int) : keys (list of strs)}

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
    key_index_width = self.key_index_width

    assert(h_width > 0)
    assert(h_width > key_index_width)

    dec_rules = []
    enc_rules = []
    bits = []
    mask = 0

    for i in range(key_index_width):
      done = False
      while(done == False):
        bit = random.randint(0, h_width - 1)
        if bit not in bits:
          bits.append(bit)
          done = True
  
    for bit in bits:
      mask = mask | (1 << bit)
    
    for i in range(2**key_index_width):
      keybits = [0] * key_index_width
      value = i
      for j in range(key_index_width):
        keybits[j] = value & 1
        value = value >> 1
      # print(str(keybits[::-1]))
      kidx = 0
      for j in range(key_index_width):
        kidx = kidx | (keybits[j] << bits[j])
      rule = 'decrypt a_decrypt ' + hex(kidx) + '&&&' + hex(mask) + ' => '
      k1 = self.gen_subkey(6)
      k2 = self.gen_subkey(6)
      k3 = self.gen_subkey(4)
      k4 = self.gen_subkey(4)
      self.keys[kidx] = [k1, k2, k3, k4]
      rule += k1 + ' ' + k2 + ' ' + k3 + ' ' + k4 + ' 1'
      dec_rules.append(rule)

      rule = 'encrypt a_encrypt ' + hex(kidx) + '&&&' + hex(mask) + ' => '
      rule += k1 + ' ' + k2 + ' ' + k3 + ' ' + k4 + ' 1'
      enc_rules.append(rule)

    return dec_rules, enc_rules

  def do_vib_ap_init(self, line):
    """Initialize VIBRANT address protection: vib_ap_init <decryptor p4_path>
     \r<enryptor p4_path> <list of devices>
    """
    minargs = 2
    dec_path = line.split()[0]
    enc_path = line.split()[1]
    for device in line.split()[2:]:
      name = device + '_vib_dec'
      vdev_create_line = dec_path + ' ' + name
      resp = self.send_request(self.user + ' vdev_create ' + vdev_create_line)
      if 'created' not in resp:
        print('Attempt to create ' + name + ' failed with this error:')
        print(resp)
        debug()
      else:
        self.dec_vdevs.append(name)
      name = device + '_vib_enc'
      vdev_create_line = enc_path + ' ' + name
      resp = self.send_request(self.user + ' vdev_create ' + vdev_create_line)
      if 'created' not in resp:
        print('Attempt to create ' + name + ' failed with this error:')
        print(resp)
        debug()
      else:
        self.enc_vdevs.append(name)

    self.dec_rules, self.enc_rules = self.gen_mask_and_keys()

    for dec_vdev in self.dec_vdevs:
      #handle = do_table_add(dev_id, rule)
      #devices[dev_id][ENC_H_IDX][kidx] = handle
      for rule in self.dec_rules:
        resp = self.do_vdev_interpret(dec_vdev + ' bmv2 table_add ' + rule)
        self.debug_print(resp)
      resp = self.do_vdev_interpretf(dec_vdev + ' bmv2 tests/t09/commands_slice1_vib_dec.txt')

    for enc_vdev in self.enc_vdevs:
      for rule in self.enc_rules:
        resp = self.do_vdev_interpret(enc_vdev + ' bmv2 table_add ' + rule)
        self.debug_print(resp)

    for device in line.split()[2:]:
      dec_vdev = device + '_vib_dec'
      self.do_lease_insert(device + ' ' + dec_vdev + ' 0 efalse')

    for device in line.split()[2:]:
      enc_vdev = device + '_vib_enc'
      resp = self.do_vdev_interpretf(enc_vdev + ' bmv2 tests/t09/commands_slice1_' \
                                     + device + '_vib_enc.txt')
      self.do_lease_append(device + ' ' + enc_vdev + ' efalse')

  def rotate_keys(self):
    for i in range(2**self.key_index_width):
      kidx = self.keys.keys()[i]
      self.keys[kidx] = 'unsafe'
      rule_mod_part1 = 'encrypt a_mod_epoch_and_encrypt '
      done = False
      while done == False:
        new_kidx = self.keys.keys()[random.randint(0, 2**self.key_index_width - 1)]
        if self.keys[new_kidx] != 'unsafe':
          k1, k2, k3, k4 = self.keys[new_kidx]
          done = True

      rule_mod_part2 = ' ' + hex(new_kidx) + ' '
      rule_mod_part2 += ' '.join([k1, k2, k3, k4])

    return 2**self.key_index_width

  def do_vib_ap_rotate(self, line):
    """ Rotate VIBRANT address protection keys: vib_ap_rotate
    """
    keys_rotated = 0
    start = time.time()
    try:
      while True:
        keys_rotated += self.rotate_keys()
    except KeyboardInterrupt:
      duration = time.time() - start
      print('Rotated %d keys in %f seconds (%f keys/second)' % (keys_rotated, duration, keys_rotated / duration))

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
