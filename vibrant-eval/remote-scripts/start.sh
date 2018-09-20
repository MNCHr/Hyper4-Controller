#!/bin/bash

cd /opt/hp4-ctrl
sudo git pull

hname="$(hostname | tr "." " " | awk '{print $1}')"

if [ "$hname" == "node-0" ] || 
   [ "$hname" == "node-1" ] || 
   [ "$hname" == "node-2" ] ||
   [ "$hname" == "node-3" ] ||
   [ "$hname" == "node-4" ]
then
  /opt/hp4-ctrl/vibrant-eval/remote-scripts/start_hp4.sh
elif [ "$hname" == "node-5" ] ||
     [ "$hname" == "node-6" ] ||
     [ "$hname" == "node-7" ] ||
     [ "$hname" == "node-8" ] ||
     [ "$hname" == "node-9" ] ||
     [ "$hname" == "node-10" ]
then
  /opt/hp4-ctrl/vibrant-eval/remote-scripts/h_config.sh
fi
