#include <stdio.h>
#include <stdlib.h>
#include "ecc.h"

int main (int argc, char *argv[]) {
	if (argc != 4) {
  		printf("Usage: rsdecode <encoded_msg> <encoded_msg_length> <num_parity_bytes>\n");
  		return 0;
  	}

  	unsigned char* codeword = (unsigned char*)argv[1];
  	int msgLength = atoi(argv[2]);
  	int num_parity_bytes = atoi(argv[3]);

  	/* Initialization the ECC library */
  	initialize_ecc ();

  	/* Decode string -- encoded codeword size must be passed */
  	decode_data(codeword, msgLength);

  	/* check if syndrome is all zeros */
  	if (check_syndrome () != 0) {
  		correct_errors_erasures (codeword, msgLength, 0, NULL);  		
  		printf("%.*s", msgLength - num_parity_bytes, codeword);
  	}
}