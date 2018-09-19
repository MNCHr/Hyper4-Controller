#!/bin/bash

controllerpid="$(pgrep -f "hp4controller.controller")"

if [ -n "$controllerpid" ]
then
  sudo kill -SIGINT $controllerpid
else
  echo "could not find pid"
fi
