#!/bin/bash

hp4pid="$(pgrep -f "/simple_switch/simple_switch")"

if [ -n "$hp4pid" ]
then
  sudo kill $hp4pid
else
  echo "could not find pid"
fi
