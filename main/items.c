#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "esp_random.h"
#include "esp_attr.h"   // EXT_RAM_BSS_ATTR
#include "items.h"

// The one fixed entry: "no item". Everything else comes from
// assets/items/<id>.c (one k_item_<id> each) via items_manifest.inc,
// which main/CMakeLists.txt regenerates from whatever files are actually
// there. Indices into s_items are NOT stable across builds (they follow
// file-name order) — maps and saves refer to items by their string id and
// resolve it with item_find() at load time.
static const item_asset_t k_none = {
    .id = "none", .display_name = "Hands", .max_stack = 0,
};

#define ITEM_ENTRY(id) extern const item_asset_t k_item_##id;
#include "items_manifest.inc"
#undef ITEM_ENTRY

const item_asset_t *const s_items[] = {
    &k_none,
#define ITEM_ENTRY(id) &k_item_##id,
#include "items_manifest.inc"
#undef ITEM_ENTRY
};
const item_id_t item_count = sizeof(s_items) / sizeof(s_items[0]);

// Runtime items (item_add_custom): indices item_count, item_count + 1, ...
#define ITEM_CUSTOM_MAX 32
static item_asset_t s_custom[ITEM_CUSTOM_MAX];
static char         s_custom_id[ITEM_CUSTOM_MAX][12];                 // "photo_1", "photo_2", ...
static char         s_custom_name[ITEM_CUSTOM_MAX][ITEM_NAME_MAX + 1];
EXT_RAM_BSS_ATTR static item_attr_t s_custom_attrs[ITEM_CUSTOM_MAX][ITEM_PHOTO_ATTR_MAX];   // PSRAM: 3.6 KB, read now and then
static uint32_t     s_custom_pid[ITEM_CUSTOM_MAX];      // item_photo_pid()
static bool         s_custom_shelved[ITEM_CUSTOM_MAX];  // item_photo_shelved()
static uint8_t      s_custom_count;

item_id_t item_add_custom(const char *name, const uint16_t *icon, uint16_t w, uint16_t h) {
    return item_add_photo(name, icon, w, h, NULL, 0);
}

item_id_t item_add_photo(const char *name, const uint16_t *icon, uint16_t w, uint16_t h,
                       const item_attr_t *attrs, uint8_t attr_count) {
    if (s_custom_count >= ITEM_CUSTOM_MAX || item_count + s_custom_count >= ITEM_ID_MAX || !icon) return ITEM_NONE;
    if (attr_count > ITEM_PHOTO_ATTR_MAX) attr_count = ITEM_PHOTO_ATTR_MAX;
    int k = s_custom_count++;
    snprintf(s_custom_id[k], sizeof(s_custom_id[k]), "photo_%d", k + 1);
    snprintf(s_custom_name[k], sizeof(s_custom_name[k]), "%s", (name && name[0]) ? name : "Photo item");
    s_custom[k] = (item_asset_t){
        .id           = s_custom_id[k],
        .display_name = s_custom_name[k],
        .max_stack    = 1,
        .passive      = { .w = w, .h = h, .frame_count = 1, .interval_ms = 1000, .loop_count = -1, .pixels = icon },
        .attrs        = s_custom_attrs[k],
        .attr_count   = attr_count,
    };
    for (uint8_t i = 0; i < attr_count; i++) s_custom_attrs[k][i] = attrs[i];
    do s_custom_pid[k] = esp_random(); while (s_custom_pid[k] == 0 || item_find_photo(s_custom_pid[k]) != (item_id_t)(item_count + k));
    s_custom_shelved[k] = false;
    return (item_id_t)(item_count + k);
}

void item_custom_reset(void) {
    for (int k = 0; k < s_custom_count; k++) free((void *)s_custom[k].passive.pixels);
    s_custom_count = 0;
}

static int custom_index(item_id_t item) {
    int k = item - item_count;
    return item >= item_count && k < s_custom_count ? k : -1;
}

uint32_t item_photo_pid(item_id_t item) {
    int k = custom_index(item);
    return k >= 0 ? s_custom_pid[k] : 0;
}

void item_photo_set_pid(item_id_t item, uint32_t pid) {
    int k = custom_index(item);
    if (k >= 0 && pid) s_custom_pid[k] = pid;
}

item_id_t item_find_photo(uint32_t pid) {
    for (int k = 0; pid && k < s_custom_count; k++)
        if (s_custom_pid[k] == pid) return (item_id_t)(item_count + k);
    return ITEM_NONE;
}

bool item_photo_shelved(item_id_t item) {
    int k = custom_index(item);
    return k >= 0 && s_custom_shelved[k];
}

void item_photo_set_shelved(item_id_t item, bool on) {
    int k = custom_index(item);
    if (k >= 0) s_custom_shelved[k] = on;
}

const item_asset_t *item_get(item_id_t item) {
    if (item < item_count) return s_items[item];
    int k = item - item_count;
    return k < s_custom_count ? &s_custom[k] : NULL;
}

int32_t item_attr(item_id_t item, const char *name, int32_t fallback) {
    const item_asset_t *a = item_get(item);
    if (!a) return fallback;
    for (uint8_t i = 0; i < a->attr_count; i++)
        if (strcmp(a->attrs[i].name, name) == 0) return a->attrs[i].value;
    return fallback;
}

