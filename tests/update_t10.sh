#!/bin/bash

t10path="tests/t10"

source $t10path/infr_manifest.sh

sudo cp $t10path/t10_admin_orig $t10path/t10_admin

sudo sed -i "s/s1 <ip> <port>/s1 $s1_ip 9090/g" $t10path/t10_admin
sudo sed -i "s/s2 <ip> <port>/s2 $s2_ip 9090/g" $t10path/t10_admin
sudo sed -i "s/s3 <ip> <port>/s3 $s3_ip 9090/g" $t10path/t10_admin
sudo sed -i "s/s4 <ip> <port>/s4 $s4_ip 9090/g" $t10path/t10_admin
