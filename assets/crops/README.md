# Crops

Every `.c` file in this folder is one crop, saved by the Game Tools
**Crops Editor** (gameTools.html → Crops Editor → Make new crop). The file name
is the crop's id (`tomato.c` → crop `"tomato"`), and each file also makes two
items: `tomato` (the harvest) and `tomato_seeds` (the seed packet). Don't
rename files by hand, and don't give an item in `../items/` one of those ids
(the build stops and says which).

Adding or removing a file here is picked up on the next `idf.py build`.
Everything in these files is `const`, so on the ESP32-S3 it stays in flash and
uses no RAM.

In game: hold the hoe and tap a tile to turn it into farmland (only ground
whose 16x16 asset is ticked **Tillable** in the Map Editor, with nothing on
top of it — re-export the map after ticking it). Then hold a seed packet and
tap the farmland to plant it; tap a ripe crop to harvest it. The farmland art
is `assets/farmland_dry.png`, `farmland_watered.png` and the winter
`farmland_winter_dry.png` / `farmland_winter_watered.png`: each Stardew's 4x4
hoed-dirt sheet (64x64, 16 cells of 16x16), one cell per way a tile joins its
neighbours (main.c `k_soil_cell`) — replace them to change the look. Growth counts game days (the clock in the corner). Seeds come from the seed
shop — every crop here whose seed packet has a price ("Seed packet costs") is
for sale in it automatically; open it by tapping any map object that has the
"Seed shop" action (Map Editor → the asset's Actions…) — or from anywhere
items come from, like a breakable's drop list.
