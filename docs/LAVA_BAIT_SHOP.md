# Lava fishing, bait and shops — how to use them

Everything here is set up in Game Tools; no code needed. After saving items or
exporting maps, rebuild and flash the firmware as usual.

## Lava fishing

1. **Lava tiles** — Map Editor › asset library: select a 16×16 lava asset and
   click **Lava** (next to Fishable). "Show tiles" draws lava tiles orange.
   Export the map again.
2. **A lava rod** — Item Editor › Fishing: tick **Fishing rod**, then
   **Can fish in lava**. It still fishes water too. Give it a price ("Sold in
   shops") and it shows up in the Tackle shop.
3. **Lava fish** — Item Editor › Fishing: tick **A fish**, then **Lives in
   lava**. Lava fish only bite in lava; water fish never bite there. That makes
   a separate loot pool. Tier, rarity, hours and weather all work the same.

In game, a normal rod cast at lava says it would burn up. With a lava rod the
minigame glows orange.

## Bait

- **Make bait** in the **Bait Editor** tab: drop in a 16×16 PNG (a bigger one
  is shrunk, a smaller one is centred), then set the name, prices and stats.
  Presets: Worm, Cork, Steady, Magnet, Lucky, Glitter. **Save bait** writes
  `assets/items/<id>.c`. The list on the left shows every bait in the folder;
  click one to edit it.
- **Stats**: bite speed, catch bar size, bar control (the bar brakes harder
  and bounces less), calm fish (they swim as if easier), reel speed, grip,
  luck, mutation chance, and "Attracts" (only Rare-or-rarer fish bite, etc.).
- **In game**: pick up a bait stack in the bag and drop it on a rod. It goes on
  the hook (up to one full stack); different bait already there swaps back.
  The rod's card shows `Bait: Worm x12` and a **TAKE OFF** button. Each catch
  uses one, and the catch card shows how many are left.
- **Item Editor extras**: a rod with **Needs bait** won't cast without bait.
  A fish with **Only bites on bait** never takes a bare hook.
- Bait belongs to the rod *kind*, so two of the same rod share it.

## Shops

- **Any item** with a price is now for sale. Item Editor › Selling & dropping:
  **Sold in shops**, set the price, and pick a **Counter** (or leave it on
  "Usual").
- Usual counters: props and buildings → Build, seeds and farm tools → Seeds,
  animal things → Ranch, rods and bait → **Tackle**, everything else →
  **General store**.
- **Shop Editor** tab: every item in `assets/items` in one table. Tick for
  sale, set the price and counter, and use **Save changes**. Only the
  attribute table in each changed `.c` is rewritten. "Price shown items at
  sell price × N" prices a filtered group in one go.
- Put shops on maps with Map Editor › Actions…: **Tackle shop** and
  **General store** are new (next to Seed / Build / Ranch). Every shop shows a
  tab for each counter that has stock.

## Attributes (for reference)

| Attribute | On | Meaning |
|---|---|---|
| `rod_lava 1` | rod | can cast into Lava tiles |
| `rod_bait 1` | rod | won't cast without bait |
| `fish_lava 1` | fish | lives in lava only |
| `fish_bait 1` | fish | only bites on bait |
| `bait 1` | item | is bait |
| `bait_bite` / `bait_reel` / `bait_grip` | bait | % (100 = normal), multiplies the rod's |
| `bait_bar` | bait | px added to the catch bar |
| `bait_control` | bait | 0..100 bar control |
| `bait_calm` | bait | 0..80 % calmer fish |
| `bait_luck` | bait | added to rod luck |
| `bait_mut` | bait | % mutation chance (200 = ×2) |
| `bait_tier` | bait | 2..6: only that tier or rarer bites |
| `shop N` | any | counter: 1 Seeds, 2 Build, 3 Ranch, 4 Tackle, 5 General |

Map flag: `TILE_FLAG_LAVA 0x08`. Save file: `world.txt` gains
`bait <rod id> <bait id> <count>` lines.

## Asset checklist for this update

- [ ] 16×16 lava tile(s) (animated is fine), ticked **Lava**
- [ ] Lava rod item (Can fish in lava; maybe Needs bait)
- [ ] 4–8 lava fish (Lives in lava), spread across tiers
- [ ] Bait icons: worm, cork, magnet, glitter…
- [ ] A Tackle shop building or counter, with the **Tackle shop** action
- [ ] A volcano / cave map with a lava pool
