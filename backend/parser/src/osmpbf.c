#include <stdio.h>
#include <stdint.h>
#include <string.h>

#include "protobuf.h"
#include "osm.h"
#include "read_helpers.h"
#include "global.h"


//To include in OSM BBox
/**
 * min, max lon
 * min, max lat
 */
typedef struct OSM_BBox{
    OSM_Lon max_lon;
    OSM_Lon min_lon;
    OSM_Lat max_lat;
    OSM_Lat min_lat;
} OSM_BBox;

//To include in OSM Node
/**
 * id, lat, and lon
 * keys
 */
typedef struct OSM_Node{
    OSM_Id id;
    OSM_Lat lat;
    OSM_Lon lon;
    struct OSM_Node *next;
} OSM_Node;

//To include in OSM way
/**
 * id of way
 * num of reference and references
 * keys
 */
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

//To include in OSM Map:
/**
 * Bounding Box (req struct)
 * num of nodes (and nodes themselves)
 * num of ways (ways themselves)
 * num of relations (dont need relations apparently)
 */
typedef struct OSM_Map{
    OSM_BBox bbox;
    struct nodes{
        size_t size;
        OSM_Node *n;
    } nodes;
    struct ways{
        size_t size;
        OSM_Way *w;
    } ways;
    size_t num_relations;
} OSM_Map;

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

int32_t len_of_string_tables = 0;
String_Table *global_table;


/**
 * @brief Read map data in OSM PBF format from the specified input stream,
 * construct and return a corresponding OSM_Map object.  Storage required
 * for the map object and any related entities is allocated on the heap.
 * @param in  The input stream to read.
 * @return  If reading was successful, a pointer to the OSM_Map object constructed
 * from the input, otherwise NULL in case of any error.
 */

