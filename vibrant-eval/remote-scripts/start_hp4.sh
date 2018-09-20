#!/bin/bash

cd /opt
script_path=/opt/hp4-ctrl/vibrant-eval/remote-scripts

# get and configure interfaces
hname="$(hostname | tr "." " " | awk '{print $1}')"

if [ "$hname" == "node-0" ]
then
  sudo $script_path/s0_get_ifaces.sh
elif [ "$hname" == "node-1" ]
then
  sudo $script_path/s1_get_ifaces.sh
elif [ "$hname" == "node-2" ]
then
  sudo $script_path/s2_get_ifaces.sh
elif [ "$hname" == "node-3" ]
then
  sudo $script_path/s3_get_ifaces.sh
elif [ "$hname" == "node-4" ]
then
  sudo $script_path/s4_get_ifaces.sh
fi

# start simple switch with hp4
ifacescommand=( sudo $script_path/iface_setup.sh )
hp4command=( sudo nohup /opt/bmv2/targets/simple_switch/simple_switch )

ifaces=(iface0 iface1 iface2 iface3 iface4)

for i in `seq 0 4`; do
  if [ -s ${ifaces[$i]} ]
  then
    ifacescommand+=( "$(cat ${ifaces[$i]})" )
    hp4command+=( -i "$i@$(cat ${ifaces[$i]})" )
  fi
done

echo "${ifacescommand[@]}"
"${ifacescommand[@]}"

hp4command+=( /opt/hp4-src/hp4/hp4.json )

echo "${hp4command[@]}"
"${hp4command[@]}" 2> /dev/null &
sleep 5
sudo sh -c 'nohup $script_path/prep_hp4.sh > prep_hp4.out 2> /dev/null &'
