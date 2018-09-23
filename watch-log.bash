#!/usr/bin/env bash
num_lines=10
if [ $1 ];
then
	num_lines=$1
fi
journalctl -u equistation.service --no-pager -n $num_lines -f

