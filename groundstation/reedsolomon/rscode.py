#!/usr/bin/python
import os
import subprocess

NPAR = 32

EXEC_DIR = os.path.dirname(os.path.abspath(__file__))

class ERROR:
    PROG_ERROR = "program execution error"
    INVALID_HEX = "invalid input hex string"
    TOO_CORRUPT = "packet had too many errors"

def encode(hex_msg):
    """ Encodes the given hex message using Reed Solomon, using the library default of 32 parity bytes. The returned message will have those bytes appended.
    Returns the encoded message in hex and any error."""
    p1 = subprocess.Popen([EXEC_DIR + '/rsencode', str(hex_msg)], stdout=subprocess.PIPE)
    encoded_msg, err = p1.communicate()

    if p1.returncode == 1:
        return "", ERROR.INVALID_HEX
    if encoded_msg == None or err != None \
        or len(encoded_msg) != len(hex_msg) + 2*NPAR \
        or p1.returncode != 0:
        return "", ERROR.PROG_ERROR
    else:
        return encoded_msg, None

def decode(hex_data, npar=NPAR):
    """ Decodes the given hex data using Reed Solomon, using npar number of parity bytes assumed to be on the end. The returned message will have no parity bytes.
    Returns the decoded message in hex and any error. """
    p2 = subprocess.Popen([EXEC_DIR + '/rsdecode', str(hex_data), str(npar)],\
        stdout=subprocess.PIPE)
    decoded_msg, err = p2.communicate()

    if p2.returncode == 1:
        return "", ERROR.INVALID_HEX
    if p2.returncode == 2:
        return "", ERROR.TOO_CORRUPT
    if decoded_msg == None or err != None \
        or len(decoded_msg) != len(hex_data) - 2*NPAR \
        or p2.returncode != 0:
        return "", ERROR.PROG_ERROR
    else:
        return decoded_msg, None
