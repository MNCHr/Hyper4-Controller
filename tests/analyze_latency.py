#!/usr/bin/python

import dpkt
import argparse
import sys
import numpy as np

import code

REQUEST = 8
RESPONSE = 0

PERCWIDTH = 1000

def gen_latency_timeseries(pcap, outpath, percpath, percval, missespath):
  ping_queue = {} # {sequence: request ts}
  counter = 0
  errors = 0
  missed = 0
  ts_first_missed = float("inf")
  ts_last_missed = 0
  seq_first_missed = 0
  seq_last_missed = 0
  percidx = 0
  perc = [0] * PERCWIDTH
  perc_ctr = 0
  out = open(outpath, 'w')
  out.write('x, y\n')
  percout = open(percpath, 'w')
  percout.write('x, y\n')
  missesf = open(missespath, 'w')
  missesf.write('ts, seq\n')
  ts_init = 0
  for ts, pkt in pcap:
    counter += 1
    if counter % 10000 == 0:
      sys.stdout.write('.')
      sys.stdout.flush()
    eth = dpkt.ethernet.Ethernet(pkt)
    if not isinstance(eth.data, dpkt.ip.IP):
      continue
    ip = eth.data
    if not isinstance(ip.data, dpkt.icmp.ICMP):
      continue
    icmp = ip.data
    if icmp.type == REQUEST:
      if icmp.echo.seq in ping_queue:
        missed += 1
        missesf.write(str(ping_queue[icmp.echo.seq]) + ", " + str(icmp.echo.seq) + '\n')
        if ping_queue[icmp.echo.seq] < ts_first_missed:
          ts_first_missed = ping_queue[icmp.echo.seq]
          seq_first_missed = icmp.echo.seq
        if ping_queue[icmp.echo.seq] > ts_last_missed:
          ts_last_missed = ping_queue[icmp.echo.seq]
          seq_last_missed = icmp.echo.seq
      ping_queue[icmp.echo.seq] = ts
      if ts_init == 0:
        ts_init = ts - 5
    elif icmp.type == RESPONSE:
      if icmp.echo.seq not in ping_queue:
        print("Error: response w/out request: #" + str(counter))
        errors += 1
        continue
      latency = ts - ping_queue[icmp.echo.seq]
      # plot: (x, y) = (ping_queue[icmp.echo.seq], latency)
      out.write(str(ping_queue[icmp.echo.seq] - ts_init) + ', ' + str(1000*latency) + '\n')
      perc[percidx] = latency
      percidx = (percidx + 1) % PERCWIDTH
      if perc_ctr < PERCWIDTH:
        perc_ctr += 1
      else:
        perclatency = np.percentile(perc, percval)
        percout.write(str(ping_queue[icmp.echo.seq] - ts_init) + ', ' + str(1000*perclatency) + '\n')
      #if icmp.echo.seq > 5104 and icmp.echo.seq < 5510:
      #  code.interact(local=dict(globals(), **locals()))
      del ping_queue[icmp.echo.seq]

  sys.stdout.write('\n')
  sys.stdout.flush()
  out.close()
  percout.close()
  missesf.close()
  print("confirmed misses: " + str(missed))
  print("ts first miss: " + str(ts_first_missed))
  print("seq first miss: " + str(seq_first_missed))
  print("ts last miss: " + str(ts_last_missed))
  print("seq last miss: " + str(seq_last_missed))

def parse_args(args):
  parser = argparse.ArgumentParser(description='Analyze ping latency')
  parser.add_argument('--pcap', help='Path for pcap',
                      type=str, action="store")
  parser.add_argument('--out', help='Path for output',
                      type=str, action="store")
  parser.add_argument('--percout', help='Path for output of rolling percentile',
                      type=str, action="store")
  parser.add_argument('--percval', help='Percentile',
                      type=int, action="store")
  parser.add_argument('--misses', help='Path for output of confirmed unanswered pings',
                      type=str, action="store")

  return parser.parse_args(args)

def main():
  args = parse_args(sys.argv[1:])
  with open(args.pcap, 'r') as f:
    pcap = dpkt.pcap.Reader(f)
    gen_latency_timeseries(pcap, args.out, args.percout, args.percval, args.misses)

if __name__ == '__main__':
  main()