OSM_Map *OSM_read_Map(FILE *in) {
    if(ferror(in)) return NULL;
    PB_Message header_msg;

    int32_t header_len = process_len(in);
    if(header_len == 0){
        return NULL;
    }
    if(header_len < 1){
        fprintf(stderr, "unexpected EOF while reading len ");
        return NULL;
    }

    int bytes = 4;

    //we are reading from HeaderBlock
    if((bytes = PB_read_message(in, header_len, &header_msg)) < 1){
        if(bytes == 0) fprintf(stderr, "no file to read from ");
        else fprintf(stderr, "unexpected end of file");
        return NULL;
    }


    PB_Field *field;
    //read the header data
    if((field = PB_get_field(header_msg, 3, VARINT_TYPE))  == NULL) {fprintf(stderr, "unable to get field "); return NULL;}
    uint64_t data_len = field->value.i64;
    if((bytes = PB_read_message(in, data_len, &header_msg)) < 1){
        if(bytes == 0) fprintf(stderr, "no file to read from ");
        else fprintf(stderr, "unexpected end of file ");
        return NULL;
    }

    //read embedded message from HeaderBlock then get BBox
    PB_Message decompressed_msg;

    if((field = PB_get_field(header_msg, 3, LEN_TYPE)) == NULL) {fprintf(stderr, "unable to get field "); return NULL;}
    if(PB_inflate_embedded_message(field->value.bytes.buf, field->value.bytes.size, &decompressed_msg)) return NULL;

    PB_Field *bbox_fld;
    if((bbox_fld = PB_get_field(decompressed_msg, 1, LEN_TYPE)) == NULL) {fprintf(stderr, "unable to get field "); return NULL;}

    PB_Message bbox;
    if (PB_read_embedded_message(bbox_fld->value.bytes.buf, bbox_fld->value.bytes.size, &bbox)) return NULL;

    //1 is min_lon, 2 is max_lon, 3 is min lat, 4 is max lat
    int64_t coord_arr[4];
    for(int i = 0; i < 4; i++){
        if((bbox_fld = PB_get_field(bbox, i+1, VARINT_TYPE)) == NULL) {fprintf(stderr, "unable to get field "); return NULL;}
        int64_t zigzag = bbox_fld->value.i64;
        if(zig_zag_decode(&zigzag)) {fprintf(stderr, "unable to do zig zag decoding "); return NULL;}

        coord_arr[i] = zigzag;
    }

    OSM_Map *map = malloc(sizeof(OSM_Map));
    if(!map) {fprintf(stderr, "unable to allocate mem for map "); return NULL;}

    map->bbox.min_lon = coord_arr[0];
    map->bbox.max_lon = coord_arr[1];
    map->bbox.min_lat = coord_arr[2];
    map->bbox.max_lat = coord_arr[3];

    int error = 0;
    //global OSM_Map
    OSM_Node *starting_node = malloc(sizeof(OSM_Node));
    starting_node->id = 0;
    starting_node->lat = 0;
    starting_node->lon = 0;
    map->nodes.size = 0;
    map->nodes.n = starting_node;

    OSM_Way *starting_way = malloc(sizeof(OSM_Way));
    starting_way->id = 0;
    map->ways.size = 0;
    map->ways.w = starting_way;

    global_table = malloc(sizeof(String_Table));

    //process data blobs here
    while(!feof(in)){
        PB_Field *blob_fld;
        int32_t blob_len = process_len(in);
        if (blob_len == 0) break;
        if (blob_len == -1){error++; break;}
        PB_Message blob_header;
        int read_msg = 0;
        if((read_msg = PB_read_message(in, blob_len, &blob_header)) < 1){fprintf(stderr, "here! couldn't read file "); error++; break;}

        if((blob_fld = PB_get_field(blob_header, 1, LEN_TYPE)) == NULL) {fprintf(stderr, "unable to get field "); error++; break;}
        char *type = blob_fld->value.bytes.buf;

        if((blob_fld = PB_get_field(blob_header, 3, VARINT_TYPE)) == NULL){fprintf(stderr,"unable to get field "); error++; break;}
        uint32_t datasize = blob_fld->value.i64;

        //Read and decompress blob data
        PB_Message blob_data;
        if(strcmp(type, "OSMData") != 0){
            fprintf(stderr, "Expected OSMData ");
            error++;
            return NULL;
        }

        if((read_msg = PB_read_message(in, datasize, &blob_data)) < 1){fprintf(stderr, "couldn't read file "); error++; break;}

        //read raw size at some point
        if((blob_fld = PB_get_field(blob_data, 3, LEN_TYPE)) == NULL) {fprintf(stderr, "unable to get field "); error++; break;}

        PB_Message emb_data;
        if(PB_inflate_embedded_message(blob_fld->value.bytes.buf, blob_fld->value.bytes.size, &emb_data) == -1){
            error++;
            break;
        }

        PB_Field *emb_fld;

        //read primitive group
        PB_Message prim_group;
        if((emb_fld = PB_get_field(emb_data, 2, LEN_TYPE)) == NULL){fprintf(stderr, "unable to get field "); error++; break;}
        if(PB_read_embedded_message(emb_fld->value.bytes.buf, emb_fld->value.bytes.size, &prim_group)){fprintf(stderr,"couldn't read file "); error++; break;}

        int32_t granularity = 100;
        int64_t lat_offset = 0;
        int64_t lon_offset = 0;
        PB_Field *coordinates;
        if((coordinates = PB_get_field(emb_data, 17, VARINT_TYPE))) granularity = coordinates->value.i32;
        if((coordinates = PB_get_field(emb_data, 19, VARINT_TYPE))) lat_offset = coordinates->value.i64;
        if((coordinates = PB_get_field(emb_data, 20, VARINT_TYPE))) lon_offset = coordinates->value.i64;
        PB_Field *group_fld;

        //reading regular nodes
        if((group_fld = PB_get_field(prim_group, 1, LEN_TYPE)) != NULL){
            PB_Field *fldp;
            OSM_Node *prev_node = map->nodes.n;
            int count = 0;
            while(map->nodes.size > count) {prev_node = prev_node->next; count++;}

            fldp = PB_next_field(prim_group, 1, LEN_TYPE, FORWARD_DIR);
            while(fldp != NULL){
                PB_Message nodes;
                if(PB_read_embedded_message(fldp->value.bytes.buf, fldp->value.bytes.size, &nodes)){fprintf(stderr,"couldn't read file "); error++; break;}
                PB_Field *id_fld;
                PB_Field *lat_fld;
                PB_Field *lon_fld;


                OSM_Node *curr_node = malloc(sizeof(OSM_Node));
                if((id_fld = PB_get_field(nodes, 1, VARINT_TYPE)) == NULL){fprintf(stderr,"no id in nodes msg "); error++; free(curr_node); break;}
                curr_node->id = id_fld->value.i64;

                if((lat_fld = PB_get_field(nodes, 8, VARINT_TYPE)) == NULL){fprintf(stderr,"no lat in node "); error++; free(curr_node); break;}
                if((lon_fld = PB_get_field(nodes, 8, VARINT_TYPE)) == NULL){fprintf(stderr,"no lon in node "); error++; free(curr_node); break;}

                int64_t decode_lat = lat_fld->value.i64;
                int64_t decode_lon = lon_fld->value.i64;

                if(zig_zag_decode(&decode_lat)){fprintf(stderr, "unable to do zig zag decoding "); return NULL;}
                if(zig_zag_decode(&decode_lon)){fprintf(stderr, "unable to do zig zag decoding "); return NULL;}

                curr_node->lat = (lat_offset + (granularity * decode_lat));
                curr_node->lon = (lon_offset + (granularity * decode_lon));

                prev_node->next = curr_node;
                prev_node = curr_node;

                map->nodes.size++;

                fldp = PB_next_field(fldp, 1, LEN_TYPE, FORWARD_DIR);
            }
        }


        //If the prim group contains densenodes,
        if((group_fld = PB_get_field(prim_group, 2, LEN_TYPE)) != NULL){
            //Field 1 contains packed list of ids nodes
            //Fields 8 and 9 contains packed lists of lats and lons, delta encoded and parallel with ids of nodes
            PB_Message dense_nodes;

            if(PB_read_embedded_message(group_fld->value.bytes.buf, group_fld->value.bytes.size, &dense_nodes)){fprintf(stderr,"couldn't read file "); error++; break;}

            if(PB_expand_packed_fields(dense_nodes, 1, I64_TYPE)){fprintf(stderr, "error in expanding packed fields for dense nodes "); error++; break;}

            //Free PB_Field 5 since dense info not needed: TO BE ADDED

            if(PB_expand_packed_fields(dense_nodes, 8, I64_TYPE)){fprintf(stderr, "error in expanding packed fields for dense nodes "); error++; break;}
            if(PB_expand_packed_fields(dense_nodes, 9, I64_TYPE)){fprintf(stderr, "error in expanding packed fields for dense nodes "); error++; break;}

            //don't use get field probably because it starts at the end
            PB_Field *currentfld1 = PB_next_field(dense_nodes, 1, I64_TYPE, FORWARD_DIR);
            PB_Field *currentfld8 = PB_next_field(dense_nodes, 8, I64_TYPE, FORWARD_DIR);
            PB_Field *currentfld9 = PB_next_field(dense_nodes, 9, I64_TYPE, FORWARD_DIR);
            //don't use get field probably because it starts at the end

            //initialize values
            OSM_Node *prev_node = map->nodes.n;
            int count = 0;
            while(map->nodes.size > count) {prev_node = prev_node->next; count++;}

            int64_t prev_id = 0;
            int64_t prev_lat = 0;
            int64_t prev_lon = 0;

            // a lot of code is repeated here, could use arrays but for now this is fine
            while(currentfld1 && currentfld8 && currentfld9){
                OSM_Node *curr_node = malloc(sizeof(OSM_Node));

                int64_t decode_id = currentfld1->value.i64;
                int64_t decode_lat = currentfld8->value.i64;
                int64_t decode_lon = currentfld9->value.i64;

                if(zig_zag_decode(&decode_lat)){fprintf(stderr, "unable to do zig zag decoding "); return NULL;}
                if(zig_zag_decode(&decode_lon)){fprintf(stderr, "unable to do zig zag decoding "); return NULL;}
                if(zig_zag_decode(&decode_id)){fprintf(stderr, "unable to do zig zag decoding "); return NULL;}

                int64_t curr_id = decode_id + prev_id;
                int64_t lat = prev_lat + decode_lat;
                int64_t lon = prev_lon + decode_lon;

                prev_lat = lat;
                prev_lon = lon;
                prev_id = curr_id;

                curr_node->lat = (lat_offset + (granularity * lat));
                curr_node->lon = (lon_offset + (granularity * lon));
                curr_node->id = curr_id;

                prev_node->next = curr_node;
                prev_node = curr_node;

                map->nodes.size++;

                currentfld1 = PB_next_field(currentfld1, 1, I64_TYPE, FORWARD_DIR);
                currentfld8 = PB_next_field(currentfld8, 8, I64_TYPE, FORWARD_DIR);
                currentfld9 = PB_next_field(currentfld9, 9, I64_TYPE, FORWARD_DIR);
            }

        }
        //Ways
        else if((group_fld = PB_get_field(prim_group, 3, LEN_TYPE)) != NULL){
            //create new pb_field for ways
            PB_Field *fldp;
            OSM_Way *prev_way = map->ways.w;
            int count = 0;
            while(map->ways.size > count) {prev_way = prev_way->next; count++;}

            fldp = PB_next_field(prim_group, 3, LEN_TYPE, FORWARD_DIR);
            while(fldp != NULL){
                PB_Message ways;
                if(PB_read_embedded_message(fldp->value.bytes.buf, fldp->value.bytes.size, &ways)){fprintf(stderr,"couldn't read file "); error++; break;}
                PB_Field *fld1;
                PB_Field *fld2;
                PB_Field *fld3;
                PB_Field *fld8;

                //Initialize OSM ways
                OSM_Way *curr_way = malloc(sizeof(OSM_Way));
                if((fld1 = PB_get_field(ways, 1, VARINT_TYPE)) == NULL){fprintf(stderr,"no id in ways msg "); error++; free(curr_way); break;}
                curr_way->id = fld1->value.i64;
                curr_way->keys.size = 0;
                curr_way->vals.size = 0;
                curr_way->string_table_index = len_of_string_tables + 1;
                if((fld2 = PB_get_field(ways, 2, LEN_TYPE)) != NULL && (fld3 = PB_get_field(ways, 3, LEN_TYPE)) != NULL){
                    //Assume right size
                    if (fld2->value.bytes.size > fld3->value.bytes.size){
                        curr_way->keys.values = calloc(fld2->value.bytes.size,sizeof(uint64_t));
                        curr_way->vals.values = calloc(fld2->value.bytes.size,sizeof(uint64_t));
                    } else {
                        curr_way->keys.values = calloc(fld3->value.bytes.size,sizeof(uint64_t));
                        curr_way->vals.values = calloc(fld3->value.bytes.size,sizeof(uint64_t));
                    }

                    FILE *keys = fmemopen(fld2->value.bytes.buf, fld2->value.bytes.size, "r");
                    FILE *values = fmemopen(fld3->value.bytes.buf, fld3->value.bytes.size, "r");
                    int keys_read = 0;
                    int values_read = 0;
                    while(!feof(keys) || !feof(values)){
                        int bytes_keys = 0;
                        int bytes_vals = 0;
                        int64_t key = 0;
                        int64_t val = 0;

                        bytes_keys = read_varint(keys, &key);
                        bytes_vals = read_varint(values, &val);

                        if(bytes_keys == 0 && bytes_vals == 0){
                            break;
                        }

                        if(bytes_keys == 0 || bytes_vals == 0){fprintf(stderr, "different sizes for key and vals, %d != %d ",bytes_keys, bytes_vals); error++; free(curr_way); break;}
                        if(bytes_keys == -1 || bytes_vals == -1){fprintf(stderr, "unexpected EOF in reading keys/vals "); error++; free(curr_way); break;}
                        curr_way->keys.values[keys_read] = key;
                        curr_way->vals.values[values_read] = val;

                        keys_read++;
                        values_read++;
                    }


                    curr_way->keys.size = keys_read;
                    curr_way->vals.size = values_read;

                    fclose(keys);
                    fclose(values);
                }

                if((fld8 = PB_get_field(ways, 8, LEN_TYPE)) != NULL){
                    curr_way->refs.values = calloc(fld8->value.bytes.size, sizeof(int64_t));
                    if(PB_expand_packed_fields(ways, 8, I64_TYPE)){fprintf(stderr, "error in expanding packed fields for dense nodes "); error++; break;}
                    PB_Field *curr_ref = PB_next_field(ways, 8, I64_TYPE, FORWARD_DIR);
                    int64_t prev_ref_id = 0;
                    curr_way->refs.size = 0;
                    while(curr_ref){
                        int64_t decode_ref = curr_ref->value.i64;
                        if(zig_zag_decode(&decode_ref)){fprintf(stderr, "unable to decode ref in ways "); error++; break;}
                        int64_t ref_id = decode_ref + prev_ref_id;
                        prev_ref_id = ref_id;

                        curr_way->refs.values[curr_way->refs.size] = ref_id;

                        curr_way->refs.size++;
                        curr_ref = PB_next_field(curr_ref, 8, I64_TYPE, FORWARD_DIR);
                    }
                }

                map->ways.size++;
                prev_way->next = curr_way;
                prev_way = curr_way;
                fldp = PB_next_field(fldp, 3, LEN_TYPE, FORWARD_DIR);
            }

            //read string table
            PB_Message string_table;
            PB_Field *str_fld;
            if((str_fld = PB_get_field(emb_data, 1, LEN_TYPE)) == NULL){fprintf(stderr, "unable to get field "); error++; break;}
            if(PB_read_embedded_message(str_fld->value.bytes.buf, str_fld->value.bytes.size, &string_table)){fprintf(stderr,"couldn't read file "); error++; break;}
            PB_Field *curr_str_fld;
            if((curr_str_fld = PB_next_field(string_table, 1, LEN_TYPE, FORWARD_DIR)) == NULL){fprintf(stderr, "unable to get field "); error++; break;}
            if(curr_str_fld->value.bytes.size != 0){fprintf(stderr,"not str table "); error++; break;}
            Strings *prev = malloc(sizeof(Strings));
            String_Table *new_table = malloc(sizeof(String_Table));
            prev->size = 0;
            new_table->size = 0;
            new_table->head = prev;

            curr_str_fld = PB_next_field(curr_str_fld, 1, LEN_TYPE, FORWARD_DIR);
            while(curr_str_fld){
                Strings *curr_str = malloc(sizeof(Strings));

                curr_str->value = curr_str_fld->value.bytes.buf;
                curr_str->size = curr_str_fld->value.bytes.size;

                prev->next = curr_str;
                prev = curr_str;

                new_table->size++;

                curr_str_fld = PB_next_field(curr_str_fld, 1, LEN_TYPE, FORWARD_DIR);
            }

            String_Table *table_ptr = global_table;
            int table_count = 0;

            while(len_of_string_tables > table_count){table_ptr = table_ptr->next; table_count++;}
            table_ptr->next = new_table;
            len_of_string_tables++;

        }

        if(error) break;
    }

    //unallocate memory
    //don't have enough time to do so ;///
    if(error) return NULL;
    return map;
}

