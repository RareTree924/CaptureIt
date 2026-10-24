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

// An item's number in s_items[] (then the photo items after it). 16 bits: room
// for ITEM_ID_MAX items in all. Numbers aren't stable across builds — maps and
// saves name items by their string id (item_find()).
typedef uint16_t item_id_t;
#define ITEM_ID_MAX 65535

// Held/used sprite animation, now a plain frame_bundle_t (see
// frame_bundle.h — shared with map animations and breakable hit effects).
// A 0x0000 pixel is transparent, same colorkey rule the map exporter uses.
//  - passive: loop_count is always -1 (loops the whole time it's held).
//  - use: a tool's swing art (see "Tools" below), drawn on the player while
//    it's swung; frame_count == 0 means none.

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
    frame_bundle_t     front;          // a prop's front layer (a bed's sheet), the same size as passive frame 0:
                                       // where it isn't 0x0000 it's drawn over the player; frame_count==0 = none
    const item_attr_t *attrs;
    uint8_t            attr_count;
} item_asset_t;

extern const item_asset_t *const s_items[];  // s_items[0] is always the ITEM_NONE sentinel
extern const item_id_t           item_count;

const item_asset_t *item_get(item_id_t item);                              // NULL if out of range
int32_t             item_attr(item_id_t item, const char *name, int32_t fallback);
const char         *item_name(item_id_t item);
uint8_t             item_max_stack(item_id_t item);
item_id_t           item_find(const char *id);                           // ITEM_NONE if not found

// Selling: an item can be sold when it has a "sellable" attribute above 0 —
// the Game Tools Item Editor "Sellable" box writes it — and that value is
// what ONE of it sells for. Items without it (photo items too) can't be sold.
#define ITEM_ATTR_SELLABLE "sellable"
int32_t             item_sell_price(item_id_t item);                       // 0 = can't be sold
// What item_sell_price() multiplies "sellable" by, in % (100 = nothing): the
// item's legendary traits, each times its demand. Defined in main.c (LEGENDARY TRAITS).
int64_t             item_price_bonus_pct(item_id_t item);

// Buying: what a shop charges for ONE of it — a "buyable" attribute above 0
// (the Crops Editor's "Seed packet costs" box writes it on a crop's seeds).
// Items without it aren't for sale. A shop picks which items it stocks and
// asks this for the price.
#define ITEM_ATTR_BUYABLE "buyable"
int32_t             item_buy_price(item_id_t item);                        // 0 = no shop sells it
// "shop N" puts an item with a price on one counter, whatever it is (Game Tools' Item Editor /
// Shop Editor "Counter"): 1 Seeds, 2 Build, 3 Ranch, 4 Fish, 5 General. None = its usual one
// (seeds and farm tools: Seeds, props: Build, animal things: Ranch, rods / bait / tackle / crab
// pots: Fish, anything else: General).
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
bool                item_has_quality(item_id_t item);
uint8_t             item_roll_quality(item_id_t item, uint32_t random);    // QUALITY_STANDARD for items without "quality"
const char         *item_quality_name(uint8_t quality);                  // "Standard", "Silver", ... (the grade; mutation ignored)
int32_t             item_sell_price_q(item_id_t item, uint8_t quality);    // item_sell_price() with the quality and mutation bonuses

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
bool                item_droppable(item_id_t item);

// Tilling: an item with "tills 1" is a hoe — used on a tile whose ground is
// ticked "Tillable" in the Map Editor, it turns it into farmland that seeds
// can be planted in (FARMING in main.c). Add the attribute in the Item Editor.
#define ITEM_ATTR_TILLS "tills"

