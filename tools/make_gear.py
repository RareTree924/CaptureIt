#!/usr/bin/env python3
"""
Draws the climate gear (GEAR in main.c): two sets — Thermal (against the
heat) and Arctic (against the cold) — of four pieces each: hat, jacket,
pants, boots. For every piece it writes

  assets/items/<id>.c              the item (Item Editor format: its 16x16 bag
                                   icon, price, "gear" slot, "protect_heat" /
                                   "protect_cold" share of the protection)
  assets/wardrobe/gear/<id>.png    how it looks worn: 20x36 cells (a composed
                                   character frame, WARD_CANVAS), 4 walking
                                   frames across x 4 directions down (down,
                                   right, left, up) = 80x144, drawn over the
                                   player at (0, 0) (tools/wardrobe.py, ward_frame())

The worn art follows the body's own shapes, frame by frame: the pants are its
legs (from the waist), the boots the bottom of them and the feet, the jacket the
shirt patch (and the sleeves take its colour, as a shirt's do), the hat is
drawn on the head (moving with its bob). Placeholder art — swap in your own
PNGs of the same layout (and icons in the Item Editor).

    python tools/make_gear.py [--write] [--force] [--preview out.png]
"""
import argparse, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import wardrobe as w   # noqa: E402

CW, CH = w.CANVAS_W, w.CANVAS_H
BX, BY = w.BOX_X, w.BOX_Y
REF_SHIRT, REF_BODY = 'shirt_000', 'male'
WAIST = 22   # the body box's row where the legs start (pants strips start there too)
SLOTS = ['hat', 'jacket', 'pants', 'boots']                    # "gear" 1..4 (main.c GEAR_*)
PRICE = {'hat': 20000, 'jacket': 40000, 'pants': 35000, 'boots': 25000}
SHARE = {'hat': 17, 'jacket': 33, 'pants': 29, 'boots': 21}   # % of the protection: the price's share of the set
CLOTHING = 34                                                  # pipeline_msgs.h CAM_TYPES "clothing" (types2 bit 3)

# outline, dark, mid, light, + accents
SETS = {
    'thermal': dict(name='Thermal', protect='protect_heat', ramp=[(70, 66, 70), (150, 150, 156), (196, 198, 204), (236, 238, 242)],
                    trim=[(120, 40, 20), (226, 106, 36), (248, 160, 70)], boot=[(40, 36, 38), (86, 80, 84), (120, 114, 118)],
                    hat=[(92, 70, 40), (196, 166, 104), (226, 202, 146), (246, 230, 190)], colours=(1, 10)),   # orange, gray
    'arctic':  dict(name='Arctic', protect='protect_cold', ramp=[(22, 30, 58), (40, 62, 116), (60, 96, 168), (104, 146, 214)],
                    trim=[(150, 156, 170), (226, 230, 238), (252, 252, 255)], boot=[(48, 30, 20), (104, 66, 40), (146, 98, 62)],
                    hat=[(54, 34, 22), (112, 74, 44), (150, 104, 64), (186, 140, 92)], colours=(4, 9)),         # blue, white
}


def cell_mask(item, cx, cy, x0, y0):
    """{(x, y): shade L (0..1)} of an item's cell placed at (x0, y0) on the canvas."""
    out = {}
    for y in range(item.ch):
        for x in range(item.cw):
            v = item.map[(cy * item.ch + y) * item.w + cx * item.cw + x]
            X, Y = x0 + x, y0 + y
            if v and 0 <= X < CW and 0 <= Y < CH:
                out[(X, Y)] = item.shades[v - 1][2] / w.Q
    return out


def ramp_of(mask, ramp):
    """Recolours a mask onto a 4-colour ramp (outline, dark, mid, light): its commonest shade
    becomes the mid tone, darker ones dark (much darker: the outline), lighter ones light."""
    if not mask:
        return {}
    counts = {}
    for L in mask.values():
        counts[L] = counts.get(L, 0) + 1
    mode = max(counts, key=counts.get)
    out = {}
    for p, L in mask.items():
        out[p] = ramp[0] if L < mode - 0.12 else ramp[1] if L < mode - 0.02 else ramp[2] if L <= mode + 0.02 else ramp[3]
    return out


