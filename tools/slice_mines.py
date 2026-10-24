"""One-off: cuts the Stardew mines sheet (Spriters Resource rip in Downloads:
"Environment - Mines.png", 384x482) into

  assets/items/<mineral>.c   ~50 minerals and gems (Item Editor format): "museum 1"
                             (donatable — MUSEUM in main.c), "mineral 1", and which
                             geodes they come out of: "geode:<geode id>" W, their
                             weight in that geode (GEODES in main.c)
  assets/items/<geode>.c     the four geodes: "geode 1" — a blacksmith cracks them
  assets/items/stone.c       what rocks give
  assets/map/mining/*.png    the mineable rocks and gem nodes for the Map Editor (just
                             the rock, bottom-centred in 16x16), already set up there
                             (--rocks): BREAKABLE — the pickaxe, ROCK_HITS hits (gem
                             nodes NODE_HITS), solid where drawn, a little shake on each
                             hit, and the dust to its right on the sheet as the last
                             hit's effect (a "fall" bundle: three DUST_MS frames, thinning
                             out, then gone). Drops are left empty: set them in the Map
                             Editor's Breakable... (stone, a gem, a geode)

Names are Stardew's minerals where the art matches one, else a made-up one.
Left out: the ores, ingots, slimes, potions, bones and the big things (stumps,
boulders, crystals).

    python tools/slice_mines.py [--sheet PNG] [--preview out.png] [--write] [--force] [--rocks]

--rocks writes the rock PNGs and their settings into assets/gametools_assets.json
(close Game Tools first — it keeps that file in memory and would write its own copy
back): an existing rock's entry is replaced, everything else is left alone.

Boxes are (x0, y0, x1, y1) in the sheet, from a connected-component cut.
"""
import argparse, base64, json, os, random, string
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHEET = os.path.join(os.path.expanduser('~'), 'Downloads', 'PC _ Computer - Stardew Valley - Environment - Mines.png')

RED, ORANGE, YELLOW, GREEN, BLUE, PURPLE, PINK, BROWN, BLACK, WHITE, GRAY = range(11)
SHINY, COLLECTIBLE = 16, 48   # pipeline_msgs.h CAM_TYPES
G, F, M, O = 'geode', 'frozen_geode', 'magma_geode', 'omni_geode'

