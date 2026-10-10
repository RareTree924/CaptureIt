# CaptureIt → Stardew-style features: evaluation, feasibility and build plan

Written 2026-09-30 after reading the whole S3 firmware (main.c, items.c/h, frame_bundle.h,
CMakeLists, partitions, sdkconfig, the build's link map) and the map editor's structure.
Nothing here changes the ESP32-CAM or the iPhone app: `pipeline_msgs.h` stays as it is.

---

## 0. Short answer

**Yes, a Stardew-style game fits on this ESP32-S3**, provided we keep the engine's
single-screen rooms (Zelda-style screen-to-screen travel) and don't add camera scrolling.

Most of Stardew is data plus one simulation step per day: crops, calendar, friendship,
shipping, machines, crafting and quests. That costs almost no CPU or RAM. The expensive
parts are all presentation: scrolling big maps, lots of moving sprites, full-screen
weather/lighting, and real-time combat. The engine already makes choices that suit a
"Stardew in 480×480 rooms" design: dirty-rect drawing, art baked into the map pixels,
art streamed from the SD card, and a night-stage swap.

The engine needs **four structural additions** before most features become cheap:

1. **Tile layer**: per-tile flags (tillable, water, forage zone…) plus runtime tile
   objects (soil, crops, rocks, forage, machines, chests) baked into the map pixels the
   same way ground items already are.
2. **Actor renderer**: more than one moving sprite (NPCs, animals, monsters), redrawn
   from "map truth" instead of the player's one-deep background cache.
3. **Day pipeline**: calendar/seasons, sleep, a day ending at 2 am, and end-of-day
   processing that catches up maps the player isn't on when they next load.
4. **Data on the SD card**: text files for NPC dialogue, schedules, shops, recipes,
   fish and bundles, so you can change content without reflashing.

---

## 1. Evaluation of what exists today

### Strengths to build on
| What | Where | Why it matters for Stardew features |
|---|---|---|
| Flicker-free compose (`compose_begin/end`, back buffer) | main.c ~446 | Every new overlay (energy bar, dialogue, rain) can reuse it |
| "Everything static is baked into `s_map_pixels`" rule, with rebake hooks on night swap (`brk_rebake_all`, `ground_rebake_all`) | ~4448, ~9629 | Crops, soil and objects can follow the exact same pattern |
| Ground items: 16×16 keyed sprite baked into a tile, pixels underneath kept | ~5359 | Already a working prototype of a Stardew "object on a tile" |
| Breakables with hits, required tool, drop tables and levels | ~2394, ~5272 | Trees and big rocks are done; drop tables can be reused for tile objects |
| Regrowth with a per-map day timer, evaluated lazily on load | ~5650 | Shows the "simulate what happened while away" idea needed for crops |
| Clock already in Stardew style (weekday, 10-minute steps) | ~9108 | Seasons are a small extension |
| Day/night: 6 stages, SD files, background loader | ~9501 | Can double as "overcast" for rainy days at no extra art cost |
| Save slots, `.tmp` / rename crash safety, text saves you can read on a PC | ~5612, ~9143 | Easy to extend with new line types |
| Data-driven items (Game Tools Item Editor → `items/*.c`, free-form name/int attributes) | items.h | Stardew item properties (energy, tool type, buy price) can be attributes: no new editor work |
| Character folders, already holding Pierre, Clint, Demetrius, Elliot, Alex sprites | assets/characters | These are your NPC sprites; the same 16×32 4-direction format |
| `player_play_anim()` override animations | ~3787 | Casting a rod, watering, eating, passing out |
| `sell_menu_open()` and the inventory grid UI | ~6980 | Base for the shipping bin, shops, chests and gifting |
| Pop-up keyboard, menu registry | ~7801, ~6680 | Naming animals/farm; yes/no confirm dialogs |
| Camera → photo item with appraisal traits (sharpness, colour, size…) | ~8662 | A unique hook: gift tastes, bundles and a museum can be trait-based |

### Constraints that shape every plan below
| Constraint | Detail | Consequence |
|---|---|---|
| Maps are exactly 480×480, no camera | `load_map` rejects other sizes | Farm, town etc. are each made of several connected screens. A 30×30-tile farm screen is about Stardew's "small farm" area per screen |
| One framebuffer, no vsync, PSRAM bandwidth shared with LCD scan-out | `num_fbs = 1`, 16 MHz pclk ≈ 32 MB/s just for scan-out | Keep full-screen redraws rare. Per-frame work must stay in small rects |
| Player redraw uses a **one-deep background cache** read from the live screen | `save_player_bg` ~4028 | Breaks as soon as a second moving sprite overlaps the player. The code's own comment says to switch to map-truth redraws |
| Touch only; a tap means "walk there", or "walk next to it and act" for solid things | TAP-TO-WALK ~6195 | Using a tool on *walkable* soil needs a new tap rule (§4.5) |
| Item index is `uint8_t` (≤255 total incl. 32 runtime photo items) | items.h | Stardew-like content needs about 200–350 items. Widen to `uint16_t` early |
| Photo items are lost on reboot | world.txt notes | Any camera-based progression needs persisted photos |
| Map saves are written **synchronously in the game loop**, and each one also rewrites world.txt | `mapsave_tick` → `mapsave_write` | Fine for a few broken trees. With farming (a change every few seconds while watering) it will cause visible hitches |
| Interactions are hard-coded C registries (`s_selected_area_registry` with placeholder rows, `s_map_regen`) | ~3172, ~5662 | Content should move into map data / SD files |
| `main.c` is 10,764 lines / 488 KB, no git repo in CaptureIt | — | Split it and put it under version control before large refactors |
| Main task stack is 3.5 KB | sdkconfig | Existing code works around it with `static` buffers. Raise it to 8 KB before adding parsers/UI |
| No host C compiler | memory notes | Testing logic needs a plan (§7.3) |

---

## 2. Hardware budget

Measured from `build/CaptureIt.map` (esp_idf_size) and sdkconfig:

| Resource | Total | Used now | Free | Notes |
|---|---|---|---|---|
| App flash partition | 15.9 MB | 2.0 MB | **~13.9 MB** | 1.13 MB of it is rodata (sprites/items) |
| Internal DIRAM (static) | 334 KB | 174 KB | 167 KB (minus heap users: Wi-Fi, FreeRTOS, FATFS) | Keep new big tables out of internal RAM |
| IRAM | 16 KB | 100 % | 0 | Don't add `IRAM_ATTR` code |
| PSRAM | 8 MB on R8 modules (Octal 80 MHz). Confirm on Settings → Dev "PSRAM free" | ≈ 2–2.5 MB in game (panel FB 450 K, back buffer 450 K, hold buffer ≥ 450 K, map pixels 450 K, masks, bundle slots); camera adds 1.6 MB, title about 1 MB, both temporary | **~5 MB** | Plenty for the new systems (budget below) |
| CPU | 2 × 240 MHz | Main loop: input + dirty rects, 10 ms delay; mixer on core 1 | Large | Daily simulation over 900 tiles is under 1 ms |
| SD (SPI, shared bus) | — | 3 audio streams + map streaming + night loader + saves | — | Adding more streams risks stutter. Cache short sound effects in PSRAM |

**Estimated new PSRAM cost for everything in this plan:** map base copy 450 KB + base masks
58 KB + tile objects/soil tables ~20 KB + NPC dialogue text ~8 KB per loaded NPC + portrait buffer
8 KB + sound-effect cache ~300 KB + chest contents ~10 KB → **≈ 0.9 MB**.

**Estimated new flash:** ~300 items × ~2–4 KB, 40 crops × 6 stages × 16×32 px (≈ 250 KB),
10 NPCs × (16 walk frames + 6 portraits 64×64) ≈ 650 KB → **≈ 2–3 MB**.

Rough render cost (estimated, measure in Phase 0): one full 480×480 copy PSRAM→PSRAM
≈ 10–15 ms with scan-out running. One 16×32 actor redraw (restore + draw + foreground restamp)
≈ tens of µs. So 16 actors ≈ well under 1 ms/frame, while scrolling would need a full
copy every frame (≈ 25 fps best case, with tearing).

---

## 3. Feasibility matrix

Legend: ✅ easy fit · 🟡 fits with work · 🟠 hard / big refactor · ❌ not recommended here

| Stardew feature | Verdict | How it maps onto this engine | Main cost |
|---|---|---|---|
| Seasons / 28-day calendar / years | ✅ | Derive from `s_clock_day`; clock panel shows "Spr 12" | Small |
| Day ends at 2 am, sleep, pass out | ✅ | Clock runs to 26:00; bed interact → end-of-day pipeline | Small–Med |
| Energy bar, eating | ✅ | Overlay like the clock panel; `energy` item attribute | Small |
| Shipping bin, overnight pay | ✅ | Inventory "SHIP" mode (copy of SELL) + pending list in world.txt | Small |
| Shops (buy) | ✅ | New buy-list UI; stock lists in SD text | Med |
| Tilling, watering, planting, harvesting | 🟡 | Tile layer (§4.2) + new tap rule (§4.5) | **Main new system** |
| Crop growth while away | ✅ | Lazy catch-up when the map loads (deterministic weather) | Small once the tile layer exists |
| Forage / debris spawns | ✅ | Tile objects on "forage zone" flags, rolled per day | Small |
| Crafting, chests, sprinklers, scarecrows | 🟡 | Placeable tile objects + recipe file + crafting UI | Med |
| Machines (keg, jar, furnace) | ✅ | Tile object with input/output/ready-at time | Small |
| NPCs walking on schedules | 🟠 | Needs the actor renderer (§4.3) + shared BFS | Big refactor once, then cheap |
| Dialogue, portraits, friendship, gifts, birthdays | ✅ | Dialogue box UI + SD text + world.txt lines | Med |
| Photo-trait gift tastes / bundles / museum | ✅ | Unique to CaptureIt; needs persisted photos | Med |
| Fishing minigame | ✅ | Hold-to-rise bar suits touch; only a ~60×300 panel redrawn | Med |
| Rain/storm/snow | 🟡 | Overcast = reuse a night stage; 30–40 small particle rects | Med |
| Seasonal map art | 🟡 | Per-season pixel files exported by the editor, loaded like night files | Editor work + SD space |
| Mines (floors, rocks, ores, ladders) | 🟡 | Authored floor layouts + spawned rock objects + runtime ladder teleporter | Med |
| Mine monsters / combat | 🟠 | Actors + simple AI; tap-to-attack is clunky on touch | Big for the fun gained. Do last, or simplify |
| Skills / XP / levels | ✅ | Counters + level-up message + recipe unlocks | Small |
| Tool upgrades | ✅ | Separate items (copper_hoe…) + upgrade "shop" with a 2-day wait | Small |
| Animals (coop/barn) | 🟡 | Actors wandering inside interior maps + daily produce objects | Med (after actors) |
| Buildings (Robin) | 🟠 | Large runtime objects on editor-defined plots + runtime door teleporters | Med–Big |
| Heart events / cutscenes | 🟡 | Tiny script interpreter on SD files | Med (after actors + dialogue) |
| Festivals | 🟠 | Events + map variants + minigames | Big, late |
| Quests / help-wanted board | ✅ | Data + UI | Small–Med |
| Marriage, kids, house upgrades | 🟠 | Possible, but a lot of content | Out of scope for now |
| Scrolling large maps | ❌ | Every draw path assumes screen = map; full redraw per frame | Rewrite; low payoff |
| Co-op multiplayer (ESP-NOW is there…) | ❌ for now | Two S3 boards could link, but state sync is huge work | — |

---

## 4. Core architecture additions

### 4.1 Map data: tile flags + interact points (map format MAP11, magic "MAPB")

Appended after the MAP10 teleporter section, so older maps still load (flags 0, no interacts):

```
tileflags_present   uint8          0 / 1
tileflags           900 bytes      one per 16×16 tile (30×30), row-major:
                                    bit0 TILLABLE      bit1 WATER (fishable)
                                    bit2 FORAGE_ZONE   bit3 DEBRIS_ZONE (farm weeds/stones)
                                    bit4 NO_PLACE      bit5 SPAWN (mine rocks / ores)
                                    bit6 NPC_AVOID     bit7 reserved
interact_count      uint8          0..64
interact_count × {
    tx, ty, tw, th  4 × uint8      area in tiles
    kind            uint8          1 bed, 2 ship_bin, 3 shop, 4 sign, 5 npc_point,
                                    6 build_plot, 7 mine_entry, 8 fishing_spot, 9 script
    name_len        uint8
    name            name_len       e.g. "pierre", "Welcome to Pelican Town", "pierre_counter"
}
```

**Map properties go in a sidecar text file** next to the map, `maps/farm/farm.txt`, so you
can change them without re-exporting:

```
indoor 0            # no rain/snow, no seasonal art swap
farm 1              # never "grows back" (replaces s_map_regen rows), crops allowed
nosave 0            # mines: 1 = state resets every day, no .sav written
music farm.wav
regrow_days 0
fish pond           # table name in fish.txt
season_art 1        # has .sum/.fal/.win pixel files
```

**Editor work (gameTools.html):**
- A **Tile Flags** paint mode (copy of the collision paint mode, with one brush per flag and a
  coloured overlay).
- An **Interact** tool (copy of the Teleport tool: drag a rect, form with kind + name).
- Export writes MAPB. `readTpSection` gains a sibling `readTileSection` for re-import.

### 4.2 Tile layer: soil, crops and tile objects

The one system that unlocks farming, forage, debris, mine rocks, machines, chests,
sprinklers and placed decorations.

**Pixels: a "base" copy and per-tile recomposition.**
- On map load (and right after `night_copy_arena()` copies a new night stage, before the
  rebakes), copy `s_map_pixels` → `s_map_base` (PSRAM, 450 KB), and the hitbox/fg masks →
  base masks (2 × 28.8 KB). Only allocate these when the map has tile-layer content.
- Rebuilding tile (tx,ty) = copy the base 16×16 → soil sprite (dry/wet) → crop or
  object lower half → the upper half of anything standing on the tile below. After that,
  `map_repaint_rect()` on the tile and on the one above it.
- Tall things (16×32: corn, keg, chest lid) set **fg mask** bits on their upper tile, so the
  player walks behind them. That's the same trick the editor uses for tree canopies.
- Solid objects set the tile's **feet band** in the hitbox (`PLAYER_FEET_H` rows), so
  `nav_classify_tiles()` and `player_feet_blocked()` work unchanged.
- Rule: tile-layer tiles may not overlap breakable footprints or animation footprints. The
  editor warns, and the runtime refuses, the same way ground items already do (`ground_tile_ok`).
- Night swap: `farm_capture_base(); farm_rebake_all();` sits next to `ground_rebake_all()`.

**Data (PSRAM, per loaded map):**

```c
// Dense: one per tile, 900 × 8 B = 7.2 KB
typedef struct {
    uint8_t  flags;        // TILLED, WATERED, FERT_MASK(2 bits), DEAD
    uint8_t  crop;         // index into k_crops, 0 = none
    uint8_t  stage;        // current visible stage
    uint8_t  stage_day;    // days spent in this stage
    uint8_t  regrow_left;  // regrowing crops: days to next harvest
    uint8_t  obj;          // index+1 into s_objs, 0 = none (an object covers this tile)
    uint16_t planted_day;  // for "dead at season change" + debugging
} tile_state_t;

// Sparse: everything that isn't soil/crop, max 256 per map (4 KB)
typedef struct {
    uint16_t type;         // index into k_obj_types (rock, weed, keg, chest, sprinkler, forage item…)
    uint8_t  tx, ty;
    uint8_t  hits_done;
    uint8_t  state;        // machine: 0 idle / 1 working / 2 ready
    uint16_t in_item, out_item;     // machines (uint16 item ids, §4.7)
    uint32_t ready_min;    // absolute game minute (day*1560 + minute) the output is ready
    uint16_t chest;        // index into chest storage, or 0xFFFF
} tile_obj_t;
```

**Object types** live in a compiled table generated at build time (same convention as items):
`assets/objects/<id>/object.txt` + `idle.png` (+ `working.png`, `ready.png`, `hit_*.png`):

```
size 16x32          # 16x16 or 16x32 (or bigger for buildings, later)
solid 1
hits 3
need pickaxe        # item id, or "any"
drop stone 1 1 100
drop coal 0 1 10
xp mining 5
machine keg         # optional: refers to machines.txt
```

**Save:** one compact binary file per map for the dense grid, `<save>/<map>.tile`
(header + 900 × 8 B + objects), written with the same .tmp/rename rule. It is about 12 KB and
far faster than 900 text lines. Sparse, human-meaningful things (chest contents) stay as text
lines in `.sav`.

**Lazy catch-up when a map loads** (`tiles_simulate_to(today)`): for each day from the
file's `simulated_through_day` up to yesterday:
- watered = (that day's weather is rain) || sprinkler in range || (the day the player left,
  if they watered).
- Crops on watered soil advance a stage day; unwatered soil dries.
- At a season change, crops not in the new season die.
- Forage/debris spawn rolls use `rng(seed, map_hash, day)`.
- Machines: `ready_min` already says when they finish. Nothing to step.

Because weather and spawns are deterministic functions of (seed, day), catch-up gives the
same result as if the map had been loaded all along, with no RAM held for unloaded maps. This
is the same idea as the existing REGROWTH.

### 4.3 Actor renderer (NPCs, animals, monsters)

Replace the player's live-screen background cache with **map-truth redraws**:

```c
typedef struct {
    int16_t x, y;                 // top-left, same convention as the player
    uint8_t w, h;                 // 16×32 for people
    const uint16_t *const (*frames)[4];   // [dir][frame], like s_player_frames
    uint8_t dir, frame;
    uint8_t kind;                 // PLAYER, NPC, ANIMAL, MONSTER
    rect_t  drawn;                // rect on screen last frame (w=0: not drawn)
    bool    dirty;
} actor_t;
#define ACTOR_MAX 16              // actor 0 = the player
```

Per frame: collect dirty rects (old ∪ new of every actor that moved or changed frame).
For each rect inside one `compose_begin/end`:
1. `restore_map_rect` (map truth, which already includes breakables, ground items and the tile layer);
2. repaint the *current* frame of any ambient animation overlapping the rect (today
   `anim_paint_instance`, clipped);
3. draw every actor overlapping the rect, **sorted by feet y** (correct overlap);
4. the held item over the player;
5. `redraw_foreground_over_rect` + `anim_restamp_foreground`;
6. restamp the XOR tile highlight and the nav marker;
7. `ui_overlays_redraw_if_overlap` (hotbar, corner button, clock, energy bar, message).

This is what `map_repaint_rect()` already does for one player. It generalises it and
deletes `s_player_bg`. **Risk:** the player path has subtle XOR/overlay handling. Do this as a
standalone refactor (Phase 4a) with no NPC logic, and test that walking, animations,
breakables, the hotbar hopping, menus closing and night swaps all still look right.

**Movement:** refactor `nav_plan()` into `nav_bfs(start_tile, goal_tile, out_path, max)` so
NPCs, animals and the player share it. NPCs move with the same per-pixel stepping as
`update_player()`. They don't collide with the player (Stardew NPCs effectively phase), but
the player's BFS treats a standing NPC's tile as blocked at plan time.

### 4.4 Calendar and the day pipeline

- `season = (day / 28) % 4`, `dom = day % 28 + 1`, `year = day / 112 + 1`. Weekday stays `day % 7`,
  so Spring 1 is Monday, as in Stardew.
- Clock speed becomes `CLOCK_MS_PER_MIN` (Stardew ≈ 700 ms; it's 1000 now).
- A game day runs 6:00 → 26:00 (2 am). `s_clock_min` may go past 1440 without incrementing
  `s_clock_day`. Only sleeping or passing out does. Places to update:
  `night_stage_for()` (≥1440 → stage 6), the clock panel (show 12:xx am / 1:xx am),
  `world_read()` validation (`minute < MIN_PER_DAY` → `< 1560`), and `clock_key()`.
- **End-of-day pipeline** (`day_end(bool passed_out)`, runs behind a fade at the loop's top
  level like `tp_travel()` does, because of the small main stack):
  1. fade out, stop the walk, close UI;
  2. pay the shipping bin → summary list;
  3. loaded map: `tiles_day_step()` (other maps catch up lazily);
  4. weather for tomorrow;
  5. NPCs: reset `talked_today` and gift counters (weekly on Sunday), friendship decay, birthdays;
  6. machines and tool-upgrade timers;
  7. skills: level-ups queued as messages;
  8. if passed out: lose 10 % of money (max 1000), wake with half energy;
  9. `s_clock_day++`, minute = 6:00, energy refilled; save world + map (one deliberate write);
  10. "Day summary" screen (shipped items, gold earned, level-ups), tap → wake in bed, fade in.

### 4.5 Touch interaction model

| Holding | Tap on… | Result |
|---|---|---|
| anything | a ready crop, forage, machine with output, chest, NPC, shop counter, bed, bin | walk next to it, face it, interact (harvest / pick / collect / open / talk / shop / sleep / ship) |
| hoe / watering can / seeds / fertilizer / placeable | a walkable tile within the "work zone" (tillable, or for placeables any free tile) | walk next to it, face it, **use the item on that tile** (new `nav_act` target type: a tile, not a breakable) |
| pickaxe / axe / scythe | a tile object (rock, weed, twig) | walk next to it, hit it (object hits/drops, like breakables) |
| fishing rod | a WATER tile | walk to the nearest standable tile facing it, cast |
| anything else | walkable tile | walk there (today's behaviour) |
| tool | **drag** across tiles | queue up to 16 tiles (shown with markers), then work through them in order: walk, use, next. Touch-native row tilling and watering |

Item roles come from Item Editor attributes (int values, no editor change needed):
`tool_hoe 1`, `tool_water 40` (capacity), `tool_pick 1`, `tool_axe 1`, `tool_scythe 1`, `rod 1`,
`seed 1` (crop found by seed id), `energy 25` (edible), `price 50` (buy price),
`place 1` (object type = same id), `gift_category 3`, `weapon 5` (damage).

Gifting: the first tap on an NPC each day talks. A later tap while holding a giftable item
asks "Give Parsnip to Pierre?" (yes/no).

### 4.6 Content data on the SD card

`/sdcard/CaptureIt/data/` (loaded at game start and on a Dev-menu "Reload data" button):

| File | Example lines |
|---|---|
| `shops.txt` | `[pierre]` `open 9 17` `closed Wed` `sell parsnip_seeds 20 spring` |
| `recipes.txt` | `chest: wood 50` / `sprinkler: copper_bar 1 iron_bar 1 \| unlock farming 2` |
| `machines.txt` | `keg: grape -> wine 10080` (minutes) / `furnace: copper_ore 5 coal 1 -> copper_bar 30` |
| `fish.txt` | `sunfish pond spring,summer 6-19 sun 30 mixed 1 2` |
| `forage.txt` | `meadows spring leek 30 dandelion 30 wild_horseradish 40 max 6` |
| `bundles.txt` | `red_bundle: photo:red 3 \| reward money 500` / `spring_crops: parsnip 1 potato 1 cauliflower 1` |
| `npcs/<name>/npc.txt` | `birthday summer 4` `home town 12 9` `loves razor_sharp vivid diamond` `likes red` `hates grayscale` |
| `npcs/<name>/schedule.txt` | `[default]` `900 town 12 9 down` `1200 saloon 5 7 up` `[rain]` … |
| `npcs/<name>/dialogue.txt` | `[intro]` / `[Mon]` / `[spring_12]` / `[rain]` / `[hearts4]` / `[gift_loved]` … |
| `events/<id>.txt` | heart events (§5.15) |

A shared parser (`data.c`) handles sections, `key value...` lines, `#` comments and `|`
options. It allocates into PSRAM, logs bad lines and skips them (the same style as
`mapsave_load`). **Why SD and not flash:** you flash by hand, and dialogue/balance numbers
change constantly. Art stays compiled into flash (fast, no SD bandwidth).

### 4.7 Item system changes
- `uint8_t` → `uint16_t` item index everywhere (`inv_slot_t.item`, ground items, brk drops,
  `item_count`). Saves already use string ids, so **no save migration** is needed.
- `ITEM_CUSTOM_MAX` 32 → 128, and move `s_custom*` arrays to PSRAM (internal RAM is tighter).
- **Persistent photo items:** on creation, write `<save>/photos/<uid>.bin` (24×24 RGB565 icon +
  name + attrs). world.txt bag lines refer to `photo:<uid>`. `world_read` re-creates them with
  `item_add_photo()` using a stable id `photo_<uid>` (not creation order).
- Optional later: item quality (normal/silver/gold) as one byte in `inv_slot_t`. Stacks only
  merge at equal quality, and the price is multiplied.

---

## 5. Feature plans

Each has: what the player sees → data → runtime → editor → save → ESP32 cost/risks.

### 5.1 Calendar & seasons
- **Player:** the clock panel shows `Mon. Spr 3` and time; a new-season message plays; crops die at a season change.
- **Runtime:** helpers in `calendar.c`; extend `clock_render()` (108×50 panel: weekday + date on line 1, time on line 2).
- **Seasonal art (later, Phase 5):** the editor exports `map.sum`, `map.fal`, `map.win`, which hold
  only the pixel block, in the same format/header as the night files. At load, if the season isn't spring and a
  file exists, read its pixels instead of the .map's day pixels (one more read of ~450 KB
  ≈ 0.3–0.5 s, hidden by the fade). Night stages for those seasons use the device's built-in
  darkening fallback, so no 4×6 file explosion. Editor side: a per-season recolour step
  (palette map + "seasonal pixels" mask painted once), reusing its existing tint tool.
- **Cost:** ~0; SD +1.4 MB per map with season art.

### 5.2 Energy, eating, sleep, passing out
- **Player:** a vertical energy bar (12×90) right of the hotbar, Stardew style. Each tool
  use costs 2 (upgraded tools cost the same and do more). At 0: "Exhausted", walk speed halves. At
  -15 they collapse. Eating: inventory card gets an **EAT** button for items with `energy`.
  Bed: tap → "Go to bed?" yes/no → `day_end()`. At 26:00 (2 am): pass out wherever they are and
  wake at home with a money penalty.
- **Runtime:** `energy.c` (state + overlay rendered like the clock: own image, blitted, put
  back by `ui_overlays_redraw_if_overlap`). A generic `confirm_open(text, on_yes)` UI built on the
  menu registry (2 buttons).
- **Editor:** Interact kind `bed` in the house map.
- **Save:** world.txt `energy 212 270`.
- **Cost:** tiny.

### 5.3 Farming
- **Player:** hoe tills TILLABLE tiles (soil sprite); watering can waters (dark soil, refill at
  WATER tiles); seeds plant if the season matches; crops grow a stage per watered night; ready crops
  wobble/sparkle (optional) and a tap harvests into the bag (drops via the existing
  `inv_add`/drop-fit logic). Regrowing crops go back N stages. Scythe clears weeds; the pickaxe removes
  tilled soil.
- **Crop pipeline (build time):** `assets/crops/<id>/crop.txt` + `stage_1.png … stage_N.png`
  + `ready.png` (16×16 or 16×32, transparent = black key like characters).
  ```
  seed parsnip_seeds
  harvest parsnip 1 1
  seasons spring
  stages 1 1 1 1         # days in each stage (Stardew parsnip: 4 days)
  regrow 0
  trellis 0
  xp farming 8
  ```
  A new `tools/crops_gen.py` (or an extension of `png_to_rgb565.py`) → `generated/crops_gen.h` with
  `k_crops[]`. CMake globs the folder with CONFIGURE_DEPENDS, as for characters.
- **Soil sprites:** `assets/ui/soil_dry.png`, `soil_wet.png` (later: autotiling with 16
  edge variants, a 4-bit neighbour mask lookup).
- **Runtime:** `farm.c` on the tile layer (§4.2): `farm_use_tool(tx,ty,item)`,
  `farm_harvest(tx,ty)`, `tiles_day_step()`, `tiles_simulate_to()`.
- **Editor:** paint TILLABLE on the farm screens.
- **Save:** `<map>.tile`.
- **Cost:** 7 KB tile state; 450 KB base copy; baking one tile ≈ µs.
- **Risks:** synchronous saves (fix first, §7.2); a tall crop under a foreground tree canopy must
  keep the canopy (recompose order: base already holds the canopy pixels and fg bits, so keep fg
  bits where the base had them).

### 5.4 Shipping bin
- **Player:** tap the bin → the inventory opens in SHIP mode (same as SELL, title "SHIP"). Items go
  into today's shipment (shown as a list, and can be taken back until night). Paid in the day summary.
- **Runtime:** copy of `sell_menu_open()` with a pending array `s_ship[64]`.
- **Save:** world.txt `ship parsnip 15`; also `shipped_total parsnip 120` (collection log).
- **Cost:** tiny.

### 5.5 Shops
- **Player:** tap the shop counter (Interact `shop:pierre`) during opening hours with the owner
  present (later) → a buy screen: list rows (icon, name, price), tap a row → quantity −/+ → BUY.
  Tool upgrade shop (Clint): pay + bars, the tool is gone for 2 days.
- **Runtime:** `ui_shop.c`, a new `UI_SHOP` screen using the UI buffer machinery (`ui_begin`,
  `s_ui_under`). Scrollable list for more than 8 rows (drag).
- **Data:** shops.txt. Prices fall back to the item's `price` attribute.
- **Cost:** small.

### 5.6 Forage, debris, trees
- **Player:** new forage appears each morning in forage zones (season-specific, tap to pick,
  foraging XP); the farm accumulates weeds/stones/twigs on untilled DEBRIS_ZONE tiles.
- **Runtime:** spawn rolls in `tiles_day_step()` / catch-up, capped per map (forage.txt `max`).
  Forage = tile object with `pick 1` (no tool). Debris = objects with hits/need/drops.
- **Trees growing from seeds:** possible later as a crop-like object with 5 stages that becomes
  choppable. Existing editor breakables stay for hand-placed big trees.
- **Cost:** tiny.

### 5.7 NPCs
**Phase 4a, actor refactor (§4.3).** No gameplay, just the new renderer with the player as actor 0.

**Phase 4b, presence and movement.**
- schedule.txt per NPC: `[key]` blocks chosen by priority: `spring_12` > `rain` > `Mon` > `default`.
  Each line: `time map tx ty facing [anim]`.
- **Where is NPC X at time T?** Walk the schedule: the last entry with `time ≤ T` is where they
  are or are heading. Off-screen NPCs aren't simulated. Entering a map places present NPCs at their
  entry's tile, or partway along the BFS path if mid-walk (computed from elapsed minutes ×
  speed). On the current map they walk with `nav_bfs`. Travel between maps: walk to the exit
  teleporter, disappear, appear on the destination map at the teleporter's arrival tile.
- NPC sprites: reuse `assets/characters/<Name>/` (the same 16×32 format, so Pierre/Clint/Demetrius/
  Elliot/Alex are ready). A character folder can be both playable and an NPC.

**Phase 4c, dialogue and friendship.**
- **Dialogue box:** a bottom panel (460×130) with a 64×64 portrait on the left, text with the 5×7
  font at scale 2 (~28 chars × 5 lines beside the portrait), a name plate, tap to advance, `#`
  page breaks. Emotion codes `$h $s $a $l` pick the portrait (`portrait_neutral.png`,
  `portrait_happy.png`, … in the NPC folder, compiled). Optional choices `[q] A|B` → branch keys.
- **Key selection** like Stardew: `spring_12` > `hearts6` > `rain` > `Mon` > `spring` > `default`,
  plus one-shot keys (`intro`, `gift_loved`…).
- **Friendship:** points 0–2500 (10 hearts × 250). Talk +20/day; gifts loved +80, liked +45,
  neutral +20, disliked −20, hated −40; ×8 on birthdays; 2 gifts per week, 1 per day; −2 per
  day not talked to. Hearts shown on a new inventory tab "Social" (list: portrait, name, hearts).
- **Gift tastes include photo traits and colours** (`loves razor_sharp vivid`, `likes red`,
  `hates blurry`). A photo item's attrs already carry those trait ids, so any real-world photo can be
  a loved gift. Matching order: item id > trait ids > category. A real-world camera hook Stardew
  doesn't have.
- **Save:** world.txt `npc pierre 340 talked 1 gweek 1 gday 0`, `seen intro_pierre`.
- **Cost:** per NPC on screen: one actor; dialogue text ~2–8 KB loaded when talking.

### 5.8 Crafting, placeables, chests, machines
- **Crafting tab** in the inventory: a grid of known recipes. Tap → ingredients shown with
  have/need counts → CRAFT. Recipes unlock by skill level or are bought.
- **Placing:** hold an item with `place 1` and tap a free tile → tile object of the same id; the
  pickaxe/axe picks it back up (returns the item; chests must be empty).
- **Chests:** a 24-slot store per chest (`chest_store_t` pool in PSRAM, up to 32 per map). UI: chest
  grid on top + bag below, tap to move stacks (reuse the inventory carry logic).
- **Machines:** tap with a valid input in hand → state working, `ready_min = now + minutes`;
  sprite switches; when ready a small item bubble shows over it; tap collects.
- **Sprinkler/scarecrow:** object types with `radius` used by the day step.
- **Save:** objects in `.tile`; chest contents as `.sav` text lines `chest 6 5 slot 3 wood 50`.

### 5.9 Fishing minigame
- **Player:** tap water with the rod → cast animation (`player_play_anim("char_cast")`) → wait 1–8 s
  → "!" above the head → tap within 0.8 s → minigame panel: a 40×300 bar with a green zone; **hold
  anywhere** = zone rises (with momentum), release = falls; the fish icon moves by behaviour (mixed,
  dart, smooth, sinker, floater) and difficulty; a progress meter fills while the fish is in the zone,
  drains otherwise. Full = caught (fishing XP, perfect bonus); empty = escaped.
- **Runtime:** `fishing.c`, a `UI_FISHING` screen. Only the panel rect (~60×320) is redrawn per
  frame into the back buffer, then copied: ~38 KB per frame, easily 60 fps. Physics uses real dt
  (`esp_timer`) because the loop period varies.
- **Data:** fish.txt keyed by the map's `fish` table, season, hours, weather.
- **Cost:** small; the best touch-native feature on this list.

### 5.10 Weather
- **Rolls:** `weather(day) = f(hash(seed, day), season)` with Stardew-like odds; Spring 1–3 sunny;
  the TV/clock shows tomorrow's forecast. Deterministic, so offline catch-up matches.
- **Overcast look:** on rain days the night system's "wanted stage" becomes `max(stage, 1)` (or
  2 for storms): the existing `.n1/.n2` files are the overcast look, with no new art and no new loader.
