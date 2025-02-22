
 #ifndef OSM_H
 #define OSM_H
 
 #include "protobuf.h"
 
 typedef struct OSM_Map OSM_Map;     // A map following the OSM data model
 typedef struct OSM_BBox OSM_BBox;   // Bounding box for map
 typedef struct OSM_Node OSM_Node;   // Node in map
 typedef struct OSM_Way OSM_Way;     // Way in map
 
 typedef int64_t OSM_Id;             // Id of OSM element (node, way, relation)
 typedef int64_t OSM_Lat;            // Latitude (in nanodegrees)
 typedef int64_t OSM_Lon;            // Longitude (in nanodegrees)
 
 /*
  * Top-level constructor used by client to create an OSM_Map
  * from an input stream.
  */
 
 OSM_Map *OSM_read_Map(FILE *in);
 
 /*
  * Accessors, for querying map objects.
  */
 
 /* OSM_Map accessors */
 
 OSM_BBox *OSM_Map_get_BBox(OSM_Map *mp);
 int OSM_Map_get_num_nodes(OSM_Map *mp);
 int OSM_Map_get_num_ways(OSM_Map *mp);
 OSM_Node *OSM_Map_get_Node(OSM_Map *mp, int index);
 OSM_Way *OSM_Map_get_Way(OSM_Map *mp, int index);
 
 /* OSM_BBox accessors */
 
 OSM_Lon OSM_BBox_get_min_lon(OSM_BBox *bbp);
 OSM_Lon OSM_BBox_get_max_lon(OSM_BBox *bbp);
 OSM_Lat OSM_BBox_get_max_lat(OSM_BBox *bbp);
 OSM_Lat OSM_BBox_get_min_lat(OSM_BBox *bbp);
 
 /* OSM_Node accessors */
 
 OSM_Id OSM_Node_get_id(OSM_Node *np);
 OSM_Lat OSM_Node_get_lat(OSM_Node *np);
 OSM_Lon OSM_Node_get_lon(OSM_Node *np);
 int OSM_Node_get_num_keys(OSM_Node *np);
 char *OSM_Node_get_key(OSM_Node *np, int index);
 char *OSM_Node_get_value(OSM_Node *np, int index);
 
 /* OSM_Way accessors */
 
 OSM_Id OSM_Way_get_id(OSM_Way *wp);
 int OSM_Way_get_num_refs(OSM_Way *wp);
 int OSM_Way_get_num_keys(OSM_Way *wp);
 OSM_Id OSM_Way_get_ref(OSM_Way *wp, int index);
 char *OSM_Way_get_key(OSM_Way *wp, int index);
 char *OSM_Way_get_value(OSM_Way *wp, int index);
 
 #endif
 