import datetime

from tracking import SatTracker

class Groundstation:
    """ A flexible framework and API for building custom satellite groundstation software.
    Simply subclass this class and implement the on_pass method with code to be run
    whenever the satellite is overhead.
    """
    DEFAULT_TLE_FNAME = "tle.txt"
    DEFAULT_TLE_ROUTE = "https://www.celestrak.com/NORAD/elements/active.txt"
    BTWN_PASS_POLL_TIME = 120 # s

    def __init__(self, norad_id, longitude, latitude, altitude, tle_fname=DEFAULT_TLE_FNAME, tle_route=DEFAULT_TLE_ROUTE):
        self.norad_id = str(norad_id)
        # TODO: in the future, clean the SatTracker class up (remove deps, domain specific code, etc.)
        self.tracker = SatTracker(norad_id, longitude, latitude, altitude, tle_fname, tle_route)
        self.cur_pass = None

    def run(self):
        while True:
            while datetime.datetime.utcnow() < next_pass["rise_time"]:
                self.tracker.update_tle()
                next_pass = self.tracker.get_next_pass()

                # TODO: wait for min(BTWN_PASS_POLL_TIME, time_to_rise_time) and then activate

            # TODO: surround with exception catching?? Or timeouts for failed passes?
            self.cur_pass = next_pass
            self.on_pass(next_pass)

            # TODO: wait for min(BTWN_PASS_POLL_TIME, time_to_set_time), grab new TLE, and then run before_pass
            # TODO: ACTUALLY, allow configurable time before pass that before_pass is run
            self.before_pass(next_next_pass)

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