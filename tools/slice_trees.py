"""One-off: cuts the Stardew tree sheets (Spriters Resource rips in Downloads:
"Environment - Trees.png" and "Environment - Fruit Trees.png") into Trees
Editor files, assets/trees/<id>.c, plus the fruit items (assets/items/<fruit>.c).

    python tools/slice_trees.py [--trees PNG] [--fruit PNG] [--preview out.png] [--write]

--preview draws every tree as the game would (each season, each stage, the
grown tree on its log) into one PNG to check the cuts; --write writes the files
(existing ones are left alone unless --force).

The files are in the exact format gameTools.html's Trees Editor saves (main/trees.h,
the TREES-EDITOR comment), so they open there to be changed like any other.

Layout of "Trees.png" (486x1280): 8 bands of 160 rows, one kind of tree each
(oak, maple, pine, mahogany, vine, weeping, fiddlehead; the last band has four
one-off trees). In a band a tree's season is a 48-wide set at x = 0 / 146 / 292
/ 438 (spring / summer / fall / winter; a missing one = the season before):
  canopy   rows 0..95 of the set (trimmed to its art)
  y+96     bush 16x32 (x+0) | 2 leaves 16x16 (x+16, y+96 and y+112) | stump 16x32 (x+32)
  y+128    sprout 16x16 (x+0) | sapling (x+16) | seed (x+32)
  y+144    3 logs 16x16 (the one under the standing tree)
A mossy canopy sits 50 px left of the next season's set (x = 96 / 242 / 388 for
spring / summer / fall), its mossy stump at its x+32, y+96.

"Fruit Trees.png" (432x720): a band of 80 rows per tree (cherry, apricot,
orange, peach, pomegranate, apple, [bare saplings — skipped], banana, mango),
cells 48 wide: 0 sapling item (top) + stage 1 (bottom), 1-3 stages 2-4,
4-7 the grown tree spring..winter, 8: leaves (16x16 each, spring/summer/fall
at y+0), the fruit's icon (x+16, y+24) and the stump (x+16, y+56, 16x32).
Everything stands on the cell's bottom.
"""
import argparse, json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DL = os.path.join(os.path.expanduser('~'), 'Downloads')
TREES_PNG = os.path.join(DL, 'PC _ Computer - Stardew Valley - Environment - Trees.png')
FRUIT_PNG = os.path.join(DL, 'PC _ Computer - Stardew Valley - Environment - Fruit Trees.png')

SET_X = [0, 146, 292, 438]          # spring, summer, fall, winter sets in a band
MOSS_X = [96, 242, 388, None]       # mossy canopies (none in winter)

# id, name, seed name, band, {season: set x or None}, {season: moss x}, seed sell price
WILD = [
    ('oak_tree',      'Oak Tree',      'Acorn',           0, SET_X,                  MOSS_X, 5),
    ('maple_tree',    'Maple Tree',    'Maple Seed',      1, SET_X,                  MOSS_X, 5),
    ('pine_tree',     'Pine Tree',     'Pine Cone',       2, [0, None, 292, 438],    [96, None, 388, None], 5),
    ('mahogany_tree', 'Mahogany Tree', 'Mahogany Seed',   3, SET_X,                  [None] * 4, 100),
    ('vine_tree',     'Vine Tree',     'Vine Seed',       4, [0, None, 292, 438],    [96, None, 388, None], 10),
    ('weeping_tree',  'Weeping Tree',  'Weeping Seed',    5, [0, None, 292, 438],    [96, None, 388, None], 10),
    ('fiddlehead_tree', 'Fiddlehead Tree', 'Fiddlehead Seed', 6, [0, None, 292, 438], [None] * 4, 10),
    ('palm_tree',     'Palm Tree',     'Coconut',         7, [0, None, None, None],  [None] * 4, 10),
    ('island_palm',   'Island Palm',   'Island Coconut',  7, [96, None, None, None], [None] * 4, 10),
    ('mushroom_tree', 'Mushroom Tree', 'Mushroom Spore',  7, [292, None, None, None], [388, None, None, None], 20),
    ('mystic_tree',   'Mystic Tree',   'Mystic Seed',     7, [438, None, None, None], [None] * 4, 50),
]

