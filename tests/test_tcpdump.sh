#!/bin/bash

TEST=0
RUN=0

if [ $# -gt 0 ]
then
  TEST=$1
  if [ $# -gt 1 ]
    then
      RUN=$2
  fi
fi

fname1=t${TEST}"_s1_eth1_run"${RUN}".dump"
fname2=t${TEST}"_s1_eth2_run"${RUN}".dump"
fname3=t${TEST}"_s1_eth3_run"${RUN}".dump"

tcpdump -i s1-eth1 -n -s 0 -w $fname1 &
PID_1=$!
tcpdump -i s1-eth2 -n -s 0 -w $fname2 &
PID_2=$!
tcpdump -i s1-eth3 -n -s 0 -w $fname3 &
PID_3=$!

read -n 1 -s

kill -15 $PID_1
sleep 1
kill -15 $PID_2
sleep 1
kill -15 $PID_3
