#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import sys, time, binascii, csv, logging, serial, struct
import config

# uplink command responses
RESPONSE_LEN = 9
uplinkResponses = {
	"echo_cmd": "ECHOCHOCO",
	"kill3_cmd": "KILLN", # plus 4 more bytes of revive timestamp
	"kill7_cmd": "KILLN",
	"killf_cmd": "KILLN",
	"flash_cmd": "FLASHING", # last byte is whether will flash
	"reboot_cmd": "REBOOTING",
	"revive_cmd": "REVIVING!",
	"flashkill_cmd": "FLASHKILL",
	"flashrevive_cmd": "FLASHREV!"
}

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

def sendUplink(cmd, response, ser):
	data = ""
	while True:
		oldtime = time.time()
		ser.write(cmd)
		while (time.time() - oldtime) < .5:
			print("searching for response...")
			inwaiting = ser.in_waiting
			if (inwaiting) > 0:
					data += ser.read(size=inwaiting)

			index = data.find(response)
			if index != -1:
				fullResponse = ""
				if index + RESPONSE_LEN < len(data):
					fullResponse = data[index:index+RESPONSE_LEN]
				else:
					fullResponse = data[index:]

				print("GOT RESPONSE: %s (%s)" % (fullResponse, \
					":".join("{:02x}".format(ord(c)) for c in s))) # https://stackoverflow.com/a/12214880
				return fullResponse

			time.sleep(.1)

def uplinkTests(cmds, ser):
	sendUplink(cmds['echo_cmd'], uplinkResponses['echo_cmd'], ser)
	sendUplink(cmds['kill3_cmd'], uplinkResponses['kill3_cmd'], ser)
	sendUplink(cmds['kill7_cmd'], uplinkResponses['kill7_cmd'], ser)
	sendUplink(cmds['killf_cmd'], uplinkResponses['killf_cmd'], ser)
	sendUplink(cmds['flash_cmd'], uplinkResponses['flash_cmd'], ser)
	sendUplink(cmds['reboot_cmd'], uplinkResponses['reboot_cmd'], ser)
	sendUplink(cmds['revive_cmd'], uplinkResponses['revive_cmd'], ser)
	sendUplink(cmds['flashkill_cmd'], uplinkResponses['flashkill_cmd'], ser)
	sendUplink(cmds['flashrevive_cmd'], uplinkResponses['flashrevive_cmd'], ser)

def main():
	ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
	cmds = loadUplinkCommands('uplink_commands.csv')
	print(cmds)
	uplinkTests(cmds, ser)

if __name__ == "__main__":
	main()
