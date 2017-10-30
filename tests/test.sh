#!/bin/bash

declare -a windows
i=0

while read -r a; do \
  windows[$i]=$a;
  windows[$i]=$((${windows[$i]} + 0));
  i=$((i+1));
done < <(who | awk '{ print $2 }' | grep pts/ | awk 'BEGIN { FS="/"; } { print $2; }')

IFS=$'\n' sorted=($(sort <<<"${windows[*]}"))
unset IFS

echo ${sorted[*]}
