#!/usr/bin/env bash
watch "journalctl -u equistation.service --no-pager | tail -n 20"