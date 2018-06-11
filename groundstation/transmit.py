#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import sys, time, binascii, csv, logging, serial, struct
import config

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

def sendUplink(cmd, response, ser, rx_buf=""):
	""" Attempts to send uplink command and waits for a time to receive
		the expected response. Returns whether the response was found
		and the update rx_buf. """
	while True:
		oldtime = time.time()
		ser.write(cmd)
		while (time.time() - oldtime) < .5:
			logging.info("searching for response...")
			inwaiting = ser.in_waiting
			if (inwaiting) > 0:
					rx_buf += ser.read(size=inwaiting)

			# search for expected response in RX buffer
			index = data.find(response)
			if index != -1:
				fullResponse = ""
				if index + RESPONSE_LEN < len(rx_buf):
					fullResponse = rx_buf[index:index+RESPONSE_LEN]
				else:
					fullResponse = rx_buf[index:]

				# https://stackoverflow.com/a/12214880
				logging.info("got TX response: %s (%s)" % (fullResponse, \
					":".join("{:02x}".format(ord(c)) for c in s)))
				return True, rx_buf

			time.sleep(.1)
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

def main():
	ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
	cmds = loadUplinkCommands(config.UPLINK_COMMANDS_FILE)
	print(cmds)
	uplinkTests(cmds, ser)

if __name__ == "__main__":
	logging.basicConfig(level=logging.INFO)
	main()
