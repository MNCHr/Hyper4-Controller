#!/bin/bash

cloc ./controller.py ./errors.py ./p4command.py ./clients/client.py \
     ./compilers/compiler.py ./compilers/p4_hp4.py ./devices/device.py \
     ./leases/lease.py ./virtualdevice/interpret.py ./virtualdevice/p4rule.py \
     ./virtualdevice/virtualdevice.py --force-lang="python"
