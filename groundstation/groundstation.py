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

import groundstation_credentials as creds
import config
from reedsolomon import rscode
from packetparse import packetparse
import transmit
import radio_control

# testing config
USE_TEST_FILE = True
TEST_FILE = "../Test Dumps/test_packet_logfile.txt"

class EQUiStation:
    # RX config
    PACKET_PUB_ROUTE = "http://api.brownspace.org/equisat/receive_data"
    CALLSIGN_HEX = "574c39585a" # WL9XZE
    PACKET_STR_LEN = 2*255 # two hex char per byte
    MAX_BUF_SIZE = 4096
    packet_regex = re.compile("(%s.{%d})" % \
        (CALLSIGN_HEX, PACKET_STR_LEN-len(CALLSIGN_HEX)))

    # doppler correction config
    PACKET_SEND_FREQ_S = 20
    FREQ_SWITCH_TIME_WINDOW_S = 60 # how close to max elevation time to switch frequency

    def __init__(self):
        # globals for api use, etc.
        self.last_data_rx = None
        self.last_packet_rx = None
        self.rx_buf = ""
        self.tx_cmd_queue = [] # TODO: method to populate
        self.only_send_tx_cmd = False

        # interfacing
        self.ser = None
        self.file_input = None
        self.file_input_read_size = self.PACKET_STR_LEN/2

        logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


    ##################################################################
    # External interface for control
    ##################################################################
    def get_last_data_rx(self):
        return self.last_data_rx

    def get_last_packet_rx(self):
        return self.last_packet_rx

    def get_rx_buf():
        return self.rx_buf

    def send_tx_cmd(cmd, response, immediate=False):
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

    ##################################################################
    # Groundstation state machine
    ##################################################################
    def run(self, serial_port=None, serial_baud=38400, filename=None,\
        file_read_size=PACKET_STR_LEN/2):
        try:
            if filename != None:
                with open(filename, "r") as f:
                    self.file_input = f
                    self.mainloop()
            else:
                with serial.Serial(serial_port, serial_baud, timeout=None) as ser:
                    self.ser = ser
                    self.mainloop()
        except KeyboardInterrupt:
            return

    def mainloop(self):
        while True:
            try:
                # try and receive data (a packet),
                got_packet = self.receive() #TODO: do this even if self.only_send_tx_cmd???

                if self.file_input == None:
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

        if self.ser is not None:
            # grab all the data we can off the serial line
            inwaiting = self.ser.in_waiting
            if inwaiting > 0:
                self.rx_buf += hexlify(self.ser.read(size=inwaiting))
                self.last_data_rx = datetime.datetime.now()

        elif self.file_input is not None:
            self.rx_buf += self.file_input.read(self.file_input_read_size)
            self.last_data_rx = datetime.datetime.now()
        else:
            return False

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
            got_response, self.rx_buf = transmit.sendUplink(command["cmd"],\
                command["response"], self.ser, rx_buf=self.rx_buf)
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
        highest_elevation_time = datetime.datetime.now() # TODO: get from API
        now = datetime.datetime.now()
        if EQUiStation.dtime_within(now, highest_elevation_time,\
            EQUiStation.FREQ_SWITCH_TIME_WINDOW_S):
            # TODO: and not close to when we expect a packet might come in

            frequency_hz = int(435.55*10e6) # TODO: get from API
            radio_control.enterCommandMode(self.ser)
            # TODO: switch pre-programmed channels?
            radio_control.setRxFreq(frequency_hz, 0)
            radio_control.setTxFreq(frequency_hz, 0)
            radio_control.exitCommandMode(self.ser)
            return True

        return False

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
            logging.info("found packet, correcting & sending...")
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
        self.rx_buf = self.rx_buf[lastindex+EQUiStation.PACKET_STR_LEN:]
        return True

    def publish_packet(self, raw, corrected, parsed, errors_corrected, route=PACKET_PUB_ROUTE):
        """ Sends a POST request to the given API route to publish the packet. """
        json = {"raw": raw, "corrected": corrected, "transmission": parsed, \
                "secret": creds.station_secret, "station_name": creds.station_name, \
                "errors_corrected": errors_corrected }
        #requests.post(route, json=json) # TODO: don't wanna spam

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
    # Doppler correct helpers
    ##################################################################
    @staticmethod
    def dtime_within(dtime1, dtime2, window_s):
        """ Returns whether the two datetimes are within window_s seconds of eachother """
        dtime1_secs = (dtime1-datetime.datetime(1970,1,1)).total_seconds()
        dtime2_secs = (dtime2-datetime.datetime(1970,1,1)).total_seconds()
        return abs(dtime1_secs - dtime2_secs) <= window_s

def main():
    gs = EQUiStation()
    if USE_TEST_FILE:
        gs.run(filename=TEST_FILE)
    else:
        gs.run(serial_port=config.SERIAL_PORT, serial_baud=config.SERIAL_BAUD)

if __name__ == "__main__":
    #print(trim_buffer("cats are cool", 4, 4)) # should be "cool"
    main()
