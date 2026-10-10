# Animals

Every `.c` file in this folder is one farm animal, saved by the Game Tools
**Animals Editor** (gameTools.html → Animals Editor). The file name is the
animal's id (`cow.c` → animal `"cow"`), and each file also makes the item of
the same id that lets the animal out (the Ranch shop sells it). Don't rename
files by hand, and don't give an item in `../items/` the same id (the build
stops and says which).

Adding or removing a file here is picked up on the next `idf.py build`.
Everything in these files is `const`, so on the ESP32-S3 it stays in flash and
uses no RAM.

In game: buy an animal at the Ranch shop (any map object with the
"Ranch shop" action — Map Editor → the asset's Actions…), hold it and tap open
ground to let it out. Animals wander, eat grass once a day (or hay — hold it
and tap them), sleep from 7 pm to 6 am and make their sound now and then
(a WAV with that name in `sounds/sound effects` on the SD card). Fed animals
make their product: dropped on the ground (eggs, truffles, rabbit wool), or
taken off them with a tool (shears: wool; milk pail: milk).

Grass: hold grass starter and tap Tillable ground. It spreads by itself
overnight; a scythe cuts it (half the time into hay). The grass art is
`assets/grass.png` (four 16x16 tiles: 1 tuft, 2, 3, full).

The products, hay and tools are ordinary items in `../items/` (egg, milk,
goat_milk, wool, truffle, rabbits_foot, hay, scythe, shears, milk_pail,
grass_starter) with placeholder art — open them in the Item Editor to give
them real art. See `main/animals.h` for what the editor writes.
