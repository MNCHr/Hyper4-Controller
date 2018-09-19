#!/bin/bash

iface0=""
iface1=""
iface2=""

#command="sudo /opt/bmv2/targets/simple_switch/simple_switch "

while read x
  do
   ipaddr="$(echo $x | awk '{print $4}')"
   if [ "$ipaddr" == "10.10.2.1/16" ]
   then
     iface0="$(echo $x | awk '{print $2}')"
   elif [ "$ipaddr" == "10.10.7.2/16" ]
   then
     iface1="$(echo $x | awk '{print $2}')"
   elif [ "$ipaddr" == "10.10.8.2/16" ]
   then
     iface2="$(echo $x | awk '{print $2}')"
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
if [ -n "$iface2" ]
then
  sudo echo $iface2 > iface2
fi
