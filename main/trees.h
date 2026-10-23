#pragma once
#include <stdbool.h>
#include <stdint.h>

// Every tree is made in the Game Tools Trees Editor and exported as ONE file,
// assets/trees/<id>.c, which holds both parts of it:
//   k_tree_<id>        the tree: its art for every stage and season, and its numbers (below)
//   k_item_<id>_seed   the seed (or sapling) the player plants it from
// main/CMakeLists.txt adds the seed to the item table and the tree to
// s_trees[], so nothing is hand-edited per tree. All of it is const: the art
// stays in flash and costs no RAM. A tree is found from its seed by id.
//
// Life of a tree (main.c TREES): four growing stages — 0 seed, 1 sprout,
// 2 sapling, 3 bush — spread evenly over grow_days game days, then grown
// (TREE_GROWN), then a stump once it's chopped down (TREE_STUMP).
//   seed     breaks with anything (bare hands too) and gives the seed back
//   sprout, sapling  break with any tool, give nothing
//   bush     chop_tool, bush_hits hits: bush_wood wood
//   grown    chop_tool, hits hits: it falls (leaves burst where it lands) and gives
//            wood_min..wood_max wood and 0..seed_max seeds; the stump is left.
//            Shaken (tapped with no tool) once a day: leaves fall and 0..shake_seed_max
//            seeds — nothing at all in winter. A fruit tree's fruit falls off too,
//            landing in front of it as items to walk over and pick up.
//            A fruit tree never drops its sapling (seed_max / shake_seed_max ignored);
//            its wood item is "hardwood" (the Trees Editor's default for one).
//   stump    chop_tool, stump_hits hits: stump_wood_min..max wood, then it's gone
// Every hit makes a few leaves fall (the season's leaf art).
//
// Art: every piece is bottom-centred on the tree's tile (its base). A grown
// tree is its log (standing on the base tile) with the canopy on top of it;
// no log = the canopy itself reaches the ground (fruit trees). Only the base
// tile is solid (bush, grown and stump; the seed, sprout and sapling are
// walked over); everything above the base tile is drawn in front of the player.
// Seasons: index 0 spring .. 3 winter. A season with no art of its own uses
// the season before it (summer -> spring...), so art that doesn't change is
// stored once. A wild tree's growing stages are seasonal; a fruit tree's are
// not (only [0] is used). Mossy: a grown wild tree with moss art turns mossy
// by chance (moss_pct a day, not in winter) and keeps it; it then shows its
// moss canopy and moss stump (where the season has them).
// Fruit trees: grown, in fruit_seasons, a fruit grows every fruit_days days
// (up to fruit_max, drawn on the canopy); shaking drops them. Out of season
// they fall off.
#define TREE_W         48    // widest art (a grown tree's canopy)
#define TREE_H         112   // tallest a grown tree can be: its canopy over its log
#define TREE_STAGES    4     // growing stages before it's grown: seed, sprout, sapling, bush
#define TREE_GROWN     4     // stage: fully grown
#define TREE_STUMP     5     // stage: chopped down, the stump left
#define TREE_LEAF_PX   16    // a falling leaf: frames of 16x16 side by side
#define TREE_FRUIT_MAX 3     // fruit shown on a tree at once

typedef struct {
    uint8_t         w, h;    // 0 x 0 = none
    const uint16_t *px;      // w * h RGB565, 0x0000 = see-through
} tree_art_t;

typedef struct {
    const char *id;                      // the seed's item is "<id>_seed"
    const char *name;                    // "Oak Tree"
    bool        fruit;                   // a fruit tree (never mossy; growing stages not seasonal)
    uint8_t     grow_days;               // game days from planted to grown (1..255)
    tree_art_t  stage[4][TREE_STAGES];   // [season][stage]: seed, sprout, sapling, bush
    tree_art_t  grown[4];                // the canopy, per season
    tree_art_t  moss[4];                 // the mossy canopy (none = never mossy)
    tree_art_t  log[4];                  // under the standing grown tree (none = the canopy stands on the ground)
    tree_art_t  stump[4];                // left when it's chopped down (none = nothing is left)
    tree_art_t  stump_moss[4];
    tree_art_t  leaf[4];                 // falling leaves: w = TREE_LEAF_PX * frames (none = no leaves that season)
    uint8_t     hits, bush_hits, stump_hits;   // chop_tool hits to fell it grown / break the bush / the stump
    uint8_t     wood_min, wood_max;      // felled grown
    uint8_t     seed_max;                // ...and 0..this seeds
    uint8_t     bush_wood;               // the bush broken
    uint8_t     stump_wood_min, stump_wood_max;
    uint8_t     shake_seed_max;          // 0..this seeds from the day's shake (not in winter)
    uint8_t     moss_pct;                // % odds a day a grown tree turns mossy (not in winter)
    const char *wood;                    // item id of the wood it gives ("wood")
    const char *chop_tool;               // item that chops it ("axe" — a better one "counts_as:axe")
    const char *fruit_item;              // fruit trees: the fruit's item id
    uint8_t     fruit_seasons;           // ...the seasons it fruits in (1 spring, 2 summer, 4 fall, 8 winter)
    uint8_t     fruit_days;              // ...a fruit every this many days
    uint8_t     fruit_max;               // ...at most this many on it (1..TREE_FRUIT_MAX)
    const char *sfx_hit, *sfx_fall;      // sounds (SD card sound effects; NULL = none)
} tree_def_t;

extern const tree_def_t *const s_trees[];
extern const uint8_t           tree_count;
