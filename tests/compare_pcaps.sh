#!/bin/bash

TEST=0
RUN1=0
RUN2=1

if [ $# -gt 0 ]
then
  TEST=$1
  if [ $# -gt 1 ]
    then
      RUN1=$2
      if [ $# -gt 2 ]
        then
        RUN2=$3
      fi
  fi
fi

f1pre=t${TEST}"_s1_eth1_run"${RUN1}
f2pre=t${TEST}"_s1_eth1_run"${RUN2}

tcpdump -r $f1pre".dump" -t -vvv -e -n > $f1pre".txt"
tcpdump -r $f2pre".dump" -t -vvv -e -n > $f2pre".txt"

./process_pcap.py $f1pre".txt" > $f1pre"_processed.txt"
./process_pcap.py $f2pre".txt" > $f2pre"_processed.txt"

diff $f1pre"_processed.txt" $f2pre"_processed.txt"
