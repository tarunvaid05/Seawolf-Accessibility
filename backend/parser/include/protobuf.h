
 #ifndef PROTOBUF_H
 #define PROTOBUF_H
 
 #include <stdio.h>
 #include <stdint.h>
#include <stdlib.h>
#include "const.h"
 
 /* Types of values that exist "on the wire" in protobuf. */
 
 typedef enum {
     VARINT_TYPE = 0,
     I64_TYPE = 1,
     LEN_TYPE = 2,
     SGROUP_TYPE = 3,
     EGROUP_TYPE = 4,
     I32_TYPE = 5,
 
     // Below are not legal wire types in protobuf messages,
     // and are used here for internal purposes.
     SENTINEL_TYPE = 8,
     ANY_TYPE = 9
 } PB_WireType;
 
 typedef enum {
     FORWARD_DIR = 0,
     BACKWARD_DIR = 1
 } PB_Direction;
 
 #define ANY_FIELD (-1)
 
 /*
  * Structure to represent a field in a message.
  */
 
 typedef struct PB_Field {
     PB_WireType type;
     int number;
     union value {
     uint32_t i32;
     uint64_t i64;
     struct bytes {
         size_t size;
         char *buf;
     } bytes;
     } value;
     struct PB_Field *next, *prev;
 } PB_Field;
 
 /*
  * A message is represented by a circular, doubly linked list of fields
  * that is headed by a "sentinel" field.  The sentinel field does not
  * contain any data and which has wire type SENTINEL_TYPE to distinguish
  * it from normal fields.  Traversing the list using either the next or
  * prev links starting from any field will eventually lead to the
  * sentinel.
  *
  * The following definition defines type PB_Message to be (PB_Field *).
  * That is, a PB_Message is simply pointer to the sentinel of a
  * list of fields comprising the message.
  */
 
 typedef PB_Field *PB_Message;
 
 /*
  * Exported functions.
  * These are discussed in the assignment document.
  * Refer also to the stubs in protobuf.c for more detailed specifications.
  */
 
 /* For reading messages from an input stream. */
 int PB_read_message(FILE *in, size_t len, PB_Message *msgp);
 int PB_read_field(FILE *in, PB_Field *fieldp);
 int PB_read_tag(FILE *in, PB_WireType *typep, int32_t *fieldp);
 int PB_read_value(FILE *in, PB_WireType type, union value *valuep);
 
 /* For reading embedded messages from memory buffers. */
 int PB_read_embedded_message(char *buf, size_t len, PB_Message *msgp);
 int PB_inflate_embedded_message(char *buf, size_t len, PB_Message *msgp);
 
 /* For traversing and manipulating PB_Message objects. */
 PB_Field *PB_next_field(PB_Field *prev, int fnum, PB_WireType type, PB_Direction dir);
 PB_Field *PB_get_field(PB_Message msg, int fnum, PB_WireType type);
 int PB_expand_packed_fields(PB_Message msg, int fnum, PB_WireType type);
 
 // For debugging (you are strongly advised to implement, but will not be tested)
 void PB_show_message(PB_Message msg, FILE *out);
 void PB_show_field(PB_Field *fp, FILE *out);
 
 #endif
 