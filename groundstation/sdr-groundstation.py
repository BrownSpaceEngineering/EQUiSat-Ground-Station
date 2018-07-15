#!/usr/bin/python
# Groundstation for auto dumps of a Airspy R2 SDR (or anything that runs via a command)
import datetime
import logging
import signal
import subprocess
import time

from groundstation import config, tracking, EQUiStation
import utils

LOGFILE = "sdr-groundstation.log"
PRE_PASS_ACTIVATE_S = 10
USE_FAKE = True

LNA_GAIN = 10
LINEARITY_GAIN = 5
SAMPLE_RATE = 2.5*1e6
AIRSPY_DUMP_DIREC = "./"
AIRSPY_CMD_PREFIX = "airspy_rx -f 435.55 -l %d -g %d -a %s" % (LNA_GAIN, LINEARITY_GAIN, SAMPLE_RATE)
FILE_TIME_FORMAT = "%m.%d.%y_%H:%M"

def get_airspy_cmd(filename):
    return AIRSPY_CMD_PREFIX + " -r %s/%s" % (AIRSPY_DUMP_DIREC, filename)

def generate_airspy_filename(pass_data, increment):
    start_date = pass_data["rise_time"].strftime(FILE_TIME_FORMAT)
    deg_pass = pass_data["max_alt"]
    return "sdr_dump_%s_%d_deg%s.wav" % (start_date, deg_pass, increment if increment > 0 else "")

def get_next_pass(tracker):
    # update the TLE cache (every pass, we might as well)
    success = tracker.update_tle()
    if not success:
        logging.error("error updating TLE data to latest")

    # compute next pass geometrically
    next_pass_data = tracker.get_next_pass()

    # on fails, our best bet is probably to use the old pass as it won't change a ton
    if next_pass_data is None:
        logging.error("error retrieving next pass data")
        return None, False

    elif next_pass_data["rise_time"] is None or next_pass_data["max_alt"] is None\
            or next_pass_data["set_time"] is None:
        logging.warning("failed to update pass data: %s" % next_pass_data)
        return None, False

    return next_pass_data, True

def run_airspy(pass_data, file_i):
    cmd = get_airspy_cmd(generate_airspy_filename(pass_data, file_i))
    logging.debug("starting sdr dump cmd: %s" % cmd)
    return subprocess.Popen(cmd)

def on_pass(pass_data):
    file_i = 0
    logging.info("starting on pass")
    try:
        proc = run_airspy(pass_data, file_i)
        while utils.dtime_after(pass_data["set_time"]):
            if proc.poll() is not None:
                file_i += 1
                logging.warning("sdr command stopped; starting new one")
                proc = run_airspy(pass_data, file_i)
            time.sleep(5)

        # send Ctrl-C to stop gracefully
        proc.send_signal(signal.SIGINT)
        logging.info("finished pass")

    except OSError or IOError as e:
        logging.error("error running airspy: " + str(e))
        raise e # let system service restart us

def wait_until(date):
    while utils.dtime_after(date):
        time.sleep(1)

def main():
    tracker = tracking.SatTracker(config.SAT_CATALOG_NUMBER)

    # config logging
    logging.basicConfig(
        filename=LOGFILE,
        format=EQUiStation.LOG_FORMAT,
        level=logging.DEBUG
    )
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
    console.setFormatter(logging.Formatter(EQUiStation.LOG_FORMAT))
    logging.getLogger().addHandler(console)

    while True:
        pass_data, success = get_next_pass(tracker)
        if USE_FAKE:
            success = True
            pass_data = EQUiStation.generate_fake_pass(40)

        if success:
            logging.info("WAITING FOR PASS: \n%s" % pass_data)
            start = pass_data["rise_time"] - datetime.timedelta(seconds=PRE_PASS_ACTIVATE_S)
            wait_until(start)
            on_pass(pass_data)
            time.sleep(30) # leave some time so tracker goes to next pass
        else:
            time.sleep(30)
            logging.error("unable to retrieve pass data; try again")

if __name__ == "__main__":
    main()