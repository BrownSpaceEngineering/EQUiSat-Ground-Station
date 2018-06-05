#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "rscode1.3/ecc.h"
#include "hex_strings.h"

//int erasures[16];
//int nerasures = 0;

int main (int argc, char *argv[]) {
    if (argc != 2) {
        printf("Usage: rsencode <hex data>\n");
        return 0;
    }

    char* hexMsg = argv[1];
    int hexMsgLength = strlen(hexMsg);

    /* convert hex string to raw data */
    unsigned char msg[hexMsgLength/2];
    int success = hex_str_to_raw(hexMsg, hexMsgLength, msg);
    if (!success) {
        printf("hex string parse error\n");
        return 1;
    }

    /* Initialization the ECC library */
    initialize_ecc();

    /* Encode data into codeword, adding NPAR parity bytes */
    unsigned char codeword[256];
    encode_data(msg, hexMsgLength/2, codeword);

    /* convert back to hex for output */
    int outputLen = hexMsgLength/2 + NPAR;
    char codeword_hex[2*outputLen];
    raw_to_hex_str(codeword, outputLen, codeword_hex);
    printf("%s", codeword_hex);
    return 0;
}
