#pragma once
#include <stdbool.h>
#include <stdint.h>
#include "frame_bundle.h"

// Every item in the game is authored in the Game Tools Item Editor and
// exported as one .c file dropped into assets/items/ — there is no
// other way to add an item. item_count / s_items below are generated at
// build time from whatever is in that folder (see items.c + the CMake glob
// in CMakeLists.txt); nothing here is hand-edited per item. The file name
// is the item's string id (wood.c -> "wood", symbol k_item_wood), and that
// id — never the index — is what map files use to say what a breakable drops.

#define ITEM_NONE 0   // empty inventory slot / bare hands — always id 0

// Held/used sprite animation, now a plain frame_bundle_t (see
// frame_bundle.h — shared with map animations and breakable hit effects).
// A 0x0000 pixel is transparent, same colorkey rule the map exporter uses.
//  - passive: loop_count is always -1 (loops the whole time it's held).
//  - use: frame_count == 0 means "no animation"; otherwise loop_count is
//    how many times the swing plays before holding its last frame.

// One name/value pair. Gameplay code reads these by name (item_attr() below)
// instead of new C code being written per attribute — e.g. "sellable 25".
typedef struct {
    const char *name;
    int32_t     value;
} item_attr_t;

typedef struct {
    const char        *id;             // stable string id, e.g. "axe" (also the export filename)
    const char        *display_name;   // shown in inventory UI
    uint8_t            max_stack;
    frame_bundle_t     passive;        // played while just holding it (loops forever)
    frame_bundle_t     use;            // played when used; frame_count==0 = none
    const item_attr_t *attrs;
    uint8_t            attr_count;
} item_asset_t;

extern const item_asset_t *const s_items[];  // s_items[0] is always the ITEM_NONE sentinel
extern const uint8_t             item_count;

const item_asset_t *item_get(uint8_t item);                              // NULL if out of range
int32_t             item_attr(uint8_t item, const char *name, int32_t fallback);
const char         *item_name(uint8_t item);
uint8_t             item_max_stack(uint8_t item);
uint8_t             item_find(const char *id);                           // ITEM_NONE if not found

// Selling: an item can be sold when it has a "sellable" attribute above 0 —
// the Game Tools Item Editor "Sellable" box writes it — and that value is
// what ONE of it sells for. Items without it (photo items too) can't be sold.
#define ITEM_ATTR_SELLABLE "sellable"
int32_t             item_sell_price(uint8_t item);                       // 0 = can't be sold
// What item_sell_price() multiplies "sellable" by, in % (100 = nothing): the
// item's legendary traits, each times its demand. Defined in main.c (LEGENDARY TRAITS).
int64_t             item_price_bonus_pct(uint8_t item);

// Buying: what a shop charges for ONE of it — a "buyable" attribute above 0
// (the Crops Editor's "Seed packet costs" box writes it on a crop's seeds).
// Items without it aren't for sale. A shop picks which items it stocks and
// asks this for the price.
#define ITEM_ATTR_BUYABLE "buyable"
int32_t             item_buy_price(uint8_t item);                        // 0 = no shop sells it
// "shop N" puts an item with a price on one counter, whatever it is (the Item
// Editor's / Shop Editor's "Counter"): 1 Seeds, 2 Build, 3 Ranch, 4 Tackle,
// 5 General. None = its usual one (props: Build, seeds and farm tools: Seeds,
// animal things: Ranch, rods and bait: Tackle, anything else: General).
#define ITEM_ATTR_SHOP    "shop"

// Quality (rarity): every stack has one. Most things are always Standard;
// an item with "quality 1" (the Item Editor's "Rolls a quality" box, or the
// Crops Editor for a crop's harvest) rolls one each time the player gets
// it — harvested, or dropped by a breakable. Rarer = worth more. The odds
// and price bonuses are k_quality[] in items.c; stacks only merge with
// the same quality. Shown as a star on the slot: none, silver, gold, emerald.
typedef enum {
    QUALITY_STANDARD = 0,   // no star
    QUALITY_SILVER,         // good
    QUALITY_GOLD,           // great
    QUALITY_EMERALD,        // best
    QUALITY_COUNT
} item_quality_t;
#define ITEM_ATTR_QUALITY "quality"
bool                item_has_quality(uint8_t item);
uint8_t             item_roll_quality(uint8_t item, uint32_t random);    // QUALITY_STANDARD for items without "quality"
const char         *item_quality_name(uint8_t quality);                  // "Standard", "Silver", ... (the grade; mutation ignored)
int32_t             item_sell_price_q(uint8_t item, uint8_t quality);    // item_sell_price() with the quality and mutation bonuses

