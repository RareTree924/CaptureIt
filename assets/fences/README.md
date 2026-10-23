# Fences, gates and pipes

Every `.c` file in this folder is one fence, gate or pipe, saved by the Game
Tools **Farm** tab → **Fences & pipes**. The file name is the piece's id
(`wood_fence.c` → `"wood_fence"`), and each file also makes the prop item of
the same id that places it (the Build shop sells it). Don't rename files by
hand, and don't give an item in `../items/` the same id (the build stops and
says which).

A piece stands on one tile. It joins the pieces next to it: it has 16 looks,
one for each set of sides it joins on (+1 up, +2 right, +4 down, +8 left), and
shows the right one by itself. Fences and gates join each other; pipes join
pipes and the barns, coops and silos they touch. A 16×32 piece's top half
stands over the tile above, and the player walks behind it.

- **Fence** — solid: the player and the animals can't cross it.
- **Gate** — tap it holding anything to open or shut it; open, the player and
  the animals walk through. A gate has 16 more looks, open.
- **Pipe** — walked over. A line of pipes from a silo to a barn or coop
  (touching both, side on) fills that building's troughs with the silo's hay
  every morning, and as soon as they're joined.

Empty hands pick a piece back up. See `main/fences.h` for what the editor writes.

## Swapping in your own art

The three here (wood_fence, wood_gate, hay_pipe) have placeholder art (the
barns, coops, silo and well in `../buildings/` are your Stardew art). To replace it:

1. Game Tools → Farm → Fences & pipes (or Barns, coops & silos) → **Open .c…**
   and pick the file (e.g. `wood_fence.c`).
2. **Save as PNG…** — it lands in Downloads (a barn also gives `barn_open.png`,
   the same picture with its animal door open).
3. Paint over it in any paint program. Keep the size and the grid.
4. **Load sheet…** / **Load picture…** (and **Load open look…**) your PNG, then
   **Save**. It writes over the same file and keeps every setting.
5. Rebuild and flash.

A barn of a different size works too; check its doors and footprint on the
picture afterwards. Barns already built in a save that no longer fit where they
stand aren't shown. A barn whose animal door is a see-through opening in its
picture (Stardew's) gets **Find the opening**, then a **shut** and an **open**
look for it (a door piece, just the door, or the whole picture again).

A pipe beside a farm building carries on right up to the building's wall by
itself, so its art only needs to reach its own tile's edge.

The barn and coop insides (`maps/small_barn_inside.map` … `large_coop_inside.map`, copied
to the SD card) are placeholders as well: open one in the Map Editor and paint
over it, or make your own inside. It needs a **Building exit** teleporter by its
door (the animals use it too), and your trough art with the **Trough** action
(one tile per animal). Export it to `maps/<name>/<name>.map` on the card. The
hay drawn in the troughs is the Hay item's art (Item Editor).
