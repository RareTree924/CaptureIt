#pragma once
#include <stdbool.h>
#include <stdint.h>

// Every building is made in the Game Tools Buildings Editor and exported as
// ONE file, assets/buildings/<id>.c, which holds both parts of it:
//   k_building_<id>   what stands on the map: its art, footprint and door
//   k_item_<id>       the item that places it (a shop sells it — "buyable")
// main/CMakeLists.txt adds the item to the item table and the building to
// s_buildings[], so nothing is hand-edited per building. All of it is const:
// the art stays in flash and costs no RAM. A building is found from its item
// by id (they share it).
//
// Placing (PLACEMENT in main.c): hold the item, and a hologram of the building
// shows in front of the player; tap the hologram to build it there. It needs
// Buildable ground under its whole footprint (the Map Editor's "Buildable" on
// a ground tile) and can't go inside another building.
//
// Art: w x h RGB565, 0x0000 = see-through, both multiples of TILE_SIZE (the
// editor pads it). It stands bottom-aligned on its footprint, w / TILE_SIZE
// tiles wide and foot_rows tiles deep — those tiles are solid. The rows above
// overhang: never solid, and drawn in front of the player (they walk behind
// the roof). The door is one tile in the footprint's bottom row, column
// door_col: walkable, and walking into it goes inside — `interior` is the map
// that's inside (MAPS_DIR/<interior>/<interior>.map). Every placed building
// gets its own copy of that inside (its own save), and the interior's
// "Building exit" teleporter brings the player back out to the door.
#define BUILDING_MAX_W 240   // px — the whole screen is 480
#define BUILDING_MAX_H 240

typedef struct {
    const char     *id;          // also its item's id
    uint16_t        w, h;        // art size in px (multiples of TILE_SIZE)
    uint8_t         foot_rows;   // bottom tile rows that are solid (1 .. h / TILE_SIZE)
    uint8_t         door_col;    // the door: this tile column of the footprint's bottom row
    const char     *interior;    // the map inside ("" = no way in)
    const uint16_t *pixels;      // w*h RGB565
} building_def_t;

extern const building_def_t *const s_buildings[];
extern const uint8_t               building_count;
