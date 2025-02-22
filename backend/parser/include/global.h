
 #ifndef CONST_H
 #define CONST_H
 
 #include <stdio.h>
 #include <stdlib.h>
 
 #include "osm.h"
 
 /*
  * Use the following macro to print out a help message and terminate
  * with a specified exit status.
  */
 
 #define USAGE(program_name, retcode) do { \
 fprintf(stderr, "USAGE: %s %s\n", program_name, \
 "[-h] [-f filename] [-s] [-b] [-n id] [-w id] [-w id key ...]\n" \
 "   -h              Help: displays this help menu.\n" \
 "   -f filename     File: read map data from the specified file\n" \
 "   -s              Summary: displays map summary information.\n" \
 "   -b              Bounding box: displays map bounding box.\n" \
 "   -n id           Node: displays information about the specified node.\n" \
 "   -w id           Way refs: displays node references for the specified way.\n" \
 "   -w id key ...   Way values: displays values associated with the specified way and keys.\n"); \
 exit(retcode); \
 } while(0)
 
 /* Variable to be set by process_args if the '-h' flag is seen. */
 extern int help_requested;
 
 /* Variable to be set by process_args to any filename specified with '-f'. */
 extern char *osm_input_file;
 
 /*
  * This function is used to validate the command-line arguments and to perform
  * query processing.  See the specification associated with the stub in
  * process_args.c for more detail.  See the assignment document for details on
  * what kinds of arguments are to be handled and what kinds of queries are to
  * be performed.
  */
 
 int process_args(int argc, char **argv, OSM_Map *mp);
 
 #endif
 