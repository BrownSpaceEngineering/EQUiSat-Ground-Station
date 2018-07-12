# Global config settings for groundstation
import logging

SERIAL_PORT = "/dev/ttyAMA0"
SERIAL_BAUD = 38400
SAT_CATALOG_NUMBER = 25544 # NORAD (Space Command) number

UPLINK_COMMANDS_FILE = "uplink_commands.csv"

# uplink command responses
RESPONSE_LEN = 9
UPLINK_RESPONSES = {
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

# testing config
LOGGING_LEVEL = logging.DEBUG

USE_TEST_FILE =             True
GENERATE_FAKE_PASSES =      True
RUN_TEST_UPLINKS =          True
PUBLISH_PACKETS =           False

TEST_INFILE = "../Test Dumps/test_packet_logfile.txt"
TEST_OUTFILE = "groundstation_serial_out.txt"