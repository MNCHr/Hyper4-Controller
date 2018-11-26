#!/bin/bash

source ./ssh_vals.sh

ssh -oStrictHostKeyChecking=no -p 22 $user@pc$1.emulab.net