/**
 * @brief  Get the number of nodes in an OSM_Map object.
 *
 * @param  mp  The map object to query.
 * @return  The number of nodes.
 */

int OSM_Map_get_num_nodes(OSM_Map *mp) {
    if(!mp) return 0;
    return mp->nodes.size;
}

/**
 * @brief  Get the number of ways in an OSM_Map object.
 *
 * @param  mp  The map object to query.
 * @return  The number of ways.
 */

int OSM_Map_get_num_ways(OSM_Map *mp) {
    if(!mp) return 0;
    return mp->ways.size;
}

/**
 * @brief  Get the node at the specified index from an OSM_Map object.
 *
 * @param  mp  The map to be queried.
 * @param  index  The index of the node to be retrieved.
 * @param  return  The node at the specifed index, if the index was in
 * the valid range [0, num_nodes), otherwise NULL.
 */

OSM_Node *OSM_Map_get_Node(OSM_Map *mp, int index) {
    int num = OSM_Map_get_num_nodes(mp);
    if(num == 0){fprintf(stderr, "no nodes to be selected from "); return NULL;}
    if(index > num || index < 0){fprintf(stderr, "invalid index "); return NULL;}

    OSM_Node *curr_node = mp->nodes.n->next;

    int count = 0;
    while(index > count){
        curr_node = curr_node->next;
        count++;
    }

    return curr_node;
}

