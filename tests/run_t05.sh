#!/bin/bash

declare -a windows
i=0

while read -r a; do \
  windows[$i]='/dev/pts/'$a;
  i=$((i+1));
done < <(who | awk '{ print $2 }' | grep pts/ | awk 'BEGIN { FS="/"; } { print $2; }')

echo ${windows[*]}

MININET=${windows[0]}
CONTROLLER=${windows[1]}
ADMIN=${windows[2]}
BMV2_CLI=${windows[3]}
SLICEMGR=${windows[4]}
TEST=${windows[5]}

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

echo "Next: expand topology"
read -n 1 -s

ttyecho -n $MININET source /home/ubuntu/hp4-ctrl/tests/t05/t05_addnodes

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

echo "Next: add L3 router to alpha and bravo"
read -n 1 -s

ttyecho -n $SLICEMGR source tests/t05/t05_jupiter_3
