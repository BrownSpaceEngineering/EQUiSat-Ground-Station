#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import sys, time, binascii, csv, logging, serial, struct
import config, station_config

CMD_LENGTH = 6
def tx_time(byts): return byts/1080.0 + 0.012

#### Continuous uplink constants
DEF_DUTY_CYCLE = 0.5 # transmit for 50% of the time
DEF_TRANS_WINDOW = 0.5 # the length of the window to transmit in
DEF_TX_PER_WINDOW = 2 # number of times to call ser.write() during transmit window; consider current ramp-up time btwn
DEF_LISTEN_WINDOW = 0.7 # how long to listen for after transmit window
# number of commands sent per ser.write() is calculated with DEF_DUTY_CYCLE * (DEF_WAIT_INTERVAL / (tx_time(len(command)))

# the goal with all of the above is to make it impossible for us not to be transmitting during an arbitrary 1s window,
# but also make it impossible for our earliest or latest transmission to be clobbered by another transmission
# (i.e. we must not transmit in a period from 0.7s after our first TX to 0.7s after our last TX)

#### Post-packet (PP) specific constants
DEF_PP_DUTY_CYCLE = 0.5
# sum of tx and rx time for each sub transmit window, ratio determined by duty cycle
# must be > duty cycle * 0.04 to be able to tx one command
DEF_PP_INDIV_TX_PERIOD = 0.16

