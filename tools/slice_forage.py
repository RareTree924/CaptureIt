"""One-off: cuts the Stardew forage sheet (Spriters Resource rip in Downloads:
"Environment - Forage.png") into forage items, assets/items/<id>.c, and the
bat sheet ("Miscellaneous - Bat.png") into assets/bat_sheet.png.

    python tools/slice_forage.py [--forage PNG] [--bat PNG] [--preview out.png] [--write] [--force]

--preview draws every forage icon with its id; --write writes the files
(existing ones are left alone unless --force).

The items are in the exact format gameTools.html's Item Editor saves, so
they open there to be changed like any other. Each has "forage W" (its
weight among the forageables that can come up), "forage_seasons" (bits: 1
spring, 2 summer, 4 fall, 8 winter; none = all year) — FORAGE in main.c
puts them on the Map Editor's Forage tiles every morning.

Layout of "Forage.png" (160x220): 7 rows of 6 icons, each at most 16x16 at
1x (CELL_X / CELL_Y are where each column / row's art is; it's trimmed to
its opaque pixels and centred in a 16x16 icon). Row 6 (sap,
fiber, wood, hardwood, stone, mixed seeds) and the tree seeds in row 5 aren't
forage here (wood, hardwood and the tree seeds are items already); the
coconut is the Palm Tree's seed and the truffle is the pig's.

"Bat.png" (256x64) is drawn at 4x: 4 frames of 16x16 in 64x64 cells. Halved
it's 4 frames of 32x32 side by side (BATS in main.c). Its black is turned
into a near-black purple (opaque black is see-through to the game).
"""
import argparse, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DL = os.path.join(os.path.expanduser('~'), 'Downloads')
FORAGE_PNG = os.path.join(DL, 'PC _ Computer - Stardew Valley - Environment - Forage.png')
BAT_PNG = os.path.join(DL, 'PC _ Computer - Stardew Valley - Miscellaneous - Bat.png')

CELL_X = [(7, 22), (34, 52), (61, 79), (86, 103), (108, 128), (132, 151)]   # each column's art (x0, x1 inclusive)
CELL_Y = [(6, 24), (36, 52), (66, 83), (98, 112), (127, 144), (157, 173), (187, 205)]
ICON = 16
BAT_COLOUR = (26, 18, 34)

SP, SU, FA, WI = 1, 2, 4, 8          # forage_seasons bits (FORAGE in main.c)
ALL = 0
# pipeline_msgs.h CAM_TYPES (market types): bit numbers
RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, PINK, BROWN, BLACK, WHITE = range(10)
ROUND, SHINY, FOOD, PLANT, COLLECTIBLE = 11, 16, 32, 44, 48

