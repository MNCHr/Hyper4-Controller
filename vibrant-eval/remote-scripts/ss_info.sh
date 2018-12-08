#!/bin/bash

res=( $(pgrep -f -a "simple_switch/simple_switch") )

if [ ${#res[@]} -eq 0 ]; then    
  echo "simple_switch not running"
else
  i=0
  declare -a ifaces
  nanolog=''
  json=''
  while [[ $i -lt ${#res[@]} ]]
  do
    case ${res[$i]} in
      -i)
      ifaces+=(${res[$i+1]})
      ;;
      --nanolog)
      nanolog=${res[$i+1]}
      ;;
      *".json"*)
      json=${res[$i]}
      ;;
      *)
            # unknown option
      ;;
    esac
    ((i++))
  done
  echo "simple_switch: $json"
  echo " ifaces: ${ifaces[@]}"
  echo " nanolog: $nanolog"
fi
