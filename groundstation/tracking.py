#!/usr/bin/python
# Utilities for tracking satellite passes
import ephem
import datetime
import math
import logging
import requests
from collections import OrderedDict

import station_config as station

DEFAULT_TLE_FNAME = "tle.txt"
TLE_API_PREFIX = "https://www.celestrak.com/cgi-bin/TLE.pl?CATNR=%s"

class SatTracker:
    def __init__(self, norad_id, tle_fname=DEFAULT_TLE_FNAME):
        self.norad_id = str(norad_id)
        self.tle_fname = tle_fname
        self.tle = None
        self.load_tle() # populates self.tle

    def get_next_pass(self):
        """ Returns a dictionary with the rise and set time and azimuth as well as
        the max alt (transmit) time and elevation, or None if TLEs are not known """
        if len(self.tle) != 3:
            return None

        try:
            sat = ephem.readtle(self.tle[0], self.tle[1], self.tle[2])
            obs = ephem.Observer()
            obs.lon = station.station_lon
            obs.lat = station.station_lat
            obs.elevation = station.station_alt
            passData = obs.next_pass(sat)
            # next_pass returns a six-element tuple giving:
            # (dates are in UTC)
            # 0  Rise time
            # 1  Rise azimuth
            # 2  Maximum altitude time
            # 3  Maximum altitude
            # 4  Set time
            # 5  Set azimuth
            # date info: http://rhodesmill.org/pyephem/date
            # next_pass info:
            # https://github.com/brandon-rhodes/pyephem/blob/592ecff661adb9c5cbed7437a23d705555d7ce57/libastro-3.7.7/riset_cir.c#L17
            return OrderedDict([
                ('rise_time', passData[0].datetime()),
                ('rise_azimuth', math.degrees(passData[1])),
                ('max_alt_time', passData[2].datetime()),
                ('max_alt', math.degrees(passData[3])),
                ('set_time', passData[4].datetime()),
                ('set_azimuth', math.degrees(passData[5]))
            ])
        except ValueError as e: # thrown by ephem
            logging.error("tracking: error computing pass: %s" % e)
            return None

    # TLE handling adapted from https://github.com/tydlwav/GSW-Sat-Tracking work
    def load_tle(self):
        try:
            with open(self.tle_fname, 'r') as tle_file:
                tles = tle_file.read()
                self.tle = self.extract_tle(self.norad_id, tles)
        except IOError as e:
            logging.warn("tracking: TLE file not found, attempting to re-download (err: %s)" % e)
            # if the file's not found, we need to perform initial update
            self.update_tle()

    @staticmethod
    def extract_tle(norad_id, tle_data):
        """ Extracts the TLE set with the given string NORAD ID from the string list of TLEs,
            and returns a three-element string list of the satellite name and two lines of elements.
            Returns None if no TLEs for norad_id was found. """
        tle_list = tle_data.split("\n")
        for i in range(len(tle_list)):
            cur_line_split = tle_list[i].split(" ")
            if len(cur_line_split) < 2:
                continue
            if cur_line_split[1].strip() == norad_id + "U":
                # handle no satellite name
                sat_name = ""
                if i > 0:
                    sat_name = tle_list[i-1]
                # handle incomplete file
                if i > len(tle_list)-2:
                    return None
                else:
                    return [sat_name, tle_list[i], tle_list[i+1]]
        return None

    def update_tle(self):
        """ Update the TLE data from the remote Celestrack server. Returns if successful """
        req = requests.get(TLE_API_PREFIX % self.norad_id)
        if req.status_code != requests.codes.ok:
            return False
        tle_data = str(req.text.decode("utf8"))

        # clean text of HTML (unless it doesn't seem to be there)
        tle_data_list = tle_data.split("\n")
        if len(tle_data_list) == 22:
            tle_data_list = tle_data_list[13:16]
            tle_data = "\n".join(tle_data_list)

        # update memory cache
        self.tle = self.extract_tle(self.norad_id, tle_data)

        try:
            # update file cache
            with open(self.tle_fname, 'w') as tle_file:
                # Make file blank
                tle_file.truncate(0)
                tle_file.write(tle_data)
                return True
        except IOError as e:
            logging.error("tracking: error writing TLE file: %s" % e)
            return False

if __name__ == "__main__":
    import config
    st = SatTracker(config.SAT_CATALOG_NUMBER)
    st.update_tle()
    print(st.get_next_pass())
