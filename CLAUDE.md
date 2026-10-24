# CaptureIt — notes for Claude

A Stardew-Valley-style game for an **ESP32-S3** board with a 480x480 touch screen. It also has a camera
"appraisal" feature: an ESP32-CAM takes a photo, AI names and prices the objects, and they become items in
the game. Everything is written in plain C on ESP-IDF v6.1. The game content (items, crops, maps, animals…)
is made in a browser editor, `gameTools.html`, and is NOT hand-written in C.

The user flashes the board and plays on it. There is no host C compiler and no Node on this PC, so screens
and JS are checked in other ways (see *Testing*).

---

## Where things are

| Path | What it is |
|---|---|
| `main/main.c` | **The whole game** (~22k lines, one file, split into `// ===` banner sections — see the map below). Grep for the section name. |
| `main/game_config.h` | Build switches: `ESPNOW_CAMERA_ENABLED` (camera/Wi-Fi code in or out), `DEV_LINK_ENABLED` (USB dev link in or out). |
| `main/items.h` / `items.c` | Item table (`s_items[]`, built from `items_manifest.inc`), `item_attr()` lookup, quality/mutation tables (`k_quality[]`, `k_mutation[]`), runtime photo items (`item_custom_*`). Note: items.c/items.h use CRLF line endings. |
| `main/crops.*`, `buildings.*`, `animals.*`, `machines.*`, `fences.*`, `trees.*` | Type definitions + tables for content made by the matching Game Tools editor (each .c just expands its generated manifest). buildings.h also has the farm fields (barns/coops/silos/wells; an animal door can have its own shut/open looks over a see-through opening, door_x/y/w/h); fences.h = fences, gates, pipes (a pipe beside a farm building is drawn on up to its wall, house_bake_pipes()). |
| `main/actions.c` / `actions.h` | `ASSET_ACTION(id, "Label", "help")` rows: what a map object does when tapped (seed_shop, build_shop, ranch_shop, bed, ledger…). **The Map Editor parses this file**, so keep each row on one line. New actions also go in `BUILTIN_ACTIONS` in gameTools.html. |
| `main/frame_bundle.h` | `frame_bundle_t`: the shared animation strip (item hold/use art, map animations, breakable hits). |
| `main/pipeline_msgs.h` | ESP-NOW message formats between the S3 and the ESP32-CAM. **Must stay byte-identical** to `c:\projects\ESP32CamFirmware\main\pipeline_msgs.h`. Changing it means flashing both boards. |
| `main/CMakeLists.txt` | Globs `assets/{items,crops,buildings,animals,machines,fences}/*.c` and writes the `*_manifest.inc` files (file name = id; it stops the build if two ids clash). Also runs `tools/png_to_rgb565.py` on the sprite PNGs. |
| `assets/` | All game content (at the project root, not in main/). `items/<id>.c` (~80), `crops/<id>.c`, `animals/`, `buildings/` (incl. barn/coop/silo), `machines/`, `fences/` = editor exports compiled into the firmware. Top-level PNGs, `ui/`, `fx/` = sprites compiled in. `wardrobe/` = everyone's looks in layers (see its README.md), compiled in by tools/wardrobe.py. `map/` = Map Editor tile art (NOT compiled in; maps are exported to the SD card). `gametools_assets.json` = per-asset editor settings (collision, layer, flags, actions). `needs_you.json` = the Needs You to-do list (see *Content pipeline*). `placeholder_art/` = the first stand-in PNGs. `Recycle Bin/` = the editor's deleted assets (gitignored). |
| `maps/` | Copies of the building interior `.map` files (the real maps live on the SD card). small/medium/large_barn_inside and _coop_inside are placeholder rooms made by a script (exit + 2/4/8 troughs). |
| `gameTools.html` | Game Tools (~23k lines, CRLF): Map Editor (its Tree tool puts the map's own trees on it → `<map>.trees`), Item Editor, Crops / Buildings / Machines Editors, the **Trees** tab (wild + fruit trees → `assets/trees/<id>.c`, with a sprite-sheet cutter), the Farm tab (Animals, Barns coops & silos, Fences & pipes — under its own #farmBar), the **Fishing** tab (fish / junk / crab pot catches / treasure / bait / tackle / rods: icon, conditions, tricks, effects, a "Who bites?" odds box, and the game-wide settings → `assets/fishing/settings.c`), the **Furniture** tab (the furniture wish list, see below), the **Wardrobe** tab (tags each wardrobe piece male / neutral / female, one click each, into `assets/wardrobe/genders.json`), the **Needs You** tab (right end of the bar, see below), and the Image Editor. Every editor tab is resizable (column bar, box grips, a panel-width grip — RESIZABLE BOXES, LAYOUT_PANELS); lists are picture grids (GRIDS, NOT LISTS: igRender, the crops list, the Fishing list; Find an item… = cfOpen); the Item Editor has **Add from a sheet…** (ADD FROM A SHEET: step through a sheet's cells, name, Save & next) and a same-name dialog on export (SAME NAME: dupAsk) (in `<template id="imageEditorPage">`, shown in an srcdoc iframe). Desktop shortcut "Game Tools.lnk" opens it with `chrome --app=file:///C:/projects/CaptureIt/gameTools.html` and uses `gameTools.ico`. If you rename it, update the shortcut and the favicon. |
| `debugPanel.html` + `tools/debug_panel.py` | Debug Panel: a cheat/test web page served on `127.0.0.1:7767`. It forwards to the dev link. Desktop shortcut "Debug Panel.lnk" runs the IDF venv `pythonw.exe tools/debug_panel.py`. |
| `tools/devlink.py` | PC side of the USB dev link (see *Dev link*). |
| `tools/png_to_rgb565.py` | Runs during the build: PNG → RGB565 headers + `sprites_gen.h`. Needs Pillow in the IDF venv. |
| `tools/wardrobe.py` | Imported by png_to_rgb565.py: `assets/wardrobe/` (bodies, pants, shirts, hair, accessories, hats) → `wardrobe_gen.h` (each PNG's shades + per-pixel map, refs, body bobs) + the outfit palettes. main.c's WARDROBE section stacks them into 20x36 frames (`ward_compose()`) for the player (Customize, outfit in NVS key `outfit`) and the shoppers (`ward_random(seed)`). `genders.json` (Game Tools' Wardrobe tab) orders every list male, neutral, female (Customize's pages) and dresses each shopper by their gender (male/female from the seed; their own + neutral pieces; untagged = neutral, bodies by name). `--preview out.png [--seed S] [--held]` draws random people without a build. |
| `tools/slice_trees.py` | One-off: cut the Stardew tree sheets (Downloads: Environment - Trees / Fruit Trees) into `assets/trees/*.c` + the fruit items, in the Trees Editor's exact format (`--preview out.png` draws them all). Layout notes in its docstring. |
| `tools/slice_food.py` | One-off: cut the food pictures (Downloads: food (1..7).png, 16x16 cells) into 73 food items (`food 1`) and write Stardew's recipe of each to Downloads/stardew_food_recipes.txt (`--write`, `--recipes`, `--preview`). |
| `tools/slice_mines.py` | One-off: cut the Stardew mines sheet (Downloads: Environment - Mines) into ~55 minerals/gems (`museum 1`, `mineral 1`, `geode:<geode id>` W pools), the 4 geodes (`geode 1`), `stone`, and the mineable rocks / gem nodes as Map Editor art in `assets/map/mining/` (`--preview`, `--write`). `--rocks` (Game Tools closed) writes those rocks' breakable settings into gametools_assets.json: pickaxe, solid, a shake hit bundle and the sheet's dust as the last-hit (fall) bundle — drops left for the user. |
| `tools/make_gear.py` | Draws the climate gear (Thermal = heat, Arctic = cold; hat/jacket/pants/boots): `assets/items/<set>_<slot>.c` + worn art `assets/wardrobe/gear/<id>.png`, from the body's own shapes per frame (`--preview out.png`, `--write [--force]`). |
| `tools/slice_forage.py` | One-off: cut the Stardew forage sheet (Downloads: Environment - Forage) into 29 forage items `assets/items/*.c` (Item Editor format, `forage`/`forage_seasons` attrs) and the bat sheet into `assets/bat_sheet.png` (`--preview out.png`). |
| `tools/slice_stardew.py` | One-off: cuts the Stardew farmer sheets (Spriters Resource rips in Downloads: Farmer Base, Pants, Hairstyles, Hats, Accessories, optional Shirts) into `assets/wardrobe/`. Layout notes in its docstring. |
| `tools/make_menu_art.py` | Generates the title screen art into `assets/ui/` (`--preview`). The strand anchors it prints must match `k_title_strands[]` in main.c. |
| `tools/gemini_test.py`, `ebay_test.py`, `sam_test.py` | PC tests of the CAM's online APIs. `tools/gemini_key.txt` holds a real key and is gitignored. Never print or commit keys. |
| `docs/STARDEW_PLAN.md` | The original plan/feasibility study for the Stardew features (2026-09-30). |
| `docs/SEASONS.md`, `docs/LAVA_AND_SHOPS.md`, `docs/FEATURE_IDEAS.md` | How seasons (crops, seasonal map art), lava fishing and the General store / Shop Editor work, and a list of feature ideas. |
| `partitions.csv` | 16 MB flash: nvs, one 15.9 MB factory app (no OTA), coredump. |
| `.vscode/tasks.json` | Old build/flash tasks that point to `C:\esp\v6.1` and COM7. They are stale; use the commands below instead. |

### main.c section map (grep the banner title)
In file order: 3-wire SPI (ST7701 init) · DISPLAY · NIGHT TINT · SHARED FULL-SCREEN BUFFERS · OFF-SCREEN COMPOSE ·
AUDIO (3-channel WAV mixer) · SOUND EFFECTS (`sfx_play`, `sfx_play_list`) · ESP32-CAM link / Camera Wi-Fi (ESP-NOW) ·
MAP LOADING (map file format notes) · FRAME BUNDLES + MAP ANIMATIONS · SD STREAMING · ITEMS + INVENTORY + BREAKABLES
(also teleporters, tile types, action triggers) · MAP NAME · SELECTED AREA REGISTRY · TOUCH PANEL (GT911) · INPUT SYSTEM ·
PLAYER (+ the energy state) · WARDROBE (layered outfits) · PLAYER ANIMATION OVERRIDE · MUTATIONS (+ wet items) · HELD ITEM · TOOL SWING (+ the NEW ITEM sparkle) · PLAYER BACKGROUND CACHE · ANIMATION PLAYBACK ·
BREAKABLE RUNTIME + HUD · MESSAGES · GROUND ITEMS · FARMING (crops, farmland, grass) · MAP SAVES (regrowth registry) · TREES (planted/wild trees, chopping, shaking, falling + leaves) · FORAGE (daily forageables on Forage tiles) ·
PLACEMENT (props, shelves, aquariums, walk-in BEDS, buildings, machines, hologram) · SPRINKLERS + SCARECROWS (the 6:00 morning, crows) · TELEPORTERS · ASSET ACTIONS · TAP-TO-WALK ·
UI SCREENS (menus, inventory, item card, shops, shelves) · MARKET (NPC shoppers, offers, auction house) · ANIMALS (+ FARM: barns/coops/silos, the herd in farm.txt, pipes, troughs) ·
FISHING (+ CRAB POTS) · FISH BOOK · MARKET BOARD (demand, photo requests, capture book) · CRAFTING (the inventory's hammer tab) · POP-UP KEYBOARD · CAMERA WI-FI · CAMERA CAPTURE · LIVE VIEW · PHOTO -> ITEM · PHOTO APPRAISAL ·
CLOCK (+ the energy bar under it) · LEDGER · SAVE SLOTS (photo items in the save) · WEATHER · DAY / NIGHT · BATS · SLEEP · ENERGY (costs, pass out) · TITLE ART · LOADING SCREEN ·
TITLE SCREEN (Customize; its Save / Load = characters on the SD card) · GAME MENU · DEV LINK · then the game loop + `app_main` at the end.

---

## Hardware

- **S3 board**: ESP32-S3R8 (8 MB octal PSRAM at 80 MHz, 16 MB flash), 240 MHz, 480x480 **ST7701 RGB panel**.
  The panel has no memory of its own: the frame (`s_fb`) is in PSRAM and is streamed out through bounce buffers
  (`LCD_BOUNCE_LINES`).
  - ST7701 init over 3-wire SPI: CS 1, SCK 12, SDA 11 (these lines are shared with the SD card).
  - SD card (SPI): SCK 12, MOSI 11, MISO 13, CS 10. It runs at 20 MHz because the card refuses the high-speed switch in SPI mode.
  - Touch GT911 (I2C 400 kHz): SDA 17, SCL 18, RST 38, address 0x5D or 0x14 (both are probed), polled with no INT pin.
  - Audio I2S: BCLK 20, LRCLK 46, DOUT 19. **GPIO 19/20 are also the S3's USB D-/D+**, so while audio is on, the USB
    serial (and the dev link) is gone. Turn audio off in Settings (it's saved in NVS as `audio_dis` and the board reboots) to use the dev link.
  - USB: native USB-Serial-JTAG, Espressif VID 0x303A, usually **COM3**.
- **ESP32-CAM** (AI-Thinker, OV2640, 4 MB flash, CH340 USB chip): its COM port changes when replugged (COM4/8/9/10).
  Its firmware is in `c:\projects\ESP32CamFirmware` (`main.c` = camera + ESP-NOW, `appraise.c` = Wi-Fi + Gemini + SAM 3 + eBay,
  `secrets.h` = Wi-Fi networks + API keys, gitignored; template = `secrets.example.h`).
- **SD card** = drive **`W:`** (label "Absolute") when it's in the PC. Older notes say `D:`, which is the same card; the reader
  used to be D:. Check with `Get-Volume` if unsure. The game reads everything from `/sdcard/CaptureIt/` (`W:\CaptureIt\`):
  - `maps/<name>/<name>.map` + night files `.n1`–`.n6`. A map **must** be in its own folder; maps exported flat into `maps/` won't load. A new game starts on `meadows`.
    Seasonal art: `<name>.<spring|summer|fall|winter>.map` + its own `.n1`–`.n6`, loaded instead in that season (main.c SEASONS, `season_map_path()`); same map name and save.
  - `characters/char1.txt`…`char6.txt`: outfits saved from Customize › Save (text, wardrobe part names + colours).
  - `saves/save1`…`save6/` (world.txt, map `.sav` files, buildings.txt, farm.txt, photos.bin, fishbook.txt, ledger.csv, market.txt, sold.txt).
  - `sounds/sound effects/*.wav` must be **16-bit mono 44.1 kHz** (the mixer doesn't resample), and are named without `.wav` in the editor.
  - The card has to go back into the board to play (the maps are on it).
  - **The card must be MBR + FAT32.** IDF's FatFs is built with `FF_LBA64 0` (no GPT support), so a GPT card won't mount
    ("SD card mount failed"), even when it's formatted FAT32. Windows' quick format keeps the old partition table. To fix it,
    as admin: `diskpart` → `select disk N` → `clean` → `convert mbr` → `create partition primary` → `format fs=fat32 quick`
    → `assign letter=D`. A copy of the card's `CaptureIt` folder is kept in `C:\D drive\CaptureIt`.

### Cores, timing, memory
- The game task (title + game loop) is pinned to **Core 1**, and `game_init()` runs there too, so the RGB panel's bounce ISR
  shares Core 1 with the game. **Keep it that way**: with the ISR on the other core, PSRAM bursts made wavy line glitches.
  Audio, sfx and Wi-Fi are on Core 0.
- Frames are paced to `FRAME_MS` = 16 ms (`pace_wait`). `CONFIG_FREERTOS_HZ=1000`.
- Internal RAM is scarce (~106 KB free on the title screen). Put big or rarely used tables in PSRAM (`EXT_RAM_BSS_ATTR`, `heap_caps_malloc(MALLOC_CAP_SPIRAM)`), and keep art `const` (in flash).
- Drawing: placed map art is **baked into one 480x480 map raster** (`s_map_pixels`) at export/load time, and the screen uses
  dirty-rect repaints (`map_repaint_rect`). Crops, props, buildings and ground items are baked in the same way. Only animated or
  breakable things are drawn each frame.
- Don't try PSRAM at 120 MHz again: it was tried and boot hangs at "MSPI Timing: Enter psram timing tuning".

---

## Networking (ESP-NOW + Wi-Fi)

- The S3 and the CAM talk over **ESP-NOW on Wi-Fi channel 1**. The S3 sends to `CAM_MAC` (main.c, the ESP32-CAM link section).
  The CAM runs a hidden AP on channel 1 only to carry ESP-NOW.
- Photo flow (the only flow): live view (`CAM_MSG_PREVIEW` → JPEG chunks) → tap → `CAM_MSG_SNAP` (the CAM keeps a 640x640 photo
  and sends a 480x480 copy) → `CAM_MSG_APPRAISE`. The CAM then sends `STATUS(AWAY)`, leaves channel 1, joins a real Wi-Fi network,
  and: **Gemini** names and boxes the objects and gives traits, value, kind and **market types** (2-5 numbers from
  `CAM_TYPES` in pipeline_msgs.h); **SAM 3 on Roboflow** outlines them while **eBay** prices them (side by side, eBay in
  its own task, since 2026-10-23). It comes back to channel 1 and sends STATUS(INFO) + OUTLINE + LABELS + TRAITS + KINDS +
  TYPES (`CAM_MSG_TYPES` 0x14, a uint64 bit set per box) + PRICES + BOXES (boxes last). This takes ~12 s beside the router.
  Faster joins: the CAM remembers each network's last AP (BSSID + channel, NVS key `lastap`) and tries it first
  (`WIFI_FAST_SCAN`, one channel), and DHCP asks for its last IP (`CONFIG_LWIP_DHCP_RESTORE_LAST_IP`). The summary line
  on the S3 shows where the time went (Wi-Fi, upload, AI, masks, eBay).
- Settings › **Camera Wi-Fi** on the S3 edits the CAM's network list (stored in the CAM's NVS; `secrets.h` only seeds it). Messages
  `CAM_MSG_NET_*` 0x10–0x13. WPA2-Enterprise works (school logins); captive-portal networks don't. Phone hotspots must be 2.4 GHz.
- Decisions already made (don't propose them again): no phone, laptop or server in the middle; the iPhone/YOLOE (CamPipe) path was dropped;
  Gemini polygons were too rough (SAM 3 does the outlines); API keys live on the CAM.
- `ESPNOW_CAMERA_ENABLED 0` in game_config.h removes all radio and camera code.

---

## Building and flashing

ESP-IDF **v6.1** is installed under `C:\Espressif`. From PowerShell:

```powershell
. C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1
idf.py build
```

- The IDF venv python is `C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe`. It has Pillow and pyserial; the system python doesn't.
- `idf.py` refuses to build from Git Bash (MSYSTEM is set). Use PowerShell, or `devlink.py flash --build`, which strips MSYSTEM.
- **Preferred**: `python tools/devlink.py flash --build`. It stops the dev link server, closes any VS Code ESP-IDF monitor on the
  port, builds, flashes, restarts the server and waits for the board.
- Run builds and flashes as **background tasks**. The user dislikes console windows popping up. Start child processes with
  `CREATE_NO_WINDOW` and never `DETACHED_PROCESS`.
- If a build fails at "Converting sprite PNGs", check that Pillow is installed in the IDF venv.
- Recovery when a bad app hangs before USB comes up: hold BOOT and replug USB, then flash with
  `esptool --before no-reset ... write-flash @build/flash_args`. Use `--after watchdog-reset` to boot it.
- ESP32CamFirmware builds the same way. If `pipeline_msgs.h` changed, build **both** projects before handing over.
- Reading boot logs: opening the port resets the board. Use pyserial with dtr/rts False, or `devlink.py log`.
- Portable kit: `START VS CODE.bat` = portable VS Code + IDF (ESP-Portable), made for a school PC that wipes its disk.
  `BUILD AND FLASH CAPTUREIT.bat` is one-click. `SYNC PROJECTS.bat` mirrors C:\projects ↔ the kit and asks which side wins.
  Since 2026-10-16 the kit, TheFishingGame and the launchers live in **`C:\D drive\`** (they were moved off the card when it was reused). The card now holds only `CaptureIt\`.
  The card copies are NOT synced automatically.

---

## Dev link (drive the game from the PC)

The board takes text commands over USB serial **only while audio is off** (and `DEV_LINK_ENABLED 1`). Opening the port resets the board,
so `devlink.py` keeps one background server holding the port (`127.0.0.1:7766`, log in `tools/devlink.log`), and all other commands talk to it.

```
python tools/devlink.py start | stop | wait | reset        # server / board control
python tools/devlink.py flash [--build]                    # build+flash+restart (use this)
python tools/devlink.py load N | load new                  # from the title screen, no taps
python tools/devlink.py cmd "state"                        # any board command, prints @@ lines
python tools/devlink.py shot out.png                       # screenshot
python tools/devlink.py tap X Y [MS]
python tools/devlink.py put LOCAL /sdcard/... | get /sdcard/... LOCAL
python tools/devlink.py log [N]
```

Any python can run it (it re-runs itself with the IDF venv python if a module is missing). Board commands (full list in the DEV LINK banner in main.c):
`ping`, `state` (no `inv` command; the bag is the `@@INV` lines), `give ID [N] [mutation] [silver|gold|emerald] [wet]`, `take`, `inv clear`,
`items`, `photo ID [LEGENDARY]`, `money N|+N|-N`, `hour H [M]`, `day N`, `clock N` (0 = stopped), `sleep`, `save`, `noclip on|off`,
`speed N`, `crops list|grow [N]|water|morning|crows [PCT]`, `tree list|plant ID TX TY [STAGE]|grow [N]|fruit|moss|unshake`, `machines list|done`, `animal list|add ID|feed|ready|day|grass X Y N`,
`forage [list|clear]`, `energy [N]`, `passout`, `bat`, `climate [NAME]`, `temp [PCT]`, `gear [ID|off SLOT|open]`, `skill [NAME XP]`, `museum`, `blacksmith`, `kitchen [ID]`,
`fish` / `fish bite` / `fish hook ID` / `fish mut N` / `fish catch` / `fish book [N]` / `fish junk|chest|trait N|level N|xp N|rig|pots [done]|here`, `rain on|off|auto`,
`animal herd|door INST 0/1|hay INST N|silo N|pipes`, `place ID TX TY`, `craft [list|open|ID]`, `npc list|spawn|clear|minute N|accept|lot SLOT`, `goto MAP [TX TY [INST]]`, `held N`, `swing` (the held tool, at what's in front), `sparkle`, `board [TAB]`, `demand`, `requests`, `capture KIND` (the held item as a camera capture), `ui close`, `dev`, `ls`/`rm`/`mkdir`,
`prof` (per-subsystem µs/frame), `psram N`, `stacks`.

Testing rules:
- **Never test in the user's `save1`.** Reuse one throwaway slot (`load N`). Each `load new` uses up a new slot, and it fails once all 6 are used.
  Ask the user before deleting saves.
- `goto` does NOT write world.txt. `npc minute N` doesn't move the clock (use `hour H`). Auction lots only end when the clock moves.
- The auction hall is the map `auction_house_inside`.
- The Debug Panel (`debugPanel.html`) wraps all of this in buttons. `/api/catalog` reads assets/*/*.c for items, animals and crops.

---

## Content pipeline (Game Tools → firmware / SD card)

- **Items / crops / animals / buildings / machines**: made in their editor tab, then exported as one `.c` into `assets/<kind>/`. The
  file name is the id (lowercase, digits, `_`). Each file holds a round-trip comment such as `// ANIMALS-EDITOR {json}` so the editor can re-open it.
  Crafting recipes are attributes too, on the item they make: `"craft:<ingredient id>" N` + optional `"craft_makes" N` (items.h).
  Gameplay reads **item attributes by name** (`item_attr(item, "sellable")`, `"prop"`, `"tills"`, `"waters"`, `"rod"`, `"fish"`, `"buyable"`, `"bed"`,
  `"shelf"`, `"aquarium"`, `"mut"`…), so a new mechanic is usually a new attribute plus an editor toggle, not per-item C code.
  An item can also carry a `.front` frame bundle (items.h): a prop's front layer, drawn over the player. Beds use it for the sheet
  (BEDS in main.c's PLACEMENT section: walked into from the side, only the frame blocks — `bed_head` / `bed_foot` rows). The Item
  Editor writes it from the Bed row's "Sheet layer PNG…".
- **Furniture list** (`assets/furniture.json` + pictures in `assets/furniture/`, Game Tools' Furniture tab): furniture the user
  wants, each with a name, price, `rotated` (one rotated look), pictures and `does` (what it should do, in their words). When asked
  to build it, make each `"status": "waiting"` piece an item (Item Editor format, `assets/items/<id>.c`, prop + buyable price), give it
  its function, then set `"status": "built"` and a short `"claude"` note saying what you made. An entry with `"item": "<id>"` is a change
  to furniture already in the game (`assets/items/<id>.c`; the tab lists every placeable item there under "Already in the game" with a
  "Give it a new function…" button) — change that item instead of making a new one. Format in the FURNITURE banner in gameTools.html.
- **Fishing** (Stardew style; items.h "Fishing", main.c FISHING + CRAB POTS): fish / junk / crab pot catches / treasure / bait / tackle / rods are items
  made in Game Tools' Fishing tab (it writes Item Editor-format .c files). Conditions are attrs: `fish_seasons` (28-day seasons), `fish_water`
  (pond 1 / river 2 / ocean 4 — the Map Editor's "Water:" on a Fishable asset = TILE_FLAG_RIVER 0x10 / TILE_FLAG_OCEAN 0x20), `fish_map:<name>`,
  `fish_depth`, `fish_level`, `fish_once`, `fish_trait` (minigame tricks), crab pots `pot`/`pot_*`. Gear effects `rod_`/`bait_`/`tackle_` + name.
  The line's bait/tackle (s_rig) and fishing xp are in world.txt (`rig ...`, `fishxp`). Crab pots reuse placed_t.mk_* (MACHINES) for their catch.
  Lava is a 4th water kind: `fish_water` bit 8 = TILE_FLAG_LAVA 0x40 (the Map Editor's Water: Lava); only `rod_lava` rods cast into it and nothing bites there without bit 8. `assets/fishing/settings.c` (k_fishing_cfg) must exist — the link needs it. Item ids are `item_id_t` (uint16_t, items.h) since 2026-10-20 — never store one in a uint8_t.
- **Seasons** (main.c SEASONS, before FARMING): SEASON_DAYS 28, `clock_season()`. Crops: a seed packet's `season` bits (Crops Editor "Grows in") — planted / sold only in season, withers when its season ends (not in building interiors). Assets can have per-season art (Map Editor › Seasons…, `asset.seasons`); Export writes `<map>.<season>.map`. Dev link `season spring|summer|fall|winter`.
- **Market board** (main.c MARKET BOARD; `market_board` action or a prop with `market_board 1`): 50 market types
  (`CAM_TYPES` in pipeline_msgs.h — APPEND ONLY, mirrored as ITEM_TYPES in gameTools.html). Items carry them as
  `types` (bits 0-30) + `types2` (bits 31-61): photo items from the AI, others from the Item Editor's Market types chips.
  Each type's demand (x0.1..x10) is a hash of the save's weather seed and the day — no RAM, no save line — and the item
  sells for the log-average of its types' (`item_price_bonus_pct()`). Photo requests: 3 a day from the same hash,
  only the done bits saved (world.txt `requests DAY BITS`). Capture book: the save's `captures.bin` (`capbook_rec_t`),
  read into PSRAM only while its tab is open. `market_photo_taken()` runs both when the camera makes an item.
- **Trees** (main.c TREES, main/trees.h, Game Tools' Trees tab): `assets/trees/<id>.c` = `k_tree_<id>` + its seed item `<id>_seed`. Stages 0-3 seed/sprout/sapling/bush, 4 grown, 5 stump; art per season (empty = the season before), mossy canopy/stump, log under the grown canopy, 16x16 leaf frames. Baked with the crops in ONE order (`s_farm_order`: a crop's plot or `FARM_MAX + tree`), top row first; nothing else is baked under a tree (dropped stacks, props, farmland check `tree_covers_rect()` / `tree_at()`). Grows in `farm_catch_up()` (`tree_day()`). Fruit trees: 28 days (wild 10), no sapling drops (firmware rule), wood = `hardwood`; shaking drops the fruit as falling items that land as dropped stacks in front of the tree (`tree_drop_fruit()`). The felled canopy and leaves are drawn over the map (`tree_fx_paint_rect()` from `farmfx_paint_rect()`), repainted through `npc_dirty_add()`. Map's own trees: the Map Editor's Tree tool exports `<map>.trees`; seeded once per save (`trees seeded` line). Save line: `tree <id> at tile X Y stage S age A moss M shaken DAY fruit N D hits H`. `tools/slice_trees.py` and `treBuildC()` write the same file — change both together.
- **Forage** (main.c FORAGE, items.h, the Item Editor's Forage card): an item with `forage W` (+ `forage_seasons` bits, `forage_map:<name>`) comes up each 6:00 on the map's Forage tiles, 1-4 a morning, max 8 lying. They're ground items with `.forage` set: saved as `forage <id> at tile X Y` + `forage day D` in the map's .sav, left alone by regrowth; a map with Forage tiles always keeps a save.
- **Energy** (main.c ENERGY; state in PLAYER, the bar in CLOCK — CLOCK_H grew by 16, so MSG_Y moved down): 270 max; `energy N` attr = a use's cost (axe/pickaxe 2, rods 5 by default). 0 = 40% walking speed; -10 = pass out → `passout_travel()` (main loop, like tp_travel) wakes them at `home` (world.txt `home MAP INST X Y`, set by sleeping; none = FIRST_MAP_NAME's middle) the next 6:00, 10% money lost (max 10000), the pass-out note in the UI_SLEEP dialog. Sleep refills (half if exhausted). world.txt `energy N`.
- **Climate** (main.c CLIMATE, inside SEASONS; the Map Editor's "Climate:" picker in the file row): each map is Normal / Hot / Cold / Dry / Lush / Volcanic / Glacial, exported as `<map>.climate` ("climate hot"; Normal = no file; a building inside without one = indoors, anything goes). Items carry a `climate` bit set (1 normal, 2 hot, 4 cold, 8 dry, 16 lush, 32 volcanic, 64 glacial; none = the mild five, CLIMATE_MILD) — seed packets (Crops Editor), tree seeds (Trees tab + slice_trees.py TREE_CLIMATES), forage + any item (Item Editor), fish/pot catches (Fishing tab; fshCondOk mirrors fish_cond_ok). Dry = no rain; Lush = +2 forage, grass regrows 2x; Volcanic/Glacial no rain. Dev `climate [NAME]`.
- **Temperature** (main.c ENERGY › TEMPERATURE; state `s_temp` in PLAYER): Hot/Cold push it to ±100% in 5 game hours, Volcanic/Glacial in 15 min, elsewhere it eases back in 1 h (`temp_protect_pct()` = the hook for future gear). Bar under the energy in the clock panel, only when it matters — the panel's height is dynamic (`s_clock_h`: CLOCK_H or CLOCK_H_MAX; keep-outs and MSG_Y use CLOCK_H_MAX). Sweat beads / shiver from 40% (player_look_t.sweat, x jitter). At 100% pass out (PASSOUT_HEAT/COLD): everything but tools and photo items goes into a BACKPACK (GROUND ITEMS: item `backpack`, `.pack` ground item, `s_pack[]`, map save `backpack ...` lines, regrowth keeps it). world.txt `temp N`. Dev `temp [PCT]`.
- **Gear** (main.c GEAR after CRAFTING; inventory's 3rd tab UI_GEAR): `gear N` (1 hat, 2 jacket, 3 pants, 4 boots), `protect_heat` / `protect_cold` P (% share; a set sums to 100). Worn = out of the bag in `s_gear[]` (world.txt `gear SLOT ID Q`). Hot/Cold: heating slowed by P% (full set: never); Volcanic/Glacial: 15 min → up to 7 h (GEAR_EXTREME_MIN). Drawn by the wardrobe's `gear` kind (tools/wardrobe.py KINDS + compose(gear=...) mirror ward_frame()). Dev `gear [ID|off SLOT|open]`.
- **Skills** (main.c SKILLS after GEAR; inventory's 4th tab UI_SKILLS): farming / foraging / mining (world.txt `skill NAME XP`) + fishing (its own `fishxp`), levels on k_fish_level_xp. XP: harvest (16 ln(0.018 price+1)), fruit, fruit-tree felling = farming; forage pickup, wild-tree felling, axe breakables = foraging; pickaxe breakables = mining (`brk_skill()`). Perks: `skill_roll_quality()` (level/4 extra quality rolls), foraging +level/3 wood, mining +4%/level extra drop. Dev `skill [NAME XP]`.
- **Geodes / blacksmith** (main.c GEODES): `blacksmith` action cracks the held `geode` item for $25 → weighted pick from items with `geode:<id>` (none: stone). Dev `blacksmith`.
- **Museum** (main.c MUSEUM): `museum_shelf` action objects; an empty one opens UI_MUSEUM (bag items with `museum 1`, not donated yet) → baked onto the shelf (icon centred, bottom at the object's middle + 4). Save's `museum.txt` (`donated ID map M at X Y day D`, X Y = the shelf object's top-left). Dev `museum`.
- **Kitchen** (main.c KITCHEN; `kitchen` action, UI_KITCHEN): pages of every item with `food` 1; tap twice to cook. Ingredients = the food's `cook:<item id>` N attributes (none = free, all of them for now). Dev `kitchen [ID]`.
- **Hospital**: passing out (any reason) wakes the player in the map `hospital` beside a random map object with the `bed` action (`hospital_bed_spot()`); no such map = home, as before.
- **Bats** (main.c BATS): 8 pm-5 am outdoors, 1.5%/game minute, `assets/bat_sheet.png` (4 frames 32x32), sfx `bat`.
- **Shops**: any item with `buyable` is for sale; `shop N` (1 Seeds, 2 Build, 3 Ranch, 4 Fish, 5 General) picks the counter, else `shop_kind_of()`'s usual one. The General store is the `general_shop` action. Game Tools' Shop Editor tab edits prices/counters for many items at once.
- **Maps**: Map Editor → Export → `W:\CaptureIt\maps\<name>\<name>.map` (the SD card). The current format is **MAP14** (magic "MAPE"); older ones
  still load. The format notes are in main.c's MAP LOADING banner and around the breakable notes. Tile flags: Tillable, Buildable `0x02`, Fishable `0x04`, Grassy `0x08` (wild grass grows back), River `0x10`, Ocean `0x20`, Lava `0x40`, Forage `0x80` (key O; forageables come up there).
  A changed sound bundle needs the map re-exported.
- The Asset Explorer in the Map Editor links to the real `assets/` folder. New map art goes in `assets/map/` (not compiled in).
- **Tools** (main.c TOOL SWING, items.h "Tools", the Item Editor's Tool use box + Swing tab): `tool 1` swings when used — the item's `use` bundle
  is its 16x32 swing art on the player (1 / 3 / 4 frames = every way / down, up, sideways / down, up, left, right; behind them facing up), plus
  the swipe (`assets/fx/tool_swipe.png`, `tool_swipe 0` = off) and `tool_sfx:<wav>`. The hit on a breakable / farmland lands mid-swing
  (TOOL_HIT_MS). `tool_power N` = hits a swing; `counts_as:<id>` = breakables needing <id> take it too. Other effects in `assets/fx/`:
  `fish_splash.png` (the bobber landing), `new_item.png` (the sparkle over the head on every item gained: `newitem_sparkle()`).
- **Some editor code mirrors C code**: TOOL_SWIPE_AT / TOOL_ART_PICK / TOOL_SWIPE_* / TOOL_ART_MAX_* (main.c TOOL SWING), FSH_TRAITS / FSH_FX / FSH_CFG / fshCondOk / fshWeight / fshFx (main.c FISHING, items.h), MUTATIONS / mutPx / mutOdds, ROD_STATS, PROP_ART_MAX (64), ITEM_SPRINKLER_MAX / ITEM_SCARECROW_MAX (6 / 15), ITEM_CRAFT_IN_MAX (6) and BUILTIN_ACTIONS in gameTools.html
  are hand ports of items.c / main.c. Change both together. Same for `random_outfit()` / `recolor()` / `compose()` / `Rng` in tools/wardrobe.py
  and `ward_random()` / `ward_shade_565()` / `ward_compose()` / `ward_rand()` in main.c (the preview must draw the same person as the board for a seed).
- **Needs You list** (`assets/needs_you.json`, shown in Game Tools' Needs You tab with a count badge). Whenever you make something
  that waits on the user, add a task there in the same change: placeholder art to swap (`"kind": "art"`), a number or price you had
  to guess (`"data"` / `"decision"`), a WAV to put on the card (`"sound"`), something only testable on the board (`"test"`). List
  the files (paths under assets/; `../` = project folder, `sd:` = the card's CaptureIt folder) and, for Item Editor placeholders,
  `"marker": "Placeholder art"` (the comment the editor drops when the user re-exports, so the tab can tell it's replaced).
  Format + rules are in the NEEDS YOU banner in gameTools.html. The user's ticks, `done` and `reply` answers are written back to
  the file: read the `reply` of related tasks before working on a feature, act on answers, and only remove tasks the user marked done.
- Save files are text lines (e.g. `crop id at tile x y grown g`, `animal ... variant V age A`, `machine at tile x y item ID ...`).
  Keep older lines loading when you add fields (`MAPSAVE_WORDS` = 20 words max per line).

---

## Testing without hardware

- **Editor JS**: there's no Node. Use headless Chrome (`C:\Program Files\Google\Chrome\Application\chrome.exe`):
  regex-extract `^function NAME\(.*?^\}` blocks from gameTools.html into a test page, or copy the whole page and append a test `<script>`
  (stub `confirm`/`alert`, or it hangs). Run `chrome --headless=new --enable-logging=stderr --v=0 --virtual-time-budget=15000 --dump-dom file:///...`
  and read PASS/FAIL from the DOM; JS errors show as `INFO:CONSOLE ... Uncaught` in stderr.
- **Firmware screens**: render Python/Pillow mock-ups, or use `devlink.py shot` on the real board.
- Many systems (animals, machines, aquarium, fishing, market) were built and compiled but **not yet tested on the device**. Say so; don't claim they work.

---

## Gotchas (they've cost time before)

- **Never put patch code in a bash heredoc.** `\n` and `\0` get mangled and once corrupted C string literals. Use Edit for small changes,
  or Write a script to the scratchpad and run it. If a file gets mangled, restore it from a backup; don't regex-repair it.
- **Line endings**: main.c is LF; gameTools.html, items.c and items.h are CRLF. Keep whatever a file has (Edit does; in Python use `newline=''`).
  Git has `core.autocrlf false`.
- **VS Code CMake Tools** adds any new `.c` under main/ to the first `file(GLOB ...)` line of main/CMakeLists.txt. Re-check that file after creating sources.
- `Copy-Item` keeps the old timestamp, so a restored file may not rebuild. Touch it, and grep the `.bin` for an expected string.
- `cat > file` with no heredoc waits on stdin and hangs the tool.
- Git refuses to run on the FAT SD card ("dubious ownership").

---

## Repo / git

- GitHub: `RareTree924/CaptureIt` (public, branch `main`). **Commit or push only when the user asks.**
- Gitignored: `build/`, `managed_components/`, `.cache/`, `sdkconfig.old`, `sdkconfig.before-16mb`, `*.log`, `secrets.h`,
  `tools/gemini_key.txt`, `assets/Recycle Bin/`. Never commit keys.
- Related projects: `c:\projects\ESP32CamFirmware` (the CAM), `c:\projects\Tetris` (a second, minimal game for the same S3 board;
  github RareTree924/Tetris; pull first because another tool syncs a journal into it), `c:\projects\FASTSAM` (the old iPhone CamPipe app, no longer used).
