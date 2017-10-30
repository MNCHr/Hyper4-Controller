#!/bin/bash

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"

ttyecho -n $MININET ./run.sh --commands hp4commands.txt --scenario chain --topo ~/hp4-ctrl/tests/t05/topo.txt

ttyecho -n $CONTROLLER ./controller --debug

# pause for keypress
echo "Next: create/provision 'jupiter' slice with lease to 'alpha' physical device"
read -n 1 -s

ttyecho -n $ADMIN ./client --debug --startup tests/t05/t05_admin_1 admin

echo "Next: create and configure L2 switch virtual device"
read -n 1 -s

ttyecho -n $SLICEMGR ./client --debug --startup tests/t05/t05_jupiter_1 jupiter

echo "Next: pairpings"
read -n 1 -s

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_pairpings

#echo "Next: expand topology"
echo "Next: update topology"
read -n 1 -s

#ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_addnodes
ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_changenodes

echo "Next: provision 'jupiter' with lease to 'bravo' physical device"
read -n 1 -s

ttyecho -n $ADMIN source tests/t05/t05_admin_2

echo "Next: create and configure L2 switch vdev for bravo"
read -n 1 -s

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_2

echo "Observe: pings between subnets don't work (no L3 router function)"
read -n 1 -s

ttyecho -n $MININET h1 ping h4 -c 1 -W 1 &
sleep 2
ttyecho -n $MININET h2 ping h5 -c 1 -W 1 &
sleep 2
ttyecho -n $MININET h3 ping h6 -c 1 -W 1 &

echo "Next: xterm h1 h2 h3 h4 h5 h6"
read -n 1 -s
#ttyecho -n $MININET "h1 xterm -hold -e \"bash -c \"tty > /tmp/pts_h1; exec bash\"\" &"
#ttyecho -n $MININET h1 xterm -e "bash -c \"tty > /tmp/pts_h1; exec bash\"" \&
#echo "press key to continue"
#read -n 1 -s
#ttyecho -n $MININET h2 xterm -e "bash -c \"tty > /tmp/pts_h2; exec bash\"" \&
echo "Next: manually start iperf h1 -> h2"
read -n 1 -s
echo "Next: manually start pings h3 -> h6: ping 10.2.0.106"
read -n 1 -s
#H1="$(cat /tmp/pts_h1)"
#H2="$(cat /tmp/pts_h2)"
#ttyecho -n $H2 python -m SimpleHTTPServer
#echo "press key to continue"
#read -n 1 -s
#ttyecho -n $H1 wget http://10.0.0.2:8000/hp4.json -O file.test --limit-rate=10k

#ttyecho -n $H1 ping 10.0.0.2

echo "Next: add L3 router to alpha and bravo"
read -n 1 -s

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_3

#ttyecho -n $MININET h1 ping h4 -c 1 -W 1 &
#sleep 2
#ttyecho -n $MININET h2 ping h5 -c 1 -W 1 &
#sleep 2
#ttyecho -n $MININET h3 ping h6 -c 1 -W 1 &
