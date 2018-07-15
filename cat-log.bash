#!/usr/bin/env bash
if [ $1 ];
then
	journalctl -u equistation.service --no-pager | tail -n $1
else
	journalctl -u equistation.service --no-pager
fi
