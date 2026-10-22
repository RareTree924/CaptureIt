# Feature ideas

Ideas that build on systems the game already has: farming, animals, machines,
buildings, shelves with visiting shoppers, the auction house, camera photo
items, mutations, weather, day/night, the fish book and the ledger. ★ marks
the ones that reuse the most existing code (cheapest to add).

## Beyond fishing

- ★ **Request board** — visitors post orders ("5 Silver tomatoes by Friday,
  $400"). Reuses shoppers, quality grades, the clock and the ledger. Gives
  farming and fishing a goal.
- ★ **Seasons** — a 28-day season cycle. A `season` attribute on crops and
  fish (like `fish_from`/`fish_to`), and seasonal map palettes (winter night
  files already exist).
- ★ **Crafting bench** — instant recipes (wood + stone → fence, fish + salt
  → bait!). Same recipe table as machines, with 0 days.
- **Cooking & buffs** — a kitchen machine makes dishes. Eating one gives a
  timed buff: fishing luck, walk speed, a bigger catch bar. Buffs can work
  like bait stats on a timer.
- **Mines / volcano cave** — a cave map with ore breakables, pickaxe tiers
  (wood → copper → obsidian), and a lava pool at the bottom for lava fishing.
- ★ **Museum / collection book** — the fish book, generalised to every item.
  Donating fills it; milestones give rewards (a golden rod, rare bait).
- **Regular customers** — visitors you sell to often come back, pay more and
  unlock dialogue lines (friendship hearts).
- **Sprinklers & greenhouse** — a prop that waters the tiles around it each
  morning, and a building whose inside crops ignore seasons.
- **Tool upgrades** — a blacksmith machine: tool + ore + days → better tool
  (bigger watering area, faster axe).
- **Festivals** — calendar days with events: a fishing derby (biggest fish
  wins), a harvest fair (best-quality crop), a night market.
- **Weather events** — storms (lightning hits a tile, Electric mutations
  more likely), fog (Ghostly fish bite more), heatwaves (crops need more
  water).
- **Photo challenges** — the camera already appraises photos with AI. A
  daily challenge like "photograph something red" pays a bonus.
- **Pets** — a cat or dog that follows you and sometimes digs up an item.
  Animal art pipeline already exists.
- **Achievements** — a list screen with progress bars, saved like the fish
  book.

## More fishing (later)

- **Treasure chests** — a chance per catch for a chest with random loot
  (non-fish items). Item attribute `fish_junk` / `fish_treasure`.
- **Crab pots** — a placeable prop on water, baited, that fills overnight.
  Reuses bait + machines.
- **Bait with uses** — `bait_uses N`: one piece lasts N catches.
- **Fish-specific bait** — bait that boosts one fish family (a family number
  on fish and bait).
- **Legendary boss fish** — one per pool that only bites once, with a
  special minigame pattern.
- **Aquarium bonuses** — a full tank of one tier sells shelf items for more,
  or gives luck.
- **Ice fishing** — a third pool (Frozen tiles plus an ice rod), the same way
  lava works now.

## Assets to make while away from Claude

- Lava tiles, a lava rod, lava fish, bait icons, a tackle shop building
- A volcano / cave map (lava pool) and a coast or lake map
- Season variants of ground tiles and trees
- NPC portraits or idle animations for regulars
- Furniture props (sell well on shelves) and decor for shops
