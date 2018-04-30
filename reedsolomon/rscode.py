import subprocess

NPAR = 32

def encode(msg):
    """ Encodes the given message using Reed Solomon, using the library default of 32 parity bytes. The returned message will have those bytes appended. """
    p1 = subprocess.Popen(['./rsencode', str(msg), str(len(msg))], stdout=subprocess.PIPE)
    encoded_msg, err = p1.communicate()
    if len(err) > 0 or len(encoded_msg) != len(msg) + NPAR:
        return ""
    else:
        return encoded_msg

def decode(data, npar=NPAR):
    """ Decodes the given data using Reed Solomon, using npar number of parity bytes assume to be on the end. The returned message will have no parity bytes. """
    p2 = subprocess.Popen(['./rsdecode', str(data), str(len(data)), str(npar)], stdout=subprocess.PIPE)
    decoded_msg, err = p2.communicate()
    # args = "./rsdecode {} {} {}".format(data, len(data), npar)
    # decoded_msg = os.system(args)
    if len(err) > 0 or len(decoded_msg) != len(data) - NPAR:
        return ""
    else:
        return decoded_msg
