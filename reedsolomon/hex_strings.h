#include <stdio.h>
#include <stdlib.h>

/**
 * Given an input hex string, converts the hex data into it's binary (character) representation.
 * The input hex string must contain only 0-9 and a-f characters, in any case.
 * It must also be of even length.
 * The outputted raw data will be half the length of the original.
 * Returns whether there were any parsing errors.
 */
int hex_str_to_raw(char* input_hex_str, size_t hex_str_len, unsigned char* dest_raw);

/**
 * Given a string of raw binary characters, converts the data into a hex string.
 * The outputted hex string will be twice the length of the raw data.
 */
void raw_to_hex_str(unsigned char* input_raw, size_t raw_len, char* dest_hex_str);


void _hex_strings_test(void);
