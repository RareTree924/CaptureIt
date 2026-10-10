# Items

Every `.c` file in this folder is one item, exported by the Game Tools
**Item Editor** (gameTools.html). The file name is the item's id (`wood.c` → `"wood"`, symbol
`k_item_wood`) — don't rename files by hand.

Adding or removing a file here is picked up on the next `idf.py build`
(CMake re-globs the folder and regenerates `items_manifest.inc`).

Maps refer to drops by this id, so a map can be exported before or after
the item exists: an unknown id is logged at map load and that drop is
skipped, instead of the whole map failing to load.