# (row, col), id, name, sell price, seasons, weight, market types
FORAGE = [
    ((0, 0), 'snow_yam',         'Snow Yam',         100, WI,      10, [BROWN, FOOD]),
    ((0, 1), 'wild_horseradish', 'Wild Horseradish', 50,  SP,      10, [WHITE, FOOD]),
    ((0, 2), 'spring_onion',     'Spring Onion',     8,   SP,      10, [GREEN, FOOD]),
    ((0, 3), 'cave_carrot',      'Cave Carrot',      25,  ALL,     4,  [ORANGE, FOOD]),
    ((0, 4), 'crystal_fruit',    'Crystal Fruit',    150, WI,      6,  [BLUE, SHINY, FOOD]),
    ((0, 5), 'winter_root',      'Winter Root',      70,  WI,      10, [BROWN, FOOD]),
    ((1, 0), 'spice_berry',      'Spice Berry',      80,  SU,      10, [RED, ROUND, FOOD]),
    ((1, 1), 'grape',            'Grape',            80,  SU,      8,  [PURPLE, ROUND, FOOD]),
    ((1, 2), 'salmonberry',      'Salmonberry',      5,   SP,      8,  [RED, ROUND, FOOD]),
    ((1, 3), 'blackberry',       'Blackberry',       20,  FA,      10, [PURPLE, ROUND, FOOD]),
    ((1, 4), 'frost_berry',      'Frost Berry',      60,  WI,      5,  [BLUE, ROUND, FOOD]),
    ((1, 5), 'wild_plum',        'Wild Plum',        80,  FA,      10, [PURPLE, ROUND, FOOD]),
    ((2, 0), 'sweet_pea',        'Sweet Pea',        50,  SU,      10, [PINK, PLANT]),
    ((2, 1), 'daffodil',         'Daffodil',         30,  SP,      10, [YELLOW, PLANT]),
    ((2, 2), 'dandelion',        'Dandelion',        40,  SP,      10, [YELLOW, PLANT]),
    ((2, 3), 'crocus',           'Crocus',           60,  WI,      10, [PURPLE, PLANT]),
    ((2, 4), 'holly',            'Holly',            80,  WI,      8,  [RED, GREEN, PLANT]),
    ((2, 5), 'fiddlehead_fern',  'Fiddlehead Fern',  90,  SU,      6,  [GREEN, PLANT, FOOD]),
    ((3, 0), 'common_mushroom',  'Common Mushroom',  40,  SP | FA, 8,  [BROWN, FOOD]),
    ((3, 1), 'morel',            'Morel',            150, SP,      4,  [BROWN, FOOD]),
    ((3, 2), 'chanterelle',      'Chanterelle',      160, FA,      4,  [ORANGE, FOOD]),
    ((3, 3), 'red_mushroom',     'Red Mushroom',     75,  SU | FA, 5,  [RED, FOOD]),
    ((3, 4), 'purple_mushroom',  'Purple Mushroom',  250, FA,      2,  [PURPLE, FOOD]),
    ((3, 5), 'magma_cap',        'Magma Cap',        400, ALL,     1,  [PINK, FOOD, COLLECTIBLE]),
    ((4, 0), 'hazelnut',         'Hazelnut',         90,  FA,      8,  [BROWN, ROUND, FOOD]),
    ((4, 1), 'cactus_fruit',     'Cactus Fruit',     75,  SU,      4,  [GREEN, FOOD]),
    ((4, 3), 'ginger',           'Ginger',           60,  SU | FA, 4,  [YELLOW, FOOD]),
    ((4, 5), 'moss',             'Moss',             5,   ALL,     6,  [GREEN, PLANT]),
    ((5, 4), 'golden_walnut',    'Golden Walnut',    250, ALL,     1,  [YELLOW, SHINY, COLLECTIBLE]),
]
SEASON_NAMES = [(SP, 'spring'), (SU, 'summer'), (FA, 'fall'), (WI, 'winter')]
# Where each comes up: its "climate" bits (main.c CLIMATE: 1 normal, 2 hot, 4 cold, 8 dry, 16 lush; none = any)
N, H, C, D, L = 1, 2, 4, 8, 16
CLIMATE = {'snow_yam': C, 'wild_horseradish': N | C, 'spring_onion': N | L, 'crystal_fruit': C, 'winter_root': N | C, 'spice_berry': N | H,
           'grape': N | H | L, 'salmonberry': N | L, 'blackberry': N | L, 'frost_berry': C, 'wild_plum': N | L, 'sweet_pea': N | L, 'daffodil': N,
           'dandelion': N | D, 'crocus': N | C, 'holly': N | C, 'fiddlehead_fern': L, 'common_mushroom': N | L, 'morel': N | L, 'chanterelle': N | L,
           'red_mushroom': N | L, 'purple_mushroom': L, 'magma_cap': H, 'hazelnut': N | C, 'cactus_fruit': H | D, 'ginger': H | L, 'moss': N | C | L,
           'golden_walnut': H | L}