/**
 * @brief  Get the way at the specified index from an OSM_Map object.
 *
 * @param  mp  The map to be queried.
 * @param  index  The index of the way to be retrieved.
 * @param  return  The way at the specifed index, if the index was in
 * the valid range [0, num_ways), otherwise NULL.
 */

OSM_Way *OSM_Map_get_Way(OSM_Map *mp, int index) {
    int num = OSM_Map_get_num_ways(mp);
    if(num == 0){fprintf(stderr, "no ways to be selected from "); return NULL;}
    if(index > num || index < 0){fprintf(stderr, "invalid index "); return NULL;}

    OSM_Way *curr_way = mp->ways.w->next;

    int count = 0;
    while(index > count) {curr_way = curr_way->next; count++;}

    return curr_way;
}

/**
 * @brief  Get the bounding box, if any, of the specified OSM_Map object.
 *
 * @param  mp  The map object to be queried.
 * @return  The bounding box of the map object, if it has one, otherwise NULL.
 */

OSM_BBox *OSM_Map_get_BBox(OSM_Map *mp) {
    if(!mp) return NULL;
    return &(mp->bbox);
}

/**
 * @brief  Get the id of an OSM_Node object.
 *
 * @param np  The node object to be queried.
 * @return  The id of the node.
 */

int64_t OSM_Node_get_id(OSM_Node *np) {
    if(np == NULL){fprintf(stderr, "invalid node for get_id "); return 0;}
    return np->id;
}

