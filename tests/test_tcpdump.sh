#!/bin/bash

# defaults for command-line arguments
TEST=0
RUN=0
SWITCHES=1
IFACES=1

while [[ $# -gt 1 ]]
do
key="$1"

case $key in
    -t|--test)
    TEST="$2"
    shift # past argument
    ;;
    -r|--run)
    RUN="$2"
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

# kick off tcpdump for each iface, collect PIDs
suffix=1
for i in `seq 1 $SWITCHES`;
do
  for j in `seq 1 $IFACES`;
  do
    fname=t${TEST}"/t"${TEST}"_s"${i}"_eth"${j}"_run_"${RUN}".dump"
    tcpdump -i s$i"-eth"$j -n -s 100 -w $fname &
    var="PID_$suffix"
    declare "$var"=$!
    ((suffix++))
  done
done

# pause for keypress
read -n 1 -s

# kill tcpdump processes one at a time for clean output
suffix=1
for i in `seq 1 $SWITCHES`;
do
  for j in `seq $IFACES $IFACES`;
  do
    echo s$i"-eth"$j
    var="PID_$suffix"
    kill -15 ${!var}
    sleep 0.25
    ((suffix++))
  done
done
