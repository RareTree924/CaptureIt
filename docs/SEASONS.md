# Seasons

Every **30 game days** a new season starts: Spring → Summer → Fall → Winter →
Spring (next year). Day 0 of a new game is Spring 1, Year 1. The clock panel
shows the season and its day (e.g. `Mon  Spr 12`). A new season pops up a
message.

## Crops

- Crops Editor › **Grows in**: tick the seasons. None ticked = all year.
- In game, a seed can only be planted in its seasons. Shops only sell seeds
  that are in season.
- On the first day of a season a crop doesn't grow in, it **withers** (it's
  removed, and the farmland stays).
- **Inside buildings** anything grows in any season, so a building works as a
  greenhouse.
- Existing crops:

| Season | Crops |
|---|---|
| Spring | parsnip, potato, cauliflower, green bean, rhubarb, radish |
| Summer | blueberry, hot pepper, melon, tomato, wheat |
| Fall | radish, wheat, garlic, kale |
| Winter | garlic, kale |

## Fish

- Item Editor › Fishing › **Bites in**: tick the seasons. None ticked = all
  year.
- The fish book's "When" line shows the seasons (e.g. `Spr/Sum, 6am - 2pm`),
  and "Biting right now" takes the season into account.
- Existing fish: carp, goldfish, common starfish, hermit crab, sea sponge and
  Progenetica bite all year. Every other fish has 1–3 seasons, and each season
  has its own legendary fish:

| Season | Legendary fish |
|---|---|
| Spring | Golden Koi |
| Summer | Airplanefish |
| Fall | Humpback Anglerfish |
| Winter | Atlantic Giant Squid |

## Seasonal map art

1. Map Editor › select an asset › **Seasons…** (or right-click › Seasonal
   art…).
2. For each season, **Load PNG…** (or drop one on it): the same size as the
   asset. For an animation, use its frames side by side, or one image for
   every frame (e.g. frozen water). **Auto** makes a first draft from the
   normal art (blossoms, deeper greens, autumn leaves, snow) for you to draw
   over.
3. File row › **Seasons…** previews the whole map in each season.
4. **Export** as usual. For each season some asset on the map has art for,
   it also writes `<map>.<season>.map` and its own night files
   (`<map>.winter.n1` …). Copy them all to the map's folder on the SD card.
   When you export into a folder, seasonal files for seasons that no longer
   have art are deleted for you.

How it works:
- Only the colours change. Collision, layers, actions, tile types and
  breakables all stay as they are on the normal map.
- Seasonal art can't paint outside the asset's normal shape; a see-through
  pixel shows what's under the asset.
- A season with no art uses the normal map.
- Pixels you hand-painted on top of placed assets stay as painted.
- Seasonal maps share one save with the normal map.
- If a season starts while you're on a map with seasonal art, the map
  reloads in place.

## Testing

Debug panel › Time has **Spring 1 / Summer 1 / Fall 1 / Winter 1** buttons.
The dev link command is `season spring|summer|fall|winter`.
