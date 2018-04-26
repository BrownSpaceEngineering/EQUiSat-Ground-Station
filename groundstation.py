#!/usr/bin/python
# The primary script for reading incoming transmissions from
# the XDL Micro over serial, performing error correcting, and
# sending the data to BSE's server.
import os
import re


# config
SERIAL_PORT = "/dev/ttyAMA0"
PACKET_PUB_ROUTE = "api.brownspace.org/equisat/receive_data"
CALLSIGN_HEX = "574c39585a" # WL9XZE
PACKET_STR_LEN = 2*255 # two hex char per byte
packet_regex = re.compile("(%s.{%d})" % \
    (CALLSIGN_HEX, PACKET_STR_LEN-len(CALLSIGN_HEX)))

def send_packet(raw, corrected, route=PACKET_PUB_ROUTE):
    """ Sends a POST request to the given API route to publish the packet. """
    # TODO
    pass

def correct_packet(raw):
    """ Calls Reed-Solomon error correcting scripts to apply parity byte corrections to the given raw packet """
    # TODO
    return ""

def extract_packets(buf):
    """ Attempts to find and extract full packets from the given buffer based on callsign matching """
    packets = packet_regex.findall(buf)
    return packets

def scan_for_packets(buf):
    packets = extract_packets(line)
    for packet in packets:
        corrected = correct_packet(raw)
        send_packet(raw, corrected)

def mainloop():
    data_buf = ""
    try:
        with serial.Serial(SERIAL_PORT, 38400, timeout=None) as ser:
            while True:
                try:
                    # TODO: do fancier delaying/work with inwaiting
                    data_buf += ser.read()
                    scan_for_packets(data_buf)

                except KeyboardInterrupt:
                    break
                except Exception, e:
                    print("ERROR: %s" % e)
                    continue

    except KeyboardInterrupt:
        pass