- **Particles:** 32 rain streaks (1×6 px, light blue, blended). Each frame: put the old streak pixels
  back from map truth (skipping pixels inside actor/overlay rects, which are repainted anyway),
  move them, draw them. ≈ 400 px per frame. Snow: 24 slower 2×2 flakes with sway. Storm: lightning =
  rare 2-frame brighten of the whole screen via `world_repaint_all` (≈ 20 ms, acceptable when rare).
- **Effects:** rain waters all farm soil (day step + catch-up). Indoors maps (`indoor 1`) skip all
  of it.
- **Audio:** the rain loop on its own channel. Raise `AUDIO_MAX_CHANNELS` to 4 (music, ambience,
  2 SFX); cache SFX < 2 s in PSRAM.

### 5.11 Mines
- **Layouts:** 10–20 authored floor maps (`mine_a` … `mine_t`) in the editor: walls, SPAWN-flagged
  tiles, an entry teleporter tile, `nosave 1`, no night/season art (`indoor 1`).
- **Floor N:** layout = `hash(seed, N) % layouts`; spawn rocks/ores/gems as tile objects on SPAWN
  tiles with depth-based tables (copper 1–39, iron 40–79, gold 80+). Each broken rock has a chance to
  reveal the **ladder** (an object whose interact is "go down"). Elevator every 5 floors (world.txt
  `mine_deepest 25`, elevator UI = a menu list).
