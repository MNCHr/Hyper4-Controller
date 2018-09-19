#!/bin/bash

iface1=""
iface2=""
iface3=""
iface4=""

#command="sudo /opt/bmv2/targets/simple_switch/simple_switch "

while read x
  do
   ipaddr="$(echo $x | awk '{print $4}')"
   if [ "$ipaddr" == "10.10.1.2/16" ]
   then
     iface1="$(echo $x | awk '{print $2}')"
   elif [ "$ipaddr" == "10.10.2.2/16" ]
   then
     iface2="$(echo $x | awk '{print $2}')"
   elif [ "$ipaddr" == "10.10.3.2/16" ]
   then
     iface3="$(echo $x | awk '{print $2}')"
   elif [ "$ipaddr" == "10.10.4.2/16" ]
   then
     iface4="$(echo $x | awk '{print $2}')"
   fi
done <<< "$(ip -o -4 addr show)"

if [ -n "$iface1" ]
then
  sudo echo $iface1 > iface1
fi
if [ -n "$iface2" ]
then
  sudo echo $iface2 > iface2
fi
if [ -n "$iface3" ]
then
  sudo echo $iface3 > iface3
fi
if [ -n "$iface4" ]
then
  sudo echo $iface4 > iface4
fi
