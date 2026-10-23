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
//
// Farm buildings (the Game Tools Farm tab, "Barns, coops & silos" — the
// same file, with the fields after `pixels` filled in; older files leave
// them zero, an ordinary building):
//   A barn or a coop houses animals: `houses` names the kind ("barn",
//   "coop"), and an animal lives in one whose kind is its animal_def_t.house
//   (animals.h) — up to `capacity` of them, with as many troughs inside (the
//   inside map's objects with the "trough" action). Its animal door is one
//   tile of the footprint's bottom row (column animal_door - 1): tapped, it
//   opens or shuts. Open, its animals walk out of it in the morning to graze
//   and back in at 5 pm (FARM in main.c); `door_open` is how that tile looks
//   while it's open (TILE_SIZE x TILE_SIZE, NULL = the closed art darkened).
//   A silo stores hay (hay_capacity of it): grass cut with a scythe goes into
//   it, and pipes (fences.h) joining it to a barn or a coop fill that
//   building's troughs from it every morning. Taps take hay out, or put it in.
//   A well (water_source) fills a watering can that has a size ("water_max").
#define BUILDING_MAX_W 240   // px — the whole screen is 480
#define BUILDING_MAX_H 240

typedef struct {
    const char     *id;          // also its item's id
    uint16_t        w, h;        // art size in px (multiples of TILE_SIZE)
    uint8_t         foot_rows;   // bottom tile rows that are solid (1 .. h / TILE_SIZE)
    uint8_t         door_col;    // the door: this tile column of the footprint's bottom row
    const char     *interior;    // the map inside ("" = no way in)
    const uint16_t *pixels;      // w*h RGB565
    // ---- a farm building (all 0 / NULL: an ordinary one) ----
    const char     *houses;       // the animals it houses: "barn", "coop" ("" or NULL = none)
    uint8_t         capacity;     // how many (and troughs inside)
    uint8_t         animal_door;  // 1 + the animal door's column in the footprint's bottom row; 0 = none
    const uint16_t *door_open;    // TILE_SIZE x TILE_SIZE RGB565: that tile while the door is open; NULL = darkened
                                  // (door_w set: door_w x door_h, at door_x/door_y — see below)
    uint16_t        hay_capacity; // a silo: the hay it stores (0 = not a silo)
    // The animal door's looks when they aren't just its tile (Stardew's barns: a 2-tile
    // opening, left see-through in the picture): door_shut while it's shut, door_open
    // while it's open, both door_w x door_h, drawn at (door_x, door_y) in the art.
    // door_w 0 = the old way (door_open over the door tile, the art itself when shut).
    uint8_t         door_x, door_y, door_w, door_h;
    const uint16_t *door_shut;    // NULL = the art as it is while shut
    bool            water_source; // a well: tap it holding a watering can to fill the can (FARMING)
} building_def_t;

extern const building_def_t *const s_buildings[];
extern const uint8_t               building_count;
