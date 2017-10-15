#!/bin/bash

MININET=/dev/pts/1
CONTROLLER=/dev/pts/2
ADMIN=/dev/pts/5
BMV2_CLI=/dev/pts/7
SLICEMGR=/dev/pts/12
TEST=/dev/pts/13

ttyecho -n $MININET ./run.sh --commands hp4commands.txt --topo ~/hp4-ctrl/tests/t02/topo.txt

ttyecho -n $CONTROLLER ./controller --debug

echo "Next: split subnet / change addresses"
read -n 1 -s

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t02/t02_mininet

echo "Next: create/provision 'jupiter' slice with lease to 'alpha' physical device"
read -n 1 -s

ttyecho -n $ADMIN ./client --debug --startup tests/t02/t02_admin admin

echo "Next: create and configure L3 router virtual devices"
read -n 1 -s

ttyecho -n $SLICEMGR ./client --debug --startup tests/t02/t02_jupiter jupiter

echo "Next: pairpings"
read -n 1 -s

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t02/t02_pairpings