// Tools (TOOL SWING in main.c; the Item Editor's "Tool use" box): "tool 1"
// makes the item swing whenever it's used on what the player walked up to —
// its `use` art (16x32, drawn right on the player; behind them facing up;
// 1 frame = every way, 3 = down, up, sideways, 4 = down, up, left, right;
// interval_ms = how long the swing shows), a swipe through the tile in front
// ("tool_swipe 0" = none), and a sound: "tool_sfx:<name>" 1 (a WAV in the
// SD card's sounds/sound effects, without .wav; several = one at random).
// The hit on a breakable / farmland lands mid-swing.
// "tool_power N": hits one swing lands on a breakable (none = 1).
// "counts_as:<item id>" 1: a breakable that needs that item takes this one
// too (a copper axe "counts_as:axe").
#define ITEM_ATTR_TOOL         "tool"
#define ITEM_ATTR_TOOL_SWIPE   "tool_swipe"
#define ITEM_ATTR_TOOL_POWER   "tool_power"
#define ITEM_ATTR_TOOL_SFX     "tool_sfx:"
#define ITEM_ATTR_COUNTS_AS    "counts_as:"

// Watering: an item with "waters 1" (the Item Editor's "Watering can") is a
// watering can — used on farmland (or a crop in it) it waters it for the
// day. Crops only grow on days their farmland was watered (FARMING in main.c).
#define ITEM_ATTR_WATERS "waters"
// "water_max N": the can holds N water (one a tile); a well or water fills it
// again. None = it never runs dry. (The Item Editor's "holds N water".)
#define ITEM_ATTR_WATER_MAX "water_max"

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
// A bed with a front layer (item_asset_t.front: its sheet and footboard) is
// walked into, Stardew style (BEDS in main.c): the player gets in from the
// side, the sheet covers them, and lying there asks "Go to bed?". Only its
// frame blocks: the art's rows above "bed_head" (the headboard; default: the
// art's height - 22 px) and from "bed_foot" down (the footboard; default:
// height - 16). Between them is where the player lies — it must hold the
// feet of a player standing on the footprint's second-to-last tile row.
#define ITEM_ATTR_BED      "bed"
#define ITEM_ATTR_BED_HEAD "bed_head"
#define ITEM_ATTR_BED_FOOT "bed_foot"

// Props: an item with "prop 1" (the Item Editor's "Can be placed") is
// furniture — a shelf, a crate, a rug. Held, a hologram of it shows in front
// of the player; tapping the hologram puts it down there (PLACEMENT in
// main.c), and tapping it with empty hands picks it back up. What's placed
// is frame 0 of its held art, at most 64x64 px, standing bottom-aligned on
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

// Sprinklers: a prop with "sprinkler N" (the Item Editor's "Sprinkler") waters
// the farmland within N tiles of it — the (2N+1)x(2N+1) square around it: 1
// bronze 3x3, 2 silver 5x5, 3 gold 7x7, 4 emerald 9x9 — every morning at 6:00,
// and sprays until 7:00 (SPRINKLERS + SCARECROWS in main.c).
// Scarecrows: a prop with "scarecrow N" keeps the crows off every crop within
// N tiles of it (7 = the 15x15 square around it).
#define ITEM_ATTR_SPRINKLER  "sprinkler"
#define ITEM_ATTR_SCARECROW  "scarecrow"

// Market board: a prop with "market_board 1" (the Item Editor's "Market board")
// opens the MARKET BOARD when tapped — today's demand for every market type,
// the day's photo requests and the capture book (main.c MARKET BOARD). Its
// screen's PICK UP button takes it back. A map object can do the same with the
// "market_board" action.
#define ITEM_ATTR_MARKET_BOARD "market_board"
// Market types (main.c "Market types + today's demand"; pipeline_msgs.h CAM_TYPES):
// "types" = bits 0-30, "types2" = bits 31-61 of the item's types (bit k = type k).
// Each type's demand moves every day (x0.1 .. x10) and the item sells for the
// average of its types'. A photo item gets the ones the AI saw; the Item
// Editor's "Market types" chips write them for any other item.
#define ITEM_ATTR_TYPES        "types"
#define ITEM_ATTR_TYPES2       "types2"