# id, name, band, fruit id, fruit name, fruit sell, fruit seasons bit, sapling buy price, colour type
FRUIT = [
    ('cherry_tree',      'Cherry Tree',      0, 'cherry',      'Cherry',      80,  1, 3400, 0),
    ('apricot_tree',     'Apricot Tree',     1, 'apricot',     'Apricot',     50,  1, 2000, 1),
    ('orange_tree',      'Orange Tree',      2, 'orange',      'Orange',      100, 2, 4000, 1),
    ('peach_tree',       'Peach Tree',       3, 'peach',       'Peach',       140, 2, 6000, 6),
    ('pomegranate_tree', 'Pomegranate Tree', 4, 'pomegranate', 'Pomegranate', 140, 4, 6000, 0),
    ('apple_tree',       'Apple Tree',       5, 'apple',       'Apple',       100, 4, 4000, 0),
    ('banana_tree',      'Banana Tree',      7, 'banana',      'Banana',      150, 2, 0,    2),
    ('mango_tree',       'Mango Tree',       8, 'mango',       'Mango',       130, 2, 0,    1),
]
TYPE_ROUND, TYPE_FOOD = 11, 32   # pipeline_msgs.h CAM_TYPES
# Where each tree grows: the seed's "climate" bits (main.c CLIMATE: 1 normal, 2 hot, 4 cold, 8 dry, 16 lush; 0 = any)
_N, _H, _C, _D, _L = 1, 2, 4, 8, 16
TREE_CLIMATES = {'oak_tree': _N | _C | _L, 'maple_tree': _N | _C, 'pine_tree': _N | _C | _D, 'mahogany_tree': _H | _L, 'vine_tree': _N | _L,
                 'weeping_tree': _N | _L, 'fiddlehead_tree': _N | _L, 'palm_tree': _H | _D, 'island_palm': _H | _L, 'mushroom_tree': _N | _L,
                 'mystic_tree': 0, 'cherry_tree': _N | _C, 'apricot_tree': _N | _H | _D, 'orange_tree': _N | _H, 'peach_tree': _N | _H,
                 'pomegranate_tree': _H | _D, 'apple_tree': _N | _C, 'banana_tree': _H | _L, 'mango_tree': _H | _L}

WILD_NUM = dict(growDays=10, hits=10, bushHits=2, stumpHits=5, woodMin=25, woodMax=35, seedMax=3, bushWood=5,
                stumpWoodMin=3, stumpWoodMax=5, shakeSeedMax=2, mossPct=5)
FRUIT_NUM = dict(WILD_NUM, growDays=28, mossPct=0, seedMax=0, shakeSeedMax=0,   # (fruit trees never drop saplings)
                 fruitDays=3, fruitMax=3)


def bbox(im, box):
    """Opaque bounding box of im inside box (x0,y0,x1,y1), or None."""
    b = im.crop(box).getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
    return None if b is None else (box[0] + b[0], box[1] + b[1], box[0] + b[2], box[1] + b[3])


def cut(im, x, y, w, h):
    return im.crop((x, y, x + w, y + h))


def trim_rows(img):
    """img with its see-through rows above the art taken off (it stands on its bottom)."""
    b = img.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
    if b is None:
        return None
    return img.crop((0, b[1], img.width, img.height))


def empty(img):
    return img is None or img.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox() is None


