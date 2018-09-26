#!/usr/bin/python

#Instructions for enabling UART Hardware on PI 3 Pins 14&15
#https://spellfoundry.com/2016/05/29/configuring-gpio-serial-port-raspbian-jessie-including-pi-3/

import sys, time, binascii, csv, logging, serial, struct
import config, station_config

DEF_CMD_REPEATS = 15
DEF_TX_REPEATS = 12
DEF_TX_RESPONSE_TIMEOUT_S = 0.3

class Uplink:
    def __init__(self, ser, uplink_file=config.UPLINK_COMMANDS_FILE, uplink_responses=config.UPLINK_RESPONSES):
        self.cmds = Uplink.loadUplinkCommands(uplink_file)
        self.responses = uplink_responses
        self.ser = ser

    @staticmethod
    def loadUplinkCommands(filename):
        try:
            with open(filename) as file:
                #format of csv is "name": "test",
                reader = csv.reader(file)
                next(reader)
                cmds = dict(reader)
                return cmds
        except IOError:
            logging.error("Could not find file: " + filename)

    def is_valid(self, cmd_name):
        """ Returns whether the command is a valid uplink command """
        return self.responses.has_key(cmd_name) and self.cmds.has_key(cmd_name)

    def send(self, cmd_name, cmd_repeats=DEF_CMD_REPEATS, repeats=DEF_TX_REPEATS, tx_response_timeout_s=DEF_TX_RESPONSE_TIMEOUT_S):
        """ Tries the given command (by name) and returns whether successful. Throws error on invalid command. """
        if not self.is_valid(cmd_name):
            raise ValueError("Invalid uplink command name: %s" % cmd_name)
        cmd = self.cmds[cmd_name]
        response = self.responses[cmd_name]
        return self.sendUplink(cmd, response, self.ser, cmd_repeats=cmd_repeats, repeats=repeats, tx_response_timeout_s=tx_response_timeout_s)

    @staticmethod
    def sendUplink(cmd, response, ser, cmd_repeats=DEF_CMD_REPEATS, repeats=DEF_TX_REPEATS, tx_response_timeout_s=DEF_TX_RESPONSE_TIMEOUT_S):
        """ Attempts to send uplink command and waits for a time to receive
            the expected response. Returns whether the response was found
            and the updated rx_buf.
            :param cmd_repeats: The number of times to repeat the uplink command characters in a single uplink packet
            :param repeats: The number of repeats of the whole sequence to perform
            :param tx_response_timeout_s: the time to spend searching for a response before repeating"""
        if station_config.tx_disabled:
            logging.error("Transmission is manually DISABLED!")
            return False, ""

        rx_buf = ""
        num_repeats = 0
        while num_repeats < repeats:
            oldtime = time.time()
            ser.write(cmd*cmd_repeats)
            ser.flush()
            while (time.time() - oldtime) < tx_response_timeout_s:
                logging.debug("searching for response (%d/%d)..." % (num_repeats, repeats))
                inwaiting = ser.in_waiting
                if inwaiting > 0:
                    rx_buf += ser.read(size=inwaiting)

                # search for expected response in RX buffer
                index = rx_buf.find(response)
                if index != -1:
                    if index + config.RESPONSE_LEN < len(rx_buf):
                        fullResponse = rx_buf[index:index+config.RESPONSE_LEN]
                    else:
                        fullResponse = rx_buf[index:]

                    # https://stackoverflow.com/a/12214880
                    logging.info("got uplink command response: %s (%s)" % (fullResponse,
                        ":".join("{:02x}".format(ord(c)) for c in fullResponse)))
                    return True, rx_buf

                time.sleep(.05)
            num_repeats += 1

        return False, rx_buf

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
    "xdl_test": xdl_test,
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
