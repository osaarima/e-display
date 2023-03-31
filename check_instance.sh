#!/bin/bash

stat_str="$(ps aux | grep -e display_continuous.py | grep -v grep)"
echo $stat_str

if [ "$stat_str" == "" ]; then
    echo "Restarting display_continuous.py instance"
    /home/piirakka/e-display/display_continuous.py -r &
fi
