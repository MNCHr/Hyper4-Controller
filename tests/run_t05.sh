#!/bin/bash

pause="read -n 1 -s"

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"

ttyecho -n $MININET ./run.sh --commands hp4commands.txt --scenario chain --topo ~/hp4-ctrl/tests/t05/topo.txt

ttyecho -n $CONTROLLER ./controller --debug

# pause for keypress
echo "Next: create/provision 'jupiter' slice with leases to alpha and bravo"
$pause

ttyecho -n $ADMIN ./client --debug --startup tests/t05/t05_admin_1 admin

echo "Next: create and configure L2 switch virtual devices"
$pause

ttyecho -n $SLICEMGR ./client --debug --startup tests/t05/t05_jupiter_1 jupiter

echo "Next: update topology"
$pause

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_changenodes

echo "Next: try pings. Expected connectivity domains: (h1 h2 h3), (h6 h7)"
$pause

echo "Next: manual xterm h1 h2 h3 h4 h5 h6"
$pause

echo "Next: manually start iperf h1 -> h2"
$pause

echo "Next: manually start pings h2 -> h6: ping 10.2.0.106"
$pause
#H1="$(cat /tmp/pts_h1)"
#H2="$(cat /tmp/pts_h2)"
#ttyecho -n $H2 python -m SimpleHTTPServer
#echo "press key to continue"
#$pause
#ttyecho -n $H1 wget http://10.0.0.2:8000/hp4.json -O file.test --limit-rate=10k

#ttyecho -n $H1 ping 10.0.0.2

echo "Next: add L3 router to alpha and bravo"
$pause

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_2

echo "Next: try pings. Expected connectivity domains: (h1 h2 h3 h6 h7)"
$pause

echo "Next: remove routers"
$pause

ttyecho -n $SLICEMGR lease_remove alpha alpha_l3
ttyecho -n $SLICEMGR lease_remove bravo bravo_l3

echo "Next: try pings. Expected connectivity domains: (h1 h2 h3), (h6 h7)"
$pause

echo "Next: add arp proxy, remove gateways from host arp caches, change netmask to /8"
$pause

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_3
ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_changenodes2

echo "Next: try pings.  Expected connectivity domains: (h1 h2 h3 h6 h7)"
$pause
