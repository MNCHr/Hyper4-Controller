#!/bin/bash

if [[ $# -gt 0 ]]
then
  echo "configuring controller for cloudlab execution"
  printf "#!/bin/bash\n\n" > tests/ssh_vals.sh
  printf "user=$1\n" >> tests/ssh_vals.sh
  echo "/opt/hp4-src/hp4/hp4.json" > hp4controller/hp4_json_path
  if [[ $# -gt 1 ]]
  then
    printf "nodes=( $2 $3 $4 $5 $6 $7 $8 $9 ${10} ${11} ${12} )\n" >> tests/ssh_vals.sh
    shift
    for i in "$@"
    do
      ssh-keygen -f "/home/ubuntu/.ssh/known_hosts" -R pc$i.emulab.net
    done
  fi
else
  echo "configuring controller for local (e.g., mininet) execution"
  rm -f hp4controller/hp4_json_path
fi
