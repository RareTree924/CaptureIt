#pragma once
#include <stdbool.h>
#include <stdint.h>

// Fences, gates and pipes are made in the Game Tools Farm tab ("Fences &
// pipes") and exported as ONE file each, assets/fences/<id>.c, which holds
// both parts of it:
//   k_fence_<id>   its looks
//   k_item_<id>    the prop item that places it ("prop 1", "prop_rows 1";
//                  a fence or a gate is solid, a pipe is walked over); a
//                  shop sells it ("buyable" — the Build shop)
// main/CMakeLists.txt adds the item to the item table and the piece to
// s_fences[], so nothing is hand-edited per piece. All of it is const: the
// art stays in flash. A piece is found from its item by id (they share it).
//
// In game (PLACEMENT in main.c) they're props, one tile each, that join up
// with their neighbours: each piece shows the look for the sides it joins on.
// Fences and gates join each other; pipes join pipes, and the farm buildings
// they touch (buildings.h). `looks` holds FENCE_LOOKS looks of w x h RGB565
// (0x0000 = see-through), look k = joined on these sides: +1 up, +2 right,
// +4 down, +8 left (look 0 = on its own, 10 = left and right). A gate has
// twice as many: those 16 shut, then the same 16 open. w is one tile; h is
// one or two tiles — the top one overhangs the tile above, which the player
// (and the animals) walk behind.
// Tap a gate holding anything to open or shut it: open, it's walked through
// by the player and the animals alike (empty hands pick it up, like any prop).
// A line of pipes from a silo to a barn or a coop fills that building's
// troughs with the silo's hay every morning (FARM in main.c).
#define FENCE_LOOKS 16

enum { FENCE_KIND_FENCE = 0, FENCE_KIND_GATE, FENCE_KIND_PIPE };

typedef struct {
    const char     *id;      // also its item's id
    uint8_t         kind;    // FENCE_KIND_*
    uint8_t         w, h;    // one look, px: TILE_SIZE x (TILE_SIZE or 2 * TILE_SIZE)
    const uint16_t *looks;   // FENCE_LOOKS (a gate: 2 x FENCE_LOOKS) looks of w*h
} fence_def_t;

extern const fence_def_t *const s_fences[];
extern const uint8_t            fence_count;
