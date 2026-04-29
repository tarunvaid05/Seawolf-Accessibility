#include <stdio.h>
#include <stdlib.h>

#include "global.h"
#include "osm.h"

int main(int argc, char **argv)
{
    FILE *fp = fopen("./data/sbu_map.pbf", "rb");
    if (fp == NULL)
    {
        printf("Error: File not found\n");
        return 1;
    }
    OSM_Map *mp = OSM_read_Map(fp);
    fclose(fp);
    if (mp == NULL)
    {
        printf("Error: Invalid file format\n");
        return 1;
    }
    FILE *json_file = fopen("ways_output.json", "w");
    if (OSM_Way_steps_to_JSON(json_file,mp)) {fprintf(stderr, "error in steps to json "); return 1;};

    return 0;
}