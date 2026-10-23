# Seasons

Every **28 game days** a new season starts: Spring → Summer → Fall → Winter →
Spring (next year). Day 0 of a new game is Spring 1, Year 1. The clock panel
shows the season and its day (e.g. `Mon  Spr 12`). A new season pops up a
message.

## Fish

The Fishing tab's season condition (`fish_seasons`) is unchanged. It uses the
same 28-day seasons.

## Crops

- Crops Editor › **Grows in**: tick the seasons. None ticked = all year. This
  writes `season` on the seed packet.
- In game, a seed can only be planted in its seasons. The seed shop only
  sells packets that are in season.
- On the first day of a season a crop doesn't grow in, it **withers** (it's
  removed, and the farmland stays).
- **Inside buildings** anything grows any time, so a building works as a
  greenhouse.
- Current picks (change them in the Crops Editor):

| Season | Crops |
|---|---|
| Spring | parsnip, potato, cauliflower, green bean, rhubarb, radish |
| Summer | blueberry, hot pepper, melon, tomato, wheat |
| Fall | radish, wheat, garlic, kale |
| Winter | garlic, kale |

## Seasonal map art

1. Map Editor › select an asset › **Seasons…** (or right-click › Seasonal
   art…).
2. For each season, **Load PNG…** (or drop one on it): the same size as the
   asset. For an animation, use its frames side by side, or one image for
   every frame (e.g. frozen water). **Auto** makes a first draft (blossoms,
   deeper greens, autumn leaves, snow) for you to draw over.
3. File row › **Seasons…** previews the whole map in each season.
4. **Export** as usual. For each season some asset on the map has art for,
   it also writes `<map>.<season>.map` and its night files
   (`<map>.winter.n1` …). Copy them all to the map's folder on the card.
   When you export into a folder, seasonal files for seasons that no longer
   have art are deleted for you.

How it works:
- Only the colours change. Collision, layers, actions, tile types and
  breakables all stay as they are on the normal map.
- Seasonal art can't paint outside the asset's normal shape; a see-through
  pixel shows what's under the asset.
- A season with no art uses the normal map.
- Pixels you hand-painted on top of placed assets stay as painted.
- Seasonal maps share one save with the normal map, because the map's name
  stops at the first `.`.
- If a season starts while you're on a map with seasonal art, the map
  reloads in place.

## Testing

Debug panel › Time has **Spring 1 / Summer 1 / Fall 1 / Winter 1** buttons.
The dev link command is `season spring|summer|fall|winter`.
