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
	time.sleep(0.1)
	okay = sendConfigCommand(ser, "+++")
	time.sleep(0.1)
	return okay

def exitCommandMode(ser):
	logging.info("Setting radio to normal mode")
	return sendConfigCommand(ser, warm_reset)

def configRadio(ser):
	enterCommandMode(ser)
	sendConfigCommand(ser, set_dealer_mode_buf)
	logging.info("Setting Channel")
	sendConfigCommand(ser, set_channel)
	logging.info("Setting rx freq")
	sendConfigCommand(ser, set_rx_freq)
	logging.info("Setting tx freq")
	sendConfigCommand(ser, set_tx_freq)
	logging.info("setting bandwidth")
	sendConfigCommand(ser, set_bandwidth)
	logging.info("setting modulation")
	sendConfigCommand(ser, set_modulation)
	logging.info("programming")
	sendConfigCommand(ser, program)
	exitCommandMode(ser)

def sendConfigCommand(ser, buf):
	""" Sends the given config command to the radio over the given serial line.
	Returns all data recieved over RX in case radio wasn't in command mode and for testing """
	rx_buf = ""
	logging.info("sending radio command: " + binascii.hexlify(buf))
	ser.write(buf)
	oldtime = time.time()
	while (time.time() - oldtime) < 2:
		inwaiting = ser.in_waiting
		if (inwaiting) > 0:
			data = ser.read(size=inwaiting)
			rx_buf += data
			logging.info("got radio command response: " + binascii.hexlify(data))
		time.sleep(0.25)
	return rx_buf

def getSetFreqCommandBuf(freqInHZ, channelNum, isTX):
	#structure is [Start of Header, Command #, Channel #, Freq Byte #1, Freq Byte #2, Freq Byte #3, Freq Byte #4, checksum]
	#Byte #1 is MSB
	freq_in_hex = '{:4x}'.format(freqInHZ).replace(" ", "0")[:4] # radio only supports 4 bytes
	freq_bytes = bytearray.fromhex(freq_in_hex)
	command_type_byte = bytearray(b'\x37') if isTX else bytearray(b'\x39')
	channel_num_byte = bytearray(chr(channelNum))
	command_buf_payload = command_type_byte + channel_num_byte + freq_bytes
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	start_of_header = bytearray(b'\x01')
	full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00') #need to null terminate string
	return full_command_buf

def setChannel(channelNum): #channelNum must be between 1 and 32
	if channelNum > 32 or channelNum < 0:
		print("Error: Channel must be between 1 and 32 (0x20)")
	start_of_header = bytearray(b'\x01')
	command_type_byte = bytearray(b'\x03')
	channel_num_byte = bytearray(chr(channelNum))
	command_buf_payload = command_type_byte + channel_num_byte
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	full_command_buf = start_of_header + command_buf_payload + checksum + bytearray(b'\x00') #need to null terminate string
	return sendConfigCommand(ser, full_command_buf)

def addChannel(channelNum, rxFreqInHez, txFreqInHz, bandwidthInHz):
	start_of_header = bytearray(b'\x01')
	command_type_byte = bytearray(b'\x70\x00')
	channel_num_byte = bytearray(chr(channelNum))
	rx_freq_in_hex = '{:4x}'.format(rxFreqInHZ).replace(" ", "0")[:4] # radio only supports 4 bytes
	rx_freq_bytes = bytearray.fromhex(rxFreq_in_hex)
	tx_freq_in_hex = '{:4x}'.format(txFreqInHZ).replace(" ", "0")[:4] # radio only supports 4 bytes
	tx_freq_bytes = bytearray.fromhex(txFreq_in_hex)
	bandwidth_in_hex = '{:4x}'.format(bandwidthInHz).replace(" ", "0")[:4] # radio only supports 4 bytes
	bandwidth_bytes = bytearray.fromhex(bandwidthInHz)
	command_buf_payload = command_type_byte + channel_num_byte + rx_freq_bytes + tx_freq_bytes + bandwidth_bytes
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	full_command_buf = start_of_header + command_buf_payload + checksum + bytearray(b'\x00')  #need to null terminate string
	return sendConfigCommand(ser, full_command_buf)

def setRxFreq(ser, freqInHZ, channelNum):
	setRxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, False)
	return sendConfigCommand(ser, setRxCommandBuf)

def setTxFreq(ser, freqInHZ, channelNum):
	setTxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, True)
	return sendConfigCommand(ser, setTxCommandBuf)

if __name__ == "__main__":
	ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
	configRadio(ser)
