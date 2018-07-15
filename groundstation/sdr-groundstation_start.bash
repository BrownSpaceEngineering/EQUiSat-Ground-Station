#!/usr/bin/env bash
# startup command for sdr groundstation
# used in system service
here=`dirname "${BASH_SOURCE[0]}"`
cd $here
sudo -u pi python sdr-groundstation.py $@
