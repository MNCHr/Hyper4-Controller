#!/bin/bash

cd /opt

hname="$(hostname | tr "." " " | awk '{print $1}')"

if [ "$hname" == "node-0" ] || 
   [ "$hname" == "node-1" ] || 
   [ "$hname" == "node-2" ] ||
   [ "$hname" == "node-3" ] ||
   [ "$hname" == "node-4" ]
then
  ./start_hp4.sh
elif [ "$hname" == "node-5" ] ||
     [ "$hname" == "node-6" ] ||
     [ "$hname" == "node-7" ] ||
     [ "$hname" == "node-8" ] ||
     [ "$hname" == "node-9" ] ||
     [ "$hname" == "node-10" ]
then
  ./h_config.sh
fi