class Uplink:
    def __init__(self, ser, uplink_file=config.UPLINK_COMMANDS_FILE, uplink_responses=config.UPLINK_RESPONSES):
        self.cmds = Uplink.loadUplinkCommands(uplink_file)
        self.responses = uplink_responses
        self.ser = ser

    @staticmethod
    def loadUplinkCommands(filename):
        try:
            with open(filename) as file:
                #format of csv is "cmd name": "cmd bytes",
                reader = csv.reader(file)
                next(reader)
                cmds = dict(reader)
                return cmds
        except IOError:
            logging.error("Could not find file: " + filename)

    def is_valid(self, cmd_name):
        """ Returns whether the command is a valid uplink command """
        return self.responses.has_key(cmd_name) and self.cmds.has_key(cmd_name)

    def send(self, cmd_name, post_packet=False, low_power=False, duty_cycle=DEF_PP_DUTY_CYCLE, transmit_time=DEF_TRANS_WINDOW,
             tx_per_window=DEF_TX_PER_WINDOW, listen_time=DEF_LISTEN_WINDOW):
        """ Tries the given command (by name) and returns whether successful. Throws error on invalid command. """
        if not self.is_valid(cmd_name):
            raise ValueError("Invalid uplink command name: %s" % cmd_name)
        if station_config.tx_disabled:
            logging.error("Transmission is manually DISABLED!")
            return False, ""

        cmd = self.cmds[cmd_name]
        response = self.responses[cmd_name]
        if post_packet:
            return self.sendPostPacketUplink(cmd, response, self.ser, low_power=low_power, duty_cycle=duty_cycle)
        else:
            return self.sendUplink(cmd, response, self.ser, duty_cycle=duty_cycle, transmit_time=transmit_time,
                               tx_per_window=tx_per_window, listen_time=listen_time)

    #### Continuous uplink

    @staticmethod
    def sendUplink(cmd, response, ser, duty_cycle=DEF_DUTY_CYCLE, transmit_time=DEF_TRANS_WINDOW,
                   tx_per_window=DEF_TX_PER_WINDOW, listen_time=DEF_LISTEN_WINDOW):
        """ Attempts to send uplink command and waits for a time to receive
            the expected response. Returns whether the response was found
            and the updated rx_buf.
            See default constants for comments. """
        rx_buf = ""

        single_tx_window = float(transmit_time) / tx_per_window
        # enough commands so that transmission occurs for duty_cycle proportion
        # of each of the tx_per_window windows
        cmd_repeats = int(duty_cycle * (single_tx_window / (tx_time(len(cmd)))))
        oldtime = time.time()
        while (time.time() - oldtime) < transmit_time: # TODO: don't do this with big delays inside (results in .1s over end)
            ser.write(cmd * cmd_repeats)
            ser.flush()
            # TODO: we should wait for the duration of the TX here to be correct
            got_response, rx_buf_tmp = Uplink.listenForUplink(ser, response, (1-duty_cycle)*single_tx_window)
            rx_buf += rx_buf_tmp
            if got_response:
                return got_response, rx_buf

        got_response, rx_buf_tmp = Uplink.listenForUplink(ser, response, listen_time)
        rx_buf += rx_buf_tmp
        return got_response, rx_buf

    #### Post packet uplink

    @staticmethod
    def sendPostPacketUplink(cmd, response, ser, low_power=False,  # idle mode covers both well
                             indiv_tx_period=DEF_PP_INDIV_TX_PERIOD, duty_cycle=DEF_PP_DUTY_CYCLE):
        rx = ""
        if low_power:
            logging.info("Transmitting post-packet uplink pattern (low power mode)")
            # delay to enter low power rx window
            # this is just under the 1s after the first tx that the sat starts listening (in low power)
            time.sleep(0.9)
            # repeat just in case low power choice is wrong (this won't help if we missed first tx)
            count = 2

        else: # idle mode
            logging.info("Transmitting post-packet uplink pattern (idle mode)")
            # delay to enter idle mode rx window
            time.sleep(0.45)
            # try to hit window even if we weren't triggered on first tx
            count = 2

        # transmit using tx/rx timing patterns that are guaranteed to hear the response
        for i in range(count):
            success, rx2 = Uplink.safeUplinkReceive(cmd, response, ser, 0.7, indiv_tx_period=indiv_tx_period,
                                                    duty_cycle=duty_cycle)
            rx += rx2
            if success:
                return True, rx
        return False, rx

    @staticmethod
    def safeUplinkReceive(cmd, response, ser, transmit_time, indiv_tx_period=DEF_PP_INDIV_TX_PERIOD, duty_cycle=DEF_PP_DUTY_CYCLE):
        cmd_repeats = int(duty_cycle * indiv_tx_period / (tx_time(len(cmd))))
        num_txs = int(transmit_time / float(indiv_tx_period))
        rx_buf = ""
        assert transmit_time <= 0.7 # s

        # transmit for period of time
        for i in range(num_txs):
            ser.write(cmd * cmd_repeats)
            ser.flush()
            time.sleep(indiv_tx_period) # tx and rx time

            inwaiting = ser.in_waiting
            if inwaiting > 0:
                rx_buf += ser.read(size=inwaiting)

            if Uplink.checkForUplink(response, rx_buf):
                logging.warning("received uplink response while transmitting")
                return True, rx_buf

        # and wait long enough to guarantee we'll hear the response
        # (note we want to make sure we are listening from 0.7 after first tx
        # to 1.2s after the last tx (satellite takes a min of 0.7 and max of 1.0s to respond)
        # (note this includes short period of rx after the last tx_period)
        receive_time = 1.2 + (0.7 - transmit_time)
        success, rx_buf2 = Uplink.listenForUplink(ser, response, receive_time)
        return success, rx_buf + rx_buf2

    #### Helpers

    @staticmethod
    def listenForUplink(ser, response, listen_time):
        """ listen for listen_time (seconds, multiple of .05s) seconds for the
        specified uplink response from satellite on serial ser """
        rx_buf = ""
        logging.debug("listening for uplink response...")
        oldtime = time.time()
        while (time.time() - oldtime) < listen_time:
            inwaiting = ser.in_waiting
            if inwaiting > 0:
                rx_buf += ser.read(size=inwaiting)

            # search for expected response in RX buffer
            if Uplink.checkForUplink(response, rx_buf):
                return True, rx_buf

            time.sleep(.01) # as fast as reasonable
        return False, rx_buf

    @staticmethod
    def checkForUplink(response, rx_buf):
        index = rx_buf.find(response)
        if index != -1:
            # take only the response out of the rx buffer,
            # or everything if it's less than the max length
            if index + config.RESPONSE_LEN < len(rx_buf):
                fullResponse = rx_buf[index:index + config.RESPONSE_LEN]
            else:
                fullResponse = rx_buf[index:]

            # https://stackoverflow.com/a/12214880
            logging.info("got uplink command response: %s (%s)" % (fullResponse,
                                                                   ":".join(
                                                                       "{:02x}".format(ord(c)) for c in fullResponse)))
            return True
        return False

    @staticmethod
    def uplinkTests(cmds, ser):
        Uplink.sendUplink(cmds['echo_cmd'], config.UPLINK_RESPONSES['echo_cmd'], ser)
        Uplink.sendUplink(cmds['kill3_cmd'], config.UPLINK_RESPONSES['kill3_cmd'], ser)
        Uplink.sendUplink(cmds['kill7_cmd'], config.UPLINK_RESPONSES['kill7_cmd'], ser)
        Uplink.sendUplink(cmds['killf_cmd'], config.UPLINK_RESPONSES['killf_cmd'], ser)
        Uplink.sendUplink(cmds['flash_cmd'], config.UPLINK_RESPONSES['flash_cmd'], ser)
        Uplink.sendUplink(cmds['reboot_cmd'], config.UPLINK_RESPONSES['reboot_cmd'], ser)
        Uplink.sendUplink(cmds['revive_cmd'], config.UPLINK_RESPONSES['revive_cmd'], ser)
        Uplink.sendUplink(cmds['flashkill_cmd'], config.UPLINK_RESPONSES['flashkill_cmd'], ser)
        Uplink.sendUplink(cmds['flashrevive_cmd'], config.UPLINK_RESPONSES['flashrevive_cmd'], ser)

