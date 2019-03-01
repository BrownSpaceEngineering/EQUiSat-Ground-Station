from station import Groundstation
import time

class HAMLibRotator(Groundstation):
    def __init__(self, norad_id, longitude, latitude, altitude, tle_fname=super.DEFAULT_TLE_FNAME, tle_route=super.DEFAULT_TLE_ROUTE):
        super(HAMLibRotator, self).__init__(norad_id, longitude, latitude, altitude, tle_fname, tle_route)

    def on_pass(self, stats):
        while not self.pass_done():
            # TODO: actually set az/el
            print(self.cur_az_el())
            time.sleep(1)

    def after_pass(self, next_stats):
        # TODO: reset rotator
        pass

if __name__ == "__main__":
    import station_config
    rot = HAMLibRotator(43552, station_config.station_lon, station_config.station_lat, station_config.station_alt)
    rot.run()