// Mutations: anything the player catches, harvests or gets from a breakable
// can come out mutated — Shiny, Radioactive, Heavy... (MUTATIONS in main.c
// rolls them; k_mutation[] in items.c has the odds and prices). Rarer = worth
// more. Each changes how the item looks (recoloured, animated while held) and
// a few how it's held: Heavy squashes the player, Floaty bobs above them.
// "mut" multiplies an item's chance of one, % (none = 100 = x1, 0 = never);
// the rarer the mutation, the more it's boosted (the Item Editor writes it).
// A mutation lives in the HIGH 4 bits of a stack's quality byte, the grade
// (item_quality_t) in the low 3, so it goes wherever quality goes — the bag,
// the ground, shelves, auctions, saves — and stacks only merge with the same
// grade AND mutation. Use QUALITY_GRADE() before comparing with QUALITY_*.
// Ordered commonest first; new ones go at the end of their odds (max 15).
typedef enum {
    MUT_NONE = 0,
    MUT_SHINY,        // x1.5   sparkles, a glint runs across it
    MUT_FLOATY,       // x1.75  pale; held, it floats up and down over the head
    MUT_ALBINO,       // x2     white, pink-eyed
    MUT_HEAVY,        // x2.5   dark iron; held, it squashes the player
    MUT_GOLDEN,       // x3     gold, with a glint
    MUT_RADIOACTIVE,  // x4     green, glowing in pulses
    MUT_ELECTRIC,     // x4.5   blue, crackling with sparks
    MUT_GHOSTLY,      // x5     see-through, flickering
    MUT_RAINBOW,      // x10    stripes of colour, scrolling
    MUT_CELESTIAL,    // x25    the night sky, twinkling stars
    MUT_COUNT
} item_mutation_t;
#define ITEM_ATTR_MUT "mut"
// Bit 3 is QUALITY_WET: got in the rain (main.c WET ITEMS) — only looks
// different (darker, dripping while held), never changes the price; wet and
// dry stacks don't merge.
#define QUALITY_WET          0x08
#define QUALITY_GRADE(q)     ((uint8_t)((q) & 0x07))
#define QUALITY_MUT(q)       ((uint8_t)(((q) >> 4) & 0x0F))
#define QUALITY_IS_WET(q)    (((q) & QUALITY_WET) != 0)
#define QUALITY_MAKE(g, m)   ((uint8_t)(((g) & 0x07) | (((m) & 0x0F) << 4)))
bool                item_quality_ok(uint8_t quality);                    // a grade and mutation this build knows (loading saves)
const char         *item_mutation_name(uint8_t mut);                     // "Shiny", ...; "" for MUT_NONE
uint16_t            item_mutation_one_in(uint8_t mut);                   // its base odds: 1 catch in this many
uint16_t            item_mutation_price_pct(uint8_t mut);                // sell price, % of an unmutated one

// Dropping: any item can be put down on the map from the inventory (the DROP
// button) and picked back up by walking onto it — unless it has "droppable 0",
// which the Game Tools Item Editor writes when "Can be dropped" is unticked.
// No attribute at all = droppable (photo items too).
#define ITEM_ATTR_DROPPABLE "droppable"
bool                item_droppable(uint8_t item);

// Tilling: an item with "tills 1" is a hoe — used on a tile whose ground is
// ticked "Tillable" in the Map Editor, it turns it into farmland that seeds
// can be planted in (FARMING in main.c). Add the attribute in the Item Editor.
#define ITEM_ATTR_TILLS "tills"

// Watering: an item with "waters 1" (the Item Editor's "Watering can") is a
// watering can — used on farmland (or a crop in it) it waters it for the
// day. Crops only grow on days their farmland was watered (FARMING in main.c).
#define ITEM_ATTR_WATERS "waters"

// Farm animals (ANIMALS in main.c; animals.h). An animal's own item (same id
// as the animal) lets it out: hold it and tap open ground. These make the rest:
//   "feed 1"    hay — tap a hungry animal to feed it for the day
//   "cuts 1"    a scythe — tap grass to cut it (half the time it gives hay)
//   "grass 1"   grass starter — tap Tillable ground to grow grass there; grass
//               spreads by itself overnight, and animals eat it
//   "shears 1", "milks 1"  tools that take an animal's product off it — an
//               animal names the attribute its tool needs (animal_def_t.tool)
#define ITEM_ATTR_FEED   "feed"
#define ITEM_ATTR_CUTS   "cuts"
#define ITEM_ATTR_GRASS  "grass"

// Beds: a prop with "bed 1" (the Item Editor's "Bed") is a bed — tapping a
// placed one asks to sleep until the next morning (SLEEP in main.c).
#define ITEM_ATTR_BED "bed"