def wild_tree(sheet, spec):
    tid, name, seed_name, band, sets, moss, seed_price = spec
    by = band * 160
    art = {}
    for s in range(4):
        x = sets[s]
        if x is None:
            continue
        b = bbox(sheet, (x, by, x + 48, by + 96))
        canopy = cut(sheet, x, b[1], 48, b[3] - b[1])            # bottom = the trunk's end
        art[f'grown_{s}'] = canopy
        art[f'log_{s}'] = cut(sheet, x + 16, by + 144, 16, 16)
        art[f'stump_{s}'] = trim_rows(cut(sheet, x + 32, by + 96, 16, 32))
        art[f'leaf_{s}'] = cut(sheet, x + 16, by + 96, 16, 32)  # 2 frames, stacked (turned side by side below)
        for k, (dx, dy, h) in enumerate([(32, 128, 16), (0, 128, 16), (16, 128, 16), (0, 96, 32)]):
            art[f'stage_{s}_{k}'] = cut(sheet, x + dx, by + dy, 16, h)
        mx = moss[s]
        if mx is not None:
            b = bbox(sheet, (mx, by, mx + 48, by + 96))
            art[f'moss_{s}'] = cut(sheet, mx, b[1], 48, b[3] - b[1])
            st = cut(sheet, mx + 32, by + 96, 16, 32)
            if not empty(st):
                art[f'stumpmoss_{s}'] = trim_rows(st)
    for key in list(art):
        if key.startswith('leaf_'):   # two 16x16 frames stacked -> side by side; drop empty frames
            col = art[key]
            frames = [col.crop((0, 16 * i, 16, 16 * i + 16)) for i in range(2)]
            frames = [f for f in frames if not empty(f)]
            if not frames:
                del art[key]
                continue
            strip = Image.new('RGBA', (16 * len(frames), 16), (0, 0, 0, 0))
            for i, f in enumerate(frames):
                strip.paste(f, (16 * i, 0))
            art[key] = strip
        elif empty(art[key]):
            del art[key]
    seed_icon = art.get('stage_0_0')
    meta = dict(name=name, seedName=seed_name, fruit=False, wood='wood', chopTool='axe', fruitItem='', fruitSeasons=0,
                fruitDays=3, fruitMax=3, sfxHit='', sfxFall='', seedPrice=seed_price, buyPrice=0, **WILD_NUM)
    return tid, meta, art, seed_icon


