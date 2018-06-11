# Global config settings for groundstation

SERIAL_PORT = "/dev/ttyAMA0"
SERIAL_BAUD = 38400
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