def icon_at(sheet, row, col):
    """The art in that cell, trimmed and centred in a 16x16 icon."""
    (x0, x1), (y0, y1) = CELL_X[col], CELL_Y[row]
    box = (x0 - 3, y0 - 3, x1 + 4, y1 + 4)
    cell = sheet.crop(box)
    solid = cell.getchannel('A').point(lambda a: 255 if a >= 128 else 0)
    bb = solid.getbbox()
    art = cell.crop(bb)
    if art.width > ICON or art.height > ICON:
        raise SystemExit(f'cell {row},{col} is {art.width}x{art.height} — bigger than {ICON}x{ICON}')
    out = Image.new('RGBA', (ICON, ICON), (0, 0, 0, 0))
    out.paste(art, ((ICON - art.width) // 2, (ICON - art.height) // 2))
    return out


def pack565(img):   # slice_trees.py's
    px = []
    for (r, g, b, a) in img.convert('RGBA').getdata():
        if a < 128:
            px.append(0)
            continue
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        px.append(0x0841 if v == 0 else v)   # CROP_NEAR_BLACK: opaque black isn't see-through
    return px


def c_array(px):   # gameTools.html u16FrameToCArray()
    rows = []
    for i in range(0, len(px), 12):
        rows.append('    ' + ', '.join(f'0x{v:04x}' for v in px[i:i + 12]) + ',')
    return '\n'.join(rows)


def item_c(fid, name, sell, seasons, weight, types, icon):
    px = pack565(icon)
    lo = sum(1 << t for t in types if t < 31)
    hi = sum(1 << (t - 31) for t in types if t >= 31)
    when = ', '.join(n for bit, n in SEASON_NAMES if seasons & bit) if seasons else 'all year'
    attrs = [('sellable', sell), ('quality', 1)]
    if lo: attrs.append(('types', lo))
    if hi: attrs.append(('types2', hi))
    attrs.append(('forage', weight))
    if seasons: attrs.append(('forage_seasons', seasons))
    if CLIMATE.get(fid): attrs.append(('climate', CLIMATE[fid]))
    lines = [
        f'// AUTO-GENERATED by gameTools.html (Item Editor) — "{name}"',
        f'// Lives in assets/items/ as {fid}.c — the file name is the item id, keep it.',
        f'// Rebuild and it\'s in the game; maps drop it by the id "{fid}".',
        f'// Forage ({when}): comes up on the Map Editor\'s Forage tiles (FORAGE in main.c). Art: Stardew Valley\'s forage sheet.',
        '#include "items.h"',
        '',
        f'static const uint16_t k_{fid}_passive_pixels[{len(px)}] = {{',
        c_array(px),
        '};',
        '',
        '',
        f'static const item_attr_t k_{fid}_attrs[] = {{',
        *[f'    {{ "{n}", {v} }},' for n, v in attrs],
        '};',
        '',
        f'const item_asset_t k_item_{fid} = {{',
        f'    .id = "{fid}",',
        f'    .display_name = "{name}",',
        '    .max_stack = 99,',
        f'    .passive = {{ .w={ICON}, .h={ICON}, .frame_count=1, .interval_ms=150, .loop_count=-1, .pixels=k_{fid}_passive_pixels }},',
        '    .use = { .frame_count = 0 },',
        f'    .attrs = k_{fid}_attrs,',
        f'    .attr_count = {len(attrs)},',
        '};',
    ]
    return '\n'.join(lines) + '\n'


def bat_sheet(path):
    src = Image.open(path).convert('RGBA')
    if src.size != (256, 64):
        raise SystemExit(f'{path} is {src.size[0]}x{src.size[1]}, expected 256x64 (4 frames at 4x)')
    out = src.resize((128, 32), Image.NEAREST)
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            px[x, y] = BAT_COLOUR + (255,) if a >= 128 else (0, 0, 0, 0)
    return out


def preview(icons, path):
    S, C = 4, 6
    rows = (len(icons) + C - 1) // C
    img = Image.new('RGBA', (C * 140, rows * (ICON * S + 18)), (90, 140, 70, 255))
    d = ImageDraw.Draw(img)
    for k, (fid, icon) in enumerate(icons):
        x, y = (k % C) * 140, (k // C) * (ICON * S + 18)
        img.alpha_composite(icon.resize((ICON * S, ICON * S), Image.NEAREST), (x + 4, y + 2))
        d.text((x + 4, y + ICON * S + 4), fid, fill=(255, 255, 255, 255))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--forage', default=FORAGE_PNG)
    ap.add_argument('--bat', default=BAT_PNG)
    ap.add_argument('--preview')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    sheet = Image.open(a.forage).convert('RGBA')
    icons = [(spec[1], icon_at(sheet, *spec[0])) for spec in FORAGE]
    if a.preview:
        preview(icons, a.preview)
        print('preview ->', a.preview)
    if a.write:
        idir = os.path.join(ROOT, 'assets', 'items')
        jobs = [(os.path.join(idir, f'{s[1]}.c'), item_c(*s[1:], icon)) for s, (_, icon) in zip(FORAGE, icons)]
        for path, text in jobs:
            if os.path.exists(path) and not a.force:
                print('kept (exists):', os.path.relpath(path, ROOT))
                continue
            with open(path, 'w', newline='\n', encoding='utf-8') as fh:
                fh.write(text)
            print('wrote', os.path.relpath(path, ROOT))
        bat_path = os.path.join(ROOT, 'assets', 'bat_sheet.png')
        if os.path.exists(bat_path) and not a.force:
            print('kept (exists):', os.path.relpath(bat_path, ROOT))
        else:
            bat_sheet(a.bat).save(bat_path)
            print('wrote', os.path.relpath(bat_path, ROOT))


if __name__ == '__main__':
    main()