def xdl_sweep_test(ser):
    for i in range(256):
        ser.write(chr(i)*(18*3))
        print("i: %d" % i)
        time.sleep(0.5)
        #print ser.read(size=ser.in_waiting),

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

def xdl_linearity_test(ser):
    # do in 18 byte sets because block size is 18 bits
    # and lcm(18, 8) is 72 bits or 9 bytes, and we double it
    # this ensures the sequence will be periodic with respect to blocks
    for i in range(4):
        num = chr(0)*17 + chr(i)
        ser.write(num*5)
        print("seq %d: %s" % (i, binascii.hexlify(num)))
        time.sleep(0.5)

def ping_test(ser):
    try:
        while True:
            print("transmitting")
            ser.write("equisat " * 100)
            time.sleep(2)
    except KeyboardInterrupt:
        return

PACKETS = [
	"574c39585a454fd7030020a1320f08e0e3555c03032855f0b2c3b3a0b22fdee2555d03032855f0b27d58c1c15555c155e3d303002fe1e1555f03032855f0b27d58c1c15555c15565d003002fe3de5a5503032855f0e17d58c1c15555c155dbcc03002fe1de5a5503032855f0e17d58c1c15455c1555dc903002fe1de5b5503032855f0e17d58c1c15455c155d3c503002fdfe0555803032855f0f27d58c1c15555c15554c203002fdfe1555803032855f0f27d58c1c1c1c1c1c1cdbe03000e02050e01059b2a069c1c009c1a009c1900263c06d64c069b2f000815069c300542270a737478524623cc2284a37b588967b5a8d6d8e6063f93f0d04c23ae3654",
	"574c39585a455319020021a5323b04dee3555c03032855f0b2c4b49fb300000000000000000000000079097c82c27c82c27f7f807678787678784616020000000000000000000000000079097c82c27c82c27f7f807678787678789611020000000000000000000000000079057c82c17c82c27f7f80767878767878e60c020000000000000000000000000079097c82c17c82c27f7f807678787678783608020000000000000000000000000079097c82c27c82c27f7f80767878767878860302009c30051c05051c02051c01059b29059b2905d64c059b2a0e9c1cff000000326466aa38edaa9523ab2ac822d84d5facd46b418f3978e88e468141ca2066",
	"574c39585a45f23304002297323c08dee3555b03032854f0b2c5b39fb203030303030303030303030303030403030303030303030203030303030303030303030303030303030301000200010001000100010002000100010002000100010001000100c5b1a0b2c6b2a1b1c6b29fb1c4b2a1b1c4b3a0b1c2b2a0b2c5b29db2161e071b2323141b232b050530300711191119112b210f21162111217f7f807f7f807f7f807f7f807f7f807f7f807f7f80f53304009b2f009c2eff9c30009b2f009c2e000815009c1fff9c1c009c20ff9c1bff9c1dff9c1eff9c19009c1f0000b5d38433b3764afbb6734b204e06f888445fbac94129af66accf0d74460e902d",
	"574c39585a45fac302002297323a07e2de5a5503032855f0e1c5b4a1b103030403030303030303030303030303030303030303030303030303030303030303030303030303030302000100010001000200010001000100010001000100010001000100c6b1a0b1c4b2a3b0c7b19eb1c3b29fb1c2b39eb3c6b1a2b0c4b39eb2050a0c1132260a19261e1b2316190f2116191419211911281b1911197f7f807f7f807f7f807f7f807f7f807f7f807f7f80fbc302000e06000e04000e03009c1aff9c19ff0e02000e01009c1cff9c19019c1fff9c20ff9c1bff9c1dff9c1eff0039a6aca520321ac66993d0219fa0c9c1bb0a752183d115979df53f83ba28c072"
]
def packet_test(ser):
    try:
        while True:
            print("sending packets")
            for i in range(4):
                ser.write(binascii.unhexlify(PACKETS[i]))
                time.sleep(0.75)
            time.sleep(20-0.75*4)
    except KeyboardInterrupt:
        return

tests = {
    "xdl_sweep_test": xdl_sweep_test,
    "xdl_generic_test": xdl_test,
    "xdl_linearity_test": xdl_linearity_test,
    "ping_test": ping_test,
    "packet_test": packet_test
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
    cmds = Uplink.loadUplinkCommands(config.UPLINK_COMMANDS_FILE)

    # run requested test
    tests[testName](ser)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
