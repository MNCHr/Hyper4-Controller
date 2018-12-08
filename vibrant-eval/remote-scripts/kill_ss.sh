#!/bin/bash

sspid="$(pgrep -f "/simple_switch/simple_switch")"

if [ -n "$sspid" ]
then
  sudo kill $sspid
else
  echo "could not find pid"
fi
