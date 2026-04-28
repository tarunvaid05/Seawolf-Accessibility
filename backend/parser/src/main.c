#include <stdio.h>
#include <stdlib.h>

#include "global.h"
#include "osm.h"

int main(int argc, char **argv)
{
    FILE *fp = fopen("./data/sbu.pbf", "rb");
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
    printf("Nodes: %d\n", OSM_Map_get_num_nodes(mp));
    printf("Ways: %d\n", OSM_Map_get_num_ways(mp));
    return 0;
}