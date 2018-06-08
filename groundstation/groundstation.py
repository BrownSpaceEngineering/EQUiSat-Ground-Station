#!/usr/bin/python
# The primary script for reading incoming transmissions from
# the XDL Micro over serial, performing error correcting, and
# sending the data to BSE's server.
import os
import re
import serial
import time
import logging
from binascii import hexlify, unhexlify
import requests

import groundstation_credentials as creds
import config
from reedsolomon import rscode
from packetparse import packetparse
import transmit

# config
PACKET_PUB_ROUTE = "http://api.brownspace.org/equisat/receive_data"
CALLSIGN_HEX = "574c39585a" # WL9XZE
PACKET_STR_LEN = 2*255 # two hex char per byte
MAX_BUF_SIZE = 4096
packet_regex = re.compile("(%s.{%d})" % \
    (CALLSIGN_HEX, PACKET_STR_LEN-len(CALLSIGN_HEX)))

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)

# testing
USE_TEST_FILE = True
TEST_FILE_READ_SIZE = PACKET_STR_LEN/2
test_file = "../Test Dumps/test_packet_logfile.txt"

def mainloop(ser=None, file_input=None):
    rx_buf = ""
    tx_cmd_queue = [] # TODO: method to populate
    while True:
        try:
            # sequence: try and receive data (a packet),
            # then if we did try and send any TX commands,
            # and then try to adjust the frequency for doppler effects
            rx_buf, got_packet = receive(rx_buf, ser=ser, file_input=file_input)

            if got_packet: # TODO: OR "transmit constantly" option
                rx_buf, _, _ = transmit(tx_cmd_queue, rx_buf, ser=ser, file_input=file_input)

            if True: # "close to time of highest elevation AND not close to expected packet RX"
                doppler_correct(ser=ser, file_input=file_input)

            time.sleep(0.1)

        except KeyboardInterrupt:
            break

##################################################################
# Groundstation states
##################################################################
def receive(rx_buf, ser=None, file_input=None):
    """ Attempts to receive, process, and store data received from the radio.
        Returns whether a packet was detected. """

    if ser is not None:
        # grab all the data we can off the serial line
        inwaiting = ser.in_waiting
        if inwaiting > 0:
            rx_buf += hexlify(ser.read(size=inwaiting))

    elif file_input is not None:
        rx_buf += file_input.read(TEST_FILE_READ_SIZE)
    else:
        return False

    # look for (and extract/send) any packets in the buffer, trimming
    # the buffer after finding any. (Only finds full packets)
    rx_buf, got_packet = scan_for_packets(rx_buf)
    # also try and trim the buffer if it exceeds a max size,
    # making sure to leave at least a packet's worth of characters
    # in case one is currently coming in
    rx_buf = trim_buffer(rx_buf, MAX_BUF_SIZE, PACKET_STR_LEN)

    return rx_buf, got_packet

def transmit(tx_cmd_queue, rx_buf, ser=None, file_input=None):
    """ Checks if there are any uplink commands on the queue and transmits
        them/waits for response if so.
        Returns whether anything was transmitted and whether it was successful. """

    if len(tx_cmd_queue) > 0:
        command = tx_cmd_queue.pop(0)
        got_response, rx_buf = sendUplink(command["cmd"], command["response"], ser, rx_buf=rx_buf)
        if got_response:
            return rx_buf, True, True
        else:
            tx_cmd_queue.insert(0, command) # add back command
            return rx_buf, True, False
    else:
        return rx_buf, False, False

def doppler_correct(ser=None, file_input=None):
    """ Shifts the receive and transmit frequency of the XDL micro to compensate
        for doppler shift based on the current estimated position of the satellite.
        Returns whether the correction was mrx_bufrx_bufade. """
    # TODO: switch pre-programmed channels (or just set frequency)
    pass


##################################################################
# Receive/Decode Helpers
##################################################################
def publish_packet(raw, corrected, parsed, errors_corrected, route=PACKET_PUB_ROUTE):
    """ Sends a POST request to the given API route to publish the packet. """
    json = {"raw": raw, "corrected": corrected, "transmission": parsed, \
            "secret": creds.station_secret, "station_name": creds.station_name, \
            "errors_corrected": errors_corrected }
    #requests.post(route, json=json) # TODO: don't wanna spam

def extract_packets(buf):
    """ Attempts to find and extract full packets from the given buffer based on callsign matching.
        Also returns a parrallel list of starting indexes of the packets in the buffer. """
    packets = packet_regex.findall(buf)
    indexes = [buf.index(packet) for packet in packets]
    return packets, indexes

def correct_packet_errors(raw):
    """ Corrects the packet's error using Reed Solomon error correction
    and the packet's parity bytes. Makes sure to avoid correcting the callsign. """
    assert len(raw) == PACKET_STR_LEN
    callsign = raw[:12]
    raw_no_callsign = raw[12:] # callsign is 6 chars
    corrected, error = rscode.decode(raw_no_callsign)
    return callsign + corrected, error

def scan_for_packets(buf):
    """ Scans for raw HEX packets in the given buffer and sends any found
        to a server. Also trims the buffer before the end of the last packet.
        Returns the new buffer and whether any packets were found.
    """
    logging.debug("reading buffer of size %d for packets" % len(buf))
    packets, indexes = extract_packets(buf)
    if len(packets) == 0:
        return buf, False

    # error correct and send packets to API
    for raw in packets:
        logging.info("found packet, correcting & sending...")
        corrected, error = correct_packet_errors(raw)
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
            %s""" \
            % (raw, len(corrected), errors_corrected, error, corrected, parsed))
        publish_packet(raw, corrected, parsed, errors_corrected)

    # trim buffer so it starts right past the end of last parsed packet
    lastindex = indexes[len(indexes)-1]
    return buf[lastindex+PACKET_STR_LEN:], True

def trim_buffer(buf, max_size, min_to_leave):
    """ Trims and returns the given buffer to be less than or equal to max_size,
        but makes sure to leave at least min_to_leave of the last characters in the buffer. """
    assert max_size >= min_to_leave
    if len(buf) > max_size:
        return buf[len(buf)-min_to_leave:]
    else:
        return buf

def main():
    try:
        if USE_TEST_FILE:
            with open(test_file, "r") as f:
                mainloop(file_input=f)
        else:
            with serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None) as ser:
                mainloop(ser=ser)
    except KeyboardInterrupt:
        return

if __name__ == "__main__":
    #print(trim_buffer("cats are cool", 4, 4)) # should be "cool"
    main()
