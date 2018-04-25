#!/usr/bin/python
# Script to extract hex packets from a log file dumped by EQUiSatOS in with the PRINT_HEX_TRANSMISSIONS flag defined.
import sys
import csv
import packetparse

CALLSIGN_HEX = "574c39585a" # WL9XZE
PACKET_STR_LEN = 2*255 # two hex char per byte
WRITE_PARSED = True

def extract_packet(line):
    """ Pulls a packet from the given line, assuming the callsign bytes were found. """
    packet_start = line.index(CALLSIGN_HEX)
    packet = line[packet_start:]
    if len(packet)-1 == PACKET_STR_LEN: # ignore newline
        return packet # probably a valid packet
    else:
        return ""

def parse_packets(filename, outfile):
    num_found = 0
    with open(filename, "r") as log:
        with open(outfile, "w") as out:
            outwriter = csv.writer(out)
            while True:
                line = log.readline()
                if line == "":
                    return num_found
                elif CALLSIGN_HEX in line:
                    packet = extract_packet(line)
                    if packet != "":
                        # remove newline
                        packet = packet[:PACKET_STR_LEN]
                        # parse too if asked
                        parsed = ""
                        if WRITE_PARSED:
                            parsed = packetparse.parse_packet(packet)

                        outwriter.writerow([packet, parsed])
                        num_found += 1

def main():
    if len(sys.argv) != 3:
        print("usage: ./log-packet-extractor.py <log file> <output csv>")
    else:
        num_found = parse_packets(sys.argv[1], sys.argv[2])
        print("Found %d packets" % num_found)

if __name__ == "__main__":
    main()
