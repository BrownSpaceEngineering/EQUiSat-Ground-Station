#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import sys, time, binascii, csv, logging, serial, struct

serial_port = "/dev/ttyAMA0"
ser = serial.Serial(serial_port, 38400, timeout=None)

# radio config settings
set_dealer_mode_buf = bytearray(b'\x01\x44\x01\xba\x00')
set_tx_freq = bytearray(b'\x01\x37\x01\x19\xf5\xf7\x30\x90\x00')
set_rx_freq = bytearray(b'\x01\x39\x01\x19\xf5\xf7\x30\x8E\x00')
set_channel = bytearray(b'\x01\x03\x01\xfb\x00')
set_bandwidth = bytearray(b'\x01\x70\x04\x01\x8a\x00')
set_modulation = bytearray(b'\x01\x2b\x01\xd3')
program = bytearray(b'\x01\x1e\xe1\x00')
delete_channel = bytearray(b'\x01\x70\x01\x01\x8d\x00')


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

def configRadio():
	sendConfigCommand("+++")
	print("Setting dealer mode")
	sendConfigCommand(set_dealer_mode_buf)
	print("Setting Channel")
	sendConfigCommand(set_channel)
	print("Setting rx freq")
	sendConfigCommand(set_rx_freq)
	print("Setting tx freq")
	sendConfigCommand(set_tx_freq)
	print("setting bandwidth")
	sendConfigCommand(set_bandwidth)
	print("setting modulation")
	sendConfigCommand(set_modulation)
	print("programming")
	sendConfigCommand(program)

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

def sendConfigCommand(buf):
	print("Sending Command: " + binascii.hexlify(data))
	ser.write(buf)
	oldtime = time.time()
	while (time.time() - oldtime) < 2:
		inwaiting = ser.in_waiting
		if (inwaiting) > 0:
			data = ser.read(size=inwaiting)
			print("Response: " + binascii.hexlify(data))
	time.sleep(0.25)

def sendUplink(cmd, response):
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

def uplinkTests(cmds):
	sendUplink(cmds['echo_cmd'], uplinkResponses['echo_cmd'])
	sendUplink(cmds['kill3_cmd'], uplinkResponses['kill3_cmd'])
	sendUplink(cmds['kill7_cmd'], uplinkResponses['kill7_cmd'])
	sendUplink(cmds['killf_cmd'], uplinkResponses['killf_cmd'])
	sendUplink(cmds['flash_cmd'], uplinkResponses['flash_cmd'])
	sendUplink(cmds['reboot_cmd'], uplinkResponses['reboot_cmd'])
	sendUplink(cmds['revive_cmd'], uplinkResponses['revive_cmd'])
	sendUplink(cmds['flashkill_cmd'], uplinkResponses['flashkill_cmd'])
	sendUplink(cmds['flashrevive_cmd'], uplinkResponses['flashrevive_cmd'])

def getSetFreqCommandBuf(freqInHZ, channelNum, isTX):
	#structure is [Start of Header, Command #, Channel #, Freq Byte #1, Freq Byte #2, Freq Byte #3, Freq Byte #4, checksum]
	#Byte #1 is MSB
	freq_bytes = bytearray.fromhex('{:4x}'.format(freqInHZ))
	command_type_byte = bytearray(b'\x37') if isTX else bytearray(b'\x39')
	channel_num_byte = bytearray(chr(channelNum))	
	command_buf_payload = command_type_byte + channel_num_byte + freq_bytes 
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	start_of_header = bytearray(b'\x01')
	full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00') #need to null terminate string
	return full_command_buf

def setRxFreq(freqInHZ, channelNum):
	setRxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, False)
	sendConfigCommand(setRxCommandBuf)

def setTxFreq(freqInHZ, channelNum):
	setTxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, True)
	sendConfigCommand(setTxCommandBuf)

def main():
	cmds = loadUplinkCommands('uplink_commands.csv')
	print(cmds)
	uplinkTests(cmds)

if __name__ == "__main__":
	main()
