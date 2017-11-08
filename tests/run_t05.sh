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

echo "Next: manual xterm h1 h2 h3 h6 h7, start test_tcpdump.sh, h1 ping -f 10.1.0.102 / iperf"
$pause

echo "Next: create and configure L2 switch virtual devices"
#$pause
sleep 5

ttyecho -n $SLICEMGR ./client --debug --startup tests/t05/t05_jupiter_1 jupiter
# t = 5

echo "Next: update topology"
#$pause
sleep 5

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_changenodes
# t = 10

#echo "Next: try pings. Expected connectivity domains: (h1 h2 h3), (h6 h7)"
#$pause

echo "Next: manually start pings h3 -> h6: ping 10.2.0.106"
#$pause
echo 5; sleep 1; echo 4; sleep 1; echo 3; sleep 1; echo 2; sleep 1; echo 1; sleep 1
echo "GO"

#H1="$(cat /tmp/pts_h1)"
#H2="$(cat /tmp/pts_h2)"
#ttyecho -n $H2 python -m SimpleHTTPServer
#echo "press key to continue"
#$pause
#ttyecho -n $H1 wget http://10.0.0.2:8000/hp4.json -O file.test --limit-rate=10k

#ttyecho -n $H1 ping 10.0.0.2

echo "Next: add L3 router to alpha and bravo"
#$pause
sleep 5

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_2
# t = 20

#echo "Next: try pings. Expected connectivity domains: (h1 h2 h3 h6 h7)"
#$pause

echo "Next: remove routers"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_remove alpha alpha_l3
ttyecho -n $SLICEMGR lease_remove bravo bravo_l3
# t = 25

echo "Next: stop pings h3 -> h6"
echo 5; sleep 1; echo 4; sleep 1; echo 3; sleep 1; echo 2; sleep 1; echo 1; sleep 1
echo "GO"

#echo "Next: try pings. Expected connectivity domains: (h1 h2 h3), (h6 h7)"
#$pause

echo "Next: add arp proxy, remove gateways from host arp caches, change netmask to /8"
#$pause
sleep 5

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_3
ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_changenodes2
# t = 35

#echo "Next: try pings.  Expected connectivity domains: (h1 h2 h3 h6 h7)"
#$pause

echo "Next: remove switch"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_remove alpha alpha_l2
ttyecho -n $SLICEMGR lease_remove bravo bravo_l2
# t = 40

echo "Next: add switch to end of chain"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_insert alpha alpha_l2 1 econd
ttyecho -n $SLICEMGR lease_insert bravo bravo_l2 1 econd
# t = 45

#echo "Next: try pings.  Expected connectivity domain: (h1 h2 h3 h6 h7)"
#$pause

echo "Next: restore previous host network configurations (e.g., netmask back to /24)"
#$pause
sleep 5

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_changenodes3
# t = 50

echo "Next: add router to end of chain"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_insert alpha alpha_l3 2 etrue
ttyecho -n $SLICEMGR lease_insert bravo bravo_l3 2 etrue
# t = 55

#echo "Next: try pings.  Expected connectivity domain: (h1 h2 h3 h6 h7)"
#$pause

echo "Next: add firewall to end of alpha chain"
#$pause
sleep 5

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_4
# t = 60

#echo "Next: try iperf between two hosts; ports 4444, 5555 blocked; other not blocked"
#$pause

echo "Next: remove routers"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_remove alpha alpha_l3
ttyecho -n $SLICEMGR lease_remove bravo bravo_l3
# t = 65

#echo "Next: try h1 <-> h2, should still work"
#$pause

echo "Next: remove arp proxies from alpha and bravo"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_remove alpha alpha_ap
ttyecho -n $SLICEMGR lease_remove bravo bravo_ap
# t = 70

#echo "Next: try h1 <-> h2, should still work"
#$pause

echo "Next: remove switch"
#$pause
sleep 5

ttyecho -n $SLICEMGR lease_remove alpha alpha_l2
ttyecho -n $SLICEMGR lease_remove bravo bravo_l2
# t = 75
