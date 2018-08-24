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
import groundstation
import utils

DEFAULT_TLE_FNAME = "tle.txt"
TLE_GET_ROUTE = "http://tracking.brownspace.org/api/tle" #"https://www.celestrak.com/cgi-bin/TLE.pl?CATNR=%s"

class SatTracker:
    SPEED_OF_LIGHT_MPS = 299792000

    def __init__(self, norad_id, tle_fname=DEFAULT_TLE_FNAME):
        self.norad_id = str(norad_id)
        self.tle_fname = tle_fname
        self.tle = None
        self.load_tle() # populates self.tle
        self.obs = ephem.Observer()
        self.obs.lon = str(station.station_lon)
        self.obs.lat = str(station.station_lat)
        self.obs.elevation = station.station_alt

    def get_next_pass(self, start=None):
        """ Returns a dictionary with the rise and set time and azimuth as well as
        the max alt (transmit) time and elevation, or None if TLEs are not known.
        Optional start time parameter can be set to None to indicate now. """
        if self.tle is None:
            return None

        try:
            if start is not None:
                self.obs.date = start
            passData = self.obs.next_pass(self.tle)
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

            rise_time = passData[0].datetime()
            set_time = passData[4].datetime()
            return OrderedDict([
                ('rise_time', rise_time),
                ('rise_azimuth', math.degrees(passData[1])),
                ('rise_doppler_factor', self.get_doppler_factor(rise_time)),
                ('max_alt_time', passData[2].datetime()),
                ('max_alt', math.degrees(passData[3])),
                ('set_time', set_time),
                ('set_azimuth', math.degrees(passData[5])),
                ('set_doppler_factor', self.get_doppler_factor(set_time))
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

    def get_next_passes(self, start=None, num=10):
        if start is None:
            start = ephem.now()
        passes = []
        for p in range(num):
            pass_data = self.get_next_pass(start)
            if pass_data is not None:
                passes.append(pass_data)
                start = self.datetime_to_ephem(pass_data["set_time"] + datetime.timedelta(minutes=1))
        return passes

    #####################
    ## Doppler Helpers ##
    #####################

    def get_doppler_freq_times(self, dev_freqs_hz, pass_data, base_freq_hz, time_step_s=5):
        """ Returns a dictionary from the values in dev_freqs_hz to the approximate datetimes
            corresponding to when those relative frequency deviations occured in the given pass.
            Returns None if the the pass did not generate sufficient data given time_step_s.
            Additionally, if any of the given frequency deviations were never reached in the pass
            (they were larger than the largest deviation or smaller than the smallest)
            they will be set to None.
            :param base_freq_hz: required to convert between
            relative doppler frequencies and doppler factors. """
        # convert the frequencies to factors for easier comparison with library output
        factors = [dev_freq_hz / float(base_freq_hz) for dev_freq_hz in dev_freqs_hz]
        factor_times = self.get_doppler_factor_times(factors, pass_data, time_step_s)
        if factor_times is None:
            return None

        # convert the factors given back to freq deviations
        freq_times = {}
        for fac_val in factor_times:
            freq_val = fac_val * base_freq_hz
            freq_times[freq_val] = factor_times[fac_val]
        return freq_times

    def get_doppler_factor_times(self, factors, pass_data, time_step_s):
        """ Returns a dictionary from the values in factors to the approximate datetimes
            corresponding to when those factors occur in the given pass.
            Returns None if the the pass did not generate sufficient data given time_step_s.
            Additionally, if any of the given factors were never reached in the pass
            (they were larger than the largest factor or smaller than the smallest)
            they will be set to None. """
        # grab a long list of all factors, equally spaced in the pass
        all_factors = self.get_doppler_factors(pass_data, time_step_s)
        if len(all_factors) < 1:
            return None

        # sort in descending order so we can go through the pass sequentially
        factors = sorted(factors, reverse=True)
        i = 0
        factors_dict = {}

        # initially, iterate through and set to None all the factors LARGER
        # than the largest factor in all_factors (they're outside this pass)
        # NOTE: the largest factor should always be the last factor in the list
        largest_fac = all_factors[0]["factor"]
        while factors[i] >= largest_fac:
            factors_dict[factors[i]] = None
            i += 1
            # if for some reason we reach the end, quit with all factors None
            if i == len(factors):
                return factors_dict

        # iterate over the long list of factors, finding the intersection point
        # of each of the given factors
        # (do linear regression with prev point so skip first point)
        for j in range(1, len(all_factors)):
            prev_point = all_factors[j-1]
            point = all_factors[j]
            # check that it's monotonically decreasing
            if prev_point["factor"] - point["factor"] < -1e-6:
                logging.error("List of doppler factors for a pass was not monotonically decreasing: %s" % all_factors)

            # print("%20s: fac=%+8f desired=%+8f (%d) (freq=%+4f)" % (point["time"], point["factor"], factors[i], i, 435.55e3 * point["factor"]))

            # as soon as the current factor in the list (decreasing) is smaller than the largest desired
            # factor ("intersects it"/has passed it) we can estimate the exact time of that factor using
            # linear regression between the previous point and this one
            if point["factor"] < factors[i]:
                # use the formula for linear interpolation to compute the expected (interpolated)
                # date given the desired factor
                # (see: https://en.wikipedia.org/wiki/Linear_interpolation#Linear_interpolation_between_two_known_points)
                # (this is on a plot of seconds vs. factor value)
                secs_per_factor = (point["time"] - prev_point["time"]).total_seconds() / (point["factor"] - prev_point["factor"])
                secs_from_prev = (factors[i] - prev_point["factor"]) * secs_per_factor
                interp_time = prev_point["time"] + datetime.timedelta(seconds=secs_from_prev)
                assert utils.dtime_after(interp_time, prev_point["time"]) and utils.dtime_after(point["time"], interp_time)
                factors_dict[factors[i]] = interp_time
                # move onto the next smallest factor in our desired list
                i += 1
                # if we reach the end, quit
                if i == len(factors):
                    return factors_dict

        # at the end, iterate through and set to None all the factors SMALLER
        # than the smallest factor in all_factors (they're outside this pass)
        # NOTE: the smallest factor should always be the last factor in the list
        smallest_fac = all_factors[len(all_factors)-1]["factor"]
        while factors[i] <= smallest_fac:
            factors_dict[factors[i]] = None
            i += 1
            # if we reach the end, quit
            if i == len(factors):
                return factors_dict

        return factors_dict

    def get_doppler_factors(self, pass_data, time_step_s):
        """ Returns a list of {'time', 'factor'} dicts giving the doppler factor at each time.
        Sorted in increasing time order.
         :param time_step_s: the time step to use to generate the list. """
        factors = []
        cur_time = pass_data["rise_time"]
        while utils.dtime_after(pass_data["set_time"], cur_time):
            factors.append({
                "time": cur_time,
                "factor": self.get_doppler_factor(cur_time)
            })
            cur_time = cur_time + datetime.timedelta(seconds=time_step_s)

        return factors

    def get_doppler_factor(self, dtime):
        self.obs.date = self.datetime_to_ephem(dtime)
        self.tle.compute(self.obs)
        # negative because negative (inbound) range rate means an increase in frequency
        return -self.tle.range_velocity / self.SPEED_OF_LIGHT_MPS

    @staticmethod
    def pass_tostr(pass_data, sig_freq_hz=1000):
        if pass_data is not None:
            return "%s (%3d azim, %+2.2f kHz) -> %s (%2.0f deg) -> %s (%3d azim, %+2.2f kHz)" % (
                    utils.date_to_str(pass_data["rise_time"]),
                    pass_data["rise_azimuth"],
                    (sig_freq_hz/1000.0) * pass_data["rise_doppler_factor"],
                    utils.date_to_str(pass_data["max_alt_time"]),
                    pass_data["max_alt"],
                    utils.date_to_str(pass_data["set_time"]),
                    pass_data["set_azimuth"],
                    (sig_freq_hz/1000.0) * pass_data["set_doppler_factor"]
                )
        else:
            return None

    @staticmethod
    def datetime_to_ephem(dt):
        return ephem.Date((dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second))

    #################
    ## TLE Helpers ##
    #################

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
    passes = st.get_next_passes(num=20, start=datetime.datetime.utcnow()) # + datetime.timedelta(hours=1))
    for pas in passes:
        print(SatTracker.pass_tostr(pas, groundstation.EQUiStation.RADIO_BASE_FREQ_HZ))

        corrections = groundstation.EQUiStation.generate_doppler_corrections(pas, st, groundstation.EQUiStation.RADIO_BASE_FREQ_HZ)
        print(groundstation.EQUiStation.doppler_corrections_tostr(corrections))

        # print(st.get_doppler_freq_times([12500-6250/2, 6250/2, -6250/2, -12500+6250/2], pas, groundstation.EQUiStation.RADIO_BASE_FREQ_HZ))

    #print(st.pyephem_pass_test()) #"2018/7/4 6:00:00"))