# box, id, name, sell, {geode: weight}, colours, a gem (shiny)
MINERALS = [
    ((195, 36, 205, 45), 'emerald', 'Emerald', 250, {O: 2}, [GREEN], True),
    ((131, 52, 142, 65), 'frozen_tear', 'Frozen Tear', 75, {F: 6, O: 4}, [BLUE], True),
    ((260, 33, 268, 45), 'ruby', 'Ruby', 250, {O: 2}, [RED], True),
    ((289, 34, 303, 45), 'amethyst', 'Amethyst', 100, {O: 4}, [PURPLE], True),
    ((226, 53, 237, 65), 'topaz', 'Topaz', 80, {O: 4}, [YELLOW], True),
    ((2, 72, 15, 81), 'jade', 'Jade', 200, {O: 3}, [GREEN], True),
    ((100, 84, 112, 95), 'diamond', 'Diamond', 750, {O: 1}, [WHITE], True),
    ((82, 83, 96, 97), 'prismatic_shard', 'Prismatic Shard', 2000, {O: 1}, [RED, YELLOW, BLUE], True),
    ((227, 34, 238, 45), 'aquamarine', 'Aquamarine', 180, {O: 3}, [BLUE], True),
    ((67, 68, 79, 81), 'fire_quartz', 'Fire Quartz', 100, {M: 6, O: 4}, [ORANGE], True),
    ((114, 82, 129, 96), 'earth_crystal', 'Earth Crystal', 50, {G: 8, O: 5}, [WHITE], True),
    ((277, 54, 283, 65), 'quartz', 'Quartz', 25, {G: 10, F: 6, O: 5}, [WHITE, PURPLE], True),
    ((195, 54, 206, 65), 'baryte', 'Baryte', 50, {M: 8}, [ORANGE], False),
    ((210, 52, 223, 65), 'aerinite', 'Aerinite', 125, {F: 6}, [BLUE], False),
    ((242, 53, 254, 65), 'nekoite', 'Nekoite', 80, {G: 6}, [PINK], False),
    ((258, 53, 271, 65), 'helvite', 'Helvite', 450, {M: 2}, [ORANGE, BROWN], False),
    ((290, 52, 304, 65), 'fluorapatite', 'Fluorapatite', 200, {F: 4}, [GREEN], False),
    ((308, 52, 317, 65), 'jasper', 'Jasper', 150, {M: 5}, [RED], False),
    ((322, 53, 335, 66), 'jagoite', 'Jagoite', 115, {G: 5}, [GREEN], False),
    ((324, 36, 334, 46), 'tigerseye', 'Tigerseye', 275, {M: 3}, [BROWN], False),
    ((338, 53, 350, 65), 'pyrite', 'Pyrite', 120, {M: 6}, [YELLOW], False),
    ((356, 34, 372, 50), 'lunarite', 'Lunarite', 200, {F: 4}, [WHITE], False),
    ((356, 53, 366, 65), 'kyanite', 'Kyanite', 250, {F: 3}, [BLUE], False),
    ((369, 51, 383, 65), 'calcite', 'Calcite', 75, {G: 8}, [WHITE], False),
    ((2, 86, 15, 97), 'soapstone', 'Soapstone', 120, {F: 6}, [GRAY], False),
    ((18, 68, 31, 81), 'obsidian', 'Obsidian', 200, {M: 5}, [BLACK], False),
    ((18, 84, 31, 98), 'geminite', 'Geminite', 150, {F: 5}, [PURPLE], False),
    ((35, 83, 47, 98), 'fairy_stone', 'Fairy Stone', 300, {O: 2}, [PINK], False),
    ((36, 72, 45, 80), 'orpiment', 'Orpiment', 80, {G: 7}, [ORANGE], False),
    ((50, 70, 63, 81), 'jamborite', 'Jamborite', 150, {G: 5}, [PINK], False),
    ((52, 84, 61, 96), 'petrified_slime', 'Petrified Slime', 120, {G: 6}, [GREEN], False),
    ((68, 85, 80, 94), 'fire_opal', 'Fire Opal', 350, {M: 3}, [ORANGE], False),
    ((114, 69, 127, 81), 'lemon_stone', 'Lemon Stone', 200, {M: 4}, [YELLOW], False),
    ((129, 69, 143, 81), 'malachite', 'Malachite', 100, {G: 7}, [GREEN], False),
    ((145, 70, 160, 82), 'ghost_crystal', 'Ghost Crystal', 200, {F: 4}, [WHITE, BLUE], False),
    ((179, 69, 189, 81), 'hematite', 'Hematite', 150, {M: 5}, [RED], False),
    ((194, 73, 207, 82), 'ocean_stone', 'Ocean Stone', 220, {F: 4}, [BLUE], False),
    ((210, 73, 223, 82), 'void_stone', 'Void Stone', 300, {M: 2}, [PURPLE], False),
    ((219, 84, 234, 99), 'bixite', 'Bixite', 300, {M: 3}, [BLACK], False),
    ((227, 67, 238, 81), 'celestine', 'Celestine', 125, {G: 5}, [BLUE], False),
    ((235, 83, 250, 99), 'neptunite', 'Neptunite', 400, {M: 2}, [BLUE, BLACK], False),
    ((242, 68, 255, 81), 'limestone', 'Limestone', 15, {G: 10}, [WHITE], False),
    ((251, 83, 265, 99), 'slate', 'Slate', 85, {G: 8}, [GRAY], False),
    ((259, 70, 270, 81), 'sandstone', 'Sandstone', 60, {G: 8}, [ORANGE], False),
    ((267, 83, 281, 98), 'opal', 'Opal', 150, {F: 4}, [PINK], False),
    ((275, 70, 287, 81), 'granite', 'Granite', 75, {G: 8}, [BROWN], False),
    ((283, 83, 298, 99), 'star_shards', 'Star Shards', 500, {M: 1, O: 1}, [PURPLE, ORANGE], False),
    ((289, 68, 303, 82), 'basalt', 'Basalt', 175, {M: 5}, [GRAY], False),
    ((299, 83, 314, 99), 'esperite', 'Esperite', 100, {F: 6}, [BLUE], False),
    ((307, 71, 317, 81), 'dolomite', 'Dolomite', 300, {M: 3}, [BROWN], False),
    ((351, 86, 366, 100), 'mudstone', 'Mudstone', 25, {G: 10}, [BROWN], False),
    ((354, 68, 367, 81), 'alamite', 'Alamite', 150, {G: 6}, [ORANGE, BROWN], False),
    ((372, 69, 383, 81), 'thunder_egg', 'Thunder Egg', 100, {G: 5}, [PURPLE], False),
    ((226, 108, 241, 121), 'fluorite', 'Fluorite', 220, {F: 3}, [GREEN], True),
    ((365, 109, 380, 123), 'void_gem', 'Void Gem', 500, {O: 1}, [PURPLE], True),
]
OMNI_DEFAULT = 3   # every geode mineral is in the omni geode too, at this weight (unless it says)