// Crafting (CRAFTING in main.c; the Item Editor's "Crafting" card). A recipe
// lives on the item it makes, one attribute per ingredient: "craft:" + the
// ingredient's item id, and how many it takes — e.g. "craft:wood" 50,
// "craft:hay" 20. "craft_makes" = how many one craft gives (none = 1). Any
// item with at least one "craft:" attribute shows in the inventory's
// crafting tab. At most ITEM_CRAFT_IN_MAX ingredients (the editor's limit too).
#define ITEM_ATTR_CRAFT_PREFIX "craft:"
#define ITEM_ATTR_CRAFT_MAKES  "craft_makes"
#define ITEM_CRAFT_IN_MAX      6

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

// ---- Fishing, Stardew Valley style (FISHING in main.c; Game Tools' Fishing tab) ----
// Where and when a fish bites — each optional, none = no limit:
//   "fish_from2" / "fish_to2"  a second window of hours (Stardew's Albacore: 6-11 and 18-2)
//   "fish_seasons"  bit set: 1 spring, 2 summer, 4 fall, 8 winter (a season is SEASON_DAYS game days)
//   "fish_days"     bit set: 1 Monday, 2 Tuesday ... 64 Sunday
//   "fish_water"    bit set: 1 pond / lake (plain Fishable water), 2 river, 4 ocean (the Map Editor's
//                   water kind on the water asset: TILE_FLAG_RIVER / TILE_FLAG_OCEAN in main.c),
//                   8 lava (TILE_FLAG_LAVA): nothing bites in lava unless its fish_water has 8
//   "fish_map:<map name>" 1   one per map ("fish_map:mines"): it only bites on those maps
//   "fish_depth" N  the bobber at least N tiles from the shore
//   "fish_level" N  fishing level N or better
//   "fish_once" 1   a legend: one per save
//   "fish_trait"    bit set of tricks it plays in the minigame (FISH_TRAIT_* below)
// Junk: "junk" W — fished up instead of a fish now and then (no minigame); W = its weight
// among the junk. The fish_ conditions above apply to it too.
// Treasure: "treasure" W — can be in a minigame's treasure chest (W = weight), "treasure_max" N
// of it at most (none = 1).
// Crab pots: a prop with "crab_pot 1" goes in water (Fishable tiles). Bait it, and by the next
// 6:00 am it has caught something — shown over it until it's collected. What it catches: items
// with "pot" W (weight), and "pot_tier" (1..6, like fish_tier), "pot_seasons", "pot_weather",
// "pot_water", "pot_map:<name>" — the same meanings as the fish_ ones.
// Bait: "bait 1" goes on a rod that takes bait ("rod_bait 1"); one is used per bite hooked.
// Tackle (bobbers, hooks, lures): "tackle" N = how many catches it lasts (Stardew: 20); goes in a
// rod's tackle slots ("rod_tackle" 1..2). Drop one on a rod in the bag to put it on.
// Effects — on a rod, a bait or a tackle as "rod_" / "bait_" / "tackle_" + the name; they add up:
//   bar (px; a rod's rod_bar is its whole bar), reel, bite, grip (% — rod_* above), luck (points),
//   junk (% of the junk chance), treasure (% of the chest chance), double (% chance of two fish),
//   quality (grades better), rare (% the Rare-and-up fish bite), and switches (1 = on): lead (the bar
//   doesn't bounce), barbed (the bar sticks to the fish), sonar (see the fish before hooking it),
//   magic (seasons, hours and weather don't matter), challenge (Stardew's challenge bait: up to 3 fish
//   if it never escapes the bar), steady (the catch meter doesn't drain while the bar holds the chest).
#define ITEM_ATTR_FISH_FROM2   "fish_from2"
#define ITEM_ATTR_FISH_TO2     "fish_to2"
#define ITEM_ATTR_FISH_SEASONS "fish_seasons"
#define ITEM_ATTR_FISH_DAYS    "fish_days"
#define ITEM_ATTR_FISH_WATER   "fish_water"
#define ITEM_ATTR_FISH_MAP     "fish_map:"
#define ITEM_ATTR_FISH_DEPTH   "fish_depth"
#define ITEM_ATTR_FISH_LEVEL   "fish_level"
#define ITEM_ATTR_FISH_ONCE    "fish_once"
#define ITEM_ATTR_FISH_TRAIT   "fish_trait"
#define ITEM_ATTR_JUNK         "junk"
#define ITEM_ATTR_TREASURE     "treasure"
#define ITEM_ATTR_TREASURE_MAX "treasure_max"
#define ITEM_ATTR_CRAB_POT     "crab_pot"
#define ITEM_ATTR_POT          "pot"
#define ITEM_ATTR_BAIT         "bait"
#define ITEM_ATTR_TACKLE       "tackle"
#define ITEM_ATTR_ROD_BAIT     "rod_bait"
#define ITEM_ATTR_ROD_TACKLE   "rod_tackle"
#define ITEM_ATTR_ROD_LAVA     "rod_lava"   // 1 = the rod casts into lava too (others: "it would burn up")
// Seasons (SEASONS in main.c, SEASON_DAYS each): a seed packet's "season" = the bit set of
// seasons its crop grows in (1 spring, 2 summer, 4 fall, 8 winter, like fish_seasons; none = all year).
// It's only planted then, the seed shop only sells it then, and it withers when its season ends
// (not inside buildings). The Crops Editor's "Grows in" writes it.
#define ITEM_ATTR_SEASON       "season"
#define SEASON_ALL             0x0F