- **Runtime:** a "virtual map" name `mine:37` → `load_map(layout)` + floor generation after load.
  `current_map_name()` stays the layout name; a separate `s_mine_floor`.
- **Monsters (optional, last):** actors with hop-toward-player AI on the BFS grid, contact damage →
  a health bar next to energy; tap a monster while holding a weapon → walk adjacent, swing anim,
  damage + knockback. Keep counts ≤ 6 per floor.
- **Cost:** spawning ≤ 60 objects per floor (bakes ≈ ms behind the fade).

### 5.12 Skills & tool upgrades
- Farming, foraging, mining, fishing, combat XP with Stardew thresholds (100, 380, 770, 1300, 2150,
  3300, 4800, 6900, 10000, 15000). Level-ups shown in the day summary; unlock recipes (+ optional
  professions later). The inventory "Skills" tab.
- Tool upgrades: copper/iron/gold items; an upgraded hoe/can affects a 3-tile line (the queue from
  §4.5 fills automatically).

### 5.13 Camera tie-ins (CaptureIt's own twist)
- **Persistent photos** (§4.7), a prerequisite.
- **"Community Board" bundles** that ask for real-world photos: "Red Things (3 photos tagged
  red)", "Sharp Eye (1 razor-sharp photo)", "Tiny World (2 tiny photos)", mixed with crop/fish
  bundles. Rewards: money, recipes, unlocking a map area (a teleporter enabled by a flag).
