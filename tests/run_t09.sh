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
echo start tcpdump $(date) > t09/t09r$RUN
echo

echo "Next: xterms for h1, h2, h3, h5, h6" 
$pause

ttyecho -n $MININET xterm h2
echo time h2 kicked off:
date
echo start h2 $(date) >> t09/t09r$RUN
sleep 1
wmctrl -r "Node: h2" -e 0,1434,0,-1,-1

ttyecho -n $MININET xterm h3
echo start h3 $(date) >> t09/t09r$RUN
sleep 1
wmctrl -r "Node: h3" -e 0,560,418,-1,-1

ttyecho -n $MININET xterm h1
echo start h1 $(date) >> t09/t09r$RUN
sleep 1
wmctrl -r "Node: h1" -e 0,0,418,-1,-1

ttyecho -n $MININET xterm h6
echo start h6 $(date) >> t09/t09r$RUN
sleep 1
wmctrl -r "Node: h6" -e 0,560,782,-1,-1

ttyecho -n $MININET xterm h5
echo time h5 kicked off:
date
echo start h5 $(date) >> t09/t09r$RUN
echo
sleep 1
wmctrl -r "Node: h5" -e 0,0,782,-1,-1

H1="$(cat /tmp/pts_h1)"
H2="$(cat /tmp/pts_h2)"
H3="$(cat /tmp/pts_h3)"
H5="$(cat /tmp/pts_h5)"
H6="$(cat /tmp/pts_h6)"

echo "Next: slice 1 enable VIBRANT protection"
$pause

ttyecho -n $SLICEMGR source tests/t09/t09_slice1_step2
date
echo start vib $(date) >> t09/t09r$RUN
echo

echo "Mark completion of VIBRANT install"
$pause
date

echo "Next: slice 1 start rotating keys"
$pause

ttyecho -n $SLICEMGR source tests/t09/t09_slice1_step3
date
echo start rotation $(date) >> t09/t09r$RUN
echo

echo "Mark completion of key rotation"
$pause
date
echo

echo "Terminate evaluation"
$pause
date

ttyecho -n $SLICEMGR EOF
ttyecho -n $SLICEMGR2 EOF
ttyecho -n $ADMIN EOF

sleep 1
echo "--terminate xterm processes"
sudo kill -s SIGINT "$(ps -ft $H2 | grep "10.1.0.104" | awk '{print $2}')"
sudo kill -s SIGINT "$(ps -ft $H5 | grep "iperf3" | awk '{print $2}')"
sudo kill -s SIGINT "$(ps -ft $H1 | grep "iperf3" | awk '{print $2}')"
sudo kill -s SIGINT "$(ps -ft $H6 | grep "iperf3" | awk '{print $2}')"
sudo kill -s SIGINT "$(ps -ft $H3 | grep "iperf3" | awk '{print $2}')"
date
echo stop xterms $(date) >> t09/t09r$RUN

sleep 1
echo "--terminate tcpdump"
ttyecho $EVALUATOR k

sleep 1
echo "--terminate controller"
sudo kill -s SIGINT "$(ps -ft $CONTROLLER | grep "hp4controller.controller" | awk '{print $2}')"

echo "--terminate mininet"
$pause
ttyecho -n $MININET exit

mv ~/hp4-src/hp4/t09h1iperf t09/t09h1iperf_r$RUN
mv ~/hp4-src/hp4/t09h5iperf t09/t09h5iperf_r$RUN