/**
 * @brief  Get the latitude of an OSM_Node object.
 *
 * @param np  The node object to be queried.
 * @return  The latitude of the node, in nanodegrees.
 */

int64_t OSM_Node_get_lat(OSM_Node *np) {
    return np->lat;
}

/**
 * @brief  Get the longitude of an OSM_Node object.
 *
 * @param np  The node object to be queried.
 * @return  The latitude of the node, in nanodegrees.
 */

int64_t OSM_Node_get_lon(OSM_Node *np) {
    return np->lon;
}

int OSM_Node_get_num_keys(OSM_Node *np){abort();};
char *OSM_Node_get_key(OSM_Node *np, int index){abort();};
char *OSM_Node_get_value(OSM_Node *np, int index){abort();};

/**
 * @brief  Get the id of an OSM_Way object.
 *
 * @param wp  The way object to be queried.
 * @return  The id of the way.
 */

int64_t OSM_Way_get_id(OSM_Way *wp) {
    return wp->id;
}

/**
 * @brief  Get the number of node references in an OSM_Way object.
 *
 * @param wp  The way object to be queried.
 * @return  The number of node references contained in the way.
 */

int OSM_Way_get_num_refs(OSM_Way *wp) {
    return wp->refs.size;
}

/**
 * @brief  Get the node reference at a specified index in an OSM_Way object.
 *
 * @param wp  The way object to be queried.
 * @param index  The index of the node reference.
 * @return  The id of the node referred to at the specified index,
 * if the index is in the valid range [0, num_refs), otherwise NULL.
 */

