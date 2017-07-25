#define BIG_ENDIAN      0
#define LITTLE_ENDIAN   1

#include <stdio.h> 
#include <stdlib.h>

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
