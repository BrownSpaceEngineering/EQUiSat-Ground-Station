#!/usr/bin/env bash
# startup command for groundstation
# used in system service
here=`dirname "${BASH_SOURCE[0]}"`
cd $here
sudo -u pi python groundstation.py $@
