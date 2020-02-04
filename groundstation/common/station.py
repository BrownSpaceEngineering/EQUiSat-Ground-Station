import datetime
import logging

from tracking import SatTracker

class Groundstation(object):
    """ A flexible framework and API for building custom satellite groundstation software.
    Simply subclass this class and implement the on_pass method with code to be run
    whenever the satellite is overhead.
    """
    DEFAULT_TLE_FNAME = "tle.txt"
    DEFAULT_TLE_ROUTE = "https://www.celestrak.com/NORAD/elements/active.txt"
    BTWN_PASS_POLL_TIME = 120 # s

    DEFAULT_CONSOLE_LOGGING_LEVEL = logging.DEBUG
    LOG_FORMAT = '%(levelname)s [%(asctime)s]: %(message)s'

    def __init__(self, norad_id, longitude, latitude, altitude, tle_fname=DEFAULT_TLE_FNAME, tle_route=DEFAULT_TLE_ROUTE, logfile="station.log"):

        self.norad_id = str(norad_id)
        # TODO: in the future, clean the SatTracker class up (remove deps, domain specific code, etc.)
        self.tracker = SatTracker(norad_id, longitude, latitude, altitude, tle_fname, tle_route)
        self.cur_pass = None

        # configure logging
        logging.basicConfig(
            filename=logfile,
            format=self.LOG_FORMAT,
            level=logging.DEBUG
        )
        self.console = logging.StreamHandler()
        self.console.setLevel(self.DEFAULT_CONSOLE_LOGGING_LEVEL)
        self.console.setFormatter(logging.Formatter(self.LOG_FORMAT))
        logging.getLogger().addHandler(self.console)

        logging.info("Started groundstation for satellite with NORAD ID: %s" % norad_id)
        logging.debug("Groundstation info: lat: %f deg, lon: %f deg, alt: %d m" % (longitude, latitude, altitude))

    def run(self):
        next_pass = self._get_next_pass()

        while True:
            while datetime.datetime.utcnow() < next_pass["rise_time"]:
                next_pass = self._get_next_pass()

                # TODO: wait for min(BTWN_PASS_POLL_TIME, time_to_rise_time) and then activate

            # TODO: surround with exception catching?? Or timeouts for failed passes?
            self.cur_pass = next_pass
            self.on_pass(self.cur_pass)

            # TODO: wait for min(BTWN_PASS_POLL_TIME, time_to_set_time), update for the next pass,
            # and then wait for a implementer-configurable amount of time before the next pass
            # starts to call before_pass (so they can choose how long they need to prep before the pass)
            # next_next_pass = self._get_next_pass()
            # self.before_pass(next_next_pass)

    def _get_next_pass(self):
        self.tracker.update_tle()
        next_pass = self.tracker.get_next_pass()
        logging.info("targeting pass: %s" % (SatTracker.pass_tostr(next_pass)))
        return next_pass

    def after_pass(self, next_stats):
        """ Method called by this classes run() method after the completion of a satellite pass, to
        allow preparing for the next pass. """
        raise NotImplementedError("please implement this method")

    def on_pass(self, stats):
        """ Method called by this classes run() method on the start of a pass of the satellite overhead """
        raise NotImplementedError("please implement this method")

    #### Subclass helper methods ####

    def pass_done(self):
        return datetime.datetime.utcnow() > self.cur_pass["set_time"]

    def cur_az_el(self):
        """ Returns a tuple of the satellite's current azimuth and elevation, respectively. """

        # TODO: investigate for accuracy

        return self.tracker.get_az_el()

    def cur_doppler_correction(self, tx_freq):
        """ Returns the current doppler frequency shift relative to the transmitter frequency tx_freq,
         in the same units as tx_freq. """
        return self.cur_doppler_factor() * tx_freq

    def cur_doppler_factor(self):
        """ Returns the current doppler factor defined by the satellite's range rate"""
        return self.tracker.get_doppler_factor()
