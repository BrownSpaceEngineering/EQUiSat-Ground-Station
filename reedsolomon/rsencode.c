#include <stdio.h>
#include <stdlib.h>
#include "rscode1.3/ecc.h"
#include "hex_strings.h"

//int erasures[16];
//int nerasures = 0;

int main (int argc, char *argv[]) {
    if (argc != 3) {
        printf("Usage: rsencode <hex data> <hex data length>\n");
        return 0;
    }

    char* hexMsg = argv[1];
    int hexMsgLength = atoi(argv[2]);

    /* convert hex string to raw data */
    unsigned char msg[hexMsgLength/2];
    int success = hex_str_to_raw(hexMsg, hexMsgLength, msg);
    if (!success) {
        // hex string parse error
        return 1;
    }

    /* Initialization the ECC library */
    initialize_ecc();

    /* Encode data into codeword, adding NPAR parity bytes */
    unsigned char codeword[256];
    encode_data(msg, hexMsgLength, codeword);

    /* convert back to hex for output */
    int outputLen = hexMsgLength/2 + NPAR;
    char codeword_hex[2*outputLen];
    raw_to_hex_str(codeword, outputLen, codeword_hex);
    printf("%s", codeword_hex);
    return 0;
}
