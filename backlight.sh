#!/usr/bin/env bash

set -e

BACKLIGHT=/sys/class/backlight/intel_backlight/brightness

[ "$1" = '+' ] || [ "$1" = '-' ] || exit 1

/usr/bin/echo $(/usr/bin/awk '{$1=$1'"$1"'1}1' $BACKLIGHT) >$BACKLIGHT
