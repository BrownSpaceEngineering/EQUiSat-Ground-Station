#!/usr/bin/python
# Functions to configure XDL Micro settings over serial
import sys
import time
import binascii
import serial
import mock_serial
import struct
import logging
import config

DEFAULT_RETRIES = 5
DEFAULT_RETRY_DELAY = 0.4
RADIO_FREQ_STEP_HZ = 6250
RADIO_DEFAULT_BANDWIDTH = 12500

START_OF_HEADER = bytearray(b'\x01')
TERMINATOR = bytearray(b'\x00')

# radio config settings
set_dealer_mode_buf = bytearray(b'\x01\x44\x01\xba\x00')
set_tx_freq = bytearray(b'\x01\x37\x01\x19\xf5\xf7\x30\x92\x00')
set_rx_freq = bytearray(b'\x01\x39\x01\x19\xf5\xf7\x30\x90\x00')
get_tx_freq = bytearray(b'\x01\x38\x01\xc6\x00')
get_rx_freq = bytearray(b'\x01\x3a\x01\xc4\x00')
set_channel = bytearray(b'\x01\x03\x01\xfb\x00')
set_bandwidth = bytearray(b'\x01\x70\x04\x01\x8a\x00')
set_modulation = bytearray(b'\x01\x2b\x01\xd3')
program_buf = bytearray(b'\x01\x1e\xe1\x00')
warm_reset = bytearray(b'\x01\x1d\x01\xe1\x00')
delete_channel = bytearray(b'\x01\x70\x01\x01\x8d\x00')

set_channel_response = b'\x83'
set_rx_freq_response = b'\xb9'
set_tx_freq_response = b'\xb7'
set_bandwidth_response = b'\xf0'
set_modulation_response = b'\xab'
program_response = b'\x9e'

