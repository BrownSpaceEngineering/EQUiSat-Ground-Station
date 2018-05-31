#include "hex_strings.h"

char data_from_hex(char hex_char);
char hex_from_data(char nibble);

int hex_str_to_raw(char* input_hex_str, size_t hex_str_len, unsigned char* dest_raw) {
	if (hex_str_len % 2 != 0) {
		return 0;
	}

	size_t dest_str_len = hex_str_len / 2;
	for (int i = 0; i < dest_str_len; i++) {
		// get a nibble from each hex char (note hex strings are big-endian like)
		char ms_nibble = data_from_hex(input_hex_str[2*i]);
		char ls_nibble = data_from_hex(input_hex_str[2*i + 1]);
		// check for invalid chars
		if (ms_nibble == 0xff || ls_nibble == 0xff) {
			return 0;
		}
		dest_raw[i] = ms_nibble << 4 | ls_nibble;
	}
	return 1;
}

void raw_to_hex_str(unsigned char* input_raw, size_t raw_len, char* dest_hex_str) {
	for (int i = 0; i < raw_len; i++) {
		char ls_nibble = hex_from_data(input_raw[i] & 0xf);
		char ms_nibble = hex_from_data(input_raw[i] >> 4);
		sprintf(dest_hex_str + 2*i, "%c%c", ms_nibble, ls_nibble); // big-endian like
	}
}

// returns the nibble value corresponding to the given hex character, or
// 0xff if the character was not a valid hex char
char data_from_hex(char hex_char) {
	if ('0' <= hex_char && hex_char <= '9') {
		return hex_char - '0';
	} else if ('a' <= hex_char && hex_char <= 'f') {
		return 10 + hex_char - 'a';
	} else {
		return 0xff;
	}
}

// returns the hex char corresponding to the given nibble value
char hex_from_data(char nibble) {
	if (nibble < 10) {
		return '0' + nibble;
	} else if (nibble <= 16) {
		return 'a' + (nibble - 10);
	} else {
		return 0;
	}
}

void _hex_strings_test(void) {
	char* data = "cats are cool";
    char out[27];
    raw_to_hex_str((unsigned char*) data, 13, out);
	printf("%s -> %s -> ", data, out);

    char out_data[14];
    hex_str_to_raw(out, 26, (unsigned char*) out_data);
    printf("%s\n", out_data);
}
