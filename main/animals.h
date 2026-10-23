#pragma once
#include <stdbool.h>
#include <stdint.h>

// Every farm animal is made in the Game Tools Animals Editor and exported as
// ONE file, assets/animals/<id>.c, which holds both parts of it:
//   k_animal_<id>   the animal: its sprite frames, how it moves, what it gives
//   k_item_<id>     the item that lets it out (a shop sells it — "buyable");
//                   hold it and tap open ground
// main/CMakeLists.txt adds the item to the item table and the animal to
// s_animals[], so nothing is hand-edited per animal. All of it is const: the
// art stays in flash and costs no RAM. An animal is found from its item by id
// (they share it).
//
// What it does (ANIMALS in main.c): it wanders the map it was let out on at
// random, and once a day, when it's hungry, walks to the nearest grass and
// eats `eats` tufts of it (or the player feeds it hay). Every product_days
// days it was FED it makes its product (product_chance % of the time — a
// pig's truffles), rare_chance % of them the rare one instead (a rabbit's
// foot). With no tool it drops it on the ground (eggs, truffles, rabbit
// wool); with a tool (`tool` = an item attribute, "shears" or "milks") the
// player takes it off the animal with that tool (wool, milk) — and until it
// grows back the animal shows frames_bare (a sheared sheep), if it has them.
// It sleeps where it stands from evening to morning, and makes its sound now
// and then (a WAV in sounds/sound effects — see SOUND EFFECTS in main.c).
//
// Art: frame_count frames of fw x fh RGB565 (0x0000 = see-through), frame
// after frame; the bottom of a frame stands on the bottom of the animal's
// tile, centred across it (a 32x32 cow overhangs half a tile each side).
// seq[] lists which frames each animation plays, seq_len[] how many (up to
// ANIMAL_SEQ_MAX). A walk with no LEFT frames plays its RIGHT frames
// mirrored. No EAT frames: it stands still eating; no SLEEP frames: it sleeps
// on its first walking-down frame.
//
// Colours (Stardew's white and brown cows and chickens): variant_count sheets
// laid out the same, one after another in frames (and frames_bare) —
// colour v's frame k is frame v * frame_count + k. The shop sells the one
// item; every animal let out is a random colour, kept for good, and is called
// "<variant name> <item name>" ("Brown Cow"). variant_count 0 or 1 = one colour.
// A colour can make its own product instead (variant_products: a white
// chicken's egg, a brown one's brown egg); "" there = the animal's `product`.
//
// Babies (Stardew's calf, chick, piglet...): with frames_baby and grow_days,
// every animal let out starts as a baby — frames_baby (laid out like
// `frames`, every colour), called "Baby <name>" — eats and wanders like the
// rest but makes nothing, and grows up after grow_days days.
//
// A home (Stardew's barns and coops): with `house` set ("barn", "coop"),
// the animal lives in a farm building of that kind (buildings.h `houses`)
// with room for it — it's let out on the map that building stands on, or in
// its inside, and from then on sleeps in it, walks out of its animal door in
// the morning when that's open, comes back at 5 pm, and eats hay from its
// troughs at night when it found no grass (FARM in main.c). No house ("" or
// NULL): it lives on the outdoor map it was let out on, the old way.
#define ANIMAL_FRAME_MAX 32   // px, either side
#define ANIMAL_SEQ_MAX   4

enum {
    ANIMAL_SEQ_DOWN = 0,
    ANIMAL_SEQ_RIGHT,
    ANIMAL_SEQ_UP,
    ANIMAL_SEQ_LEFT,
    ANIMAL_SEQ_EAT,
    ANIMAL_SEQ_SLEEP,
    ANIMAL_SEQ_COUNT
};

typedef struct {
    const char     *id;              // also its item's id
    uint8_t         fw, fh;          // frame size, px (at most ANIMAL_FRAME_MAX)
    uint8_t         frame_count;
    const uint16_t *frames;          // frame_count x fw*fh
    const uint16_t *frames_bare;     // the same frames with the product taken off it (NULL = looks the same)
    uint8_t         seq_len[ANIMAL_SEQ_COUNT];
    uint8_t         seq[ANIMAL_SEQ_COUNT][ANIMAL_SEQ_MAX];
    uint8_t         speed_q;         // walking speed, quarter pixels a game tick (the player walks 12)
    uint8_t         eats;            // grass tufts one meal takes (a tile has up to 4)
    const char     *product;         // item id of what it makes ("" = nothing)
    const char     *rare;            // item id it sometimes makes instead ("" = never)
    uint8_t         rare_chance;     // percent of products that are the rare one
    uint8_t         product_days;    // fed days from one product to the next (1 = every day)
    uint8_t         product_chance;  // percent chance a product that's due comes at all
    const char     *tool;            // "" = drops it on the ground; else the attribute of the tool that takes it
    const char     *sound;           // its sound effect ("" = none)
    uint8_t         variant_count;   // colours (0 / 1 = just the one)
    const char *const *variant_names;   // variant_count names ("White", "Brown"); NULL = none
    const uint16_t *frames_baby;     // its baby look, laid out like frames; NULL = no baby stage
    uint8_t         grow_days;       // days a baby takes to grow up (0 = no baby stage)
    const char *const *variant_products;   // per colour: the item it makes instead ("" = product); NULL = all make product
    const char     *house;           // the farm building kind it lives in ("barn", "coop"); "" or NULL = none
} animal_def_t;

extern const animal_def_t *const s_animals[];
extern const uint8_t             animal_count;
