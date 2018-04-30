#!/usr/bin/python
# The primary script for reading incoming transmissions from
# the XDL Micro over serial, performing error correcting, and
# sending the data to BSE's server.
import os
import re
import serial
import traceback
from binascii import hexlify, unhexlify
import requests
import groundstation_config as config
from reedsolomon import rscode

# TODO: logging

# config
SERIAL_PORT = "/dev/ttyAMA0"
PACKET_PUB_ROUTE = "http://api.brownspace.org/equisat/receive_data"
CALLSIGN_HEX = "574c39585a" # WL9XZE
PACKET_STR_LEN = 2*255 # two hex char per byte
MAX_BUF_SIZE = 4096
packet_regex = re.compile("(%s.{%d})" % \
    (CALLSIGN_HEX, PACKET_STR_LEN-len(CALLSIGN_HEX)))

# testing
USE_TEST_FILE = True
TEST_FILE_READ_SIZE = PACKET_STR_LEN/2
test_file = "./Test Dumps/test_packet_logfile.txt"


def send_packet(raw, corrected, route=PACKET_PUB_ROUTE):
    """ Sends a POST request to the given API route to publish the packet. """
    json = {"raw": raw, "corrected": corrected, \
            "station_id": config.station_id, "station_name": config.station_name }
    #requests.post(route, json=json) # TODO: don't wanna spam

def correct_packet(raw):
    """ Calls Reed-Solomon error correcting scripts to apply parity byte corrections to the given raw HEX packet """
    # should always contain an even number of hex chars
    raw_bin = unhexlify(raw)
    return hexlify(rscode.decode(raw_bin))

def extract_packets(buf):
    """ Attempts to find and extract full packets from the given buffer based on callsign matching.
        Also returns a parrallel list of starting indexes of the packets in the buffer. """
    packets = packet_regex.findall(buf)
    indexes = [buf.index(packet) for packet in packets]
    return packets, indexes

def scan_for_packets(buf):
    """ Scans for raw HEX packets in the given buffer and sends any found
        to a server. Also trims the buffer before the end of the last packet.
    """
    packets, indexes = extract_packets(buf)
    if len(packets) == 0:
        return buf

    # error correct and send packets to API
    for raw in packets:
        print("found packet, correcting & sending...")
        corrected = correct_packet(raw)
        print("raw:\n%s \ncorrected:\n%s" % (raw, corrected))
        send_packet(raw, corrected)

    # trim buffer so it starts right past the end of last parsed packet
    lastindex = indexes[len(indexes)-1]
    return buf[lastindex+PACKET_STR_LEN:]

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
            with serial.Serial(SERIAL_PORT, 38400, timeout=None) as ser:
                mainloop(ser_input=ser)
    except KeyboardInterrupt:
        return

def mainloop(ser_input=None, file_input=None):
    data_buf = ""
    while True:
        try:
            if ser_input is not None:
                # grab all the data we can off the serial line
                inwaiting = ser.in_waiting
                if inwaiting > 0:
                        data_buf += hexlify(ser.read(size=inwaiting))

            elif file_input is not None:
                data_buf += file_input.read(TEST_FILE_READ_SIZE)
            else:
                return

            # look for (and extract/send) any packets in the buffer, trimming
            # the buffer after finding any
            data_buf = scan_for_packets(data_buf)
            # also try and trim the buffer if it exceeds a max size,
            # making sure to leave at least a packet's worth of characters
            # in case one is currently coming in
            data_buf = trim_buffer(data_buf, MAX_BUF_SIZE, PACKET_STR_LEN)

        except KeyboardInterrupt:
            break
        except Exception, e:
            print("EXCEPTION: %s" % e)
            print(traceback.format_exc())
            continue

if __name__ == "__main__":
    #print(trim_buffer("cats are cool", 4, 4)) # should be "cool"

    main()