def outline(px, col):
    """Edge pixels of a drawn shape (a see-through neighbour) in the outline colour."""
    out = dict(px)
    for (x, y) in px:
        if any((x + dx, y + dy) not in px for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
            out[(x, y)] = col
    return out


def hat_px(kind, r, dy, S):
    """A hat on the head: r = strip row (0 down, 1 right, 2 left, 3 up)."""
    px = {}
    top = BY + w.HEAD_TOP + dy   # the head's top row on the canvas
    H = S['hat']
    def put(x0, x1, y, c):
        for x in range(x0, x1 + 1):
            px[(x, y)] = c
    if kind == 'thermal':   # a wide-brimmed sun hat: crown, orange band, brim
        for y in range(top - 3, top + 1):
            put(7, 12, y, H[2] if y > top - 3 else H[3])
        put(7, 12, top, S['trim'][1])
        if r in (0, 3):
            put(3, 16, top + 1, H[1]); put(4, 15, top + 2, H[2])
        else:
            front = 1 if r == 1 else -1
            x0, x1 = (5, 17) if front > 0 else (2, 14)
            put(x0, x1, top + 1, H[1]); put(x0 + 1, x1 - 1, top + 2, H[2])
        return outline(px, H[0])
    # arctic: a fur trapper hat — crown, a white fur front, ear flaps
    fur = S['trim']
    for y in range(top - 2, top + 3):
        put(5, 14, y, H[2] if y < top + 1 else H[1])
    put(6, 13, top - 3, H[3])
    if r == 0:
        put(5, 14, top + 2, fur[1]); put(5, 14, top + 3, fur[2])
    if r in (0, 3):
        for y in range(top + 3, top + 9):
            px[(4, y)] = H[1]; px[(5, y)] = H[2]; px[(14, y)] = H[2]; px[(15, y)] = H[1]
    else:
        back = 6 if r == 1 else 12   # the flap behind the face
        for y in range(top + 3, top + 9):
            px[(back, y)] = H[2]; px[(back + 1, y)] = H[1]
        put(5, 14, top + 2, fur[1])
    return outline(px, H[0])


def worn_frames(set_id, slot, wd):
    """{(f, r): {(x, y): rgb}} for every walking frame and direction."""
    S = SETS[set_id]
    find = lambda kind, name: next(it for it in wd[kind] if it.name == name)
    body, shirt = find('bodies', REF_BODY), find('shirts', REF_SHIRT)
    out = {}
    for r in range(4):
        for f in range(4):
            dy = body.bob[r * 4 + f]
            bm = cell_mask(body, f, r, BX, BY)                     # the body's own legs, frame by frame
            waist = BY + WAIST
            legs = {p: L for p, L in bm.items() if p[1] >= waist}
            feet_top = max((y for (_, y) in legs), default=CH - 1) - 2   # the boots: the bottom of the legs and the feet
            if slot == 'pants':
                px = outline(ramp_of({p: L for p, L in legs.items() if p[1] < feet_top}, S['ramp']), S['ramp'][0])
                if set_id == 'thermal':   # a reflective orange band at the knees
                    knee = feet_top - 5
                    for p in list(px):
                        if p[1] == knee and px[p] != S['ramp'][0]: px[p] = S['trim'][1]
            elif slot == 'boots':
                feet = {p: L for p, L in legs.items() if p[1] >= feet_top}
                px = outline(ramp_of(feet, S['boot'] + [S['boot'][2]]), S['boot'][0])
                for p in list(px):
                    if p[1] == max(y for (_, y) in feet):   px[p] = S['boot'][0]   # the sole
                    elif p[1] == feet_top:                  px[p] = S['trim'][1] if set_id == 'thermal' else S['trim'][2]   # the cuff
            elif slot == 'jacket':
                sm = cell_mask(shirt, 0, r, BX + w.SHIRT_X, BY + w.SHIRT_Y + dy)
                px = ramp_of(sm, S['ramp']) if sm else {}
                if sm:
                    xs = [x for (x, _) in sm]
                    bottom = max(y for (_, y) in sm)
                    for y in (bottom + 1, bottom + 2):   # the hem, over the belt
                        for x in range(min(xs), max(xs) + 1):
                            if (x, y) in legs: px[(x, y)] = S['ramp'][1] if y == bottom + 2 else S['ramp'][2]
                    top = min(y for (_, y) in sm)
                    for x in range(min(xs), max(xs) + 1):   # the collar (fur on the arctic one)
                        if (x, top) in px: px[(x, top)] = S['trim'][2] if set_id == 'arctic' else S['trim'][1]
                    if r == 0:                          # the zip down the front
                        zx = (min(xs) + max(xs) + 1) // 2
                        for y in range(top + 1, bottom + 3):
                            if (zx, y) in px: px[(zx, y)] = S['trim'][1] if set_id == 'thermal' else S['ramp'][0]
                    px = outline(px, S['ramp'][0])
            else:
                px = hat_px(set_id, r, dy, S)
            out[(f, r)] = px
    return out


def worn_png(frames):
    im = Image.new('RGBA', (CW * 4, CH * 4), (0, 0, 0, 0))
    for (f, r), px in frames.items():
        for (x, y), c in px.items():
            im.putpixel((f * CW + x, r * CH + y), c + (255,))
    return im


def icon(set_id, slot):
    """The 16x16 bag icon."""
    S, px = SETS[set_id], {}
    R, T, B, H = S['ramp'], S['trim'], S['boot'], S['hat']
    def rect(x0, y0, x1, y1, c):
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1): px[(x, y)] = c
    if slot == 'hat':
        if set_id == 'thermal':
            rect(5, 4, 10, 8, H[2]); rect(5, 4, 10, 4, H[3]); rect(5, 8, 10, 8, T[1]); rect(1, 9, 14, 10, H[1]); rect(2, 11, 13, 11, H[2])
        else:
            rect(3, 3, 12, 8, H[2]); rect(4, 2, 11, 2, H[3]); rect(3, 8, 12, 9, T[1]); rect(2, 9, 3, 14, H[1]); rect(12, 9, 13, 14, H[1])
        return outline(px, H[0])
    if slot == 'jacket':
        rect(4, 3, 11, 13, R[2]); rect(1, 4, 3, 11, R[1]); rect(12, 4, 14, 11, R[1]); rect(5, 3, 10, 3, T[2] if set_id == 'arctic' else T[1])
        rect(7, 4, 8, 13, T[1] if set_id == 'thermal' else R[0]); rect(1, 11, 3, 11, R[3]); rect(12, 11, 14, 11, R[3])
        return outline(px, R[0])
    if slot == 'pants':
        rect(3, 2, 12, 5, R[2]); rect(3, 6, 7, 14, R[2]); rect(8, 6, 12, 14, R[1]); rect(3, 2, 12, 2, R[3])
        if set_id == 'thermal': rect(3, 9, 7, 9, T[1]); rect(8, 9, 12, 9, T[1])
        return outline(px, R[0])
    rect(4, 3, 9, 11, B[1]); rect(4, 11, 13, 13, B[1]); rect(5, 4, 8, 10, B[2]); rect(4, 14, 13, 14, B[0])
    rect(3, 3, 10, 4, T[1] if set_id == 'thermal' else T[2])
    return outline(px, B[0])


