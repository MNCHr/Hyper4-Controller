#!/usr/bin/python

import random
import argparse
import sys
from cStringIO import StringIO
import runtime_CLI
from sswitch_CLI import SimpleSwitchAPI
import socket
import time

# TODO: eval multiprocessing.dummy
from multiprocessing import Process, Lock, Pool

import itertools

import code

IP_IDX =   0
PORT_IDX = 1
RTA_IDX =  2
LOCK_IDX = 3
ENC_H_IDX = 4
DEC_H_IDX = 5
devices = {} # 'id': (ip, port, rta, lock, enc_handles, dec_handles)

class RtaError(Exception):
  pass

# http://stackoverflow.com/questions/16571150/how-to-capture-stdout-output-from-a-python-function-call
class Capturing(list):
  def __enter__(self):
    self._stdout = sys.stdout
    sys.stdout = self._stringio = StringIO()
    return self
  def __exit__(self, *args):
    self.extend(self._stringio.getvalue().splitlines())
    del self._stringio
    sys.stdout = self._stdout

def add_device(dev_id, ip, port):
  services = runtime_CLI.RuntimeAPI.get_thrift_services(runtime_CLI.PreType.SimplePreLAG)
  services.extend(SimpleSwitchAPI.get_thrift_services())
  try:
    std_client, mc_client, sswitch_client = runtime_CLI.thrift_connect(ip, port, services)
  except:
      raise Exception("Error - create_device: " + str(sys.exc_info()[0]))
  json = 'vib2.json'
  runtime_CLI.load_json_config(std_client, json)
  rta = SimpleSwitchAPI(runtime_CLI.PreType.SimplePreLAG, std_client,
                               mc_client, sswitch_client)
  devices[dev_id] = (ip, port, rta, Lock(), {}, {})

def do_table_modify(dev_id, rule):
  try:
    devices[dev_id][LOCK_IDX].acquire()
    devices[dev_id][RTA_IDX].do_table_modify(rule)
  except:
    raise Exception('Error - do_table_modify: ' + str(sys.exc_info()[0]))
  finally:
    devices[dev_id][LOCK_IDX].release()
  return 'do_table_modify'

def do_table_add(dev_id, rule):
  with Capturing() as output:
    try:
      devices[dev_id][RTA_IDX].do_table_add(rule)
    except KeyboardInterrupt:
      pass
    except:
      raise Exception('Error - do_table_add: ' + str(sys.exc_info()[0]))
  for out in output:
    if 'Entry has been added' in out:
      return int(out.split('handle ')[1])
  raise Exception('do_table_add: did not detect success (rule: ' + rule + ')')

