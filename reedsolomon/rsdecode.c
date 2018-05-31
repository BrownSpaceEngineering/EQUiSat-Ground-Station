#include <stdio.h>
#include <stdlib.h>
#include "rscode1.3/ecc.h"
#include "hex_strings.h"

int main (int argc, char *argv[]) {
    if (argc != 4) {
        printf("Usage: rsdecode <encoded hex msg> <encoded hex msg length> <num parity bytes>\n");
        return 0;
    }

    char* hexCodeword = argv[1];
    int hexCodewordLength = atoi(argv[2]);
    int codewordLength = hexCodewordLength/2;
    int numParityBytes = atoi(argv[3]);

    /* convert hex string to raw data */
    unsigned char codeword[codewordLength];
    int success = hex_str_to_raw(hexCodeword, hexCodewordLength, codeword);
    if (!success) {
        // hex string parse error
        return 1;
    }

    /* Initialization the ECC library */
    initialize_ecc();

    /* Decode string -- encoded codeword size must be passed */
    decode_data(codeword, codewordLength);

    /* check if syndrome is all zeros */
    if (check_syndrome () != 0) {
        correct_errors_erasures(codeword, codewordLength, 0, NULL);

        // convert back to hex for output
        int outputLen = codewordLength - numParityBytes;
        char codeword_hex[2*outputLen];
        raw_to_hex_str(codeword, outputLen, codeword_hex);
        printf("%.*s", 2*outputLen, codeword_hex);
        return 0;

    } else {
        // error correction error
        return 2;
    }
}
