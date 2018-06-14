#!/usr/bin/python
import random

# A mock serial class that can be hot-swapped with serial.Serial to emulate it.
class MockSerial:
    def __init__(self, infile_name=None, outfile_name=None, max_inwaiting=100):
        self.infile = open(infile_name, "r")
        self.outfile = open(outfile_name, "w")

        self.max_inwaiting = max_inwaiting

        # important class members
        self.in_waiting = self._rand_in_waiting()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def _rand_in_waiting(self):
        return random.randint(0, self.max_inwaiting)

    def write(self, data):
        if self.outfile != None:
            self.outfile.write(data)

    def read(self, size=-1):
        if size == -1:
            size = self.in_waiting
        self._rand_in_waiting()

        if self.infile == None:
            return chr(random.random.randint(255))*size
        else:
            return self.infile.read(size)

    def close(self):
        if self.outfile != None:
            self.outfile.close()
        if self.infile != None:
            self.infile.close()
