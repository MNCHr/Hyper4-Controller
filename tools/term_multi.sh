#!/bin/bash

cd /home/ubuntu/hp4-src/hp4
gnome-terminal --window-with-profile=mininet --geometry=80x20+0+0 --command="bash -c \"tty > /tmp/pts_mininet; exec bash\"" &
sleep 0.2
cd /home/ubuntu/hp4-ctrl
gnome-terminal --window-with-profile=controller --geometry=90x30+800+0 --command="bash -c \"tty > /tmp/pts_controller; exec bash\"" &
sleep 0.2
gnome-terminal --window-with-profile=admin --geometry=80x20+0+415 --command="bash -c \"tty > /tmp/pts_admin; exec bash\"" &
sleep 0.2
cd /home/ubuntu/hp4-src/hp4
gnome-terminal --window-with-profile=bmv2_CLI --geometry=80x20+0+805 --command="bash -c \"tty > /tmp/pts_bmv2_cli; exec bash\"" &
sleep 0.2
cd /home/ubuntu/hp4-ctrl
gnome-terminal --geometry=90x30+800+600 --command="bash -c \"tty > /tmp/pts_slice_manager; exec bash\"" &
sleep 0.2
cd /home/ubuntu/hp4-ctrl/tests
gnome-terminal --window-with-profile=tests --geometry=80x20+1200+400 &
sleep 0.2
cd /home/ubuntu/hp4-ctrl
gnome-terminal --geometry=90x30+1000+800 --command="bash -c \"tty > /tmp/pts_slice_manager_saturn; exec bash\"" &