def enterCommandMode(ser, dealer=False, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
    """ Sets the radio to be in command mode, optimally with full dealer access
    Returns whether dealer_access mode was successful entered if selected """
    logging.debug("Setting radio to command mode")
    time.sleep(0.1)
    _, rx_buf1, _ = sendConfigCommand(ser, "+++", "", retries=0)
    time.sleep(0.1)
    if dealer:
        okay, rx_buf2, response = sendConfigCommand(ser, set_dealer_mode_buf, b'\xc4',
            retries=retries, retry_delay_s=retry_delay_s)
        return okay and response == bytearray(b'\x00'), rx_buf1 + rx_buf2
    else:
        return True, rx_buf1

def exitCommandMode(ser, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
    logging.debug("Setting radio to normal mode")
    res = sendConfigCommand(ser, warm_reset, b'\x9d', retries=retries, retry_delay_s=retry_delay_s)
    return validateConfigResponse(b'\x00', res)

def program(ser):
    """ Persists the radio's current settings in nonvolatile memory """
    res = sendConfigCommand(ser, program_buf, program_response)
    return validateConfigResponse(b'\x00', res)

def sendConfigCommand(ser, buf, response_cmd, response_size=1, \
        retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
    """ Sends the given config command to the radio over the given serial line.
    Returns whether a valid response was recieved, all data recieved over RX, and the response args """
    rx_buf = ""
    retry = -1
    while retry < retries:
        logging.debug("sending radio command%s: %s" % \
            ("" if retry < 0 else " (try %d)"%(retry+1), binascii.hexlify(buf)))
        ser.write(buf)
        oldtime = time.time()
        while (time.time() - oldtime) < 2:
            if ser.in_waiting > 0:
                data = ser.read(size=ser.in_waiting)
                rx_buf += data

                okay, response = checkCommandResponse(data, response_cmd, response_size)
                logging.debug("got radio command response (%s; %s): %s" % \
                        (okay, binascii.hexlify(response), binascii.hexlify(data)))
                if okay or response_cmd == "":
                    return True, rx_buf, response

            time.sleep(0.25)

        retry += 1
        if retry < retries:
            time.sleep(retry_delay_s)

    return False, rx_buf, bytearray()

def checkCommandResponse(buf, response_cmd, response_size):
    """ Checks for a valid response with a payload of size response_size in the buffer 
    and returns the contents of the response """
    if response_cmd == "":
        return False, bytearray()
    start = buf.find(START_OF_HEADER)
    # checks 
    if start == -1:
        return False, bytearray()
    if len(buf)-start < 1 + response_size + 1: # start of header, response, checksum
        return False, bytearray()

    response = buf[start+2:start+2+response_size]
    if buf[start+1] != bytearray(response_cmd):
        return False, response # may not be valid

    # check checksum
    payload = bytearray(buf[start+1:start+2+response_size])
    expected_checksum = computeChecksum(payload)
    actual_checksum = buf[start+2+response_size]
    if expected_checksum != actual_checksum:
        return False, response
    return True, response

def validateConfigResponse(expected, rets):
    """ Given the expected response and the three return values of sendConfigCommand, 
    returns whether the command was correct and the full rx buffer """
    response_okay = rets[2][0] == expected
    if not response_okay:
        logging.error("unexpected response: %s; wanted %s" % (rets[2][0], expected))
    return rets[0] and response_okay, rets[1]

def computeChecksum(payload):
    """ Returns the checksum byte for the given payload
    (should not include start of header) """
    # checksum is one's complement of the LSB of the sum of the bytes
    return chr(~sum(payload) & 255) 

def buildCommand(command_code, args=''):
    """ Builds a command out of a payload according to XDL specs """
    payload = bytearray(command_code) + bytearray(args)
    checksum = computeChecksum(payload)
    return START_OF_HEADER + payload + checksum + TERMINATOR

def getSetFreqCommandBuf(freqInHZ, channelNum, isTX):
    #structure is [Start of Header, Command #, Channel #, Freq Byte #1, Freq Byte #2, Freq Byte #3, Freq Byte #4, checksum]
    #Byte #1 is MSB
    freq_in_hex = '{:4x}'.format(freqInHZ).replace(" ", "0")[:8] # radio only supports 4 bytes
    freq_bytes = bytearray.fromhex(freq_in_hex)
    command_type_byte = bytearray(b'\x37') if isTX else bytearray(b'\x39')
    channel_num_byte = bytearray(chr(channelNum))
    command_buf_payload = command_type_byte + channel_num_byte + freq_bytes
    checksum_byte = computeChecksum(command_buf_payload)
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
    checksum_byte = computeChecksum(command_buf_payload)
    full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00') #need to null terminate string
    rets = sendConfigCommand(ser, full_command_buf, set_channel_response, retries=retries, retry_delay_s=retry_delay_s)
    return validateConfigResponse(b'\x00', rets)

def addChannel(ser, channelNum, rxFreqInHz, txFreqInHz, bandwidthInHz=RADIO_DEFAULT_BANDWIDTH,
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
    checksum_byte = computeChecksum(command_buf_payload)
    full_command_buf = start_of_header + command_buf_payload + checksum_byte + bytearray(b'\x00')  #need to null terminate string
    rets = sendConfigCommand(ser, full_command_buf, b'\xf0', retries=retries, retry_delay_s=retry_delay_s)
    return validateConfigResponse(b'\x00', rets) 

def setRxFreq(ser, freqInHZ, channelNum, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
    """ Sets the radio's RX frequency for the given channel. freqInHZ must be a multiple of 6250 """
    if freqInHZ % RADIO_FREQ_STEP_HZ != 0:
        return False, ""
    setRxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, False)
    rets = sendConfigCommand(ser, setRxCommandBuf, set_rx_freq_response, retries=retries, retry_delay_s=retry_delay_s)
    return validateConfigResponse(b'\x00', rets)

def setTxFreq(ser, freqInHZ, channelNum, retries=DEFAULT_RETRIES, retry_delay_s=DEFAULT_RETRY_DELAY):
    """ Sets the radio's TX frequency for the given channel. freqInHZ must be a multiple of 6250 """
    if freqInHZ % RADIO_FREQ_STEP_HZ != 0:
        return False, ""
    setTxCommandBuf = getSetFreqCommandBuf(freqInHZ, channelNum, True)
    rets = sendConfigCommand(ser, setTxCommandBuf, set_tx_freq_response, retries=retries, retry_delay_s=retry_delay_s)
    return validateConfigResponse(b'\x00', rets)

def setFreq(ser, freq, channel):
    """ Sets TX and RX frequency and returns success, buffer. """
    rx_okay, rx1 = setRxFreq(ser, freq, channel)
    tx_okay, rx2 = setTxFreq(ser, freq, channel)
    return rx_okay and tx_okay, rx1 + rx2

def getRxFreq(ser, channel):
    command = buildCommand(b'\x3a', chr(channel))
    rets = sendConfigCommand(ser, command, b'\xba', response_size=5)
    return validateConfigResponse(b'\x00', rets)

def getTxFreq(ser, channel):
    command = buildCommand(b'\x38', chr(channel))
    rets = sendConfigCommand(ser, command, b'\xb8', response_size=5)
    return validateConfigResponse(b'\x00', rets)

def configRadio(ser):
    enterCommandMode(ser, dealer=True)
    logging.info("Setting Channel")
    channel_okay, _, _ = sendConfigCommand(ser, set_channel, set_channel_response)
    logging.info("Setting rx freq")
    rx_okay, _, _ = sendConfigCommand(ser, set_rx_freq, set_rx_freq_response)
    logging.info("Setting tx freq")
    tx_okay, _, _  = sendConfigCommand(ser, set_tx_freq, set_tx_freq_response)
    logging.info("setting bandwidth")
    bandwidth_okay, _, _ = sendConfigCommand(ser, set_bandwidth, set_bandwidth_response)
    logging.info("setting modulation")
    modulation_okay, _, _ = sendConfigCommand(ser, set_modulation, set_modulation_response)
    logging.info("programming")
    program_okay, _, _ = sendConfigCommand(ser, program_buf, program_response)
    exit_okay, _ = exitCommandMode(ser)
    return channel_okay and rx_okay and tx_okay \
        and bandwidth_okay and modulation_okay and program_okay and exit_okay

if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    if len(sys.argv) == 2 and sys.argv[1] == "debug":
        ser = mock_serial.MockSerial(infile_name="/dev/null", outfile_name="/dev/null", max_inwaiting=5)
    else:
        ser = serial.Serial(config.SERIAL_PORT, config.SERIAL_BAUD, timeout=None)
    #configRadio(ser)
