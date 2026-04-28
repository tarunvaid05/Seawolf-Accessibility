#ifndef READ_HELPERS_H
#define READ_HELPERS_H

#include <stdio.h>
#include <stdint.h>
#include "protobuf.h"
#include "osm.h"

/**
 * HELPER FUNCTIONS FOR READING FILE
**/
unsigned int process_len(FILE *in);
int read_varint(FILE *in, uint64_t *val);
int create_sentinel(PB_Message *msg);
int zig_zag_decode(int64_t *val);
OSM_Node *Find_Node_by_id(OSM_Map *mp, OSM_Id id);
OSM_Way *Find_Way_by_id(OSM_Map *mp, OSM_Id id);
int give_index_of_str(char *key, OSM_Way *wp);
int val_using_key(int key, OSM_Way *wp);

#endif

