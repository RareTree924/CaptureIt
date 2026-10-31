#include <string.h>
#include "actions.h"

// The actions an asset can run when it's tapped — see actions.h. The Game
// Tools Map Editor lists every ASSET_ACTION(...) row below (it reads this
// file), so keep each row on one line, in the exact form
//     ASSET_ACTION(id, "Label", "What it does"),

// Opens the seed shop: every crop in the game, its seed packet at its
// "buyable" price (the Crops Editor's "Seed packet costs").
static void action_seed_shop(const action_ctx_t *ctx)
{
    (void)ctx;
    seed_shop_open();
}

// Opens the build shop: every prop (Item Editor "Can be placed") and every
// building (Buildings Editor) that has a "buyable" price.
static void action_build_shop(const action_ctx_t *ctx)
{
    (void)ctx;
    build_shop_open();
}

// Opens the ranch shop (Stardew's Marnie): every farm animal (Animals Editor)
// with a price, then hay, grass starter and the animal tools.
static void action_ranch_shop(const action_ctx_t *ctx)
{
    (void)ctx;
    ranch_shop_open();
}

// Opens the fish shop (Stardew's Willy): fishing rods, bait, tackle and crab
// pots that have a "buyable" price (FISHING in main.c).
static void action_fish_shop(const action_ctx_t *ctx)
{
    (void)ctx;
    fish_shop_open();
}
// Opens the general store: anything with a "buyable" price that no other
// counter sells (plus anything put on the General counter by hand).
static void action_general_shop(const action_ctx_t *ctx)
{
    (void)ctx;
    general_shop_open();
}

// Opens the boat shop: every boat ("boat" 1 — the Item Editor's Boat card) with
// a price. A built dock's post opens it too (BOATS + DOCKS in main.c).
static void action_boat_shop(const action_ctx_t *ctx)
{
    (void)ctx;
    boat_shop_open();
}

// Opens the auction house: what's being auctioned, and putting a stack from
// the bag up for auction. Bidders keep bidding while the player is elsewhere.
static void action_auction_house(const action_ctx_t *ctx)
{
    (void)ctx;
    auction_open();
}

// A bench: in an auction hall, bidders gather on (or beside) every bench
// and shout their bids. Tapped, it says how the soonest-ending lot is going.
static void action_bench(const action_ctx_t *ctx)
{
    (void)ctx;
    auction_bench_info();
}

// Opens the ledger: everything bought and sold in the last 20 days, with the
// day totals. The same list is in the save's ledger.csv on the SD card.
static void action_ledger(const action_ctx_t *ctx)
{
    (void)ctx;
    ledger_open();
}

// A bed: asks "Go to bed?" and, on SLEEP, skips to 6:00 the next morning —
// crops in watered farmland grow overnight (SLEEP in main.c).
static void action_bed(const action_ctx_t *ctx)
{
    (void)ctx;
    bed_open();
}

// A trough, inside a barn or a coop (FARM in main.c): holding hay, fills its
// empty troughs from the held stack; else says how many have hay. The barn's
// animals eat from them at night.
static void action_trough(const action_ctx_t *ctx)
{
    trough_tapped(ctx->tx, ctx->ty);
}

// A notice board: today's demand for every market type (round things, metal
// things... from x0.1 to x10), the day's photo requests and the capture book.
static void action_market_board(const action_ctx_t *ctx)
{
    (void)ctx;
    market_board_open();
}

// A blacksmith's anvil: holding a geode, cracks it open (for $25) — out comes a
// random mineral (GEODES in main.c).
static void action_blacksmith(const action_ctx_t *ctx)
{
    (void)ctx;
    blacksmith_tapped();
}

// A museum shelf: an empty one opens the donation picker — a mineral not donated
// yet goes on it; one holding a donation says what it is (MUSEUM in main.c).
static void action_museum_shelf(const action_ctx_t *ctx)
{
    museum_shelf_tapped(ctx->x, ctx->y, ctx->w, ctx->h);
}

// A kitchen (a stove, a counter): the cooking screen — every food, free until a
// dish has ingredients ("cook:<item id>" attributes; KITCHEN in main.c).
static void action_kitchen(const action_ctx_t *ctx)
{
    (void)ctx;
    kitchen_tapped();
}

const asset_action_t k_asset_actions[] = {
    ASSET_ACTION(seed_shop, "Seed shop", "Opens a shop that sells the seeds of every crop in the game"),
    ASSET_ACTION(build_shop, "Build shop", "Opens a shop that sells every prop and building that has a price"),
    ASSET_ACTION(ranch_shop, "Ranch shop", "Opens a shop that sells farm animals, hay, grass starter and animal tools"),
    ASSET_ACTION(fish_shop, "Fish shop", "Opens a shop that sells fishing rods, bait, tackle and crab pots"),
    ASSET_ACTION(general_shop, "General store", "Opens a shop that sells any other item with a price (Item Editor / Shop Editor)"),
    ASSET_ACTION(boat_shop, "Boat shop", "Opens a shop that sells the boats (sail them from a dock: hold one and tap the water)"),
    ASSET_ACTION(auction_house, "Auction house", "Opens the auction house: put things up for auction, see the bids"),
    ASSET_ACTION(bench, "Bench", "Auction crowds gather here: bidders stand on it (if walkable) or beside it and shout their bids"),
    ASSET_ACTION(ledger, "Ledger", "Opens the ledger: everything bought and sold in the last 20 days (also ledger.csv in the save)"),
    ASSET_ACTION(bed, "Bed", "Asks to go to bed: sleeps until 6:00 am the next morning, and crops in watered soil grow overnight"),
    ASSET_ACTION(market_board, "Market board", "Opens the market board: today's demand for every type of thing (x0.1 to x10), the day's photo requests and the capture book"),
    ASSET_ACTION(blacksmith, "Blacksmith", "Holding a geode, tap it to crack the geode open ($25): out comes a random mineral"),
    ASSET_ACTION(kitchen, "Kitchen", "Opens the kitchen: cook any food (free for now; a dish with cook:<item> attributes takes those from the bag)"),
    ASSET_ACTION(museum_shelf, "Museum shelf", "Tap an empty one to donate a mineral (one of each) onto it; it shows there from then on. A full one says what it holds"),
    ASSET_ACTION(trough, "Trough", "Inside a barn or coop: every tile of it is one trough. Hold hay and tap it to fill them; the animals eat from them at night"),
};
const int asset_action_count = sizeof(k_asset_actions) / sizeof(k_asset_actions[0]);

int asset_action_find(const char *id)
{
    for (int i = 0; i < asset_action_count; i++)
        if (strcmp(k_asset_actions[i].id, id) == 0) return i;
    return -1;
}
