import subprocess

NPAR = 32

class ERROR:
    PROG_ERROR, INVALID_HEX, TOO_CORRUPT

def encode(hex_msg):
    """ Encodes the given hex message using Reed Solomon, using the library default of 32 parity bytes. The returned message will have those bytes appended.
    Returns the encoded message in hex and any error."""
    p1 = subprocess.Popen(['./rsencode', str(hex_msg), str(len(hex_msg))],\
        stdout=subprocess.PIPE)
    encoded_msg, err = p1.communicate()

    if p1.returncode == 1:
        return "", INVALID_HEX
    if len(err) > 0 or len(encoded_msg) != len(hex_msg) + 2*NPAR or p1.returncode != 0:
        return "", PROG_ERROR
    else:
        return encoded_msg, None

def decode(hex_data, npar=NPAR):
    """ Decodes the given hex data using Reed Solomon, using npar number of parity bytes assumed to be on the end. The returned message will have no parity bytes.
    Returns the decoded message in hex and any error. """
    p2 = subprocess.Popen(['./rsdecode', str(hex_data), str(len(hex_data)), str(npar)],\
        stdout=subprocess.PIPE)
    decoded_msg, err = p2.communicate()

    if p2.returncode == 1:
        return "", INVALID_HEX
    if p2.returncode == 2:
        return "", TOO_CORRUPT
    if len(err) > 0 or len(decoded_msg) != len(hex_data) - 2*NPAR or p2.returncode != 0:
        return "", PROG_ERROR
    else:
        return decoded_msg, None
