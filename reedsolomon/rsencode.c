#include <stdio.h>
#include <stdlib.h>
#include "ecc.h"

//int erasures[16];
//int nerasures = 0;
unsigned char codeword[256];

int main (int argc, char *argv[]) {
	if (argc != 3) {
    	printf("Usage: rsencode <msg> <msg_length>\n");
      	return 0;
  	}

  	unsigned char* msg = (unsigned char*) argv[1];
  	int msgLength = atoi(argv[2]);  

  	/* Initialization the ECC library */
    initialize_ecc ();

	/* Encode data into codeword, adding NPAR parity bytes */	
    encode_data(msg, msgLength, codeword);
    printf("%s", codeword);
}