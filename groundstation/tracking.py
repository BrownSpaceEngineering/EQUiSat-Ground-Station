#!/usr/bin/python
# Utilities for tracking satellite passes
# Good resource: https://brainwagon.org/2009/09/27/how-to-use-python-to-predict-satellite-locations/
import ephem
import datetime
import math
import logging
import requests
from collections import OrderedDict

import station_config as station

DEFAULT_TLE_FNAME = "tle.txt"
TLE_GET_ROUTE = "http://tracking.brownspace.org/api/tle" #"https://www.celestrak.com/cgi-bin/TLE.pl?CATNR=%s"

class SatTracker:
    def __init__(self, norad_id, tle_fname=DEFAULT_TLE_FNAME):
        self.norad_id = str(norad_id)
        self.tle_fname = tle_fname
        self.tle = None
        self.load_tle() # populates self.tle

    def get_next_pass(self, start=None):
        """ Returns a dictionary with the rise and set time and azimuth as well as
        the max alt (transmit) time and elevation, or None if TLEs are not known.
        Optional start time parameter can be set to None to indicate now. """
        if self.tle is None:
            return None

        try:
            obs = ephem.Observer()
            obs.lon = str(station.station_lon)
            obs.lat = str(station.station_lat)
            obs.elevation = station.station_alt
            if start is not None:
                obs.date = start
            passData = obs.next_pass(self.tle)
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
            if passData is None:
                return None
            for data in passData:
                if data is None:
                    return None

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
        for i in range(2):
            try:
                with open(self.tle_fname, 'r') as tle_file:
                    tles = tle_file.read()
                    self.tle = self.extract_tle(self.norad_id, tles)
                    if self.tle is None:
                        raise IOError("tracking file could not be parsed")

            except IOError as e:
                logging.warn("tracking: TLE file not found, attempting to re-download (err: %s)" % e)
                # if the file's not found, we need to perform initial update
                self.update_tle()

    def get_next_passes(self, num=10):
        start = ephem.now()
        passes = []
        for p in range(num):
            pass_data = self.get_next_pass(start)
            if pass_data is not None:
                passes.append(pass_data)
                start = self.datetime_to_ephem(pass_data["set_time"] + datetime.timedelta(minutes=1))
        return passes

    @staticmethod
    def pass_tostr(pass_data):
        def date_to_string(dt):
            return dt.strftime("%m/%d/%y %H:%M:%S UTC")
        if pass_data is not None:
            return "%s (%3d azim) -> %s (%2.0f deg) -> %s (%3d azim)" % (
                    date_to_string(pass_data["rise_time"]),
                    pass_data["rise_azimuth"],
                    date_to_string(pass_data["max_alt_time"]),
                    pass_data["max_alt"],
                    date_to_string(pass_data["set_time"]),
                    pass_data["set_azimuth"]
                )
        else:
            return None

    @staticmethod
    def datetime_to_ephem(dt):
        return ephem.Date((dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))

    @staticmethod
    def extract_tle(norad_id, tle_data):
        """ Extracts the TLE set with the given string NORAD ID from the string list of TLEs,
            and returns a three-element string list of the satellite name and two lines of elements.
            Returns None if no TLEs for norad_id was found. """
        tle_list = tle_data.split("\n")

        # invalid TLE file
        if len(tle_list) < 3:
            return None

        for i in range(0, len(tle_list)-2):
            try:
                tle = ephem.readtle(tle_list[i], tle_list[i+1], tle_list[i+2])
            except ValueError:
                # watch for bad TLE line formats when we're in the middle of the line
                continue

            if str(tle.catalog_number) == norad_id:
                return tle

        return None

    def update_tle(self):
        """ Update the TLE data from the remote Celestrack server. Returns if successful """
        # watch for any connection failure
        try:
            req = requests.get(TLE_GET_ROUTE)
            if req.status_code != requests.codes.ok:
                logging.error("tracking: error code getting TLEs: %d" % req.status_code)
                return False
        except Exception as ex:
            logging.error("tracking: exception getting TLEs: %s" % ex)
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

    def pyephem_pass_test(self, start_date=None, num=10):
        """ Adapted from https://brainwagon.org/2009/09/27/how-to-use-python-to-predict-satellite-locations/ """
        obs = ephem.Observer()
        obs.lat = str(station.station_lat)
        obs.long = str(station.station_lon)
        if start_date is not None:
            obs.date = start_date

        for p in range(num):
            pass_data = obs.next_pass(self.tle)
            tr, azr, tt, altt, ts, azs = pass_data
            print(pass_data)

            while tr < ts :
                obs.date = tr
                self.tle.compute(obs)
                print "%s %4.1f %5.1f" % (tr, math.degrees(self.tle.alt), math.degrees(self.tle.az))
                tr = ephem.Date(tr + 60.0 * ephem.second)
            print
            obs.date = tr + ephem.minute

if __name__ == "__main__":
    import config
    st = SatTracker(config.SAT_CATALOG_NUMBER)
    #st.update_tle()
    print("next passes:")
    passes = st.get_next_passes()
    for pas in passes:
        print(SatTracker.pass_tostr(pas))

        #print(st.pyephem_pass_test()) #"2018/7/4 6:00:00"))
