#!/usr/bin/python
# Functions to configure XDL Micro settings over serial
import sys
import time
import binascii
import serial
import struct
import logging
import config

DEFAULT_RETRIES = 5
DEFAULT_RETRY_DELAY = 0.4
RADIO_FREQ_STEP_HZ = 6250

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

def enterCommandMode(ser, dealer_access=False, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	""" Sets the radio to be in command mode, optimally with full dealer access
	Returns whether dealer_access mode was successful entered if selected """
	logging.info("Setting radio to command mode")
	time.sleep(0.1)
	_, rx_buf1 = sendConfigCommand(ser, "+++")
	time.sleep(0.1)
	if dealer_access:
		okay, rx_buf2 = sendConfigCommand(ser, set_dealer_mode_buf, \
			retries=retries, retry_delay_s=retry_delay_s)
		return okay, rx_buf1 + rx_buf2
	else:
		return True, rx_buf1

def exitCommandMode(ser, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	logging.info("Setting radio to normal mode")
	return sendConfigCommand(ser, warm_reset, retries=retries, retry_delay_s=retry_delay_s)

def sendConfigCommand(ser, buf, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	""" Sends the given config command to the radio over the given serial line.
	Returns whether a valid response was recieved and all data recieved over RX """
	okay = False
	rx_buf = ""
	retry = 0
	while retry < retries and not okay:
		logging.info("sending radio command%s: %s" % \
			("" if retry == 0 else "(try %d)"%i, binascii.hexlify(buf)))
		ser.write(buf)
		oldtime = time.time()
		while (time.time() - oldtime) < 2:
			if ser.in_waiting > 0:
				data = ser.read(size=ser.in_waiting)
				rx_buf += data
				logging.info("got radio command response: " + binascii.hexlify(data))
				okay = True # TODO: actually read packet and then quit if correct
			time.sleep(0.25)
		time.sleep(retry_delay_s)
	return okay, rx_buf

def getSetFreqCommandBuf(freqInHZ, channelNum, isTX):
	#structure is [Start of Header, Command #, Channel #, Freq Byte #1, Freq Byte #2, Freq Byte #3, Freq Byte #4, checksum]
	#Byte #1 is MSB
	freq_in_hex = '{:4x}'.format(freqInHZ).replace(" ", "0")[:8] # radio only supports 4 bytes
	freq_bytes = bytearray.fromhex(freq_in_hex)
	command_type_byte = bytearray(b'\x37') if isTX else bytearray(b'\x39')
	channel_num_byte = bytearray(chr(channelNum))
	command_buf_payload = command_type_byte + channel_num_byte + freq_bytes
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	start_of_header = bytearray(b'\x01')
	full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00') #need to null terminate string
	return full_command_buf

def setChannel(ser, channelNum, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	""" Sets the radio's channel to channelNum. channelNum must be between 1 and 32 """
	if channelNum > 32 or channelNum < 0:
		print("Error: Channel must be between 1 and 32 (0x20)")
	start_of_header = bytearray(b'\x01')
	command_type_byte = bytearray(b'\x03')
	channel_num_byte = bytearray(chr(channelNum))
	command_buf_payload = command_type_byte + channel_num_byte
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00') #need to null terminate string
	return sendConfigCommand(ser, full_command_buf, retries=retries, retry_delay_s=retry_delay_s)

def addChannel(ser, channelNum, rxFreqInHz, txFreqInHz, bandwidthInHz, \
		retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	start_of_header = bytearray(b'\x01')
	command_type_byte = bytearray(b'\x70\x00')
	channel_num_byte = bytearray(chr(channelNum))
	rx_freq_in_hex = '{:4x}'.format(rxFreqInHz).replace(" ", "0")[:8] # radio only supports 4 bytes
	rx_freq_bytes = bytearray.fromhex(rx_freq_in_hex)
	tx_freq_in_hex = '{:4x}'.format(txFreqInHz).replace(" ", "0")[:8] # radio only supports 4 bytes
	tx_freq_bytes = bytearray.fromhex(tx_freq_in_hex)
	bandwidth_in_hex = '{:4x}'.format(bandwidthInHz).replace(" ", "0")[:8] # radio only supports 4 bytes
	bandwidth_bytes = bytearray.fromhex(bandwidth_in_hex)
	command_buf_payload = command_type_byte + channel_num_byte + rx_freq_bytes + tx_freq_bytes + bandwidth_bytes
	checksum_byte = chr(~(sum(command_buf_payload) % 255) & 255) #checksum is sum of bytes (not including start of header) mod 0xFF, then one's complement
	full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00')  #need to null terminate string
	return sendConfigCommand(ser, full_command_buf, retries=retries, retry_delay_s=retry_delay_s)

def setRxFreq(ser, freqInHZ, channelNum, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	""" Sets the radio's RX frequency for the given channel. freqInHZ must be a multiple of 6250 """
	if freqInHZ % RADIO_FREQ_STEP_HZ != 0:
		return False, ""
	setRxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, False)
	return sendConfigCommand(ser, setRxCommandBuf, retries=retries, retry_delay_s=retry_delay_s)

def setTxFreq(ser, freqInHZ, channelNum, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
	""" Sets the radio's TX frequency for the given channel. freqInHZ must be a multiple of 6250 """
	if freqInHZ % RADIO_FREQ_STEP_HZ != 0:
		return False, ""
	setTxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, True)
	return sendConfigCommand(ser, setTxCommandBuf, retries=retries, retry_delay_s=retry_delay_s)

def configRadio(ser):
	enterCommandMode(ser)
	dealer_okay, _ = sendConfigCommand(ser, set_dealer_mode_buf)
	logging.info("Setting Channel")
	channel_okay, _ = sendConfigCommand(ser, set_channel)
	logging.info("Setting rx freq")
	rx_okay, _ = sendConfigCommand(ser, set_rx_freq)
	logging.info("Setting tx freq")
	tx_okay, _ = sendConfigCommand(ser, set_tx_freq)
	logging.info("setting bandwidth")
	bandwidth_okay, _ = sendConfigCommand(ser, set_bandwidth)
	logging.info("setting modulation")
	modulation_okay, _ = sendConfigCommand(ser, set_modulation)
	logging.info("programming")
	program_okay, _ = sendConfigCommand(ser, program)
	exit_okay, _ = exitCommandMode(ser)
	return dealer_okay and channel_okay and rx_okay and tx_okay \
		and bandwidth_okay and modulation_okay and program_okay and exit_okay

if __name__ == "__main__":
        logging.basicConfig(level=logging.DEBUG)
	ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
	#configRadio(ser)