GEODES = [   # box, id, name, sell
    ((64, 49, 80, 66), 'geode', 'Geode', 50),
    ((80, 49, 96, 66), 'frozen_geode', 'Frozen Geode', 100),
    ((95, 51, 110, 65), 'magma_geode', 'Magma Geode', 150),
    ((61, 130, 77, 146), 'omni_geode', 'Omni Geode', 200),
]
STONE = ((17, 49, 32, 64), 'stone', 'Stone', 2)

NODES = [   # box, file name: the rock only (its debris pieces are left out)
    ((2, 1, 17, 15), 'node_diamond'), ((35, 2, 49, 15), 'node_ruby'), ((66, 1, 81, 15), 'node_jade'),
    ((98, 0, 112, 15), 'node_amethyst'), ((129, 1, 145, 15), 'node_topaz'), ((162, 1, 177, 15), 'node_emerald'),
    ((193, 2, 209, 15), 'node_aquamarine'), ((226, 2, 240, 16), 'node_mystic'), ((244, 2, 260, 18), 'node_glowing'),
    ((366, 1, 380, 16), 'rock_brown_big'),
    ((1, 17, 16, 30), 'rock_dark'), ((33, 20, 47, 30), 'rock_grey_small'), ((65, 17, 80, 31), 'rock_tan'),
    ((98, 16, 111, 30), 'rock_beige'), ((128, 18, 144, 31), 'rock_brown'), ((161, 18, 175, 30), 'rock_grey'),
    ((193, 18, 208, 30), 'rock_slate'), ((225, 17, 240, 30), 'rock_mud'), ((257, 20, 271, 30), 'rock_clay'),
    ((289, 17, 303, 30), 'rock_red'), ((320, 17, 336, 31), 'rock_purple'),
    ((0, 34, 16, 47), 'rock_ice_big'), ((33, 37, 47, 47), 'rock_ice'), ((34, 52, 45, 63), 'rock_pebble'),
    ((130, 35, 143, 47), 'rock_magma'), ((162, 34, 176, 47), 'rock_magma_2'),
]


