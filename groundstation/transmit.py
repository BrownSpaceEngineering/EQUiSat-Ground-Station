#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import sys, time, binascii, csv, logging, serial, struct
import config

TX_RESPONSE_TIMEOUT_S = 1.0

def loadUplinkCommands(filename):
	try:
		with open(filename) as file:
			#format of csv is "name": "test",
			reader = csv.reader(file)
			next(reader)
			cmds = dict(reader)
			return cmds
	except (IOError):
		logging.error("Could not find file: " + filename)

def sendUplink(cmd, response, ser, repeats=1):
	""" Attempts to send uplink command and waits for a time to receive
		the expected response. Returns whether the response was found
		and the updated rx_buf. """
	rx_buf = ""
	num_repeats = 0
	while num_repeats < repeats:
		oldtime = time.time()
		ser.write(cmd)
		while (time.time() - oldtime) < TX_RESPONSE_TIMEOUT_S:
			logging.debug("searching for response...")
			inwaiting = ser.in_waiting
			if (inwaiting) > 0:
				rx_buf += ser.read(size=inwaiting)

			# search for expected response in RX buffer
			index = rx_buf.find(response)
			if index != -1:
				fullResponse = ""
				if index + RESPONSE_LEN < len(rx_buf):
					fullResponse = rx_buf[index:index+RESPONSE_LEN]
				else:
					fullResponse = rx_buf[index:]

				# https://stackoverflow.com/a/12214880
				logging.info("got uplink command response: %s (%s)" % (fullResponse, \
					":".join("{:02x}".format(ord(c)) for c in fullResponse)))
				return True, rx_buf

			time.sleep(.1)
		num_repeats += 1

	return False, rx_buf

def uplinkTests(cmds, ser):
	sendUplink(cmds['echo_cmd'], config.UPLINK_RESPONSES['echo_cmd'], ser)
	sendUplink(cmds['kill3_cmd'], config.UPLINK_RESPONSES['kill3_cmd'], ser)
	sendUplink(cmds['kill7_cmd'], config.UPLINK_RESPONSES['kill7_cmd'], ser)
	sendUplink(cmds['killf_cmd'], config.UPLINK_RESPONSES['killf_cmd'], ser)
	sendUplink(cmds['flash_cmd'], config.UPLINK_RESPONSES['flash_cmd'], ser)
	sendUplink(cmds['reboot_cmd'], config.UPLINK_RESPONSES['reboot_cmd'], ser)
	sendUplink(cmds['revive_cmd'], config.UPLINK_RESPONSES['revive_cmd'], ser)
	sendUplink(cmds['flashkill_cmd'], config.UPLINK_RESPONSES['flashkill_cmd'], ser)
	sendUplink(cmds['flashrevive_cmd'], config.UPLINK_RESPONSES['flashrevive_cmd'], ser)

def xdl_sweep_test(ser):
    for i in range(255):
        ser.write(chr(i)*1000)
        print("i: %d" % i)
        time.sleep(0.5)
        print ser.read(size=ser.in_waiting),

def xdl_test(ser):
    for i in range(3):
        ser.write(chr(0)*1000)
        time.sleep(0.5)
        #print ser.read(size=ser.in_waiting),
        ser.write(chr(255)*1000)
        time.sleep(0.5)
        #print ser.read(size=ser.in_waiting),

    for i in range(3):
        ser.write(chr(0b01010101)*1000)
        time.sleep(0.5)

    for i in range(3):
        ser.write(chr(0b10101010)*1000)
        time.sleep(0.5)

    for i in range(3):
        ser.write("equisat "*500)
        time.sleep(0.5)

    time.sleep(10)

def ping_test(ser):
	try:
	    while True:
	        print("transmitting")
	        ser.write("equisat " * 100)
	        time.sleep(2)
	except KeyboardInterrupt:
		return

tests = {
	"xdl_sweep_test": xdl_sweep_test,
	"xdl_test": xdl_test,
	"ping_test": ping_test
}
usage = "usage: ./transmit.py <test name>\ntest names: %s" % tests.keys()

def main():
	# command line args
	if len(sys.argv) < 2 or not tests.has_key(sys.argv[1]) or len(sys.argv) > 2:
	    print(usage)
            exit()
	testName = sys.argv[1]

	# setup
	ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
	cmds = loadUplinkCommands(config.UPLINK_COMMANDS_FILE)
	print("uplink commands: %s" % cmds)

	# run requested test
	tests[testName](ser)

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	main()
