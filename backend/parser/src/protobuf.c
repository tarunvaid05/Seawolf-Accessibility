#include <stdio.h>
#include <stdlib.h>

#include "protobuf.h"
#include "zlib_inflate.h"
#include "read_helpers.h"
#include <zlib.h>

/**
 * @brief  Read data from an input stream, interpreting it as a protocol buffer
 * message.
 * @details  This function assumes that the input stream "in" contains at least
 * len bytes of data.  The data is read from the stream, interpreted as a
 * protocol buffer message, and a pointer to the resulting PB_Message object is
 * returned.
 *
 * @param in  The input stream from which to read data.
 * @param len  The number of bytes of data to read from the input stream.
 * @param msgp  Pointer to a caller-provided variable to which to assign the
 * resulting PB_Message.
 * @return 0 in case of an immediate end-of-file on the input stream without
 * any error and no input bytes having been read, -1 if there was an error
 * or unexpected end-of-file after reading a non-zero number of bytes,
 * otherwise the number n > 0 of bytes read if no error occurred.
 */

int PB_read_message(FILE *in, size_t len, PB_Message *msgp) {
    create_sentinel(msgp);
    int bytes_read = 0;
    while(bytes_read < len){
        //I'm very iffy on calling malloc inside a while loop like this, I should look for alt
        PB_Field *field = malloc(sizeof(PB_Field));
        int read_field = 0;
        if((read_field = PB_read_field(in, field)) < 1){
            if(read_field){ fprintf(stderr, "read_field error "); return -1;}
            else{ fprintf(stderr, "read_field didnt read any char "); return read_field;}
        }

        field->prev = (*msgp)->prev;
        field->next = (*msgp);
        (*msgp)->prev->next = field;
        (*msgp)->prev = field;
        bytes_read += read_field;
    }
    if(bytes_read != len) fprintf(stderr, "wrong bytes read and len, %d bytes != %ld len ", bytes_read, len);
    return bytes_read;
}

/**
 * @brief  Read data from a memory buffer, interpreting it as a protocol buffer
 * message.
 * @details  This function assumes that buf points to a memory area containing
 * len bytes of data.  The data is interpreted as a protocol buffer message and
 * a pointer to the resulting PB_Message object is returned.
 *
 * @param buf  The memory buffer containing the compressed data.
 * @param len  The length of the compressed data.
 * @param msgp  Pointer to a caller-provided variable to which to assign the
 * resulting PB_Message.
 * @return 0 in case of success, -1 in case any error occurred.
 */

int PB_read_embedded_message(char *buf, size_t len, PB_Message *msgp) {
    FILE *memstream = fmemopen(buf, len, "r");
    if (!memstream) return -1;
    int bytes_read = PB_read_message(memstream, len, msgp);
    if(bytes_read == len) return 0;
    fprintf(stderr, "failed to read embedded msg ");
    return -1;
}

/**
 * @brief  Read zlib-compressed data from a memory buffer, inflating it
 * and interpreting it as a protocol buffer message.
 * @details  This function assumes that buf points to a memory area containing
 * len bytes of zlib-compressed data.  The data is inflated, then the
 * result is interpreted as a protocol buffer message and a pointer to
 * the resulting PB_Message object is returned.
 *
 * @param buf  The memory buffer containing the compressed data.
 * @param len  The length of the compressed data.
 * @param msgp  Pointer to a caller-provided variable to which to assign the
 * resulting PB_Message.
 * @return 0 in case of success, -1 in case any error occurred.
 */

int PB_inflate_embedded_message(char *buf, size_t len, PB_Message *msgp) {
    FILE *source = fmemopen(buf, len, "r");
    if (!source){fprintf(stderr, "file fmemopen in inflate not working "); return -1;}

    FILE *dest = open_memstream(&buf, &len);
    if(!dest){fprintf(stderr, "open_mem in inflate not working "); return -1;}
    fflush(dest);

    int err;
    if((err = zlib_inflate(source, dest)) != Z_OK){
        fprintf(stderr, "zlib inflate error: %d\n", err);
        return -1;
    }

    fclose(source);
    fclose(dest);

    if(PB_read_embedded_message(buf, len, msgp)) return -1;
    return 0;
}

/**
 * @brief  Read a single field of a protocol buffers message and initialize
 * a PB_Field structure.
 * @details  This function reads data from the input stream in and interprets
 * it as a single field of a protocol buffers message.  The information read,
 * consisting of a tag that specifies a wire type and field number,
 * as well as content that depends on the wire type, is used to initialize
 * the caller-supplied PB_Field structure pointed at by the parameter fieldp.
 * @param in  The input stream from which data is to be read.
 * @param fieldp  Pointer to a caller-supplied PB_Field structure that is to
 * be initialized.
 * @return 0 in case of an immediate end-of-file on the input stream without
 * any error and no input bytes having been read, -1 if there was an error
 * or unexpected end-of-file after reading a non-zero number of bytes,
 * otherwise the number n > 0 of bytes read if no error occurred.
 */

