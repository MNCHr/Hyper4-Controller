#!/bin/bash

RUN=0

if [ $# -eq 1 ]
  then
    RUN=$1
fi

sudo tcpdump -i s1-eth1 -n -s 0 -w t01_s1_eth1_run$RUN.dump &
sudo tcpdump -i s1-eth2 -n -s 0 -w t01_s1_eth2_run$RUN.dump &
sudo tcpdump -i s1-eth3 -n -s 0 -w t01_s1_eth3_run$RUN.dump &
