# Wardrobe

Everyone in the game (the player and the market's shoppers) is drawn from these layers, stacked
the way Stardew Valley draws its farmer. Add a PNG to a folder and rebuild: it's in the Customize
screen and the shoppers' random outfits. The file name is its name. `tools/slice_stardew.py` made the
first set from the Stardew sheets; `python tools/wardrobe.py --preview out.png` draws random people
from whatever is here, without a build.

Strips are cells stacked top to bottom, **directions in this order: down, right, left, up**.
Transparent (or pure black) pixels are see-through.

| Folder | Cell | PNG size | Rows |
|---|---|---|---|
| `bodies/` | 16x32 | 64 x 384 | 4 columns = the 4 walking frames (1 = standing). Rows 0-3: the body (no arms). Rows 4-7: the arms, drawn over the shirt. Rows 8-11: the arms raised, carrying something. |
| `pants/` | 16x32 | 64 x 128 (or 256) | One per body frame, in the same place. Rows 0-3; optional rows 4-7 are a second fit, worn by bodies whose name starts with `female`. |
| `shirts/` | 8x8 | 8 x 32 | One per direction, drawn at (4, 14) on the body. |
| `hair/` | 16x32 | 16 x 96 (or 128) | down, right, up (and left; without it, left is right mirrored). Drawn on the body. |
| `accessories/` | 16x16 | 16 x 32 (or 16) | down, right (left: mirrored). None from behind. Drawn at (0, 2). |
| `hats/` | 20x20 | 20 x 80 | down, right, left, up. Drawn at (-2, -4): a brim may stick out of the body's 16 px. |
| `gear/` | 20x36 | 80 x 144 | Climate gear, worn by the player only (main.c GEAR): named after its item (`thermal_jacket.png`). A whole composed frame a cell — 4 columns = the walking frames, rows down, right, left, up — drawn at (0, 0) over the outfit, in place of its hat / shirt / pants (boots go over the pants); a jacket's colour goes on the sleeves. Never in Customize or on shoppers. `tools/make_gear.py` drew the first ones. |

Everything above the waist moves with the frame's head: each body frame's "bob" is how much lower
its head is than a Stardew body's (whose head starts at row 4).

## Colours

Four colours, each any colour (Customize's bars) or the art's own: **skin, hair, shirt, pants**.

- Body: its most-used colour and its shading ramp are the **skin**. Colours in the arm rows that
  aren't on the body are the **sleeves**, which take the shirt's colour.
- Hair, shirts, pants: every colour takes the item's colour. Draw them in greys (like Stardew's) or
  in colour: either works, the shading is kept. A coloured shirt (most of Stardew's) is worn as
  drawn when it's picked, and by the shoppers; Customize's bars still recolour it.

## Who wears what

`genders.json` (set in Game Tools' **Wardrobe** tab, one click a piece) tags each piece male, neutral
or female. Every list is built male first, neutral in the middle, female last (Customize's pages
go in that order; your own character can wear anything). Each shopper is a man or a woman (from
their seed) and only wears their own pieces and the neutral ones. Untagged pieces count as
neutral; an untagged body goes by its name (`female*` = female, else male).

Customize: `<` `>` step through a row; tapping the row's number opens the whole list, a page of
24 at a time, each drawn on your character.
- Accessories: grey art (beards, moustaches) takes the hair colour; coloured art stays as drawn.
- Hats: always as drawn.
