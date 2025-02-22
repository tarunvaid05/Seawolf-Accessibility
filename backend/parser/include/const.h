/*
 * DO NOT MODIFY THE CONTENTS OF THIS FILE.
 * IT WILL BE REPLACED DURING GRADING
 */
 #ifndef CONST_H
 #define CONST_H
 
 #include <stdio.h>
 #include <stdlib.h>
 #include <stdint.h>
 #include <limits.h>
 #include <time.h>
 #include <utime.h>
 #include <dirent.h>
 #include <sys/stat.h>
#include <inttypes.h> // For PRId64, PRIu64 macros

 
 /*
  * Use the following macro to print out a help message and terminate
  * with a specified exit status.
  */
 
 #define USAGE(program_name, retcode) do { \
 fprintf(stderr, "USAGE: %s %s\n", program_name, \
 "[-h] [-s] [-b] [-n id] [-w id key ...]\n" \
 "   -h              Help: displays this help menu.\n" \
 "   -s              Summary: displays map summary information.\n" \
 "   -b              Bounding box: displays map bounding box.\n" \
 "   -n id           Node: displays information about the specified node.\n" \
 "   -w id key ...   Way: displays information about the specified way.\n" \
 exit(retcode); \
 } while(0)
 
 #endif
 