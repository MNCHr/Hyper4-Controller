#!/bin/bash

RUN=$1

echo Test t10 run $RUN...

pause="read -n 1 -s"

source ssh_vals.sh

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"
SLICEMGR2="$(cat /tmp/pts_slice_manager2)"
EVALUATOR="$(cat /tmp/pts_evaluator)"

# connect each window
ttyecho -n $MININET ssh -p 22 $user@pc${nodes[0]}.emulab.net
ttyecho -n $CONTROLLER ssh -p 22 $user@pc${nodes[0]}.emulab.net
ttyecho -n $ADMIN ssh -p 22 $user@pc${nodes[0]}.emulab.net
ttyecho -n $SLICEMGR ssh -p 22 $user@pc${nodes[0]}.emulab.net
ttyecho -n $SLICEMGR2 ssh -p 22 $user@pc${nodes[0]}.emulab.net
ttyecho -n $EVALUATOR ssh -p 22 $user@pc${nodes[0]}.emulab.net

echo "If necessary acknowledge SSH key update; next: launch controller"
$pause

ttyecho -n $MININET cd /opt
ttyecho -n $CONTROLLER cd /opt/hp4-ctrl
ttyecho -n $ADMIN cd /opt/hp4-ctrl
ttyecho -n $SLICEMGR cd /opt/hp4-ctrl
ttyecho -n $SLICEMGR2 cd /opt/hp4-ctrl

s1_ip="$(ssh -p 22 $user@pc${nodes[1]}.emulab.net "ifconfig eth0 | grep 'inet ' | tr ':' ' '" | awk '{print $3}' )"
echo s1@$s1_ip
s2_ip="$(ssh -p 22 $user@pc${nodes[2]}.emulab.net "ifconfig eth0 | grep 'inet ' | tr ':' ' '" | awk '{print $3}' )"
echo s2@$s2_ip
s3_ip="$(ssh -p 22 $user@pc${nodes[3]}.emulab.net "ifconfig eth0 | grep 'inet ' | tr ':' ' '" | awk '{print $3}' )"
echo s3@$s3_ip
s4_ip="$(ssh -p 22 $user@pc${nodes[4]}.emulab.net "ifconfig eth0 | grep 'inet ' | tr ':' ' '" | awk '{print $3}' )"
echo s4@$s4_ip

printf '#!/bin/bash\n' > infr_manifest.sh
printf "s1_ip=${s1_ip}\n" >> infr_manifest.sh
printf "s2_ip=${s2_ip}\n" >> infr_manifest.sh
printf "s3_ip=${s3_ip}\n" >> infr_manifest.sh
printf "s4_ip=${s4_ip}\n" >> infr_manifest.sh

scp infr_manifest.sh $user@pc${nodes[0]}.emulab.net:~/
ttyecho -n $CONTROLLER sudo cp /users/$user/infr_manifest.sh /opt/hp4-ctrl/tests/t10/
ttyecho -n $CONTROLLER sudo ./tests/update_t10.sh

ttyecho -n $CONTROLLER "sudo ./controller --debug | sudo tee -i controller.out"

ttyecho -n $ADMIN sudo cp /opt/hp4-src/hp4/hp4.json /opt/hp4-ctrl/tests/t10/node-0-hp4.json
scp $user@pc${nodes[1]}.emulab.net:/opt/hp4-src/hp4/hp4.json node-1-hp4.json
scp $user@pc${nodes[2]}.emulab.net:/opt/hp4-src/hp4/hp4.json node-2-hp4.json
scp $user@pc${nodes[3]}.emulab.net:/opt/hp4-src/hp4/hp4.json node-3-hp4.json
scp $user@pc${nodes[4]}.emulab.net:/opt/hp4-src/hp4/hp4.json node-4-hp4.json
scp node-1-hp4.json $user@pc${nodes[0]}.emulab.net:~/
ttyecho -n $ADMIN sudo cp /users/$user/node-1-hp4.json /opt/hp4-ctrl/tests/t10/node-1-hp4.json
scp node-2-hp4.json $user@pc${nodes[0]}.emulab.net:~/
ttyecho -n $ADMIN sudo cp /users/$user/node-2-hp4.json /opt/hp4-ctrl/tests/t10/node-2-hp4.json
scp node-3-hp4.json $user@pc${nodes[0]}.emulab.net:~/
ttyecho -n $ADMIN sudo cp /users/$user/node-3-hp4.json /opt/hp4-ctrl/tests/t10/node-3-hp4.json
scp node-4-hp4.json $user@pc${nodes[0]}.emulab.net:~/
ttyecho -n $ADMIN sudo cp /users/$user/node-4-hp4.json /opt/hp4-ctrl/tests/t10/node-4-hp4.json

echo "Next: create/provision slice1 with lease to s1, s2, and s3, slice2 w/ lease to s1, s4, and s5"
$pause

ttyecho -n $ADMIN sudo ./client --debug --startup tests/t10/t10_admin admin

echo "Next: create and configure vdevs for slice 1"
$pause