OSM_Id OSM_Way_get_ref(OSM_Way *wp, int index) {
    int num = OSM_Way_get_num_refs(wp);
    if(num == 0){fprintf(stderr, "no refs to be selected from "); return 0;}
    if(index > num || index < 0){fprintf(stderr, "invalid index "); return 0;}

    return wp->refs.values[index];
}

/**
 * @brief  Get the number of keys in an OSM_Way object.
 *
 * @param np  The node object to be queried.
 * @return  The number of keys (or key/value pairs) in the way.
 */

int OSM_Way_get_num_keys(OSM_Way *wp) {
    return wp->keys.size;
}

/**
 * @brief  Get the key at a specified index in an OSM_Way object.
 *
 * @param wp  The way object to be queried.
 * @param index  The index of the key.
 * @return  The key at the specified index, if the index is in the valid range
 * [0, num_keys), otherwise NULL.  The key is returned as a pointer to a
 * null-terminated string.
 */

char *OSM_Way_get_key(OSM_Way *wp, int index)
{
    int num = OSM_Way_get_num_keys(wp);
    if(num == 0){fprintf(stderr, "no keys to be selected from "); return NULL;}
    if(index > num || index < 0){fprintf(stderr, "invalid index "); return NULL;}
    String_Table *way_table = global_table;
    uint64_t count = 0;
    while(wp->string_table_index > count){ way_table = way_table->next; count++;}

    uint64_t key = *(wp->keys.values + index);
    Strings *curr = way_table->head;
    count = 0;
    while(count < key){
        curr = curr->next;
        count++;
    }

    return curr->value;
}

/**
 * @brief  Get the value at a specified index in an OSM_Way object.
 *
 * @param wp  The way object to be queried.
 * @param index  The index of the value.
 * @return  The value at the specified index, if the index is in the valid range
 * [0, num_keys), otherwise NULL.  The value is returned as a pointer to a
 * null-terminated string.
 */