// Props: an item with "prop 1" (the Item Editor's "Can be placed") is
// furniture — a shelf, a crate, a rug. Held, a hologram of it shows in front
// of the player; tapping the hologram puts it down there (PLACEMENT in
// main.c), and tapping it with empty hands picks it back up. What's placed
// is frame 0 of its held art, at most 48x48 px, standing bottom-aligned on
// a footprint as many tiles wide as the art. "prop_rows" = how many tile
// rows deep that footprint is (default: all of the art's rows); the rows
// above it overhang and are drawn in front of the player. "prop_solid 0"
// makes the footprint walk-on (a rug); default solid.
#define ITEM_ATTR_PROP       "prop"
#define ITEM_ATTR_PROP_ROWS  "prop_rows"
#define ITEM_ATTR_PROP_SOLID "prop_solid"

// Shelves: a prop with "shelf N" (1..4, the Item Editor's "Shelf") holds N
// stacks for sale, shown on it side by side, standing on pixel row
// "shelf_y" of its art (counted from the top; default: half way down).
// Tapping a placed shelf opens it: stock it from the bag, set each slot's
// price, take things back (SHELVES in main.c).
#define ITEM_ATTR_SHELF      "shelf"
#define ITEM_ATTR_SHELF_Y    "shelf_y"

// Aquariums: a prop with "aquarium N" (1..4, the Item Editor's "Aquarium")
// holds N fish (items with "fish") that swim around in it (AQUARIUMS in
// main.c). They keep inside the box "aqua_x" "aqua_y" "aqua_w" "aqua_h" of
// its art (px from its top-left; default: 3 px in from each side). Tapping a
// placed one holding a fish puts the fish in; with empty hands takes the
// last one out (and picks the tank up once it's empty).
#define ITEM_ATTR_AQUARIUM   "aquarium"
#define ITEM_ATTR_AQUA_X     "aqua_x"
#define ITEM_ATTR_AQUA_Y     "aqua_y"
#define ITEM_ATTR_AQUA_W     "aqua_w"
#define ITEM_ATTR_AQUA_H     "aqua_h"

// Fishing (FISHING in main.c; the Item Editor's "Fishing" card). "rod 1" is a
// fishing rod: held, tapping Fishable water casts. "rod_bar" = its catch bar
// in the minigame, px (none = 64; the water is 280 tall — bigger is easier).
// "fish N" makes the item a fish, N = difficulty 1..100 (how wildly it swims);
// the rest are optional: "fish_move" 0 mixed, 1 smooth, 2 darting, 3 sinker,
// 4 floater; "fish_from" / "fish_to" the hours it bites (to < from = overnight;
// none = all day); "fish_weather" 0 any, 1 rain only, 2 dry only;
// "fish_rarity" its weight against the other fish that could bite (none = 10);
// "fish_min" / "fish_max" its size in inches.
// "fish_tier" 1..6 how rare it is: Common, Uncommon, Rare, Epic, Legendary,
// Mythic (none = Common) — shown on the catch card, colours the bite "!" and
// the fish in the minigame; a Mythic bites a quarter as often as its
// "fish_rarity" says. The Item Editor's "A fish" pop-up writes it, a rarity
// to match and the fish's "mut" (its mutation multiplier, see Mutations).
// A rod's stats (the Item Editor's sliders; each can be worse than normal too):
// "rod_reel" % how fast the catch meter fills (none = 100), "rod_bite" % how
// soon fish bite (200 = in half the time), "rod_luck" -50..100 (rarer fish and
// better quality; below 0 the other way), "rod_grip" % how slowly the meter
// drains with the fish out of the bar (200 = half as fast).
#define ITEM_ATTR_ROD          "rod"
#define ITEM_ATTR_ROD_BAR      "rod_bar"
#define ITEM_ATTR_ROD_REEL     "rod_reel"
#define ITEM_ATTR_ROD_BITE     "rod_bite"
#define ITEM_ATTR_ROD_LUCK     "rod_luck"
#define ITEM_ATTR_ROD_GRIP     "rod_grip"
#define ITEM_ATTR_FISH         "fish"
#define ITEM_ATTR_FISH_MOVE    "fish_move"
#define ITEM_ATTR_FISH_FROM    "fish_from"
#define ITEM_ATTR_FISH_TO      "fish_to"
#define ITEM_ATTR_FISH_WEATHER "fish_weather"
#define ITEM_ATTR_FISH_RARITY  "fish_rarity"
#define ITEM_ATTR_FISH_MIN     "fish_min"
#define ITEM_ATTR_FISH_MAX     "fish_max"
#define ITEM_ATTR_FISH_TIER    "fish_tier"

// Seasons (SEASONS in main.c): every 30 game days the next one of Spring,
// Summer, Fall, Winter. A set of them is a bit mask, SEASON_BIT(s) each
// (0 or no attribute = all year):
//  - "season" on a crop's SEED PACKET (the Crops Editor writes it): it can
//    only be planted then, shops only sell it then, and it withers the first
//    day of a season outside it (not inside buildings — a greenhouse).
//  - "fish_season" on a fish: it only bites then.
#define ITEM_ATTR_SEASON       "season"
#define ITEM_ATTR_FISH_SEASON  "fish_season"
enum { SEASON_SPRING, SEASON_SUMMER, SEASON_FALL, SEASON_WINTER, SEASON_COUNT };
#define SEASON_BIT(s)          (1u << (s))
#define SEASON_ALL             0x0F