// Forage (FORAGE in main.c; the Item Editor's "Forage" card): "forage" W makes the item a
// forageable — every morning a few come up on the loaded map's Forage tiles (the Map Editor's
// "Forage" on a 16x16 ground asset), W = its weight against the other forageables that could.
// "forage_seasons" = the seasons it comes up in (bits like fish_seasons; none = all year),
// "forage_map:<map name>" 1 = only on those maps (one attribute per map; none = any map).
// Picked up by walking onto it, like a dropped stack.
#define ITEM_ATTR_FORAGE         "forage"
#define ITEM_ATTR_FORAGE_SEASONS "forage_seasons"
#define ITEM_ATTR_FORAGE_MAP     "forage_map:"

// Climate (CLIMATE in main.c): every map is Normal, Hot, Cold, Dry, Lush, Volcanic or Glacial (the
// Map Editor's "Climate"). "climate" = the bit set of climates the item lives in — 1 normal, 2 hot,
// 4 cold, 8 dry, 16 lush, 32 volcanic, 64 glacial; none = the first five (Volcanic and Glacial only
// have what names them). On a seed packet or a tree's seed: planted only there; on a
// forageable: comes up only there; on a fish, junk or a crab pot catch: bites / is caught only
// there. A building's inside without a climate of its own is indoors: anything goes.
#define ITEM_ATTR_CLIMATE        "climate"

// Energy (ENERGY in main.c): "energy N" = what one use costs the player — a tool's swing, a
// rod's cast (the Item Editor's "Energy a use"). None = 0 for tools, ENERGY_ROD_DEFAULT (5)
// for fishing rods.
#define ITEM_ATTR_ENERGY         "energy"
// Minigame tricks ("fish_trait" bits).
#define FISH_TRAIT_FREEZE   0x001   // plays dead: caught in the bar it freezes a moment, then bolts
#define FISH_TRAIT_STICKY   0x002   // sticky: while the bar is on it, the bar gets stuck (barely moves)
#define FISH_TRAIT_DASHER   0x004   // dasher: now and then a flash, then a dash across the whole water
#define FISH_TRAIT_JUMPER   0x008   // jumper: leaps up out of the water and falls back in
#define FISH_TRAIT_GHOST    0x010   // ghost: fades out of sight now and then
#define FISH_TRAIT_DECOY    0x020   // decoy: a second, fake fish swims too — only the real one counts
#define FISH_TRAIT_CURRENT  0x040   // current: the water pushes the bar up or down, turning now and then
#define FISH_TRAIT_HEAVY    0x080   // heavy: it drags the bar down
#define FISH_TRAIT_SHRINK   0x100   // shrinker: the bar shrinks as the fight goes on
#define FISH_TRAIT_THIEF    0x200   // thief: out of the bar, it snatches bits of the catch meter back
#define FISH_TRAIT_FRENZY   0x400   // frenzy: faster and wilder the closer it is to caught
#define FISH_TRAIT_COUNT    11

