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

const asset_action_t k_asset_actions[] = {
    ASSET_ACTION(seed_shop, "Seed shop", "Opens a shop that sells the seeds of every crop in the game"),
    ASSET_ACTION(build_shop, "Build shop", "Opens a shop that sells every prop and building that has a price"),
    ASSET_ACTION(ranch_shop, "Ranch shop", "Opens a shop that sells farm animals, hay, grass starter and animal tools"),
    ASSET_ACTION(fish_shop, "Fish shop", "Opens a shop that sells fishing rods, bait, tackle and crab pots"),
    ASSET_ACTION(general_shop, "General store", "Opens a shop that sells any other item with a price (Item Editor / Shop Editor)"),
    ASSET_ACTION(auction_house, "Auction house", "Opens the auction house: put things up for auction, see the bids"),
    ASSET_ACTION(bench, "Bench", "Auction crowds gather here: bidders stand on it (if walkable) or beside it and shout their bids"),
    ASSET_ACTION(ledger, "Ledger", "Opens the ledger: everything bought and sold in the last 20 days (also ledger.csv in the save)"),
    ASSET_ACTION(bed, "Bed", "Asks to go to bed: sleeps until 6:00 am the next morning, and crops in watered soil grow overnight"),
    ASSET_ACTION(trough, "Trough", "Inside a barn or coop: every tile of it is one trough. Hold hay and tap it to fill them; the animals eat from them at night"),
};
const int asset_action_count = sizeof(k_asset_actions) / sizeof(k_asset_actions[0]);

int asset_action_find(const char *id)
{
    for (int i = 0; i < asset_action_count; i++)
        if (strcmp(k_asset_actions[i].id, id) == 0) return i;
    return -1;
}
