#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "protobuf.h"
#include "osm.h"
#include "zlib_inflate.h"


struct OSM_Node{
    OSM_Id id;
    OSM_Lat lat;
    OSM_Lon lon;
    struct OSM_Node *next;
} typedef OSM_Node;

typedef struct OSM_Way{
    OSM_Id id;
    struct refs{
        size_t size;
        OSM_Id *values;
    } refs;
    struct keys{
        size_t size;
        uint64_t *values;
    } keys;
    struct vals{
        size_t size;
        uint64_t *values;
    } vals;
    size_t string_table_index;
    struct OSM_Way *next;
} OSM_Way;

typedef struct Strings{
    size_t size;
    char *value;
    struct Strings *next;
} Strings;

typedef struct String_Table{
    size_t size;
    struct Strings *head;
    struct String_Table *next;
} String_Table;

int32_t len_of_string_tables;
String_Table *global_table;

//read length
uint32_t process_len(FILE *in){
    unsigned int len = 0;
    for(int i = 3; i >= 0; i--){
        uint32_t ch = fgetc(in);
        if(i == 3 && feof(in)) return 0;
        if(feof(in) || ch == EOF) return -1;
        //little endian reading
        len += (ch << (i * 8));
    }
    return len;
}


//read varint, we could POSSIBLY make this a union, however, I think it works either way even if we use just uint64_t.
//I will change to union if there appears to be an error

/**
 * @details FROM https://protobuf.dev/programming-guides/encoding/
 * Each byte in the varint has a continuation bit that indicates if the byte that follows it is part of the varint.
 * This is the most significant bit (MSB) of the byte (sometimes also called the sign bit).
 * The lower 7 bits are a payload; the resulting integer is built by appending together the 7-bit payloads of its constituent bytes.
 * We use shift because varint is stored as little-endian
 * @param in  The input stream from which data is to be read.
 * @param val  The pointer to put the value being read to
 * @return 0 if immediate EOF without error, no bytes read, -1 if immed EOF without error with bytes read, otherwise
 * returns n number of bytes read
 * */
int read_varint(FILE *in, uint64_t *val){
    uint64_t res = 0;
    int shift = 0;
    uint64_t ch;
    int bytes_read = 0;
    if(feof(in)) return 0;
    do
    {
        ch = fgetc(in);
        if(feof(in)){
            if(bytes_read) return -1;
            return 0;
        }

        //the first 7 bits are payloads
        res |= (ch & 0x7F) << shift;
        shift += 7;
        bytes_read++;
    }
    // keep reading until MSB is a 0 (1 meaning continuation, 0 means stop)
    while(ch & 0x80);
    if(bytes_read > 9) return -1;

    *val = res;
    return bytes_read;
}

int zig_zag_decode(int64_t *val){
    if(val == NULL) return -1;
    int64_t res = 0;

    //if val is odd, encode to negative: -(n+1)/2
    if(0x1 & *val){
        res = -((*val + 1) >> 1);

    }
    else {
        res = *val >> 1;
    }
    *val = res;

    return 0;
}

int create_sentinel(PB_Message *msg){
    *msg = malloc(sizeof(PB_Field));
    if (!msg) return -1;
    (*msg)->type = SENTINEL_TYPE;
    (*msg)->next = (*msg)->prev = (*msg);
    return 0;
}

/**
 * not much to this function, still nice to abstract it away
*/
int delta_decoding(uint64_t prev, uint64_t current, int64_t *val){
    uint64_t res = prev;
    res += prev;
    return res;
}


OSM_Node *Find_Node_by_id(OSM_Map *mp, OSM_Id id){
    if (!mp || OSM_Map_get_num_nodes(mp) == 0) return NULL;
    OSM_Node *curr_nd = OSM_Map_get_Node(mp, 0)->next;

    while(curr_nd && curr_nd->id != id) curr_nd = curr_nd->next;
    return curr_nd;
}

OSM_Way *Find_Way_by_id(OSM_Map *mp, OSM_Id id){
    if(!mp || OSM_Map_get_num_ways(mp) == 0) return NULL;
    OSM_Way *curr_w = OSM_Map_get_Way(mp, 0)->next;
    while(curr_w && curr_w->id != id) {curr_w = curr_w->next;}
    return curr_w;
}

int give_index_of_str(char *key, OSM_Way *wp){
    if(!key) return -1;
    if(len_of_string_tables == 0) return -1;
    String_Table *way_index = global_table;
    int count = 0;
    while(wp->string_table_index > count){way_index = way_index->next; count++;}
    count = 1;
    int size = way_index->size;
    Strings *curr = way_index->head->next;
    while(size > count){
        if(!strcmp(curr->value, key)) return count;
        count++;
        curr = curr->next;
    }

    return -1;
}

int val_using_key(int src_key, OSM_Way *wp){
    int index = 0;
    int num = wp->keys.size;
    while(num > index){
        int key = *(wp->keys.values+index);
        if (key == src_key) return index;
        index++;
    }
    return index;
}