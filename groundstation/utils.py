#!/usr/bin/python
# Various common utilities
import datetime

def dtime_within(dtime1, dtime2, window_s):
    """ Returns whether the two datetimes are within window_s seconds of eachother """
    dtime1_secs = (dtime1-datetime.datetime(1970,1,1)).total_seconds()
    dtime2_secs = (dtime2-datetime.datetime(1970,1,1)).total_seconds()
    return abs(dtime1_secs - dtime2_secs) <= window_s

def dtime_after(maybe_after, before=None):
    """ Returns whether the datetime "before" is after "maybe_after"
        "before" defaults to now """
    if before == None:
        before = datetime.datetime.now()
    return (maybe_after - before).total_seconds() > 0