- **Gallery (museum):** donate photos; a gallery map with frame objects (32×32 tile objects whose
  sprite is the donated photo's icon, drawn at runtime from `<save>/photos`). Milestone rewards.
- **Label-aware photos:** the prompt typed in the live view ("apple") is kept as an attr/category
  via a keyword table on SD (`apple banana → fruit`), so NPC tastes like `loves fruit` work for photos.
- No change to the CAM firmware or the iPhone app.

### 5.14 Quests
- Help-wanted board (Interact `script:board`): a daily generated quest — "Bring Clint 10
  copper ore in 2 days", "Catch a sunfish for Willy", "Photograph something blue for Elliot".
  Quest log tab. Data: templates in `quests.txt`.

### 5.15 Events / cutscenes
- A script interpreter (`script.c`), one command per tick, input blocked except dialogue taps:
  ```
  trigger map town hearts pierre 2 time 900-1700 weather sun once
  fade out
  warp player 12 14 up
  npc pierre 12 10 down
  fade in
  move pierre 12 12
  say pierre "$h I've been thinking about expanding the shop..."
  anim player char_wave 120 1
  choice "That's great!" great | "Why?" why
  [great] friendship pierre 50
  end
  ```
- Triggers are checked on map load (cheap: a list per map).

### 5.16 Animals & buildings (late)
- **Animals:** coop/barn interior maps; animals = actors wandering (random BFS target every few
  seconds); feeding = hay object in a trough tile; the day step makes produce objects (egg/milk) if
  fed; petting = tap (+friendship); bought from a shop of type `animals` with the naming keyboard.
  world.txt `animal 3 chicken "Clucky" 420 coop fed 1 pet 0`.
- **Buildings:** the editor defines `build_plot:<id>` interact rects on farm screens. Building = a large
  runtime object (e.g. 96×80, art/masks from PNG alpha, roof in fg) baked onto the plot + a runtime
  teleporter at its door tile (added to `s_tp` on load). Construction takes N days (a scaffold sprite).

---

## 6. Pipelines

### 6.1 Content pipelines (where things are authored → how they reach the device)

```
ART (compiled into flash)                           DATA (on the SD card)
──────────────────────────                          ──────────────────────
Game Tools ─ Item Editor ────► assets/items/<id>.c ─┐
assets/characters/<Name>/*.png ─────────────────────────┤
assets/crops/<id>/{crop.txt,*.png}  ── crops_gen.py ────┤    data/shops.txt, recipes.txt,
assets/objects/<id>/{object.txt,*.png} ─ objects_gen.py ┼──► idf.py build ──► flash
assets/ui/*.png (soil, energy bar, icons) ──────────────┤    fish.txt, forage.txt, bundles.txt,
assets/characters/<Name>/portrait_*.png ────────────────┘    quests.txt, npcs/<n>/*.txt, events/*.txt
                                                                   │ copy to card
Map editor ─ Export ──► maps/<m>/<m>.map (+ .n1–.n6, + .sum .fal .win)   └──► /sdcard/CaptureIt/data/
            + maps/<m>/<m>.txt (properties, hand-edited)                      (Dev menu: Reload data)
```

Rules:
- Every generator script fails the build with a clear message on bad data (like the item-id check in
  `main/CMakeLists.txt`).
- Every SD loader logs and skips bad lines, never crashes, and shows a count via `message()`.
- Ids are lowercase `[a-z0-9_]`, the same rule as items. SD data refers to ids, never indices.

### 6.2 Implementation phases

Each phase ends with a flashable build and a "done when" check you can do on the device.
Sizes: S ≈ one focused session, M ≈ 2–3, L ≈ 4+.

| Phase | Contents | Depends on | Size | Done when |
|---|---|---|---|---|
| **0. Foundations** | `git init` + first commit; split main.c (§7.1) into modules, starting with leaves; main stack 8 KB; `uint16` items; PSRAM custom items; **background save writer** (§7.2); SD data parser; Dev menu cheats (skip day, set time/season/weather, give item, money, energy); perf probe (time a full-screen copy, map load, save write; show on the Dev screen) | — | L | Game plays exactly as before; Dev screen shows timings; saving doesn't hitch |
| **1. Days** | Calendar/seasons on the clock; 6:00–26:00 day; energy bar; eating; bed + yes/no dialog; pass out; day-end pipeline + summary screen; shipping bin; MAPB reader + editor Interact tool (bed, ship_bin, shop, sign); map sidecar .txt (replaces `s_map_regen` + `s_selected_area_registry`) | 0 | M–L | Play several days in a row, ship wood, get paid overnight, survive a reboot mid-day |
| **2. Farming** | Tile flags (editor paint mode + reader); tile layer (base copy, dense state, rebake on night swap, `.tile` save); tap rule for tools; hoe/can/seeds/scythe; crops pipeline (`crops_gen.py`) + 5 spring crops; catch-up simulation; Pierre's buy shop | 1 | L | Spring 1 plant parsnips, water 4 days (including one day away on another map), harvest, ship, buy more seeds |
| **3. Farm life** | Forage + debris spawns; objects pipeline (`objects_gen.py`); hitting objects; crafting tab + recipes.txt; chests UI; sprinkler, scarecrow; keg/jar/furnace; drag-to-queue tool use | 2 | M–L | Craft a chest and a sprinkler from foraged/debris materials; a keg produces after N days, including while away |
| **4a. Actor refactor** | Map-truth renderer, player as actor 0, `nav_bfs` shared | 0 | M | No visual regressions: walk under trees, past animations, by breakables, under the hotbar, open/close menus, night swap |
| **4b–c. NPCs** | Schedules, cross-map presence, talk, dialogue box + portraits, friendship, gifts (incl. photo traits), birthdays, Social tab | 4a, 1 | L | Pierre walks his route; talking/gifting changes hearts; dialogue changes by day/season/hearts |
| **5. World** | Weather (overcast via night stage, rain/snow particles, auto-watering); seasonal art (editor recolour + `.sum/.fal/.win` loader); fishing minigame + fish.txt; 4th audio channel + SFX cache | 2 (weather), 0 | M–L | Rainy day waters the farm and looks overcast; catch 3 fish types; the farm turns orange in fall |
| **6. Mines & progression** | Mine floors + ore spawns + ladder + elevator; skills/XP + level-up unlocks; Clint upgrades + smelting | 3 | M–L | Reach floor 20, smelt copper, upgrade the hoe, see a level-up in the summary |
| **7. Camera progression** | Persistent photos; community board bundles with photo requirements; gallery; label keywords; quests board | 0, 1 | M | Complete a "3 red photos" bundle with real photos after a reboot |
| **8. Late game** | Animals, buildings on plots, scripted heart events, a first festival, monsters (optional) | 4, 3 | L+ | Buy a chicken, collect eggs; see Pierre's 2-heart event |

Two tracks can run in parallel after Phase 1: **2 → 3 → 6** (farm/economy) and **4a → 4b–c → 8**
(people). Weather/fishing (5) only needs Phase 2's tile flags and the day step.

---

## 7. Engineering plan

### 7.1 Splitting main.c (Phase 0)
Proposed files; move code **as is** first, one module per build, then refactor:

| Module | From main.c sections |
|---|---|
| `gfx.c/h` | DISPLAY, NIGHT TINT LUT, SHARED BUFFERS, COMPOSE, round rects, font/text |
| `audio.c/h` | AUDIO |
| `map.c/h` | MAP LOADING, BUNDLES, SD STREAMING, ANIMATION PLAYBACK, BREAKABLES (data + runtime), TELEPORTERS |
| `world_draw.c/h` | repaint helpers, PLAYER BG/actor renderer (4a), overlays, highlight |
| `input.c/h`, `nav.c/h` | TOUCH, INPUT, TAP-TO-WALK |
| `inventory.c/h`, `ground.c/h` | inventory/money/traits, GROUND ITEMS |
| `ui.c/h`, `ui_inventory.c`, `ui_menu.c`, `ui_keyboard.c` | UI SCREENS, menus, keyboard |
| `save.c/h` | MAP SAVES, SAVE SLOTS |
| `clock.c/h`, `night.c/h` | CLOCK, DAY/NIGHT |
| `camera.c/h` | ESP-NOW camera, live view, appraisal |
| `title.c/h` | TITLE ART, LOADING, TITLE SCREEN, GAME MENU |
| new: `calendar.c`, `energy.c`, `dayend.c`, `tiles.c`, `farm.c`, `objects.c`, `actors.c`, `npc.c`, `dialogue.c`, `data.c`, `shop.c`, `craft.c`, `fishing.c`, `weather.c`, `mines.c`, `skills.c`, `script.c` | — |

Shared state goes in `game.h` (extern globals today declared `static`). Keep the existing comment
style: a banner per section, comments that explain why.

### 7.2 Saving without hitches
- A **save task** (core 0, low priority): the game loop fills a PSRAM snapshot (map save text +
  `.tile` bytes + world.txt) and posts it; the task writes .tmp → rename. The game never waits on
  the card. `load_map` waits for an in-flight write of the *same* map before reading it.
- Coalesce: watering 10 tiles = one write 2 s after the last change (`MAPSAVE_DELAY_MS`),
  but world.txt only on the hour, at day end and on map change (not with every map save as now).

### 7.3 Testing
- **Dev cheats** (Phase 0) are the main on-device test tool.
- **Pure-logic modules** (calendar, crop step, catch-up, weather RNG, dialogue key choice,
  schedule lookup, save-line parsing, recipe matching) are written with no ESP-IDF includes, so
  they can compile on a PC. Options, in order of preference:
  1. install a host compiler once (LLVM/clang or MSYS2 gcc via winget) and add a `tests/` folder
     with a tiny runner;
  2. check whether IDF v6.1's `idf.py qemu` supports esp32s3 for headless unit tests;
  3. keep the Python-mock approach already used for the title screen.
- **Editor changes:** the headless-Chrome method in the memory notes (extract functions, dump DOM).

### 7.4 Performance guard rails
- Per frame: only dirty rects; no full-screen work except night/weather swaps and fades.
- Anything that reads the SD card in the game loop goes through a task (streamer, night loader,
  save task, new SFX cache loader).
- Limits as named constants with editor checks: ACTOR_MAX 16, TILE_OBJ_MAX 256, CHESTS 32 per map,
  forage max per map, monsters ≤ 6.

---

## 8. Open questions for you

1. **Scope:** a full Stardew loop (farm + town + mines + NPCs), or a smaller "photo-farmer"
   game where the camera is the centre and farming supports it? This changes Phase 7's priority.
2. **Clock speed:** Stardew's ~0.7 s per game minute (≈14 min days) or the current 1 s (≈20 min days)?
3. **Farm size:** how many 480×480 screens for the farm (1, 2×1, 2×2)? Each screen holds about
   20×20 usable tiles once paths and buildings are in.
4. **Art:** do you have, or will you draw, crop stages, soil, portraits and object sprites?
   (Stardew's own assets are fine for a private build, but not for anything shared.)
5. **Combat:** keep the mines peaceful (rocks, ores, gems only), or invest in touch combat?
6. **Hardware:** is the PSRAM 8 MB? (Settings → Dev shows the total.)
