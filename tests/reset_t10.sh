#!/bin/bash

pause="read -n 1 -s"

source ssh_vals.sh

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"
SLICEMGR2="$(cat /tmp/pts_slice_manager2)"
EVALUATOR="$(cat /tmp/pts_evaluator)"

echo "Manually kill controller and tcpdump"
$pause

for i in `seq 0 4`; do
  echo "Resetting pc${nodes[$i]}..."
  ssh -oStrictHostKeyChecking=no -tt -p 22 $user@pc${nodes[$i]}.emulab.net <<zzzLIMITzzz
  sudo /opt/rs/reset.sh > /dev/null 2>&1 &
  exit
zzzLIMITzzz
  echo "...done."
done

ttyecho -n $ADMIN EOF
ttyecho -n $SLICEMGR EOF
ttyecho -n $SLICEMGR2 EOF

ttyecho -n $MININET exit
ttyecho -n $CONTROLLER exit
ttyecho -n $ADMIN exit
ttyecho -n $SLICEMGR exit
ttyecho -n $SLICEMGR2 exit
ttyecho -n $EVALUATOR exit
