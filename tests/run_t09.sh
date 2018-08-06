#!/bin/bash

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"
SLICEMGR2="$(cat /tmp/pts_slice_manager2)"

ttyecho -n $MININET ./run.sh --commands hp4commands.txt --scenario chain --topo ~/hp4-ctrl/tests/t09/topo.txt

ttyecho -n $CONTROLLER ./controller --debug

# pause for keypress
echo "Next: create/provision slice1 with lease to s1, s2, and s3, slice2 w/ lease to s1, s4, and s5"
read -n 1 -s

ttyecho -n $ADMIN ./client --debug --startup tests/t09/t09_admin admin

echo "Next: create and configure vdevs for slice 1"
read -n 1 -s

ttyecho -n $SLICEMGR ./vibclient --debug --startup tests/t09/t09_slice1_step1 slice1

echo "Next: create and configure vdevs for slice 2"
read -n 1 -s

ttyecho -n $SLICEMGR2 ./client --debug --startup tests/t09/t09_slice2_step1 slice2

echo "Next: slice 1 enable VIBRANT protection"
read -n 1 -s

ttyecho -n $SLICEMGR source tests/t09/t09_slice1_step2
