#!/usr/bin/python
# Terminal and CLI interface for the groundstation
import threading
import argparse
import cmd
import logging

import groundstation
import config

class GroundstationCLI(cmd.Cmd):
    prompt = '>> '

    def __init__(self, station):
        cmd.Cmd.__init__(self)
        """ Given an EQUiStation constructs an interactive terminal """
        self.station = station

    def do_debug(self, level):
        """ Sets level of debug messages to show"""
        level = level.lower()
        set_level = None
        if level == "debug" or level == "verbose" or level == "on":
            set_level = logging.DEBUG
        if level == "info":
            set_level = logging.INFO
        elif level == "warn" or level == "warning":
            set_level = logging.WARNING

        if set_level is not None:
            self.station.set_logging_level(set_level)
            print("set debug to: %s" % level)
        else:
            print("invalid debug setting; choose one of 'debug', 'info', or 'warn'")

    def do_status(self, line):
        """ Prints out a summary of the current status of the groundstation """
        print("===================================================================")
        print("station info:\n%s" % self.station.get_station_config())
        print("last data rx:            %s" % self.station.get_last_data_rx())
        print("last packet rx:          %s" % self.station.get_last_packet_rx())
        print("update pass data time:   %s" % self.station.get_update_pass_data_time())

        print("doppler corrections: \n%s" % self.station.get_doppler_corrections_str())

        next_pass_info = None
        if self.station.get_next_pass_data() is not None:
            next_pass_info = ""
            for key, value in self.station.get_next_pass_data().items():
                next_pass_info += "\t%s: %s\n" % (key, value)
        print("next pass info:\n%s" % next_pass_info)
        print("===================================================================")

    def do_tx_queue(self, line):
        """ Prints out the current TX queue """
        print(self.station.get_tx_cmd_queue())
        if self.station.only_send_tx_cmd:
            print("(transmitting first constantly)")

    def do_rx(self, line):
        """ Prints out the entire RX buffer """
        buf = self.station.get_rx_buf()
        print("RX buffer (len: %d):" % len(buf))
        print(buf)

    def do_tx(self, line):
        """ Queues the given uplink command or sends immediately if set to """
        args = line.split(" ")
        if not (1 <= len(args) <= 2):
            print("invalid arguments")
        else:
            cmd = args[0]
            immediate = args[1] if len(args) == 2 else False
            immediateSet = immediate == "true" or immediate == "now" or immediate == "on"
            success = self.station.send_tx_cmd(cmd, immediate=immediateSet)
            if not success:
                print("invalid uplink command; available:")
                for cmd in config.UPLINK_RESPONSES.keys():
                    print(cmd)

    def do_tx_rm(self, line):
        """ Removes the given uplink command, either first found or all if specified """
        args = line.split(" ")
        if not (1 <= len(args) <= 2):
            print("invalid arguments")
        else:
            cmd = args[0]
            all = args[1] if len(args) == 2 else False
            allSet = all == "all"
            success = self.station.cancel_tx_cmd(cmd, all=allSet)
            if not success:
                print("command not in queue:")
                print(self.station.get_tx_cmd_queue())

def start_station(station, radio_preconfig, serial_port, serial_baud, ser_infilename, ser_outfilename):
    if radio_preconfig is None:
        radio_preconfig = False

    def runner_serial():
        station.run(serial_port=serial_port, serial_baud=serial_baud, radio_preconfig=radio_preconfig)
    def runner_test():
        station.run(ser_infilename=ser_infilename, ser_outfilename=ser_outfilename, radio_preconfig=radio_preconfig)

    runner = None
    if serial_baud is not None and serial_baud is not None:
        runner = runner_serial
    elif ser_infilename is not None and ser_outfilename is not None:
        runner = runner_test

    if runner is not None:
        print("Starting EQUiStation...")
        thread = threading.Thread(target=runner)
        thread.daemon = True # close on app close
        thread.start()
        return True
    else:
        return False

def config_parser():
    parser = argparse.ArgumentParser(description="Launch and control the EQUiStation")
    parser.add_argument('--debug', metavar="d", type=bool, default=False, help="toggle debug printing")
    parser.add_argument('--radio_preconfig', metavar="pre", type=bool, default=False, help="whether to pre-configure radio frequencies")
    parser.add_argument('--serial_port', metavar="port", type=str, default=config.SERIAL_PORT, help="radio's serial port")
    parser.add_argument('--serial_baud', metavar="baud", type=int, default=config.SERIAL_BAUD, help="radio's serial baud rate")
    parser.add_argument('--test', metavar="t", type=bool, default=config.USE_TEST_FILE, help="whether to use serial spoofing")
    parser.add_argument('--serial_infile', metavar="in", type=str, default=config.TEST_INFILE, help="file to spoof serial input from")
    parser.add_argument('--serial_outfile', metavar="out", type=str, default=config.TEST_OUTFILE, help="file for redirecting serial output")
    return parser

def main():
    # get CLI args
    parser = config_parser()
    args = parser.parse_args()

    station = groundstation.EQUiStation()
    station.set_logging_level(logging.DEBUG if args.debug else logging.WARNING)

    # null out serial args if test added
    if args.test:
        args.serial_port = None
        args.serial_baud = None

    # start groundstation on new thread and command loop on this one
    success = start_station(station, args.radio_preconfig, args.serial_port, args.serial_baud,
        args.serial_infile, args.serial_outfile)
    if not success:
        print("Invalid CLI args")
        parser.print_help()
        exit(1)

    try:
        GroundstationCLI(station).cmdloop()
    except KeyboardInterrupt:
        return

if __name__ == "__main__":
    main()