// Lava fishing (FISHING in main.c). Ground ticked "Lava" in the Map Editor is
// a second pool with its own fish:
//  - "rod_lava 1": the rod can cast into lava (others: "it would burn up").
//    It still fishes water too.
//  - "fish_lava 1": the fish lives in lava — it only bites there, and water
//    fish never bite in lava.
#define ITEM_ATTR_ROD_LAVA     "rod_lava"
#define ITEM_ATTR_FISH_LAVA    "fish_lava"

// Bait (FISHING + BAIT in main.c; the Game Tools Bait Editor). "bait 1" makes
// an item bait: drop a stack of it on a rod in the inventory to put it on
// (BAIT_MAX at most); the card's TAKE OFF button gives it back. Each catch
// uses one. Bait stays with the rod's kind (two of the same rod share it).
//  - "rod_bait 1": the rod only casts with bait on it.
//  - "fish_bait 1": the fish only bites when there's bait on the line.
// A bait's stats (all optional; none = no change):
//  "bait_bite" % how soon fish bite (200 = in half the time)
//  "bait_bar" px more catch bar (below 0: smaller)
//  "bait_control" 0..100 bar control: the bar brakes and turns faster, bounces less
//  "bait_calm" 0..80 % calmer fish: their difficulty goes down that much
//  "bait_reel" / "bait_grip" % — times the rod's own (see rod_reel / rod_grip)
//  "bait_luck" points added to the rod's luck
//  "bait_mut" % mutation chance (200 = twice as likely)
//  "bait_tier" 2..6: only fish of this tier or rarer bite (when any can)
#define ITEM_ATTR_BAIT         "bait"
#define ITEM_ATTR_ROD_NEEDS_BAIT "rod_bait"
#define ITEM_ATTR_FISH_BAIT    "fish_bait"
#define ITEM_ATTR_BAIT_BITE    "bait_bite"
#define ITEM_ATTR_BAIT_BAR     "bait_bar"
#define ITEM_ATTR_BAIT_CONTROL "bait_control"
#define ITEM_ATTR_BAIT_CALM    "bait_calm"
#define ITEM_ATTR_BAIT_REEL    "bait_reel"
#define ITEM_ATTR_BAIT_GRIP    "bait_grip"
#define ITEM_ATTR_BAIT_LUCK    "bait_luck"
#define ITEM_ATTR_BAIT_MUT     "bait_mut"
#define ITEM_ATTR_BAIT_TIER    "bait_tier"

// Items made while the game runs (the camera viewer's "make it an item"). They
// come after the compiled-in ones and go through item_get() like any other item;
// the ones in the bag are kept with the save (photos.bin, see PHOTO ITEMS in main.c). `icon` (w*h RGB565, 0x0000 = transparent) becomes the
// item's passive art and must stay allocated. Max stack 1: each one is unique.
// Returns the new item, or ITEM_NONE if the table is full.
#define ITEM_NAME_MAX 20   // longest display name for a made item
uint8_t             item_add_custom(const char *name, const uint16_t *icon, uint16_t w, uint16_t h);

// The same, with attributes: a photo item carries its sell price ("sellable")
// and the traits the camera's appraisal found (see PHOTO TRAITS in main.c),
// e.g. { "razor_sharp", 2000 }. Up to ITEM_PHOTO_ATTR_MAX are kept; the
// names must stay valid for good (string literals).
#define ITEM_PHOTO_ATTR_MAX 14
uint8_t             item_add_photo(const char *name, const uint16_t *icon, uint16_t w, uint16_t h,
                                   const item_attr_t *attrs, uint8_t attr_count);

// Forgets every item made while the game ran and frees their icons (loading a
// save or starting a new one: the save's own photo items are made again from its
// photos.bin). Nothing may still hold one of them.
void                item_custom_reset(void);

// A photo item's lasting id ("pid"): random when it's made, kept in photos.bin,
// so a map's save can name one that sits on a shelf (SHELVES in main.c) —
// the "photo_N" ids change every time a save loads. 0 = not a photo item.
uint32_t            item_photo_pid(uint8_t item);
void                item_photo_set_pid(uint8_t item, uint32_t pid);   // loading photos.bin
uint8_t             item_find_photo(uint32_t pid);                    // ITEM_NONE if there's none
// A photo item standing on a shelf somewhere (not in the bag): photos.bin keeps it too.
bool                item_photo_shelved(uint8_t item);
void                item_photo_set_shelved(uint8_t item, bool on);
