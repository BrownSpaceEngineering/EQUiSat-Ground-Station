#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import os, sys, serial, datetime, time

dumps_direc = "./receiveTest_dumps"
def generate_new_outfile():
    try:
        os.mkdir(dumps_direc)
    except OSError:
        pass

    return dumps_direc + "/recieveTest_dump_" + datetime.datetime.now().strftime("%m.%d.%y_%H:%M") + ".txt"

# defaults
output_file = generate_new_outfile()
serial_port = "/dev/ttyAMA0"

# parse CLI args
if len(sys.argv) >= 2:
    output_file = sys.argv[1]
if len(sys.argv) == 3:
    serial_port = sys.argv[2]
if len(sys.argv) > 3:
    print("usage: recieveTest.py <output file> <serial port>")

try:
    with serial.Serial(serial_port, 38400, timeout=None) as ser:
        if len(output_file) > 0:
            with open(output_file, "a") as f:
                while True:
                    try:
                        data = ser.read(size=1)
                        f.write(data)
                        f.flush()
                        sys.stdout.write(data)
                        sys.stdout.flush()
                    except KeyboardInterrupt:
                        break
                    except:
                        continue

except KeyboardInterrupt:
    pass