// The Fishing tab's settings for the whole game: assets/fishing/settings.c (k_fishing_cfg).
typedef struct {
    uint16_t luck_pct;        // every luck (rods, bait, tackle, the day's) times this, % (100 = x1)
    uint8_t  daily_luck;      // the day's luck: from -this to +this points, a new roll each day
    uint8_t  junk_pct;        // % of bites that are junk (before luck and bait)
    uint8_t  treasure_pct;    // % of fights with a treasure chest in the water
    uint8_t  pot_junk_pct;    // % of crab pot catches that are junk
    uint8_t  pot_needs_bait;  // 1 = an unbaited crab pot catches nothing
    uint16_t bite_min_ms;     // a bite comes after this...
    uint16_t bite_max_ms;     // ...to this (less in the rain, with bait, with a quick rod)
    uint16_t difficulty_pct;  // every fish fights this hard, % (100 = as set)
    uint16_t xp_pct;          // fishing xp, % (100 = Stardew's)
    uint8_t  level_bar;       // the catch bar grows this many px a fishing level
    uint8_t  perfect_grade;   // 1 = a perfect catch is a grade better
} fishing_cfg_t;
extern const fishing_cfg_t k_fishing_cfg;

// Items made while the game runs (the camera viewer's "make it an item"). They
// come after the compiled-in ones and go through item_get() like any other item;
// the ones in the bag are kept with the save (photos.bin, see PHOTO ITEMS in main.c). `icon` (w*h RGB565, 0x0000 = transparent) becomes the
// item's passive art and must stay allocated. Max stack 1: each one is unique.
// Returns the new item, or ITEM_NONE if the table is full.
#define ITEM_NAME_MAX 20   // longest display name for a made item
item_id_t           item_add_custom(const char *name, const uint16_t *icon, uint16_t w, uint16_t h);

// The same, with attributes: a photo item carries its sell price ("sellable")
// and the traits the camera's appraisal found (see PHOTO TRAITS in main.c),
// e.g. { "razor_sharp", 2000 }. Up to ITEM_PHOTO_ATTR_MAX are kept; the
// names must stay valid for good (string literals).
#define ITEM_PHOTO_ATTR_MAX 14
item_id_t           item_add_photo(const char *name, const uint16_t *icon, uint16_t w, uint16_t h,
                                   const item_attr_t *attrs, uint8_t attr_count);

// Forgets every item made while the game ran and frees their icons (loading a
// save or starting a new one: the save's own photo items are made again from its
// photos.bin). Nothing may still hold one of them.
void                item_custom_reset(void);

// A photo item's lasting id ("pid"): random when it's made, kept in photos.bin,
// so a map's save can name one that sits on a shelf (SHELVES in main.c) —
// the "photo_N" ids change every time a save loads. 0 = not a photo item.
uint32_t            item_photo_pid(item_id_t item);
void                item_photo_set_pid(item_id_t item, uint32_t pid);   // loading photos.bin
item_id_t           item_find_photo(uint32_t pid);                    // ITEM_NONE if there's none
// A photo item standing on a shelf somewhere (not in the bag): photos.bin keeps it too.
bool                item_photo_shelved(item_id_t item);
void                item_photo_set_shelved(item_id_t item, bool on);
