#!/bin/bash

RUN=0

if [ $# -eq 1 ]
  then
    RUN=$1
fi

sudo tcpdump -i s1-eth1 -n -s 0 -w t01_s1_eth1_run$RUN.dump &
PID_1=$!
sudo tcpdump -i s1-eth2 -n -s 0 -w t01_s1_eth2_run$RUN.dump &
PID_2=$!
sudo tcpdump -i s1-eth3 -n -s 0 -w t01_s1_eth3_run$RUN.dump &
PID_3=$!

read -n 1 -s

kill -15 $PID_1
sleep 1
kill -15 $PID_2
sleep 1
kill -15 $PID_3