def fruit_cut(sheet, cx, top, bottom, w):
    """The art of a fruit tree cell standing on `bottom`, w wide, centred on cx."""
    b = bbox(sheet, (cx - w // 2, top, cx + w // 2, bottom))
    if b is None:
        return None
    return sheet.crop((cx - w // 2, b[1], cx + w // 2, b[3]))


def fruit_tree(sheet, spec):
    tid, name, band, fruit_id, fruit_name, fruit_sell, seasons, buy, colour = spec
    y0 = band * 80
    art = {}
    stage_w = [16, 32, 32, 48]
    for k in range(4):
        cx = 48 * k + 24
        top = y0 + 48 if k == 0 else y0      # cell 0's top half is the sapling item
        art[f'stage_0_{k}'] = fruit_cut(sheet, cx, top, y0 + 80, stage_w[k])
    # stage 1 is 17 rows: keep it one tile tall, losing its top row
    s1 = art['stage_0_0']
    if s1.height > 16:
        art['stage_0_0'] = s1.crop((0, s1.height - 16, 16, s1.height))
    for s in range(4):
        g = fruit_cut(sheet, 192 + 48 * s + 24, y0, y0 + 80, 48)
        if g is not None:
            art[f'grown_{s}'] = g
    for s in range(3):
        lf = cut(sheet, 384 + 16 * s, y0, 16, 16)
        if not empty(lf):
            art[f'leaf_{s}'] = lf
    st = fruit_cut(sheet, 408, y0 + 48, y0 + 80, 16)
    if st is not None:
        art['stump_0'] = st
    for key in [k for k, v in art.items() if v is None or empty(v)]:
        del art[key]
    sapling = fruit_cut(sheet, 24, y0, y0 + 48, 16)      # the sack: the sapling item's icon
    fruit_icon = cut(sheet, 400, y0 + 24, 16, 16)
    meta = dict(name=name, seedName=f'{fruit_name} Sapling', fruit=True, wood='hardwood', chopTool='axe', fruitItem=fruit_id,
                fruitSeasons=seasons, sfxHit='', sfxFall='', seedPrice=0, buyPrice=buy, **FRUIT_NUM)
    return tid, meta, art, sapling, (fruit_id, fruit_name, fruit_sell, colour, fruit_icon)


# ---- the files, exactly as the Trees Editor writes them ----
def pack565(img):
    px = []
    rgba = img.convert('RGBA')
    for (r, g, b, a) in rgba.getdata():
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


def c_str(s):
    return s.replace('\\', '\\\\').replace('"', '\\"')


ART_GROUPS = ['grown', 'moss', 'log', 'stump', 'stumpmoss', 'leaf']
ART_FIELD = {'grown': 'grown', 'moss': 'moss', 'log': 'log', 'stump': 'stump', 'stumpmoss': 'stump_moss', 'leaf': 'leaf'}


META_ORDER = ['name', 'seedName', 'fruit', 'wood', 'chopTool', 'fruitItem', 'fruitSeasons', 'fruitDays', 'fruitMax', 'sfxHit', 'sfxFall',
              'seedPrice', 'buyPrice', 'growDays', 'hits', 'bushHits', 'stumpHits', 'woodMin', 'woodMax', 'seedMax', 'bushWood',
              'stumpWoodMin', 'stumpWoodMax', 'shakeSeedMax', 'mossPct', 'climates']   # gameTools.html treBuildC()'s order


def tree_c(tid, meta, art, seed_icon):
    seed_id = f'{tid}_seed'
    keys = sorted(art)
    meta = dict(meta, climates=TREE_CLIMATES.get(tid, 0))
    meta = {k: meta[k] for k in META_ORDER}
    meta.update(art={k: [art[k].width, art[k].height] for k in keys}, seedIcon=[seed_icon.width, seed_icon.height])
    out = []
    days = meta['growDays']
    felled = f"{meta['woodMin']}-{meta['woodMax']} {meta['wood']}, 0-{meta['seedMax']} seeds ({meta['hits']} {meta['chopTool']} hits)"
    out.append(f'// AUTO-GENERATED by gameTools.html (Trees Editor) — "{meta["name"]}"')
    out.append(f'// Lives in assets/trees/ as {tid}.c — the file name is the tree id, keep it.')
    out.append(f'// One tree = the tree below + its seed item "{seed_id}" ("{meta["seedName"]}", what\'s planted).')
    line = f'// Grown after {days} game day{"" if days == 1 else "s"}. Felled: {felled}.'
    if meta['fruit']:
        line += f" Fruit: {meta['fruitItem']} every {meta['fruitDays']} days."
    out.append(line)
    out.append('// Everything here is const: it stays in flash (no RAM). RGB565, 0x0000 = see-through.')
    out.append('// TREES-EDITOR ' + json.dumps(meta, separators=(',', ':'), ensure_ascii=False))
    out.append('#include "items.h"')
    out.append('#include "trees.h"')
    out.append('')
    for k in keys:
        px = pack565(art[k])
        out.append(f'static const uint16_t k_tree_{tid}_{k}[{len(px)}] = {{')
        out.append(c_array(px))
        out.append('};')
    out.append('')

    def ref(k):
        return f'{{ {art[k].width}, {art[k].height}, k_tree_{tid}_{k} }}'

    def opt_str(v):
        return f'"{c_str(v)}"' if v else 'NULL'

    out.append(f'const tree_def_t k_tree_{tid} = {{')
    out.append(f'    .id = "{tid}",')
    out.append(f'    .name = "{c_str(meta["name"])}",')
    out.append(f'    .fruit = {"true" if meta["fruit"] else "false"},')
    out.append(f'    .grow_days = {days},')
    rows = []
    for s in range(4):
        cells = [f'[{k}] = {ref(f"stage_{s}_{k}")}' for k in range(4) if f'stage_{s}_{k}' in art]
        if cells:
            rows.append(f'        [{s}] = {{ {", ".join(cells)} }},')
    out.append('    .stage = {')
    out.extend(rows)
    out.append('    },')
    for g in ART_GROUPS:
        cells = [f'[{s}] = {ref(f"{g}_{s}")}' for s in range(4) if f'{g}_{s}' in art]
        if cells:
            out.append(f'    .{ART_FIELD[g]} = {{ {", ".join(cells)} }},')
    out.append(f'    .hits = {meta["hits"]}, .bush_hits = {meta["bushHits"]}, .stump_hits = {meta["stumpHits"]},')
    out.append(f'    .wood_min = {meta["woodMin"]}, .wood_max = {meta["woodMax"]}, .seed_max = {meta["seedMax"]}, .bush_wood = {meta["bushWood"]},')
    out.append(f'    .stump_wood_min = {meta["stumpWoodMin"]}, .stump_wood_max = {meta["stumpWoodMax"]}, .shake_seed_max = {meta["shakeSeedMax"]}, .moss_pct = {meta["mossPct"]},')
    out.append(f'    .wood = {opt_str(meta["wood"])}, .chop_tool = {opt_str(meta["chopTool"])},')
    out.append(f'    .fruit_item = {opt_str(meta["fruitItem"] if meta["fruit"] else "")}, .fruit_seasons = {meta["fruitSeasons"] if meta["fruit"] else 0}, '
               f'.fruit_days = {meta["fruitDays"]}, .fruit_max = {meta["fruitMax"]},')
    out.append(f'    .sfx_hit = {opt_str(meta["sfxHit"])}, .sfx_fall = {opt_str(meta["sfxFall"])},')
    out.append('};')
    out.append('')
    attrs = []
    if meta['seedPrice'] > 0:
        attrs.append(('sellable', meta['seedPrice']))
    if meta['buyPrice'] > 0:
        attrs.append(('buyable', meta['buyPrice']))
        attrs.append(('shop', 1))
    if meta['climates']:
        attrs.append(('climate', meta['climates']))
    px = pack565(seed_icon)
    out.append(f'// The {"sapling" if meta["fruit"] else "seed"}: hold it and tap open ground to plant the tree.')
    out.append(f'static const uint16_t k_{seed_id}_icon_pixels[{len(px)}] = {{')
    out.append(c_array(px))
    out.append('};')
    if attrs:
        out.append(f'static const item_attr_t k_{seed_id}_attrs[] = {{')
        out.extend(f'    {{ "{a}", {v} }},' for a, v in attrs)
        out.append('};')
    out.append(f'const item_asset_t k_item_{seed_id} = {{')
    out.append(f'    .id = "{seed_id}",')
    out.append(f'    .display_name = "{c_str(meta["seedName"])}",')
    out.append('    .max_stack = 99,')
    out.append(f'    .passive = {{ .w={seed_icon.width}, .h={seed_icon.height}, .frame_count=1, .interval_ms=150, .loop_count=-1, .pixels=k_{seed_id}_icon_pixels }},')
    out.append('    .use = { .frame_count = 0 },')
    out.append(f'    .attrs = {f"k_{seed_id}_attrs" if attrs else "NULL"},')
    out.append(f'    .attr_count = {len(attrs)},')
    out.append('};')
    return '\n'.join(out) + '\n'


def fruit_item_c(fid, name, sell, colour, icon, tree_name):
    px = pack565(icon)
    types = 1 << colour | 1 << TYPE_ROUND
    types2 = 1 << (TYPE_FOOD - 31)
    lines = [
        f'// AUTO-GENERATED by gameTools.html (Item Editor) — "{name}"',
        f'// Lives in assets/items/ as {fid}.c — the file name is the item id, keep it.',
        f'// Rebuild and it\'s in the game; maps drop it by the id "{fid}".',
        f'// The {tree_name} grows it (assets/trees/, TREES in main.c).',
        '#include "items.h"',
        '',
        f'static const uint16_t k_{fid}_passive_pixels[{len(px)}] = {{',
        c_array(px),
        '};',
        '',
        '',
        f'static const item_attr_t k_{fid}_attrs[] = {{',
        f'    {{ "sellable", {sell} }},',
        '    { "quality", 1 },',
        f'    {{ "types", {types} }},',
        f'    {{ "types2", {types2} }},',
        '};',
        '',
        f'const item_asset_t k_item_{fid} = {{',
        f'    .id = "{fid}",',
        f'    .display_name = "{name}",',
        '    .max_stack = 99,',
        f'    .passive = {{ .w={icon.width}, .h={icon.height}, .frame_count=1, .interval_ms=150, .loop_count=-1, .pixels=k_{fid}_passive_pixels }},',
        '    .use = { .frame_count = 0 },',
        f'    .attrs = k_{fid}_attrs,',
        '    .attr_count = 4,',
        '};',
    ]
    return '\n'.join(lines) + '\n'


# ---- the preview: every tree as the game draws it ----
def season_art(art, group, s, fruit=False):
    for t in range(s, -1, -1):
        if f'{group}_{t}' in art:
            return art[f'{group}_{t}']
    return None


def stage_art(art, s, k, fruit):
    if fruit:
        s = 0
    for t in range(s, -1, -1):
        if f'stage_{t}_{k}' in art:
            return art[f'stage_{t}_{k}']
    return None


def mossy_art(art, group, s):
    """main.c tree_mossy_art(): the moss art of season s, or the plain art when the season has its own
    (winter: bare, no moss), else the season before's."""
    for t in range(s, -1, -1):
        if f'{group}moss_{t}' in art or (group == '' and f'moss_{t}' in art):
            return art[f'{group}moss_{t}'] if group else art[f'moss_{t}']
        if f'{group or "grown"}_{t}' in art:
            return art[f'{group or "grown"}_{t}']
    return None


def grown_look(art, s, mossy):
    canopy = mossy_art(art, '', s) if mossy else season_art(art, 'grown', s)
    log = season_art(art, 'log', s)
    lh = log.height if log else 0
    h = canopy.height + lh
    img = Image.new('RGBA', (48, h), (0, 0, 0, 0))
    if log:
        img.alpha_composite(log, ((48 - log.width) // 2, h - lh))
    img.alpha_composite(canopy, ((48 - canopy.width) // 2, 0))
    return img


def preview(trees, path):
    cell_w, cell_h = 56, 124
    cols = 4 * 2 + 5     # per season: grown + mossy; then stages 1-4 + stump
    W = cols * cell_w + 120
    H = len(trees) * cell_h + 20
    out = Image.new('RGBA', (W, H), (70, 110, 60, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(out)
    for row, (tid, meta, art, seed_icon) in enumerate(trees):
        y = 10 + row * cell_h
        d.text((4, y + 4), tid, fill=(255, 255, 255, 255))
        out.alpha_composite(seed_icon, (4, y + 20))
        x = 120
        for s in range(4):
            for mossy in (False, True):
                if mossy and not any(k.startswith('moss_') for k in art):
                    x += cell_w
                    continue
                g = grown_look(art, s, mossy)
                out.alpha_composite(g, (x + (cell_w - g.width) // 2, y + cell_h - 8 - g.height))
                d.rectangle((x + cell_w // 2 - 8, y + cell_h - 24, x + cell_w // 2 + 7, y + cell_h - 9), outline=(255, 255, 0, 120))
                x += cell_w
        for k in range(4):
            a = stage_art(art, 1, k, meta['fruit'])
            if a:
                out.alpha_composite(a, (x + (cell_w - a.width) // 2, y + cell_h - 8 - a.height))
            x += cell_w
        st = season_art(art, 'stump', 0)
        if st:
            out.alpha_composite(st, (x + (cell_w - st.width) // 2, y + cell_h - 8 - st.height))
        lf = season_art(art, 'leaf', 0)
        if lf:
            out.alpha_composite(lf, (x + 20, y + 10))
    out.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--trees', default=TREES_PNG)
    ap.add_argument('--fruit', default=FRUIT_PNG)
    ap.add_argument('--preview')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    sheet = Image.open(a.trees).convert('RGBA')
    fsheet = Image.open(a.fruit).convert('RGBA')
    trees, fruits = [], []
    for spec in WILD:
        trees.append(wild_tree(sheet, spec))
    for spec in FRUIT:
        tid, meta, art, sapling, fruit = fruit_tree(fsheet, spec)
        trees.append((tid, meta, art, sapling))
        fruits.append((fruit, meta['name']))
    if a.preview:
        preview(trees, a.preview)
        print('preview ->', a.preview)
    if a.write:
        tdir = os.path.join(ROOT, 'assets', 'trees')
        idir = os.path.join(ROOT, 'assets', 'items')
        os.makedirs(tdir, exist_ok=True)
        jobs = [(os.path.join(tdir, f'{t[0]}.c'), tree_c(*t)) for t in trees]
        jobs += [(os.path.join(idir, f'{f[0]}.c'), fruit_item_c(*f, tree_name)) for f, tree_name in fruits]
        for path, text in jobs:
            if os.path.exists(path) and not a.force:
                print('kept (exists):', os.path.relpath(path, ROOT))
                continue
            with open(path, 'w', newline='\n', encoding='utf-8') as fh:
                fh.write(text)
            print('wrote', os.path.relpath(path, ROOT), f'({len(text) // 1024} KB)')


if __name__ == '__main__':
    main()