int PB_read_field(FILE *in, PB_Field *fieldp) {
    int bytes_read_tag = 0;
    PB_WireType type;
    int32_t field;
    if((bytes_read_tag = PB_read_tag(in, &type, &field)) < 1){
        if (bytes_read_tag) fprintf(stderr, "unexpected end to file ");
        else fprintf(stderr, "no characters to read ");
        return bytes_read_tag;
    }

    int bytes_read_val = 0;
    if((bytes_read_val = PB_read_value(in, type, &fieldp->value)) < 1){
        fprintf(stderr, "unexpected end to file ");
        return -1;
    }

    fieldp->type = type;
    fieldp->number = field;
    return bytes_read_val + bytes_read_tag;
}

/**
 * @brief  Read the tag portion of a protocol buffers field and return the
 * wire type and field number.
 * @details  This function reads a varint-encoded 32-bit tag from the
 * input stream in, separates it into a wire type (from the three low-order bits)
 * and a field number (from the 29 high-order bits), and stores them into
 * caller-supplied variables pointed at by parameters typep and fieldp.
 * If the wire type is not within the legal range [0, 5], an error is reported.
 * @param in  The input stream from which data is to be read.
 * @param typep  Pointer to a caller-supplied variable in which the wire type
 * is to be stored.
 * @param fieldp  Pointer to a caller-supplied variable in which the field
 * number is to be stored.
 * @return 0 in case of an immediate end-of-file on the input stream without
 * any error and no input bytes having been read, -1 if there was an error
 * or unexpected end-of-file after reading a non-zero number of bytes,
 * otherwise the number n > 0 of bytes read if no error occurred.
 */

int PB_read_tag(FILE *in, PB_WireType *typep, int32_t *fieldp) {
    if(feof(in) || ferror(in)){
        return 0;
    }

    uint64_t tag;
    int bytes_read = 0;
    if((bytes_read = read_varint(in, &tag)) < 1){
        return bytes_read;
    }

    //type is first 3 bits
    *typep = (PB_WireType)(tag & 0x07);

    //field is the rest of the bits
    *fieldp = (int32_t)(tag >> 3);

    return bytes_read;
}

/**
 * @brief  Reads and returns a single value of a specified wire type from a
 * specified input stream.
 * @details  This function reads bytes from the input stream in and interprets
 * them as a single protocol buffers value of the wire type specified by the type
 * parameter.  The number of bytes actually read is variable, and will depend on
 * the wire type and on the particular value read.  The data read is used to
 * initialize the caller-supplied variable pointed at by the valuep parameter.
 * In the case of wire type LEN_TYPE, heap storage will be allocated that is
 * sufficient to hold the number of bytes read and a pointer to this storage
 * will be stored at valuep->bytes.buf.
 * @param in  T e input stream from which data is to be read.
 * @param type  The wire type of the value to be read.
 * @param valuep  Pointer to a caller-supplied variable that is to be initialized
 * with the data read.
 * @return 0 in case of an immediate end-of-file on the input stream without
 * any error and no input bytes having been read, -1 if there was an error
 * or unexpected end-of-file after reading a non-zero number of bytes,
 * otherwise the number n > 0 of bytes read if no error occurred.
 */

int PB_read_value(FILE *in, PB_WireType type, union value *valuep) {
    int bytes_read = 0;
    int64_t varint = 0;
    int64_t val_64 = 0;
    int64_t len = 0;
    int32_t val_32 = 0;
    switch(type){
        case VARINT_TYPE:
            if((bytes_read = read_varint(in, &varint)) < 1){
                return bytes_read;
            }
            valuep->i64 = varint;
            return bytes_read;
        

        case I64_TYPE: 
            if(fread(&val_64, sizeof(int64_t), 1, in) != 1) return -1;
            valuep->i64 = val_64;
            return 8;
        

        //len encoded as an int32 varint
        case LEN_TYPE: 
            if((bytes_read = read_varint(in,&len)) < 1){
                return bytes_read;
            }

            //ADD a check maybe for different length values, len may be more than 32 bits somehow ://

            valuep->bytes.size = len;
            valuep->bytes.buf = malloc(len);
            int read_len = 0;

            //fread reads data rt
            if((read_len = fread(valuep->bytes.buf, 1, len, in)) != len){
                free(valuep->bytes.buf);
                fprintf(stderr, "end of file while reading message ");
                return -1;
            }
            return bytes_read + read_len;

        case I32_TYPE:
            int32_t val_32;
            if(fread(&val_32, sizeof(int32_t), 1, in) != 1) return -1;
            valuep->i64 = val_32;
            return 4;

        default:
            fprintf(stderr, "unknown wire type %d", type);
            return -1;
    }
    //compiler bugs out without this return statement
    return bytes_read;
}