char *OSM_Way_get_value(OSM_Way *wp, int index) {
    int num = OSM_Way_get_num_keys(wp);
    if(num == 0){fprintf(stderr, "no keys to be selected from "); return NULL;}
    if(index > num || index < 0){fprintf(stderr, "invalid index "); return NULL;}
    String_Table *way_table = global_table;
    uint64_t count = 0;
    while(wp->string_table_index > count){ way_table = way_table->next; count++;}

    uint64_t value = *(wp->vals.values + index);
    Strings *curr = way_table->head;
    count = 0;
    while(value > count){
        curr = curr->next;
        count++;
    }

    return curr->value;
}

/**
 * @brief  Get the minimum longitude coordinate of an OSM_BBox object.
 *
 * @param bbp the bounding box to be queried.
 * @return  the minimum longitude coordinate of the bounding box, in nanodegrees.
 */

int64_t OSM_BBox_get_min_lon(OSM_BBox *bbp) {
    if(!bbp) return 0;
    return bbp->min_lon;
}

/**
 * @brief  Get the maximum longitude coordinate of an OSM_BBox object.
 *
 * @param bbp the bounding box to be queried.
 * @return  the maximum longitude coordinate of the bounding box, in nanodegrees.
 */

int64_t OSM_BBox_get_max_lon(OSM_BBox *bbp) {
    if(!bbp) return 0;
    return bbp->max_lon;
}

/**
 * @brief  Get the maximum latitude coordinate of an OSM_BBox object.
 *
 * @param bbp the bounding box to be queried.
 * @return  the maximum latitude coordinate of the bounding box, in nanodegrees.
 */

int64_t OSM_BBox_get_max_lat(OSM_BBox *bbp) {
    if(!bbp) return 0;
    return bbp->max_lat;
}

/**
 * @brief  Get the minimum latitude coordinate of an OSM_BBox object.
 *
 * @param bbp the bounding box to be queried.
 * @return  the minimum latitude coordinate of the bounding box, in nanodegrees.
 */

int64_t OSM_BBox_get_min_lat(OSM_BBox *bbp) {
    if(!bbp) return 0;
    return bbp->min_lat;
}

int way_is_steps(OSM_Way *wp) {

    int num_keys = OSM_Way_get_num_keys(wp);
    for(int i = 0; i < num_keys; i++){
        char *key = OSM_Way_get_key(wp, i);
        char *value = OSM_Way_get_value(wp, i);
        if(strcmp(key, "highway") == 0 && strcmp(value, "steps") == 0) return 1;
    }
    return 0;
}

int OSM_Way_steps_to_JSON(FILE *fp, OSM_Map *mp){
    if(!mp) {fprintf(stderr, "not a map "); return -1;}
    int num_ways = OSM_Map_get_num_ways(mp) - 1;
    if(num_ways == 0) {fprintf(stderr, "no ways to be selected from "); return -1;}
    fprintf(fp,"[\n");
    OSM_Way *way= OSM_Map_get_Way(mp, 0)->next;
    int printed_something = 0;
    for(int i = 0; i < num_ways; i++)
    {
        if(way_is_steps(way)){
            // if not the first item, print a comma to keep valid JSON syntax
            if(printed_something) fprintf(fp,",\n");
            printed_something = 1;

            // Printing the way_id
            fprintf(fp, "\t{\n");
            fprintf(fp, "\t\t\"way_id\": %ld,\n", way->id);
            fprintf(fp,"\t\t\"refs\": [");

            int num_refs = OSM_Way_get_num_refs(way);
            for(int j = 0; j < num_refs; j++){
                OSM_Id ref_id = OSM_Way_get_ref(way, j);
                OSM_Node *nd = Find_Node_by_id(mp, ref_id);

                // print comma between references
                if(j > 0) fprintf(fp,", ");

                if(nd){
                    fprintf(fp, "{\"id\": %ld, \"lat\": %ld, \"lon\": %ld}", 
                        ref_id, nd->lat, nd->lon);
                } else {
                    fprintf(fp, "{\"id\": %ld, \"lat\": 0, \"lon\": 0}", ref_id);
                }
            }
            fprintf(fp, "]\n\t}");
        }
        way = way->next;
    }
    fprintf(fp, "\n]\n");
    return 0;
}