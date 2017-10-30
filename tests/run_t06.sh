#!/bin/bash

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"

ttyecho -n $MININET ./run.sh --commands hp4commands.txt --scenario chain --topo ~/hp4-ctrl/tests/t05/topo.txt

ttyecho -n $CONTROLLER ./controller --debug

# pause for keypress
echo "Next: create/provision 'jupiter' slice with lease to alpha and bravo"
read -n 1 -s

ttyecho -n $ADMIN ./client --debug --startup tests/t06/t06_admin_1 admin

echo "Next: update topology"
read -n 1 -s

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t06/t06_changenodes

echo "Next: create and configure L3 routers"
read -n 1 -s

ttyecho -n $SLICEMGR ./client --debug --startup tests/t06/t06_jupiter_1 jupiter
