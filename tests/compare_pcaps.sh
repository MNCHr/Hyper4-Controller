#!/bin/bash

TEST=0
RUN1=0
RUN2=1
IFACES=3

if [ $# -gt 0 ]
then
  TEST=$1
  if [ $# -gt 1 ]
    then
      RUN1=$2
      if [ $# -gt 2 ]
        then
          RUN2=$3
          if [ $# -gt 3 ]
            then
              IFACES=$4
          fi
      fi
  fi
fi

for i in `seq 1 $IFACES`;
do
  f1pre=t${TEST}"_s1_eth"$i"_run"${RUN1}
  f2pre=t${TEST}"_s1_eth"$i"_run"${RUN2}
  tcpdump -r $f1pre".dump" -t -vvv -e -n > $f1pre".txt"
  tcpdump -r $f2pre".dump" -t -vvv -e -n > $f2pre".txt"
  ./process_pcap.py $f1pre".txt" > $f1pre"_processed.txt"
  ./process_pcap.py $f2pre".txt" > $f2pre"_processed.txt"
  diff $f1pre"_processed.txt" $f2pre"_processed.txt"
done
