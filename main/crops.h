#pragma once
#include <stdbool.h>
#include <stdint.h>

// Every crop is made in the Game Tools Crops Editor and exported as ONE
// file, assets/crops/<id>.c, which holds all three parts of it:
//   k_crop_<id>         the plant: its growth-stage art and timers (below)
//   k_item_<id>         what a harvest gives (sell value, icon, "quality 1")
//   k_item_<id>_seeds   the seed packet the player plants it from
// main/CMakeLists.txt adds both items to the item table and the crop to
// s_crops[], so nothing is hand-edited per crop. All of it is const: the art
// stays in flash and costs no RAM. A crop is found from its seeds by id.
//
// Growth is counted in GAME days (the CLOCK in main.c), separately for every
// planted crop. Stage art is CROP_W x CROP_H, 0x0000 = transparent; the bottom
// half sits on the tile it's planted in, the top half overhangs the tile above.
//   One harvest (regrow_days == 0): stages 0 .. N-1, the LAST one is ripe;
//     harvesting it removes the plant.
//   Regrows (regrow_days > 0): stages 0 .. N-2 grow it, the SECOND-TO-LAST is
//     ripe; harvesting shows the last stage (picked), and regrow_days later
//     it's ripe again — those two stages loop for good.
// Collision: only the bottom half (the planted tile, 16x16) can block the
// player — unless walk_through is set ("Solid" unticked in the editor). The
// top half never blocks. All its art is drawn in front of the player.
// Harvest size: 1, or — with extra_chance percent odds — extra_min..extra_max
// of it. extra_chance 0 (older crop files) = always 1. One quality roll
// covers the whole harvest.
#define CROP_W          16
#define CROP_H          32
#define CROP_STAGES_MIN 6
#define CROP_STAGES_MAX 8

typedef struct {
    const char     *id;            // also the harvest item's id; the seeds are "<id>_seeds"
    uint8_t         stage_count;   // CROP_STAGES_MIN .. CROP_STAGES_MAX
    uint8_t         grow_days;     // game days from planting to ripe (1..255)
    uint8_t         regrow_days;   // 0 = harvested once; else days from picked back to ripe
    const uint16_t *stages;        // stage_count x CROP_W*CROP_H RGB565, stage after stage
    bool            walk_through;  // false = its tile is solid (the default); true = the player walks through it
    uint8_t         extra_chance;  // 0..100: percent chance a harvest gives extra_min..extra_max instead of 1
    uint8_t         extra_min, extra_max;
} crop_def_t;

extern const crop_def_t *const s_crops[];
extern const uint8_t           crop_count;