def pack565(c):
    v = ((c[0] >> 3) << 11) | ((c[1] >> 2) << 5) | (c[2] >> 3)
    return 0x0841 if v == 0 else v


def item_c(set_id, slot):
    S = SETS[set_id]
    iid, name = f'{set_id}_{slot}', f'{S["name"]} {slot.capitalize()}'
    ic = icon(set_id, slot)
    px = [pack565(ic[(x, y)]) if (x, y) in ic else 0 for y in range(16) for x in range(16)]
    rows = ['    ' + ', '.join(f'0x{v:04x}' for v in px[i:i + 12]) + ',' for i in range(0, 256, 12)]
    lo = sum(1 << c for c in S['colours'])
    attrs = [('sellable', PRICE[slot] // 2), ('buyable', PRICE[slot]), ('shop', 5), ('types', lo), ('types2', 1 << (CLOTHING - 31)),
             ('gear', SLOTS.index(slot) + 1), (S['protect'], SHARE[slot]), ('mut', 0)]
    against = 'the heat' if S['protect'] == 'protect_heat' else 'the cold'
    return '\n'.join([
        f'// AUTO-GENERATED by gameTools.html (Item Editor) — "{name}"',
        f'// Lives in assets/items/ as {iid}.c — the file name is the item id, keep it.',
        f'// Rebuild and it\'s in the game; maps drop it by the id "{iid}".',
        f'// Gear against {against} (GEAR in main.c): worn from the inventory\'s gear tab, drawn on the player from',
        f'// assets/wardrobe/gear/{iid}.png. {SHARE[slot]}% of the set\'s protection. Made by tools/make_gear.py.',
        '// Placeholder art: open this file in the Item Editor, load your own 16x16 icon and Export.',
        '#include "items.h"',
        '',
        f'static const uint16_t k_{iid}_passive_pixels[256] = {{',
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
        '    .max_stack = 1,',
        f'    .passive = {{ .w=16, .h=16, .frame_count=1, .interval_ms=150, .loop_count=-1, .pixels=k_{iid}_passive_pixels }},',
        '    .use = { .frame_count = 0 },',
        f'    .attrs = k_{iid}_attrs,',
        f'    .attr_count = {len(attrs)},',
        '};',
    ]) + '\n'


def preview(path, wd):
    """Each set worn by the default player: every direction, frames 0 and 1, carrying and not."""
    o = w.Outfit(body=next(i for i, it in enumerate(wd['bodies']) if it.name == REF_BODY))
    o.hair_c, o.pants_c = w.oklab_q((106, 66, 40)), w.oklab_q((62, 92, 150))
    S = 4
    sheet = Image.new('RGB', ((CW * 9 + 2) * S, (CH * 3 + 4) * S), (72, 104, 72))
    for row, gear in enumerate((None, [f'thermal_{s}' for s in SLOTS], [f'arctic_{s}' for s in SLOTS])):
        fr = w.compose(o, wd, False, gear)
        held = w.compose(o, wd, True, gear)
        for j, (frames, k) in enumerate([(fr, k) for k in (0, 1, 4, 5, 8, 9, 12, 13)] + [(held, 0)]):
            im = Image.new('RGBA', (CW, CH))
            for y in range(CH):
                for x in range(CW):
                    if frames[k][y][x]: im.putpixel((x, y), frames[k][y][x] + (255,))
            im = im.resize((CW * S, CH * S), Image.NEAREST)
            sheet.paste(im, (j * CW * S, row * (CH + 1) * S), im)
    sheet.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--preview')
    a = ap.parse_args()
    wd = w.load_wardrobe(warn=lambda *x: None)
    if a.write:
        gdir = os.path.join(ROOT, 'assets', 'wardrobe', 'gear')
        os.makedirs(gdir, exist_ok=True)
        for set_id in SETS:
            for slot in SLOTS:
                iid = f'{set_id}_{slot}'
                jobs = [(os.path.join(gdir, iid + '.png'), None), (os.path.join(ROOT, 'assets', 'items', iid + '.c'), item_c(set_id, slot))]
                for path, text in jobs:
                    if os.path.exists(path) and not a.force:
                        print('kept (exists):', os.path.relpath(path, ROOT)); continue
                    if text is None: worn_png(worn_frames(set_id, slot, wd)).save(path)
                    else: open(path, 'w', encoding='utf-8', newline='\n').write(text)
                    print('wrote', os.path.relpath(path, ROOT))
    if a.preview:
        preview(a.preview, w.load_wardrobe(warn=lambda *x: None))
        print('preview ->', a.preview)


if __name__ == '__main__':
    main()
