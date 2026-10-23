# Lava fishing and the General store

## Lava fishing

Lava is a fourth water kind, alongside Pond / lake, River and Ocean.

1. **Lava tiles**: Map Editor › select a 16×16 lava asset › tick
   **Fishable**, then click its **Water:** button until it says **Lava**.
   "Show tiles" draws lava orange. Export the map again.
2. **A lava rod**: Fishing tab › Rod › tick **Can fish in lava**
   (`rod_lava 1`). It still fishes water too. Other rods say they'd burn up.
3. **Lava fish**: Fishing tab › a fish's **Water** buttons › Lava
   (`fish_water` bit 8). Nothing bites in lava unless its Water includes Lava.
   A fish with no Water set means "any water", which never includes lava.
   Junk and crab pot catches follow the same rule.

In game, the cast stays on lava (it won't fly from water out into lava), the
bite ripple is orange, and the minigame glows orange with embers.

## Selling any item

- **Any item** with a price is now for sale. Item Editor › **Sold in shops**,
  set the price and pick a **Counter**, or leave it on "Usual".
- Usual counters: seeds and farm tools → Seeds, props and buildings → Build,
  animal things → Ranch, rods / bait / tackle / crab pots → Fish, everything
  else → **General store** (new).
- **Shop Editor** tab: every item in `assets/items` in one table. Tick for
  sale, set the price and counter, and use **Save changes**. Only the
  attribute table in each changed `.c` is rewritten. "Price shown items at
  sell price × N" prices a filtered group in one go.
- Put a **General store** on a map with Map Editor › Actions…. Every shop
  shows a tab for each counter that has stock. With 4 or more tabs, the
  money moves down to the footer.

## Attributes (for reference)

| Attribute | On | Meaning |
|---|---|---|
| `rod_lava 1` | rod | can cast into Lava water |
| `fish_water` bit 8 | fish / junk / pot catch | lives in lava |
| `season` | seed packet | the crop's seasons (1 spring, 2 summer, 4 fall, 8 winter) |
| `shop N` | any item with `buyable` | counter: 1 Seeds, 2 Build, 3 Ranch, 4 Fish, 5 General |

Map tile flag: `TILE_FLAG_LAVA 0x40`, set on a Fishable tile whose water kind
is Lava.
