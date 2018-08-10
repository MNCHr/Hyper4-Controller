#!/bin/bash

RUN=$1

echo Test t09 run $RUN...

pause="read -n 1 -s"

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"
SLICEMGR2="$(cat /tmp/pts_slice_manager2)"
EVALUATOR="$(cat /tmp/pts_evaluator)"

ttyecho -n $MININET ./run.sh --commands hp4commands.txt --scenario chain --topo ~/hp4-ctrl/tests/t09/topo.txt

ttyecho -n $CONTROLLER ./controller --debug

echo "Next: change MTU for all interfaces belonging to slice1"
$pause

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t09/change_mtu

echo "Next: create/provision slice1 with lease to s1, s2, and s3, slice2 w/ lease to s1, s4, and s5"
$pause

ttyecho -n $ADMIN ./client --debug --startup tests/t09/t09_admin admin

echo "Next: create and configure vdevs for slice 1"
$pause

ttyecho -n $SLICEMGR ./vibclient --debug --startup tests/t09/t09_slice1_step1 slice1

echo "Next: create and configure vdevs for slice 2"
$pause

ttyecho -n $SLICEMGR2 ./client --debug --startup tests/t09/t09_slice2_step1 slice2

echo "NEXT: tcpdump"
ttyecho -n $EVALUATOR sudo ./test_tcpdump.sh -t 09 -r $RUN -s 1
date
echo

echo "Next: xterms for h1, h2, h3, h5, h6" 
$pause

ttyecho -n $MININET xterm h2
echo time h1 kicked off:
date
sleep 1
wmctrl -r "Node: h2" -e 0,1434,0,-1,-1

ttyecho -n $MININET xterm h3
sleep 1
wmctrl -r "Node: h3" -e 0,560,418,-1,-1

ttyecho -n $MININET xterm h1
sleep 1
wmctrl -r "Node: h1" -e 0,0,418,-1,-1

ttyecho -n $MININET xterm h6
sleep 1
wmctrl -r "Node: h6" -e 0,560,782,-1,-1

ttyecho -n $MININET xterm h5
echo time h5 kicked off:
date
echo
sleep 1
wmctrl -r "Node: h5" -e 0,0,782,-1,-1

echo "Next: slice 1 enable VIBRANT protection"
$pause

ttyecho -n $SLICEMGR source tests/t09/t09_slice1_step2
date
echo

echo "Next: slice 1 start rotating keys"
$pause

ttyecho -n $SLICEMGR source tests/t09/t09_slice1_step3
date
echo