def cut(sheet, box):
    """The box, trimmed to its opaque pixels and centred in a 16x16 icon."""
    spr = sheet.crop(box)
    bb = spr.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
    spr = spr.crop(bb)
    if spr.width > 16 or spr.height > 16:
        raise SystemExit(f'{box} is {spr.width}x{spr.height}: bigger than 16x16')
    out = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    out.paste(spr, ((16 - spr.width) // 2, (16 - spr.height) // 2))
    return out


def pack565(img):
    px = []
    for (r, g, b, a) in img.convert('RGBA').getdata():
        if a < 128:
            px.append(0)
            continue
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        px.append(0x0841 if v == 0 else v)
    return px


def item_c(iid, name, icon, attrs, about, stack=99):
    px = pack565(icon)
    rows = ['    ' + ', '.join(f'0x{v:04x}' for v in px[i:i + 12]) + ',' for i in range(0, len(px), 12)]
    return '\n'.join([
        f'// AUTO-GENERATED by gameTools.html (Item Editor) — "{name}"',
        f'// Lives in assets/items/ as {iid}.c — the file name is the item id, keep it.',
        f'// Rebuild and it\'s in the game; maps drop it by the id "{iid}".',
        f'// {about} Art: Stardew Valley\'s mines sheet (tools/slice_mines.py).',
        '#include "items.h"',
        '',
        f'static const uint16_t k_{iid}_passive_pixels[{len(px)}] = {{',
        *rows,
        '};',
        '',
        '',
        f'static const item_attr_t k_{iid}_attrs[] = {{',
        *[f'    {{ "{a}", {v} }},' for a, v in attrs],
        '};',
        '',
        f'const item_asset_t k_item_{iid} = {{',
        f'    .id = "{iid}",',
        f'    .display_name = "{name}",',
        f'    .max_stack = {stack},',
        f'    .passive = {{ .w=16, .h=16, .frame_count=1, .interval_ms=150, .loop_count=-1, .pixels=k_{iid}_passive_pixels }},',
        '    .use = { .frame_count = 0 },',
        f'    .attrs = k_{iid}_attrs,',
        f'    .attr_count = {len(attrs)},',
        '};',
    ]) + '\n'


def types_attrs(colours, extra):
    bits = colours + extra
    lo = sum(1 << b for b in bits if b < 31)
    hi = sum(1 << (b - 31) for b in bits if b >= 31)
    return ([('types', lo)] if lo else []) + ([('types2', hi)] if hi else [])


def jobs(sheet):
    out = []
    for box, iid, name, sell, pools, colours, gem in MINERALS:
        pools = dict(pools)
        if not gem and O not in pools: pools[O] = OMNI_DEFAULT
        attrs = [('sellable', sell), ('museum', 1), ('mineral', 1)] + types_attrs(colours, [COLLECTIBLE] + ([SHINY] if gem else []))
        attrs += [(f'geode:{g}', w) for g, w in pools.items()]
        where = ', '.join(n.replace('_', ' ') for n in pools)
        out.append((os.path.join(ROOT, 'assets', 'items', iid + '.c'),
                    item_c(iid, name, cut(sheet, box), attrs, f'A {"gem" if gem else "mineral"}: donate it to the museum. In: {where}.')))
    for box, iid, name, sell in GEODES:
        out.append((os.path.join(ROOT, 'assets', 'items', iid + '.c'),
                    item_c(iid, name, cut(sheet, box), [('sellable', sell), ('geode', 1), ('types', 1 << BROWN)],
                           'A geode: a blacksmith cracks it open for a random mineral (GEODES in main.c).')))
    box, iid, name, sell = STONE
    out.append((os.path.join(ROOT, 'assets', 'items', iid + '.c'),
                item_c(iid, name, cut(sheet, box), [('sellable', sell), ('types', 1 << GRAY)], 'What rocks give when they\'re mined.')))
    return out


def node_images(sheet):
    return [(os.path.join(ROOT, 'assets', 'map', 'mining', n + '.png'), rock_and_dust(sheet, box, n)[0]) for box, n in NODES]


# ---- the rocks as Map Editor breakables (--rocks) ----
ROCK_HITS, NODE_HITS = 2, 4                # pickaxe hits to break a rock / a gem node
SHAKE_MS, DUST_MS = 30, 200                # a hit's shake frames; the dust's three frames (~0.6 s, then gone)
BANDS = [(0, 16), (16, 33), (33, 49), (49, 66)]
NO_DUST = {'node_mystic', 'node_glowing', 'rock_brown_big', 'rock_pebble'}   # nothing (or no dust) right of them: rock_grey's
META = os.path.join(ROOT, 'assets', 'gametools_assets.json')


def bottom16(img):
    """Trimmed to its opaque pixels, bottom-centred in 16x16 (it stands on its tile)."""
    bb = img.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox()
    out = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    if not bb:
        return out
    spr = img.crop(bb)
    if spr.width > 16 or spr.height > 16:
        raise SystemExit(f'a rock is {spr.width}x{spr.height}: bigger than 16x16')
    out.paste(spr, ((16 - spr.width) // 2, 16 - spr.height))
    return out


def dust_of(sheet, box):
    """The debris right of a rock on the sheet: the next 16 px cell, within the rock's rows."""
    cell = (box[0] + box[2]) // 2 // 16
    cy = (box[1] + box[3]) // 2
    b = next(bb for bb in BANDS if bb[0] <= cy < bb[1])
    x0 = max(cell * 16 + 16, box[2])   # (not the rock's own pixels where it spills into the next cell)
    return bottom16(sheet.crop((x0, max(b[0], box[1] - 2), cell * 16 + 32, min(b[1], box[3] + 1))))


def rock_and_dust(sheet, box, name):
    rock = bottom16(sheet.crop(box))
    if name in NO_DUST:
        grey = next(bx for bx, n in NODES if n == 'rock_grey')
        return rock, dust_of(sheet, grey)
    return rock, dust_of(sheet, box)


def rgb_frame(img, keep=lambda x, y: True):
    """A Frame Bundle frame: 16x16 RGB, see-through = pure black (opaque black nudged)."""
    out = bytearray()
    for y in range(16):
        for x in range(16):
            r, g, b, a = img.getpixel((x, y))
            if a < 128 or not keep(x, y): out += b'\x00\x00\x00'
            elif r < 8 and g < 4 and b < 8: out += bytes((8, 4, 8))   # (gameTools.html CROP_NEAR_BLACK)
            else: out += bytes((r, g, b))
    return {'color': base64.b64encode(bytes(out)).decode()}


def shifted(img, dx):
    out = Image.new('RGBA', (16, 16), (0, 0, 0, 0))
    out.paste(img, (dx, 0))
    return out


def bundle(name, frames, ms):
    return {'name': name, 'w': 16, 'h': 16, 'frameCount': len(frames), 'intervalMs': ms, 'loopCount': 1, 'seeThrough': True, 'frames': frames}


def uid():
    return 'am' + ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(13))


def write_rocks(sheet):
    meta = json.load(open(META, encoding='utf-8'))
    os.makedirs(os.path.join(ROOT, 'assets', 'map', 'mining'), exist_ok=True)
    for box, name in NODES:
        rock, dust = rock_and_dust(sheet, box, name)
        rock.save(os.path.join(ROOT, 'assets', 'map', 'mining', name + '.png'))
        key = f'map/mining/{name}.png'
        old = meta['assets'].get(key, {})
        shake = bundle(f'{name} shake', [rgb_frame(shifted(rock, d)) for d in (1, -1, 1, 0)], SHAKE_MS)
        thin = lambda x, y: (x + y) % 2 == 0
        fade = bundle(f'{name} dust', [rgb_frame(dust), rgb_frame(dust), rgb_frame(dust, thin)], DUST_MS)
        idx = {}
        for b in (shake, fade):   # one bundle of each name: replaced in place, else added
            k = next((i for i, x in enumerate(meta['bundles']) if x.get('name') == b['name']), None)
            if k is None:
                meta['bundles'].append(b)
                k = len(meta['bundles']) - 1
            else:
                meta['bundles'][k] = b
            idx[b['name']] = k
        hitbox = bytes(1 if rock.getpixel((x, y))[3] >= 128 else 0 for y in range(16) for x in range(16))
        meta['assets'][key] = {
            'uid': old.get('uid') or uid(), 'walkable': False, 'hitbox': base64.b64encode(hitbox).decode(),
            'breakable': {'hits': NODE_HITS if name.startswith('node_') else ROCK_HITS, 'needItem': 'pickaxe', 'drops': (old.get('breakable') or {}).get('drops', []),
                          'hitSound': (old.get('breakable') or {}).get('hitSound', ''), 'breakSound': (old.get('breakable') or {}).get('breakSound', ''),
                          'bundle': idx[shake['name']], 'final': idx[fade['name']], 'levels': []},
        }
        print('rock', key)
    with open(META, 'w', encoding='utf-8', newline='') as f:
        f.write(json.dumps(meta, ensure_ascii=False, separators=(',', ':')))
    print('wrote', os.path.relpath(META, ROOT))


def preview(sheet, path):
    S, C = 4, 10
    icons = [(m[1], cut(sheet, m[0])) for m in MINERALS] + [(g[1], cut(sheet, g[0])) for g in GEODES] + [(STONE[1], cut(sheet, STONE[0]))]
    icons += [(n[1], cut(sheet, n[0])) for n in NODES]
    rows = (len(icons) + C - 1) // C
    img = Image.new('RGBA', (C * 100, rows * (16 * S + 14)), (70, 100, 70, 255))
    d = ImageDraw.Draw(img)
    for k, (n, ic) in enumerate(icons):
        x, y = (k % C) * 100, (k // C) * (16 * S + 14)
        img.alpha_composite(ic.resize((16 * S, 16 * S), Image.NEAREST), (x + 18, y))
        d.text((x + 2, y + 16 * S + 1), n[:16], fill=(255, 255, 255, 255))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--sheet', default=SHEET)
    ap.add_argument('--preview')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--rocks', action='store_true')
    a = ap.parse_args()
    sheet = Image.open(a.sheet).convert('RGBA')
    if a.preview:
        preview(sheet, a.preview)
        print('preview ->', a.preview)
    if a.write:
        os.makedirs(os.path.join(ROOT, 'assets', 'map', 'mining'), exist_ok=True)
        for path, text in jobs(sheet) + node_images(sheet):
            if os.path.exists(path) and not a.force:
                print('kept (exists):', os.path.relpath(path, ROOT)); continue
            if isinstance(text, str): open(path, 'w', encoding='utf-8', newline='\n').write(text)
            else: text.save(path)
            print('wrote', os.path.relpath(path, ROOT))
    if a.rocks:
        write_rocks(sheet)


if __name__ == '__main__':
    main()
