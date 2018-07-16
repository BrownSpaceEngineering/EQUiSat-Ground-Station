#!/usr/bin/env bash
if [ $1 ];
then
	watch "journalctl -u equistation.service --no-pager | tail -n $1"
else
	watch "journalctl -u equistation.service --no-pager | tail -n 10"
fi
