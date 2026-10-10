# Machines

Every `.c` file in this folder is one machine (Stardew's keg, cheese press,
loom...), saved by the Game Tools **Machines Editor**. The file name is the
machine's id (`cheese_press.c` → `"cheese_press"`), and each file also makes
the prop item of the same id that places it. Don't rename files by hand, and
don't give an item in `../items/` the same id (the build stops and says which).

A machine is 16x32: its bottom tile is solid, its top half overhangs the tile
above and the player walks behind it. It's sold in the Build shop (its price
in the editor). In game: hold a recipe's input and tap the machine; after the
recipe's days (steps of 0.5 — half a day is 12 game hours) the output's icon
floats on top of it; tap it to take the output. Game time keeps running on
other maps and while you sleep. Empty hands on an empty machine pick it up.

The inputs and outputs are ordinary items (`../items/`, made in the Item
Editor) — make the output item (e.g. cheese) before you expect to get it.
See `main/machines.h` for what the editor writes.
