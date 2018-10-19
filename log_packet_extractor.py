#!/usr/bin/python
# Script to extract hex packets from a log file dumped by EQUiSatOS in with the PRINT_HEX_TRANSMISSIONS flag defined.
import sys
import csv
from binascii import hexlify
from groundstation import groundstation
from groundstation.packetparse import packetparse
import json

CONVERT_TO_HEX = False # as opposed to assuming it's in hex
WRITE_PARSED = True
CSV_HEADERS = ["packet", "valid (only hex chars)", "parsed timestamp", "parsed message type", "parsed sat state", "full parsed JSON"]

def check_line_for_packets(line, outwriter):
    if CONVERT_TO_HEX:
        line = hexlify(line)

    packets, _ = groundstation.EQUiStation.extract_packets(line)
    for packet in packets:
        # whether valid
        valid = packetparse.is_hex_str(packet)

        # grab some metadata
        try:
            preamble = {"timestamp": -1, "message_type": "[corrupted]", "satellite_state": "[corrupted]"}
            if valid:
                preamble = packetparse.parse_preamble(packet)

            # parse too if asked
            parsed = ""
            if WRITE_PARSED and valid:
                parsed, _ = packetparse.parse_packet(packet)

            outwriter.writerow([packet, valid, preamble["timestamp"], preamble["message_type"], preamble["satellite_state"], json.dumps(parsed, indent=4)])
        except KeyError:
            continue # parsing error

    return len(packets)

def parse_packets(filename, outfile):
    num_found = 0
    with open(filename, "r") as log:
        with open(outfile, "w") as out:
            outwriter = csv.writer(out)
            outwriter.writerow(CSV_HEADERS)

            while True:
                line = log.readline()
                if line == "":
                    return num_found
                else:
                    num_found += check_line_for_packets(line, outwriter)

def main():
    if len(sys.argv) != 3:
        print("usage: ./log_packet_extractor.py <log file> <output csv>")
    else:
        num_found = parse_packets(sys.argv[1], sys.argv[2])
        print("Found %d packets" % num_found)

if __name__ == "__main__":
    main()
