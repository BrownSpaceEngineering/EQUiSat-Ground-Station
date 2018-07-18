#!/usr/bin/python
import random, binascii

# A mock serial class that can be hot-swapped with serial.Serial to emulate it.
class MockSerial:
    def __init__(self, infile_name=None, outfile_name=None, max_inwaiting=100, unhex=False):
        self.infile = open(infile_name, "r")
        self.outfile = open(outfile_name, "w")

        self.unhex = unhex
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
        val = random.randint(1, self.max_inwaiting)
        if self.unhex and val % 2 != 0:
            val -= 1
        return val

    def write(self, data):
        if self.outfile is not None:
            self.outfile.write(data)

    def read(self, size=-1):
        if size == -1:
            size = self.in_waiting
        self._rand_in_waiting()

        ret = ""
        if self.infile is None:
            ret = chr(random.random.randint(255))*size
        else:
            # wrap around when can't read anymore
            ret = self.infile.read(size)
            if len(ret) < size:
                self.infile.seek(0)

        if self.unhex:
            return binascii.unhexlify(ret)
        else:
            return ret

    def close(self):
        if self.outfile is not None:
            self.outfile.close()
        if self.infile is not None:
            self.infile.close()

    def flush(self):
        if self.outfile is not None:
            self.outfile.flush()
        if self.infile is not None:
            self.infile.flush()
