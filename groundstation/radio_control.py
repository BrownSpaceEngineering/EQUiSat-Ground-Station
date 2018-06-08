#!/usr/bin/python
# Functions to configure XDL Micro settings over serial
import sys
import time
import binascii
import serial
import struct
import logging
import config

# radio config settings
set_dealer_mode_buf = bytearray(b'\x01\x44\x01\xba\x00')
set_tx_freq = bytearray(b'\x01\x37\x01\x19\xf5\xf7\x30\x90\x00')
set_rx_freq = bytearray(b'\x01\x39\x01\x19\xf5\xf7\x30\x8E\x00')
set_channel = bytearray(b'\x01\x03\x01\xfb\x00')
set_bandwidth = bytearray(b'\x01\x70\x04\x01\x8a\x00')
set_modulation = bytearray(b'\x01\x2b\x01\xd3')
program = bytearray(b'\x01\x1e\xe1\x00')
warm_reset = bytearray(b'\x01\x1d\x01\xe1\x00')
delete_channel = bytearray(b'\x01\x70\x01\x01\x8d\x00')

def enterCommandMode(ser):
	logging.info("Setting radio to command mode")
	sendConfigCommand("+++", ser)

def exitCommandMode(ser):
	logging.info("Setting radio to normal mode")
	sendConfigCommand(warm_reset, ser)

def configRadio(ser):
	enterCommandMode(ser)
	sendConfigCommand(set_dealer_mode_buf, ser)
	logging.info("Setting Channel")
	sendConfigCommand(set_channel, ser)
	logging.info("Setting rx freq")
	sendConfigCommand(set_rx_freq, ser)
	logging.info("Setting tx freq")
	sendConfigCommand(set_tx_freq, ser)
	logging.info("setting bandwidth")
	sendConfigCommand(set_bandwidth, ser)
	logging.info("setting modulation")
	sendConfigCommand(set_modulation, ser)
	logging.info("programming")
	sendConfigCommand(program, ser)
	exitCommandMode(ser)

def sendConfigCommand(buf, ser):
	logging.info("sending radio command: " + binascii.hexlify(buf))
	ser.write(buf)
	oldtime = time.time()
	while (time.time() - oldtime) < 2:
		inwaiting = ser.in_waiting
		if (inwaiting) > 0:
			data = ser.read(size=inwaiting)
			logging.info("got radio command response: " + binascii.hexlify(data))
	time.sleep(0.25)

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

if __name__ == "__main__":
	ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
	configRadio(ser)
