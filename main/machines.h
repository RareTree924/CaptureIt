#pragma once
#include <stdbool.h>
#include <stdint.h>

// Every machine (Stardew's keg, cheese press, loom...: put something in, get
// something else out some days later) is made in the Game Tools Machines
// Editor and exported as ONE file, assets/machines/<id>.c, which holds both
// parts of it:
//   k_machine_<id>   what it makes: its recipes, and its art while it works
//   k_item_<id>      the item that places it: a prop ("prop 1", "prop_rows 1"),
//                    its held art being the machine as it stands idle (16x32);
//                    a shop sells it ("buyable" — the Build shop)
// main/CMakeLists.txt adds the item to the item table and the machine to
// s_machines[], so nothing is hand-edited per machine. All of it is const: the
// art stays in flash. A machine is found from its item by id (they share it).
//
// In game (MACHINES in main.c): it stands on one tile; the tile above is its
// top half, which the player walks behind. Tap it holding a recipe's input
// (at least in_count of it): that many go in, and `minutes` game minutes
// later (a day is 1440; the editor counts half days) out_count of the output
// are ready — its 16x16 icon shows over the machine until the player taps it
// to take them. Meanwhile it shows `working` (16x32, NULL = its idle art).
// Game time runs on maps the player isn't on, and while they sleep.
#define MACHINE_W           16
#define MACHINE_H           32
#define MACHINE_RECIPES_MAX 16

typedef struct {
    const char *input;      // item id that goes in
    uint8_t     in_count;   // how many of it one batch takes (1..)
    const char *output;     // item id that comes out
    uint8_t     out_count;  // how many of it (1..)
    uint32_t    minutes;    // game minutes it takes (720 = half a day)
} machine_recipe_t;

typedef struct {
    const char             *id;            // also its item's id
    const uint16_t         *working;       // MACHINE_W x MACHINE_H RGB565 while it works; NULL = the idle art
    uint8_t                 recipe_count;
    const machine_recipe_t *recipes;
} machine_def_t;

extern const machine_def_t *const s_machines[];
extern const uint8_t              machine_count;
