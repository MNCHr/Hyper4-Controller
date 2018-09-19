#!/bin/bash

macs=( "00:04:00:00:00:01"
       "00:04:00:00:00:02"
       "00:04:00:00:00:03" 
       "00:04:00:00:00:04"
       "00:04:00:00:00:05"
       "00:04:00:00:00:06")

hnames=( "node-5"
         "node-6"
         "node-7" 
         "node-8"
         "node-9"
         "node-10" )

ips=( "10.10.5.1/16"
      "10.10.6.1/16"
      "10.10.7.1/16" 
      "10.10.8.1/16"
      "10.10.9.1/16"
      "10.10.10.1/16" )

hname="$(hostname | tr "." " " | awk '{print $1}')"

for i in `seq 0 5`; do
  if [ "$hname" == ${hnames[$i]} ]
  then
    ip=${ips[$i]}
    mac=${macs[$i]}
    break
  fi
done

while read x
  do
    ipaddr="$(echo $x | awk '{print $4}')"
    if [ "$ipaddr" == "$ip" ]
    then
      iface="$(echo $x | awk '{print $2}')"
      sudo ifconfig $iface down
      sudo ifconfig $iface hw ether $mac
      sudo ifconfig $iface up
      echo "updated MAC for $ipaddr to $mac"
      break
    fi
done <<< "$(ip -o -4 addr show)"
