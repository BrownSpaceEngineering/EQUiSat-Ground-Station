#!/usr/bin/python
# Script to grab a subset of rows from a .CSV produced by log-packet-extractor
import sys
import csv
import random
from groundstation.packetparse.packetparse import get_message_type
from log_packet_extractor import CSV_HEADERS

BUF_SIZE = 128

def nrandom(array, n):
    if len(array) > n:
        random.shuffle(array)
        return array[:n]
    else:
        return array

def extract(incsv_file, buf_size):
    with open(incsv_file, "r") as incsv:
        reader = csv.DictReader(incsv)

        types = [[], [], [], [], []]
        cur_types = [[], [], [], [], []]
        row_i = 0
        for row in reader:
            for i in range(5):
                if row["parsed message type"] == get_message_type(i):
                    cur_types[i].append(row)

                # only append one out of every buffer
                if row_i % buf_size == 0 and len(cur_types[i]) > 0:
                    types[i].append(nrandom(cur_types[i], 1)[0])
                    cur_types[i] = []

            row_i += 1

        return types

def reduce(types, outcsv_file, num_per_type):
    with open(outcsv_file, "w") as outcsv:
        writer = csv.DictWriter(outcsv, CSV_HEADERS)
        writer.writeheader()

        counts = [0,0,0,0,0]
        for i in range(5):
            for pkt_row in nrandom(types[i], num_per_type):
                writer.writerow(pkt_row)
                counts[i] += 1
        return counts

def main():
    if len(sys.argv) != 4:
        print("usage: ./log_csv_cleaner.py <input csv> <output csv> <num of each msg type>")
    else:
        num = int(sys.argv[3])
        types = extract(sys.argv[1], BUF_SIZE)
        counts = reduce(types, sys.argv[2], num)
        for i in range(len(counts)):
            print("Found %d packets of type %s" % (counts[i], get_message_type(i)))

if __name__ == "__main__":
    main()
