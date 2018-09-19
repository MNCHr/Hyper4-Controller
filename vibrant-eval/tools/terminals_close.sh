#!/bin/bash

pids=" $(pidof gnome-terminal) "

if [ "$pids" = "  " ]; then
    echo "There is no program named '$0' opened at the moment."
    exit 1
fi

wmctrl -lp | while read identity desktop_number PID window_title; do
    if [ "${pids/ $PID }" != "$pids" ]; then
        wmctrl -ic $identity
    fi
done