class Controller(object):

  def __init__(self, args):
    self.h_width = args.hki_width
    self.k_width = args.ki_width
    self.outfile = args.outfile
    self.threaded = args.threaded
    self.debug = args.debug
    self.devices = {}
    for deviceport in args.devices:
      dev_id = 'local_' + str(deviceport)
      self.devices[dev_id] = ('localhost', deviceport)
    for dev_id in self.devices:
      add_device(dev_id,
                 self.devices[dev_id][IP_IDX],
                 self.devices[dev_id][PORT_IDX])
    self.pool = Pool(processes=2)
    self.keys = {} # {key index (int) : keys (list of strs)}

  @staticmethod
  def gen_subkey(nbytes):
    ret = '0x'
    for i in range(nbytes):
      ret += hex(random.randint(0, 255)).split('0x')[1]
    return ret

  def gen_mask_and_keys(self):
    h_width = self.h_width
    k_width = self.k_width
    outfile = self.outfile
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
    
    with open(outfile, 'w') as f:
      print("MASK: " + hex(mask))
      f.write(hex(mask) + '\n')

      for i in range(2**k_width):
        keybits = [0] * k_width
        value = i
        for j in range(k_width):
          keybits[j] = value & 1
          value = value >> 1
        # print(str(keybits[::-1]))
        kidx = 0
        for j in range(k_width):
          kidx = kidx | (keybits[j] << bits[j])
        rule = 'decrypt a_decrypt ' + hex(kidx) + '&&&' + hex(mask) + ' => '
        k1 = self.gen_subkey(6)
        k2 = self.gen_subkey(6)
        k3 = self.gen_subkey(4)
        k4 = self.gen_subkey(4)
        self.keys[kidx] = [k1, k2, k3, k4]
        rule += k1 + ' ' + k2 + ' ' + k3 + ' ' + k4 + ' 1'
        f.write(rule + '\n')

        for dev_id in self.devices:
          handle = do_table_add(dev_id, rule)
          devices[dev_id][DEC_H_IDX][kidx] = handle

        rule = 'encrypt a_encrypt ' + hex(kidx) + '&&&' + hex(mask) + ' => '
        rule += k1 + ' ' + k2 + ' ' + k3 + ' ' + k4 + ' 1'
        f.write(rule + '\n')

        for dev_id in self.devices:
          handle = do_table_add(dev_id, rule)
          devices[dev_id][ENC_H_IDX][kidx] = handle

  def update_kidx(self, kidx):
    "rule_mod: \'<table name> <action> <handle> <[aparams]>\'"

    #print('Key index: ' + hex(kidx))
    #for dev_id in self.devices:
    #  handle = devices[dev_id][ENC_H_IDX][kidx]
    #  print('  ' + dev_id + ' encrypt handle: ' + str(handle))
    #k1, k2, k3, k4 = self.keys[kidx]
    #print('Old Keys: ' + k1 + ' ' + k2 + ' ' + k3 + ' ' + k4)

    # 1: Change key index when assigned to new packets

    self.keys[kidx] = 'unsafe'

    rule_mod_part1 = 'encrypt a_mod_epoch_and_encrypt '

    done = False
    while done == False:
      new_kidx = self.keys.keys()[random.randint(0, 2**self.k_width - 1)]
      if self.keys[new_kidx] != 'unsafe':  
        k1, k2, k3, k4 = self.keys[new_kidx]
        done = True

    rule_mod_part2 = ' ' + hex(new_kidx) + ' '
    rule_mod_part2 += k1 + ' ' + k2 + ' ' + k3 + ' ' + k4

    jobs = []
    for dev_id in self.devices:
      handle = devices[dev_id][ENC_H_IDX][kidx]
      #print(dev_id + ' encrypt handle: ' + str(handle))
      rule_mod = rule_mod_part1 + str(handle) + rule_mod_part2
      jobs.append((dev_id, rule_mod))

    results = []

    if(self.threaded):
      #if(self.debug):
      #  print('Step 1: pre do_table_modify')
      #  code.interact(local=dict(globals(), **locals()))
      for job in jobs:
        results.append(self.pool.apply_async(do_table_modify, (job[0], job[1])))
      #if(self.debug):
      #  print('Step 1: post do_table_modify')
      #  code.interact(local=dict(globals(), **locals()))

    else:
      for job in jobs:
        devices[job[0]][RTA_IDX].do_table_modify(job[1])

    # 2: Update key
    k1 = self.gen_subkey(6)
    k2 = self.gen_subkey(6)
    k3 = self.gen_subkey(4)
    k4 = self.gen_subkey(4)
    self.keys[kidx] = [k1, k2, k3, k4]

    # 3: Wait for packets in flight w/ old key index to drain
    # By this point, more than likely, all packets with
    #  the old key index have already drained.  For now,
    #  we forego any explicit attempt to wait an RTT or to
    #  detect that such packets are still in flight, but
    #  we will evaluate whether key index updates cause packet loss.

    # 4: Update decrypt keys everywhere
    rule_mod_part1 = 'decrypt a_decrypt '
    rule_mod_part2 = ' ' + k1 + ' ' + k2 + ' ' + k3 + ' ' + k4

    #print('New keys:' + rule_mod_part2 + '\n')

    jobs = []
    for dev_id in self.devices:
      handle = devices[dev_id][DEC_H_IDX][kidx]
      rule_mod = rule_mod_part1 + str(handle) + rule_mod_part2
      jobs.append((dev_id, rule_mod))
    if(self.threaded):
      #if(self.debug):
      #  print('Step 4: pre do_table_modify')
      #  code.interact(local=dict(globals(), **locals()))
      for job in jobs:
        results.append(self.pool.apply_async(do_table_modify, (job[0], job[1])))
      #if(self.debug):
      #  print('Step 4: post do_table_modify')
      #  code.interact(local=dict(globals(), **locals()))
    else:
      for job in jobs:
        devices[job[0]][RTA_IDX].do_table_modify(job[1])

    # 5: Stop changing key index when assigned to new packets 
    rule_mod_part1 = 'encrypt a_encrypt '
    rule_mod_part2 = ' ' + k1 + ' ' + k2 + ' ' + k3 + ' ' + k4

    jobs = []
    for dev_id in self.devices:
      handle = devices[dev_id][ENC_H_IDX][kidx]
      rule_mod = rule_mod_part1 + str(handle) + rule_mod_part2
      jobs.append((dev_id, rule_mod))
    if(self.threaded):
      #if(self.debug):
      #  print('Step 5: pre do_table_modify')
      #  code.interact(local=dict(globals(), **locals()))
      for job in jobs:
        results.append(self.pool.apply_async(do_table_modify, (job[0], job[1])))
      #if(self.debug):
      #  print('Step 5: post do_table_modify')
      #  code.interact(local=dict(globals(), **locals()))
    else:
      for job in jobs:
        devices[job[0]][RTA_IDX].do_table_modify(job[1])

    if(self.threaded):
      for res in results:
        res.wait()

#def server(args):
#  ctrl = Controller(args)
#  ctrl.serverloop()

def parse_args(args):
  parser = argparse.ArgumentParser(description='VIBRANT AP Control')
  parser.add_argument('--devices', help='ports for bmv2 devices',
                      default=[22222, 22223, 22224], type=int, nargs='*')
  parser.add_argument('--hki_width', help='hidden key index field width',
                      type=int, action='store', default=64)
  parser.add_argument('--ki_width', help='actual key index width',
                      type=int, action='store', default=8)
  parser.add_argument('--outfile', help='output file',
                      type=str, action='store', default='entries')
  parser.add_argument('--threaded', help='enable threading',
                      action="store_true")
  parser.add_argument('--debug', help='enable debugging',
                      action="store_true")
  #parser.set_defaults(func=server)
  return parser.parse_args(args)

def print_args(args):
  print("devices: " + str(args.devices))
  print("hidden key index field width: " + str(args.hki_width))
  print("actual key index field width: " + str(args.ki_width))
  print("output file: " + args.outfile)
  print("threaded: " + str(args.threaded))
  print("debug: " + str(args.debug))

def main():
  args = parse_args(sys.argv[1:])
  print_args(args)

  ctrl = Controller(args)
  ctrl.gen_mask_and_keys()

  raw_input("Press Enter to begin key rotation...")

  count = 0
  start = time.time()

  while count < 4:

    for i in range(2**args.ki_width):
      ctrl.update_kidx(ctrl.keys.keys()[i])

    count += 1

  end = time.time()
  print(end - start)

if __name__ == '__main__':
  main()
