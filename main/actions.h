#pragma once
#include <stdbool.h>
#include <stdint.h>

// ============================================================
//  ASSET ACTIONS — what happens when the player taps an object on the map.
//
//  Every ASSET_ACTION(...) row in main/actions.c is an action. In the Game
//  Tools Map Editor, a library asset's "Actions…" button lists them (the
//  editor reads main/actions.c itself — reload it there after adding one);
//  tick one or more. Every placed copy of that asset, on a map exported
//  after that, becomes a trigger: tapping it walks the player next to it,
//  faces it, and runs its actions in the order they're listed in the file.
//  The same action can go on any number of assets.
//
//  Adding an action, in main/actions.c:
//      static void action_<id>(const action_ctx_t *ctx) { ... }
//  plus a row in k_asset_actions[]:
//      ASSET_ACTION(<id>, "Label", "What it does, for the editor"),
//  The id is lowercase letters, digits and _ (at most ACTION_ID_MAX). Maps
//  store the id, so renaming one breaks the maps that use it (the device logs
//  and skips an id it doesn't have).
// ============================================================
#define ACTION_ID_MAX 31

typedef struct {
    const char *map;    // the map it's on (current_map_name(), e.g. "meadows")
    int x, y, w, h;     // the tapped object's footprint on the map, in pixels
    int tx, ty;         // the tile of it the player is facing
} action_ctx_t;

typedef void (*action_fn_t)(const action_ctx_t *ctx);

typedef struct {
    const char *id;     // what maps store, e.g. "seed_shop"
    const char *label;  // shown in the editor
    const char *help;   // ...as the description
    action_fn_t fn;
} asset_action_t;

#define ASSET_ACTION(id, label, help) { #id, label, help, action_##id }

extern const asset_action_t k_asset_actions[];
extern const int            asset_action_count;
int asset_action_find(const char *id);   // index into k_asset_actions[], -1 = not in this build

// ---- what main.c offers actions ----
bool     seed_shop_open(void);    // the shop selling every crop's seeds (SEED SHOP in main.c)
bool     build_shop_open(void);   // the shop selling every prop and building with a "buyable" price
bool     ranch_shop_open(void);   // the ranch: every farm animal, hay and animal tools with a "buyable" price (ANIMALS in main.c)
bool     fish_shop_open(void);    // the fish shop: rods, bait, tackle, crab pots with a "buyable" price (FISHING in main.c)
bool     general_shop_open(void); // anything else with a "buyable" price (items.h ITEM_ATTR_SHOP)
bool     auction_open(void);      // the auction house: lots running, and putting a stack up (MARKET in main.c)
void     auction_bench_info(void); // a bench, tapped: how the soonest-ending lot is going
bool     ledger_open(void);       // every buy and sell of the last 20 days (LEDGER in main.c)
bool     bed_open(void);          // "Go to bed?" — sleep until the next morning (SLEEP in main.c)
void     trough_tapped(int tx, int ty);   // a barn's trough: fill it with the held hay (FARM in main.c)
bool     sell_menu_open(void);    // the inventory as a SELL screen
bool     market_board_open(void); // today's demand for every market type, the photo requests, the capture book (MARKET BOARD in main.c)
uint32_t money_get(void);
void     money_add(int32_t amount);
bool     money_spend(uint32_t amount);
void     message(uint32_t time_ms, const char *fmt, ...) __attribute__((format(printf, 2, 3)));
