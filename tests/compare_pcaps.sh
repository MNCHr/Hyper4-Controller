#!/bin/bash

# defaults for command-line arguments
TEST=0
RUN1=0
RUN2=1
SWITCHES=3
IFACES=10

while [[ $# -gt 1 ]]
do
key="$1"

case $key in
    -t|--test)
    TEST="$2"
    shift # past argument
    ;;
    -r1|--run1)
    RUN1="$2"
    shift # past argument
    ;;
    -r2|--run2)
    RUN2="$2"
    shift # past argument
    ;;
    -s|--switches)
    SWITCHES="$2"
    shift # past argument
    ;;
    -i|--ifaces)
    IFACES="$2"
    shift # past argument
    ;;
    *)
            # unknown option
    ;;
esac
shift # past argument or value
done

for i in `seq 1 $SWITCHES`;
do
  for j in `seq 1 $IFACES`;
  do
    f1pre=${TEST}"/"${TEST}"_s"$i"_eth"$j"_run_"${RUN1}
    f2pre=${TEST}"/"${TEST}"_s"$i"_eth"$j"_run_"${RUN2}
    tcpdump -r $f1pre".dump" -vvv -e -n > $f1pre".rdump"
    tcpdump -r $f2pre".dump" -vvv -e -n > $f2pre".rdump"
    #./process_pcap.py $f1pre".rdump" > $f1pre"_processed.rdump"
    #./process_pcap.py $f2pre".rdump" > $f2pre"_processed.rdump"
    #diff $f1pre"_processed.rdump" $f2pre"_processed.rdump"
  done
done
