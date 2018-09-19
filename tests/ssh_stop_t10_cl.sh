#!/bin/bash

MININET="$(cat /tmp/pts_mininet)"
CONTROLLER="$(cat /tmp/pts_controller)"
ADMIN="$(cat /tmp/pts_admin)"
BMV2_CLI="$(cat /tmp/pts_bmv2_cli)"
SLICEMGR="$(cat /tmp/pts_slice_manager)"
SLICEMGR2="$(cat /tmp/pts_slice_manager2)"
EVALUATOR="$(cat /tmp/pts_evaluator)"

ttyecho -n $MININET exit
ttyecho -n $CONTROLLER exit
ttyecho -n $ADMIN exit
ttyecho -n $SLICEMGR exit; echo slicemgr
ttyecho -n $SLICEMGR2 exit; echo slicemgr2
ttyecho -n $EVALUATOR exit; echo evaluator
