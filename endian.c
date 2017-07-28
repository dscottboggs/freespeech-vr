#define BIG_ENDIAN      0
#define LITTLE_ENDIAN   1

#include <stdio.h> 
#include <stdlib.h>

/*	Determines the endian-ness of the system.
 *	This was extracted from a shell script that was a part of the
 *	 installation for the CMU-Cambridge Statistical Language Modelling
 *	 toolkit. 
 * 
 *	It's easier in my opinion to have this C code be separate from the
 *	 installation script for my use case and be called by the script,
 *	 which checks the return value and then modifies the Makefile
 *	 instead of simply requesting the user to modify it.
*/

int little_endian(void) {
      short int w = 0x0001;
      char *byte = (char *) &w;
      return(byte[0] ? LITTLE_ENDIAN : BIG_ENDIAN);
}

main () {  
  if(!little_endian()) {
     printf("Big-endian, DO NOT set -DSLM_SWAP_BYTES in Makefile\n");
     exit(1);
  } 
  else {
     printf("Little-endian, set -DSLM_SWAP_BYTES in Makefile\n");
     exit(2);
  } 
}
