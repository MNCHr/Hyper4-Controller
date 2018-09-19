#!/bin/bash

iface0=""
iface1=""

#command="sudo /opt/bmv2/targets/simple_switch/simple_switch "

while read x
  do
   ipaddr="$(echo $x | awk '{print $4}')"
   if [ "$ipaddr" == "10.10.4.1/16" ]
   then
     iface0="$(echo $x | awk '{print $2}')"
   elif [ "$ipaddr" == "10.10.10.2/16" ]
   then
     iface1="$(echo $x | awk '{print $2}')"
   fi
done <<< "$(ip -o -4 addr show)"

if [ -n "$iface0" ]
then
  sudo echo $iface0 > iface0
fi
if [ -n "$iface1" ]
then
  sudo echo $iface1 > iface1
fi
