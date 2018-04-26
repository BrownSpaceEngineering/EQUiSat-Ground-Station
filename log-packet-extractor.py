#!/usr/bin/python
# Script to extract hex packets from a log file dumped by EQUiSatOS in with the PRINT_HEX_TRANSMISSIONS flag defined.
import sys
import csv
import re
import packetparse
import groundstation

WRITE_PARSED = False

def check_line_for_packets(line, outwriter):
    packets = groundstation.extract_packets(line)
    for packet in packets:
        # parse too if asked
        parsed = ""
        if WRITE_PARSED:
            parsed = packetparse.parse_packet(packet)

        outwriter.writerow([packet, parsed])

    return len(packets)

def parse_packets(filename, outfile):
    num_found = 0
    with open(filename, "r") as log:
        with open(outfile, "w") as out:
            outwriter = csv.writer(out)
            while True:
                line = log.readline()
                if line == "":
                    return num_found
                else:
                    num_found += check_line_for_packets(line, outwriter)

def main():
    if len(sys.argv) != 3:
        print("usage: ./log-packet-extractor.py <log file> <output csv>")
    else:
        num_found = parse_packets(sys.argv[1], sys.argv[2])
        print("Found %d packets" % num_found)

if __name__ == "__main__":
    main()
