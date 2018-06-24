#!/usr/bin/python
# The primary script for reading incoming transmissions from
# the XDL Micro over serial, performing error correcting, and
# sending the data to BSE's server.
import os
import re
import serial
import time
import datetime
import logging
from binascii import hexlify, unhexlify
import requests
from collections import OrderedDict

import mock_serial
from utils import *
from reedsolomon import rscode
from packetparse import packetparse
import transmit
import tracking
import radio_control

import station_config as station
import config

# testing config
USE_TEST_FILE = True
GENERATE_FAKE_PASSES = True # see below for params
RUN_TEST_UPLINKS = True
TEST_INFILE = "../Test Dumps/test_packet_logfile.txt"
TEST_OUTFILE = "groundstation_serial_out.txt"

class EQUiStation:
    LOGGING_LEVEL = logging.INFO

    # RX config
    PACKET_PUB_ROUTE = "http://api.brownspace.org/equisat/receive_data"
    CALLSIGN_HEX = "574c39585a" # WL9XZE
    PACKET_STR_LEN = 2*255 # two hex char per byte
    MAX_BUF_SIZE = 4096
    packet_regex = re.compile("(%s.{%d})" % \
        (CALLSIGN_HEX, PACKET_STR_LEN-len(CALLSIGN_HEX)))

    # doppler correction config
    ORBITAL_PERIOD_S = 93*60 if not GENERATE_FAKE_PASSES else 90
    TRACKING_API_ROUTE = "http://127.0.0.1/api"
    RADIO_BASE_FREQ_HZ = int(435.55*10e6)
    RADIO_FREQ_STEP_HZ = radio_control.RADIO_FREQ_STEP_HZ
    RADIO_INBOUND_CHAN = 2
    RADIO_OUTBOUND_CHAN = 3
    DOPPLER_MAX_ELEV_THRESH = 20 # deg
    PACKET_SEND_FREQ_S = 20

    def __init__(self):
        # globals for external api use, etc.
        self.last_data_rx = None
        self.last_packet_rx = None
        self.rx_buf = ""
        self.tx_cmd_queue = []
        self.only_send_tx_cmd = False

        # doppler shift/tracking
        self.station_lat = station.station_lat
        self.station_lon = station.station_lon
        self.station_alt = station.station_alt
        self.next_pass_data = {}
        self.doppler_correct_time = datetime.datetime.now()
        self.update_pass_data_time = datetime.datetime.now()
        self.radio_cur_frequency_hz = self.RADIO_BASE_FREQ_HZ
        self.radio_inbound_freq_hz = self.RADIO_BASE_FREQ_HZ
        self.radio_outbound_freq_hz = self.RADIO_BASE_FREQ_HZ
        self.ready_for_next_pass = False # allow it to be set if it's in the window on boot, in case of failure

        self.ser = None
        self.tracker = tracking.SatTracker(config.SAT_CATALOG_NUMBER)
        logging.basicConfig(format='%(asctime)s %(message)s', level=self.LOGGING_LEVEL)

    ##################################################################
    # Groundstation state machine
    ##################################################################
    def run(self, serial_port=None, serial_baud=38400, \
        ser_infilename=None, ser_outfilename=None, file_read_size=PACKET_STR_LEN):
        try:
            if ser_infilename != None and ser_outfilename != None:
                with mock_serial.MockSerial(infile_name=ser_infilename, outfile_name=ser_outfilename, max_inwaiting=file_read_size) as ser:
                    self.ser = ser
                    self.mainloop()
            else:
                with serial.Serial(serial_port, serial_baud, timeout=None) as ser:
                    self.ser = ser
                    self.mainloop()

        except KeyboardInterrupt:
            return

    def pre_init(self):
        if RUN_TEST_UPLINKS:
            cmds = transmit.loadUplinkCommands(config.UPLINK_COMMANDS_FILE)
            self.send_tx_cmd(cmds['echo_cmd'], config.UPLINK_RESPONSES['echo_cmd'])
            self.send_tx_cmd(cmds['kill3_cmd'], config.UPLINK_RESPONSES['kill3_cmd'])
            self.send_tx_cmd(cmds['kill7_cmd'], config.UPLINK_RESPONSES['kill7_cmd'])
            self.send_tx_cmd(cmds['killf_cmd'], config.UPLINK_RESPONSES['killf_cmd'])
            self.send_tx_cmd(cmds['flash_cmd'], config.UPLINK_RESPONSES['flash_cmd'])
            self.send_tx_cmd(cmds['reboot_cmd'], config.UPLINK_RESPONSES['reboot_cmd'])
            self.send_tx_cmd(cmds['revive_cmd'], config.UPLINK_RESPONSES['revive_cmd'])
            self.send_tx_cmd(cmds['flashkill_cmd'], config.UPLINK_RESPONSES['flashkill_cmd'])
            self.send_tx_cmd(cmds['flashrevive_cmd'], config.UPLINK_RESPONSES['flashrevive_cmd'])

        # get radio ready for a pass
        self.update_radio_for_pass()


    def mainloop(self):
        self.pre_init()
        while True:
            try:
                # try and receive data (a packet),
                got_packet = self.receive() #TODO: do this even if self.only_send_tx_cmd???

                # and if we did try and send any TX commands,
                if got_packet or self.only_send_tx_cmd:
                    _, _ = self.transmit()

                # and then try to adjust the frequency for doppler effects
                self.correct_for_doppler()

                time.sleep(0.1)

            except KeyboardInterrupt:
                break

    ##################################################################
    # Groundstation states
    ##################################################################
    def receive(self):
        """ Attempts to receive, process, and store data received from the radio.
            Returns whether a packet was detected. """

        # grab all the data we can off the serial line
        inwaiting = self.ser.in_waiting
        if inwaiting > 0:
            in_data = self.ser.read(size=inwaiting)
            self.rx_buf += hexlify(in_data)
            self.last_data_rx = datetime.datetime.now()

        # look for (and extract/send) any packets in the buffer, trimming
        # the buffer after finding any. (Only finds full packets)
        got_packet = self.scan_for_packets()

        # if we got a packet, update the last packet rx time to when we got data
        if got_packet:
            self.last_packet_rx = self.last_data_rx

        # also try and trim the buffer if it exceeds a max size,
        # making sure to leave at least a packet's worth of characters
        # in case one is currently coming in
        self.rx_buf = EQUiStation.trim_buffer(self.rx_buf, self.MAX_BUF_SIZE,\
            self.PACKET_STR_LEN)

        return got_packet

    def transmit(self):
        """ Checks if there are any uplink commands on the queue and transmits
            them/waits for response if so.
            Returns whether anything was transmitted and whether it was successful. """

        if len(self.tx_cmd_queue) > 0:
            command = self.tx_cmd_queue.pop(0)
            logging.info("SENDING UPLINK COMMAND: %s" % command)

            got_response, rx = transmit.sendUplink(command["cmd"], \
                command["response"], self.ser)
            self.rx_buf += rx

            logging.info("uplink command success: %s" % got_response)
            logging.debug("full uplink response: %s" % rx)

            if got_response:
                return True, True
            else:
                self.tx_cmd_queue.insert(0, command) # add back command
                return True, False
        else:
            return False, False

    def correct_for_doppler(self):
        """ Shifts the receive and transmit frequency of the XDL micro to compensate
            for doppler shift based on the current estimated position of the satellite.
            Returns whether the correction was made. """

        # on every iteration as we're coming onto a pass,
        # check if the doppler_correct_time will land close
        # to our expected next RX, and correct it if necessary
        if self.ready_for_next_pass:
            self.interlace_doppler_and_tx_times()

        now = datetime.datetime.now()
        # if the satellite is far past (on opposite side of planet),
        # update our data on the next pass and the actual radio frequency
        # settings to be ready for the next pass
        if now >= self.update_pass_data_time and not self.ready_for_next_pass:
            good = self.update_radio_for_pass()
            # keep trying again on any failure
            if good:
                self.ready_for_next_pass = True
                # (NOTE: doppler_correct_time updated in above function)
                # schedule the next update (tentatively) for an orbital period away
                self.update_pass_data_time = datetime.datetime.now() + \
                    datetime.timedelta(seconds=EQUiStation.ORBITAL_PERIOD_S)
            return good

        # otherwise, if we've just passed the point of max elevation,
        # swap the frequency to be the outbound-corrected one
        # (this may be slightly off to avoid an RX)
        elif now >= self.doppler_correct_time and self.ready_for_next_pass:
            good = self.radio_activate_pass_freq(inbound=False)
            # indicate we need to set up for next pass at some point
            if good:
                self.ready_for_next_pass = False
                # (NOTE: leave doppler_correct_time as it was, just for historical purposes)
                # change the update time to halfway around the orbit from here
                self.update_pass_data_time = datetime.datetime.now() + \
                    datetime.timedelta(seconds=EQUiStation.ORBITAL_PERIOD_S/2)

            logging.info("ADJUSTED FOR DOPPLER: %s" % "success" if good else "FAILURE")
            return good

    def interlace_doppler_and_tx_times(self):
        """ Shifts the scheduled doppler correction to be centered between
            times of satellite transmissions to avoid missing data during the radio update """
        epoch = self.last_packet_rx # TODO: maybe actually self.last_data_rx if we get bad data?
        delta_to_doppler = (self.doppler_correct_time - epoch).total_seconds()
        remainder = delta_to_doppler % self.PACKET_SEND_FREQ_S

        # calculate correction to center the new doppler shift in the middle of the interval
        # timing:
        #  doppler  TX(epoch) TX       TX doppler TX
        # |.|.......|.........|.........|......|..|.........|
        # in first case, we should bump doppler correct forward, while in the second we bump it back
        # so, correct down if the remainder is less than half the period and up otherwise
        # (if the midpoint is greater than the remainder this is positive,
        # otherwise it is negative)
        # NOTE: this also works with negatives (-9 % 10 == 1, so we'll correct forward 4s as req),
        # but this shouldn't matter because we'll run it right after this function either way
        # (we rely on this compensating based on packets throughout the pass, plus if we just
        # got a packet RX and passed over the doppler correct while in the process, we're probably
        # fine to correct now)
        correction = self.PACKET_SEND_FREQ_S / 2 - remainder

        # actually adjust time
        self.doppler_correct_time = self.doppler_correct_time + \
            datetime.timedelta(seconds=correction)

    ##################################################################
    # Receive/Decode Helpers
    ##################################################################
    def scan_for_packets(self):
        """ Scans for raw HEX packets in the recieve buffer and sends any found
            to a server. Also trims the buffer before the end of the last packet.
            Returns whether any packets were found.
        """
        logging.debug("reading buffer of size %d for packets" % len(self.rx_buf))
        packets, indexes = EQUiStation.extract_packets(self.rx_buf)
        if len(packets) == 0:
            return False

        # error correct and send packets to API
        for raw in packets:
            logging.info("FOUND PACKET, correcting & sending...")
            corrected, error = EQUiStation.correct_packet_errors(raw)
            errors_corrected = error == None

            # parse if was corrected
            parsed = {}
            if errors_corrected:
                parsed, err = packetparse.parse_packet(corrected)
                if err != None:
                    logging.error("error parsing packet: %s" % err)

            # post packet to API
            logging.info("""publishing packet:
raw:
%s
corrected: (len: %d, actually corrected: %r, error: %s):
%s
parsed:
%s""" % (raw, len(corrected), errors_corrected, error, corrected, parsed))
            self.publish_packet(raw, corrected, parsed, errors_corrected)

        # trim buffer so it starts right past the end of last parsed packet
        lastindex = indexes[len(indexes)-1]
        self.rx_buf = self.rx_buf[lastindex+self.PACKET_STR_LEN:]
        return True

    def publish_packet(self, raw, corrected, parsed, errors_corrected, route=PACKET_PUB_ROUTE):
        """ Sends a POST request to the given API route to publish the packet. """
        json = {"raw": raw, "corrected": corrected, "transmission": parsed, \
                "secret": station.station_secret, "station_name": station.station_name, \
                "errors_corrected": errors_corrected }
        # r = requests.post(route, json=json) # TODO: don't wanna spam
        # if r.status_code != requests.codes.ok:
        #     logging.warning("couldn't publish packet (%d): %s" % (r.status_code, r.text))

    @staticmethod
    def extract_packets(buf):
        """ Attempts to find and extract full packets from the given buffer based on callsign matching.
            Also returns a parrallel list of starting indexes of the packets in the buffer. """
        packets = EQUiStation.packet_regex.findall(buf)
        indexes = [buf.index(packet) for packet in packets]
        return packets, indexes

    @staticmethod
    def correct_packet_errors(raw):
        """ Corrects the packet's error using Reed Solomon error correction
        and the packet's parity bytes. Makes sure to avoid correcting the callsign. """
        assert len(raw) == EQUiStation.PACKET_STR_LEN
        callsign = raw[:12]
        raw_no_callsign = raw[12:] # callsign is 6 chars
        corrected, error = rscode.decode(raw_no_callsign)
        return callsign + corrected, error

    @staticmethod
    def trim_buffer(buf, max_size, min_to_leave):
        """ Trims and returns the given buffer to be less than or equal to max_size,
            but makes sure to leave at least min_to_leave of the last characters in the buffer. """
        assert max_size >= min_to_leave
        if len(buf) > max_size:
            return buf[len(buf)-min_to_leave:]
        else:
            return buf

    ##################################################################
    # Radio control helpers
    ##################################################################
    def radio_update_pass_freqs(self):
        enter_okay, rx1 = radio_control.enterCommandMode(self.ser, dealer_access=True)
        rx_in_okay, rx2 = radio_control.setRxFreq(self.ser, self.radio_inbound_freq_hz, self.RADIO_INBOUND_CHAN)
        tx_in_okay, rx3 = radio_control.setTxFreq(self.ser, self.radio_inbound_freq_hz, self.RADIO_INBOUND_CHAN)
        rx_out_okay, rx4 = radio_control.setRxFreq(self.ser, self.radio_outbound_freq_hz, self.RADIO_OUTBOUND_CHAN)
        tx_out_okay, rx5 = radio_control.setTxFreq(self.ser, self.radio_outbound_freq_hz, self.RADIO_OUTBOUND_CHAN)
        exit_okay, rx6 = radio_control.exitCommandMode(self.ser)
        self.rx_buf += rx1 + rx2 + rx3 + rx4 + rx5 + rx6
        return enter_okay and rx_in_okay and tx_in_okay and rx_out_okay \
            and tx_out_okay and exit_okay

    def radio_activate_pass_freq(self, inbound):
        """ (Quickly) sets the radio to either it's inbound mode or
            outbound mode. Does so by simply changing pre-configured channels """

        channel = self.RADIO_INBOUND_CHAN if inbound else self.RADIO_OUTBOUND_CHAN
        _, rx1 = radio_control.enterCommandMode(self.ser)
        channel_okay, rx2 = radio_control.setChannel(self.ser, channel)
        exit_okay, rx3 = radio_control.exitCommandMode(self.ser)

        self.rx_buf += rx1 + rx2 + rx3
        okay = channel_okay and exit_okay
        if not okay:
            return False

        if inbound:
            self.radio_cur_frequency_hz = self.radio_inbound_freq_hz
        else:
            self.radio_cur_frequency_hz = self.radio_outbound_freq_hz
        return True

    ##################################################################
    # Doppler correct helpers
    ##################################################################
    def update_radio_for_pass(self):
        data_good = self.update_pass_data()
        freqs_good = self.radio_update_pass_freqs()
        activate_good = self.radio_activate_pass_freq(inbound=True)
        good = data_good and freqs_good and activate_good

        logging.info("UPDATED FOR NEXT PASS: | pass data: %s | freq setting: %s | activating freqs: %s |" \
            % (data_good, freqs_good, activate_good))
        return good

    def update_pass_data(self):
        """ Updates our cached information on the next EQUiSat pass via an API call """

        # update the TLE cache (every pass, we might as well)
        success = self.tracker.update_tle()
        if not success:
            logging.error("error updating TLE data to latest")

        # compute next pass geometrically
        next_pass_data = self.tracker.get_next_pass()

        # TESTING override; generate fake pass instead
        if GENERATE_FAKE_PASSES:
            rise_time = rand_dtime(datetime.datetime.now(), 10)
            set_time = rand_dtime(rise_time, 30)
            max_alt_time = rise_time + (set_time - rise_time)/2 # avg
            next_pass_data = OrderedDict([
                ('rise_time', rise_time),
                ('rise_azimuth', random.randint(0, 360)),
                ('max_alt_time', max_alt_time),
                ('max_alt', random.randint(-90, 90)),
                ('set_time', set_time),
                ('set_azimuth', random.randint(0, 360))
            ])

        if next_pass_data == None:
            logging.error("error retrieving next pass data")
            return False
            # our best bet is probably to use the old pass as it won't change a ton
        else:
            self.next_pass_data = next_pass_data
            # note we may change this time to avoid correcting during an RX
            self.doppler_correct_time = self.next_pass_data["max_alt_time"]
            max_elevation = self.next_pass_data["max_alt"]
            self.radio_inbound_freq_hz, self.radio_outbound_freq_hz = \
                self.determine_optimal_pass_freqs(max_elevation)

            logging.info("updated pass data with:\n%s\nfreqs: %d -> %d" % \
                (self.next_pass_data, self.radio_inbound_freq_hz, self.radio_outbound_freq_hz))
            return True

    def determine_optimal_pass_freqs(self, max_elevation):
        """ Determines the optimal pair of frequencies to maximize the change of error-free
        packets during the inbound and outbound component of a pass,
        based on the latest pass information.
        Returns a tuple of (inbound freq in hz, outbound freq in hz) """

        # the radio's frequency correction is so coarse (6.25 kHz),
        # we just choose between the 6.25 and 12.5 kHz corrections based on
        # the elevation of the pass
        # (very low passes need less doppler shift while higher ones need more)
        deviation = self.RADIO_FREQ_STEP_HZ
        if max_elevation > self.DOPPLER_MAX_ELEV_THRESH:
            deviation = 2 * self.RADIO_FREQ_STEP_HZ

        return (self.RADIO_BASE_FREQ_HZ + deviation, self.RADIO_BASE_FREQ_HZ - deviation)

    ##################################################################
    # External interface for control
    ##################################################################
    def get_last_data_rx(self):
        return self.last_data_rx

    def get_last_packet_rx(self):
        return self.last_packet_rx

    def get_rx_buf(self):
        return self.rx_buf

    def send_tx_cmd(self, cmd, response, immediate=False):
        """ Queues the given transmit command name and expected response to
        be transmitted when best, or sets it to transmit immediately and
        continually if immediate is set """
        self.tx_cmd_queue.append({"cmd": cmd, "response": response})
        if not self.only_send_tx_cmd and immediate:
            self.only_send_tx_cmd = True

    def cancel_immediate_tx_cmd(self, remove=True):
        self.only_send_tx_cmd = False
        if remove:
            self.tx_cmd_queue.pop(0) # immediate is always at end

    def cancel_tx_cmd(self, cmd):
        pass # TODO

    # TODO: callbacks: on_freq_change, on_packet_rx, on_data_rx, etc.


def main():
    gs = EQUiStation()
    if USE_TEST_FILE:
        gs.run(ser_infilename=TEST_INFILE, ser_outfilename=TEST_OUTFILE)
    else:
        gs.run(serial_port=config.SERIAL_PORT, serial_baud=config.SERIAL_BAUD)

if __name__ == "__main__":
    #print(trim_buffer("cats are cool", 4, 4)) # should be "cool"
    main()


# Helpful command for converting hex packets to raw strings:
# """python -c "from binascii import unhexlify
# print unhexlify('574c39585a45d36b00002297323b03e3dc5b5547472855f0e1b8b29eb3474747474747474746474747464646474646474746474747464646474747474746474647464746474647ff000000000000000000000000000000000000000000000000000000a59db29da69db39da79cb09ea59eb09da69db29da49db39da69db29d070a020a0707050a070a050a0707050a070a02070707020a0707050a7f7f807f7f807f7f807f7f807f7f807f7f807f7f80d56b00002643009c1fff9c1cff9c20ff9c1bff9c1dff9c1aff9c1eff9c19ff263c01d64c019c1f019c1c019c200100b113eb92ebab70e5d6e24a74a82e3b3411f20fbd1ac8a54f6aac3c57e5a127a8')" - > hex_packet"""