/**
 * @brief Get the next field with a specified number from a PB_Message object,
 * scanning the fields in a specified direction starting from a specified previous field.
 * @details  This function iterates through the fields of a PB_Message object,
 * until the first field with the specified number has is encountered or the end of
 * the list of fields is reached.  The list of fields is traversed, either in the
 * forward direction starting from the first field after prev if dir is FORWARD_DIR,
 * or the backward direction starting from the first field before prev if dir is BACKWARD_DIR.
 * When the a field with the specified number is encountered (or, if fnum is ANY_FIELD
 * any field is encountered), the wire type of that field is checked to see if it matches
 * the wire type specified by the type parameter.  Unless ANY_TYPE was passed, an error
 * is reported if the wire type of the field is not equal to the wire type specified.
 * If ANY_TYPE was passed, then this check is not performed.  In case of a mismatch,
 * an error is reported and NULL is returned, otherwise the matching field is returned.
 *
 * @param prev  The field immediately before the first field to be examined.
 * If dir is FORWARD_DIR, then this will be the field immediately preceding the first
 * field to be examined, and if dir is BACKWARD_DIR, then this will be the field
 * immediately following the first field to be examined.
 * @param fnum  Field number to look for.  Unless ANY_FIELD is passed, fields that do
 * not have this number are skipped over.  If ANY_FIELD is passed, then no fields are
 * skipped.
 * @type type  Wire type expected for a matching field.  If the first field encountered
 * with the specified number does not match this type, then an error is reported.
 * The special value ANY_TYPE matches any wire type, disabling this error check.
 * @dir  Direction in which to traverse the fields.  If dir is FORWARD_DIR, then traversal
 * is in the forward direction and if dir is BACKWARD_DIR, then traversal is in the
 * backward direction.
 * @return  The first matching field, or NULL if no matching fields are found, or the
 * first field that matches the specified field number does not match the specified
 * wire type.
 */

PB_Field *PB_next_field(PB_Field *prev, int fnum, PB_WireType type, PB_Direction dir) {
    if(!prev || fnum < 1) return NULL;
    if(prev->prev->type == SENTINEL_TYPE && prev->next->type == SENTINEL_TYPE) return NULL;
    if(dir != FORWARD_DIR && dir != BACKWARD_DIR){ fprintf(stderr, "invalid direction "); return NULL;};
    PB_Field *current = prev;
    current = (dir == FORWARD_DIR) ? (current->next) : current->prev;


    while(current->type != SENTINEL_TYPE){
        if(current == NULL) fprintf(stderr, "error in next field");

        if(fnum == ANY_FIELD || current->number == fnum){
            if(type != ANY_TYPE && current->type != type){
                fprintf(stderr, "correct field (%d) but wrong type (%d != %d) ", fnum, current->type, type);
                return NULL;
            }
            return current;
        }
        current = (dir == FORWARD_DIR) ? (current->next) : current->prev;
    }

    //Loop breaks if no matching fields found, thus return null
    return NULL;
}

/**
 * @brief Get a single field with a specified number from a PB_Message object.
 * @details  This is a convenience function for use when it is desired to get just
 * a single field with a specified field number from a PB_Message, rather than
 * iterating through a sequence of fields.  If there is more than one field having
 * the specified number, then the last such field is returned, as required by
 * the protocol buffers specification.
 *
 * @param msg  The PB_Message object from which to get the field.
 * @param fnum  The field number to get.
 * @param type  The wire type expected for the field, or ANY_TYPE if no particular
 * wire type is expected.
 * @return  A pointer to the field, if a field with the specified number exists
 * in the message, and (unless ANY_TYPE was passed) that the type of the field
 * matches the specified wire type.  If there is no field with the specified number,
 * or the last field in the message with the specified field number does not match
 * the specified wire type, then NULL is returned.
 */

PB_Field *PB_get_field(PB_Message msg, int fnum, PB_WireType type) {
    return PB_next_field(msg, fnum, type, BACKWARD_DIR);
}


/**
 * @brief  Replace packed fields in a message by their expansions.
 * @detail  This function traverses the fields in a message, looking for fields
 * with a specified field number.  For each such field that is encountered,
 * the content of the field is treated as a "packed" sequence of primitive values.
 * The original field must have wire type LEN_TYPE, otherwise an error is reported.
 * The content is unpacked to produce a list of normal (unpacked) fields,
 * each of which has the specified wire type, which must be a primitive type
 * (i.e. not LEN_TYPE) and the specified field number.
 * The message is then modified by splicing in the expanded list in place of
 * the original packed field.
 *
 * @param msg  The message whose fields are to be expanded.
 * @param fnum  The field number of the fields to be expanded.
 * @param type  The wire type expected for the expanded fields.
 * @return 0 in case of success, -1 in case of an error.
 * @modifies  the original message in case any fields are expanded.
 */

