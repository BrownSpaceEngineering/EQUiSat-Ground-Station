#!/usr/bin/python
import binascii
import random
import re
import logging


# A mock serial class that can be hot-swapped with serial.Serial to emulate it.
class MockSerial:
    def __init__(self, infile_name=None, outfile_name=None, max_inwaiting=100):
        self.infile = open(infile_name, "r")
        self.outfile = open(outfile_name, "w")

        self.max_inwaiting = max_inwaiting

        # write cbs are tried on each write,
        # and any responses based on those are stacked (FIFO) in the response_queue
        self.write_cbs = []
        self.response_queue = []

        # important class members
        self.in_waiting = self._rand_in_waiting()

    def __del__(self):
        self.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def on(self, regex, response=None, responder=None, in_hex=False):
        """ Registers a handler for any single write events that match regex.
        If response is not None, that string will be returned.
        Otherwise if responder is not None it will be passes the input
        and must return the desired response.
        Also converts to hex for regex matching and as input to the responder if specified.
        (note output from responder is not converted at all)"""
        if response is not None:
            self.write_cbs.append({
                "regex": re.compile(regex),
                "hex": in_hex,
                "responder": lambda _: response
            })
        elif responder is not None and type(responder) == function:
            self.write_cbs.append({
                "regex": re.compile(regex),
                "hex": in_hex,
                "responder": responder
            })
        else:
            raise ValueError

    def write(self, data):
        # check if we need to use a write handler to register a later response
        for resp in self.write_cbs:
            data_to_match = data
            if resp["hex"]:
                data_to_match = binascii.hexlify(data)
            if resp["regex"].match(data_to_match):
                response = ""
                try:
                    response = str(resp["responder"](data_to_match)) # cast so uniform type
                except Exception as e:
                    logging.error("exception in MockSerial during responder call on %s: %s" % (data_to_match, e))
                self.response_queue.append(response)
                # responders should be independent, but add all responses if multiple

        if self.outfile is not None:
            self.outfile.write(data)

    def read(self, size=-1):
        # read an amount of data according to the previous in_waiting,
        # but update in_waiting here so that any later calls will see what will be read on
        # the next read() call
        if size == -1:
            size = self.in_waiting
        self.in_waiting = self._rand_in_waiting()

        # however, if there is a response waiting we will just ignore in_waiting
        # (applications can't expect any in_waiting they grab to be correct on read anyways)
        if len(self.response_queue) > 0:
            response = self.response_queue[0]
            if len(response) <= size:
                # remove response from queue
                self.response_queue.pop(0)
                # return all of response but nothing else (less than size is fine)
                return response
            else:  # len(response) > size
                # remove what we've written from queue element
                self.response_queue[0] = response[size:]
                # take only what part we need; rest will be taken next time
                return response[:size]

        elif self.infile is None:
            return self._rand_seq(size)

        else:
            # wrap around when can't read anymore
            data = self.infile.read(size)
            if len(data) < size:
                self.infile.seek(0)
            return data

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

    def _rand_in_waiting(self):
        return random.randint(1, self.max_inwaiting)

    def _rand_seq(self, size):
        seq = ""
        for i in range(size):
            seq += chr(random.randint(0, 255))
        return seq