int32_t item_sell_price(item_id_t item) {
    int32_t price = item_attr(item, ITEM_ATTR_SELLABLE, 0);
    if (price <= 0) return 0;
    int64_t p = (int64_t)price * item_price_bonus_pct(item) / 100;   // legendary traits x their demand (main.c)
    return p < 1 ? 1 : p > INT32_MAX ? INT32_MAX : (int32_t)p;
}

int32_t item_buy_price(item_id_t item) {
    int32_t price = item_attr(item, ITEM_ATTR_BUYABLE, 0);
    return price > 0 ? price : 0;
}

// Quality odds (per thousand, each tier on its own) and sell price (% of the
// Standard price). Rarer tiers are worth more — tune them here.
static const struct { const char *name; uint16_t per_mille; uint16_t price_pct; } k_quality[QUALITY_COUNT] = {
    [QUALITY_STANDARD] = { "Standard",   0, 100 },   // whatever the others leave: ~72.5%
    [QUALITY_SILVER]   = { "Silver",   200, 125 },   // 20%
    [QUALITY_GOLD]     = { "Gold",      60, 150 },   // 6%
    [QUALITY_EMERALD]  = { "Emerald",   15, 200 },   // 1.5%
};

bool item_has_quality(item_id_t item) {
    return item != ITEM_NONE && item_attr(item, ITEM_ATTR_QUALITY, 0) != 0;
}

uint8_t item_roll_quality(item_id_t item, uint32_t random) {
    if (!item_has_quality(item)) return QUALITY_STANDARD;
    uint32_t r = random % 1000, edge = 0;
    for (int q = QUALITY_COUNT - 1; q > QUALITY_STANDARD; q--) {   // rarest first
        edge += k_quality[q].per_mille;
        if (r < edge) return (uint8_t)q;
    }
    return QUALITY_STANDARD;
}

const char *item_quality_name(uint8_t quality) {
    uint8_t g = QUALITY_GRADE(quality);
    return k_quality[g < QUALITY_COUNT ? g : QUALITY_STANDARD].name;
}

// Mutations: base odds (1 in N, each tried on its own, rarest first — main.c
// mut_roll(), where an item's "mut" boosts them) and the sell price (% of an
// unmutated one). All of them together: about 1 roll in 11. Tune them here.
static const struct { const char *name; uint16_t one_in; uint16_t price_pct; } k_mutation[MUT_COUNT] = {
    [MUT_NONE]        = { "",               0,  100 },
    [MUT_SHINY]       = { "Shiny",         30,  150 },
    [MUT_FLOATY]      = { "Floaty",        60,  175 },
    [MUT_ALBINO]      = { "Albino",        75,  200 },
    [MUT_HEAVY]       = { "Heavy",        100,  250 },
    [MUT_GOLDEN]      = { "Golden",       150,  300 },
    [MUT_RADIOACTIVE] = { "Radioactive",  250,  400 },
    [MUT_ELECTRIC]    = { "Electric",     300,  450 },
    [MUT_GHOSTLY]     = { "Ghostly",      400,  500 },
    [MUT_RAINBOW]     = { "Rainbow",     1500, 1000 },
    [MUT_CELESTIAL]   = { "Celestial",   5000, 2500 },
};

bool item_quality_ok(uint8_t quality) {
    return QUALITY_GRADE(quality) < QUALITY_COUNT && QUALITY_MUT(quality) < MUT_COUNT;
}

const char *item_mutation_name(uint8_t mut)      { return k_mutation[mut < MUT_COUNT ? mut : MUT_NONE].name; }
uint16_t    item_mutation_one_in(uint8_t mut)    { return k_mutation[mut < MUT_COUNT ? mut : MUT_NONE].one_in; }
uint16_t    item_mutation_price_pct(uint8_t mut) { return k_mutation[mut < MUT_COUNT ? mut : MUT_NONE].price_pct; }

int32_t item_sell_price_q(item_id_t item, uint8_t quality) {
    uint8_t g = QUALITY_GRADE(quality);
    int64_t p = (int64_t)item_sell_price(item) * k_quality[g < QUALITY_COUNT ? g : 0].price_pct * item_mutation_price_pct(QUALITY_MUT(quality));
    p = (p + 5000) / 10000;
    return (int32_t)(p > INT32_MAX ? INT32_MAX : p);
}

bool item_droppable(item_id_t item) {
    return item != ITEM_NONE && item_get(item) && item_attr(item, ITEM_ATTR_DROPPABLE, 1) != 0;
}

const char *item_name(item_id_t item) {
    const item_asset_t *a = item_get(item);
    return a ? a->display_name : "?";
}

uint8_t item_max_stack(item_id_t item) {
    const item_asset_t *a = item_get(item);
    return a ? a->max_stack : 0;
}

item_id_t item_find(const char *id) {
    for (item_id_t i = 0; i < item_count; i++)
        if (strcmp(s_items[i]->id, id) == 0) return i;
    for (uint8_t k = 0; k < s_custom_count; k++)
        if (strcmp(s_custom[k].id, id) == 0) return (item_id_t)(item_count + k);
    return ITEM_NONE;
}