ttyecho -n $SLICEMGR sudo ./vibclient --enc_cmd_path tests/t10 --debug --startup tests/t10/t10_slice1_step1 slice1

echo "Next: create and configure vdevs for slice 2"
$pause

ttyecho -n $SLICEMGR2 sudo ./client --debug --startup tests/t10/t10_slice2_step1 slice2

echo "NEXT: tcpdump"
fname="t10_run_"${RUN}".dump"
ttyecho -n $EVALUATOR "sudo tcpdump -i \$(cat /opt/iface1) -n -s 100 -w $fname" &

date
echo start tcpdump $(date) > t10/t10r$RUN
echo

echo "Next: xterms for h1, h2, h3, h5, h6" 
$pause

xterm -title "Node: h2" -geometry 80x20+1434+0 &
sleep 1
xterm -title "Node: h3" -geometry 80x20+550+500 &
sleep 1
xterm -title "Node: h1" -geometry 80x20+0+500 &
sleep 1
xterm -title "Node: h6" -geometry 80x20+550+810 &
sleep 1
xterm -title "Node: h5" -geometry 80x20+0+810 &

echo "strategic pause..."
$pause

H1="$(cat /tmp/pts_h1)"
H2="$(cat /tmp/pts_h2)"
H3="$(cat /tmp/pts_h3)"
H5="$(cat /tmp/pts_h5)"
H6="$(cat /tmp/pts_h6)"

ttyecho -n $H1 ssh -p 22 $user@pc${nodes[5]}.emulab.net
ttyecho -n $H2 ssh -p 22 $user@pc${nodes[6]}.emulab.net
ttyecho -n $H3 ssh -p 22 $user@pc${nodes[7]}.emulab.net
ttyecho -n $H5 ssh -p 22 $user@pc${nodes[9]}.emulab.net
ttyecho -n $H6 ssh -p 22 $user@pc${nodes[10]}.emulab.net
echo "xterms should be up and connected; ack SSH key update if necessary"
$pause

H1ip="10.10.5.1"
H2ip="10.10.6.1"
H3ip="10.10.7.1"
H4ip="10.10.8.1"
H5ip="10.10.9.1"
H6ip="10.10.10.1"

#t9h2.sh
ttyecho -n $H2 ping $H4ip -i 0.2 -w 120
echo time h2 kicked off:
date
echo start h2 $(date) >> t10/t10r$RUN
sleep 1

#t9h3.sh
ttyecho -n $H3 iperf3 -s
echo start h3 $(date) >> t10/t10r$RUN
sleep 1

#t9h1.sh
ttyecho -n $H1 iperf3 -c $H3ip -t 120 --logfile /users/$user/t10h1iperf
echo start h1 $(date) >> t10/t10r$RUN
sleep 1

#t9h6.sh
ttyecho -n $H6 iperf3 -s
echo start h6 $(date) >> t10/t10r$RUN
sleep 1

#t9h5.sh
ttyecho -n $H5 iperf3 -c $H6ip -t 120 --logfile /users/$user/t10h5iperf
echo time h5 kicked off:
date
echo start h5 $(date) >> t10/t10r$RUN
echo
sleep 1

echo "Next: slice 1 enable VIBRANT protection"
$pause

ttyecho -n $SLICEMGR source tests/t10/t10_slice1_step2
date
echo start vib $(date) >> t10/t10r$RUN
echo

echo "Mark completion of VIBRANT install"
$pause
date

echo "Next: slice 1 start rotating keys"
$pause

ttyecho -n $SLICEMGR source tests/t10/t10_slice1_step3
date
echo start rotation $(date) >> t10/t10r$RUN
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
#sudo kill -s SIGINT "$(ps -ft $H2 | grep "10.1.0.104" | awk '{print $2}')"
$pause
ssh -p 22 $user@pc${nodes[6]}.emulab.net "kill -s SIGINT $(ps -ft | grep 10.10.6.1 | awk '{print $2}')"
$pause
#sudo kill -s SIGINT "$(ps -ft $H5 | grep "iperf3" | awk '{print $2}')"
#sudo kill -s SIGINT "$(ps -ft $H1 | grep "iperf3" | awk '{print $2}')"
#sudo kill -s SIGINT "$(ps -ft $H6 | grep "iperf3" | awk '{print $2}')"
#sudo kill -s SIGINT "$(ps -ft $H3 | grep "iperf3" | awk '{print $2}')"
date
echo stop xterms $(date) >> t10/t10r$RUN

sleep 1
echo "--terminate tcpdump"
ttyecho $EVALUATOR k

sleep 1
echo "--terminate controller"
sudo kill -s SIGINT "$(ps -ft $CONTROLLER | grep "hp4controller.controller" | awk '{print $2}')"

echo "--terminate mininet"
$pause
ttyecho -n $MININET exit

ttyecho -n $EVALUATOR sudo mv ~/t10h1iperf t10/t10h1iperf_r$RUN
ttyecho -n $EVALUATOR sudo mv ~/t10h5iperf t10/t10h5iperf_r$RUN