int PB_expand_packed_fields(PB_Message msg, int fnum, PB_WireType type) {
    if(type == LEN_TYPE || type == SENTINEL_TYPE){fprintf(stderr, "invalid wiretype for expand fields "); return -1;}
    PB_Field *fld;
    if ((fld = PB_get_field(msg, fnum, LEN_TYPE)) == NULL){fprintf(stderr, "couldn't find field "); return -1;}

    FILE *memstream = fmemopen(fld->value.bytes.buf, fld->value.bytes.size, "r");
    if (!memstream) return -1;

    PB_Message packed_content;
    create_sentinel(&packed_content);
    uint64_t bytes_read = 0;
    while((!feof(memstream) && !ferror(memstream)) && fld->value.bytes.size > bytes_read){
        PB_Field *packed_fld = malloc(sizeof(PB_Field));
        packed_fld->type = type;
        packed_fld->number = fnum;
        uint64_t test;
        uint8_t bytes_read_varint = 0;
        if((bytes_read_varint = read_varint(memstream, &test)) < 1){
            if(bytes_read_varint){fprintf(stderr, "unexpected end to file "); return -1;}
            else {fprintf(stderr, "end of memstream and can't read, length more than file length, %zu != %zu ", fld->value.bytes.size, bytes_read); break;}
        } //free everything later

        bytes_read += bytes_read_varint;
        if(type == VARINT_TYPE || type == I64_TYPE){
            packed_fld->value.i64 = test;
        } else if(type == I32_TYPE){
            packed_fld->value.i32 = test;
        } else {
            fprintf(stderr, "wrong type ");
            return -1;
        }

        packed_fld->prev = packed_content->prev;
        packed_fld->next = packed_content;

        packed_content->prev->next = packed_fld;
        packed_content->prev = packed_fld;
    }

    packed_content->next->prev = fld->prev;
    packed_content->prev->next = fld->next;

    fld->prev->next = packed_content->next;
    fld->next->prev = packed_content->prev;

    free(fld);
    free(packed_content);
    return 0;
}



/**
 * @brief  Output a human-readable representation of a message field
 * to a specified output stream.
 * @details  This function, which is intended only for debugging purposes,
 * outputs a human-readable representation of the message field object
 * pointed to by fp, to the output stream out.  The output may be in any
 * format deemed useful.
 */

void PB_show_field(PB_Field *fp, FILE *out) {
    fprintf(out, " PB_Field #%d [",fp->number);
        fprintf(out, "type: ");
        switch(fp->type){
        case VARINT_TYPE:
            fprintf(out, "VARINT, ");
            fprintf(out, "value: %zu",fp->value.i64);
            break;

        case I32_TYPE:
            fprintf(out,"I32, ");
            fprintf(out,"value: %u", fp->value.i32);
            break;

        case I64_TYPE:
            fprintf(out, "I64, ");
            fprintf(out, "value: %zu", fp->value.i64);
            break;

        case LEN_TYPE:
            fprintf(out, "LEN, ");
            fprintf(out,"size: %zu, ", fp->value.bytes.size);
            fprintf(out,"content: ");
            for(int i = 0; i < fp->value.bytes.size && i < 32; i++){
                unsigned char val = *(fp->value.bytes.buf+i);
                if (val < 65 || val > 122) fprintf(out, "\\%o", val);
                else fprintf(out, "\\%c", val);
            }
            break;

        case SENTINEL_TYPE:
            fprintf(out,"somehow sentinel??");
            break;

        default:
            fprintf(out, "unknown type");
            break;
        }
        fprintf(out,"]\n");
}

/**
 * @brief  Output a human-readable representation of a message object
 * to a specified output stream.
 * @details  This function, which is intended only for debugging purposes,
 * outputs a human-readable representation of the message object msg to
 * the output stream out.  The output may be in any format deemed useful.
 */

void PB_show_message(PB_Message msg, FILE *out) {
    // if (PB_expand_packed_fields(msg, 3, ANY_TYPE)){fprintf(out,"invalid expand"); return;}
    // if(msg == NULL || msg->type != SENTINEL_TYPE){
    //     fprintf(out, "Invalid Message");
    //     return;
    // }
    fprintf(out, "sentinel: %d",msg->type);
    PB_Message *current = &(msg->next);
    fprintf(out, "next node: %d", (*current)->type);
    int total_fields = 0;
    fprintf(out, "Protocol Buffer Message:\n");
    fprintf(out, "=======================\n{\n");
    while(*current != msg){
        PB_show_field(*current, out);
        current = &(*current)->next;
        total_fields++;
    }

    fprintf(out,"}\n Total fields: %d\n", total_fields);
    return;
}
