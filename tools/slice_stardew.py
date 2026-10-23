#!/usr/bin/env python3
"""
Cuts the Stardew Valley farmer sheets (The Spriters Resource rips in
Downloads) into assets/wardrobe/: one small PNG per body, hairstyle, hat,
accessory, pair of pants and shirt, in the layouts tools/wardrobe.py reads
(see assets/wardrobe/README.md). Run it once (again to start over: it only
writes, it never deletes what you've drawn yourself):

    python tools/slice_stardew.py [--src "C:/Users/<you>/Downloads"] [--out assets/wardrobe]

Sheets it looks for (in --src), the frame layouts it found in them:
  "... - Farmer Base.png"   8 sheets of 288x672 (4 across, 2 down): 6 columns x
                            21 rows of 16x32 body frames; arms 96 px right of
                            each body frame, raised (carrying) arms 192 px right.
                            Sheet 1 = male (bald), 5 = female (bald).
                            Walking: down 0,1,2  right 6,7,8  up 12,13,14
                            (left = right mirrored). The carrying arms (raised
                            straight up) are drawn here, not taken from the sheet.
  "... - Pants.png"         20 pants in 192x688 blocks (10 across): the same
                            frames as the body; male in the left 96 px, female the right.
  "... - Hairstyles.png"    16x32 cells. Two files side by side: the left 128 px 3 down
                            per style (down, right, up), the right 128 px 4 down (+ left).
  "... - Hats.png"          20x20 cells, 12 across, 4 down per hat: down, right, left, up.
  "... - Accessories.png"   16x16 cells, 8 across, 2 down each: down, right.
  "... - Shirts.png"        (optional) 8x8 cells, 16 across in the left 128 px,
                            4 down per shirt: down, right, left, up.
Without a shirts sheet, one plain shirt is made from the body's own chest.
"""
import os
import argparse
from PIL import Image, ImageOps

PREFIX = 'PC _ Computer - Stardew Valley - Playable Characters - '
WALK = {'down': (0, 1, 0, 2), 'right': (6, 7, 6, 8), 'up': (12, 13, 12, 14)}
ROWS = ('down', 'right', 'left', 'up')      # the row order of every 4-direction strip
BODIES = {'male': 1, 'female': 5}           # sheet index in Farmer Base.png


def empty(im):
    return im.getchannel('A').getextrema()[1] == 0


def head_top(cell):
    a = cell.getchannel('A')
    for y in range(cell.size[1]):
        if a.crop((0, y, cell.size[0], y + 1)).getextrema()[1]:
            return y
    return 0


def frame(sheet, ox, oy, f, dx=0):
    x, y = ox + dx + f % 6 * 16, oy + f // 6 * 32
    return sheet.crop((x, y, x + 16, y + 32))


def save(im, path, made):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    im.save(path)
    made.append(path)


ARM_OUT, ARM_SKIN, ARM_SHADE = (107, 0, 58), (249, 174, 137), (224, 107, 101)   # a Stardew body's skin ramp
ARM_SLEEVE, ARM_CUFF = (112, 23, 24), (74, 12, 6)   # its sleeve colours (they take the shirt's)


def raised_arms(d, top):
    """Arms raised straight up for carrying, 3 px wide (outline, skin, shadow),
    from the shoulder (10 rows under the head's top) to 2 rows over it: the
    hands under the held item, a sleeve at the shoulder."""
    im = Image.new('RGBA', (16, 32))
    px = im.load()
    shoulder, hand = top + 11, top - 2

    def arm(x0, inner):   # inner: the side towards the head (0 or 2), in the skin's shadow, not outlined
        px[x0 + 1, hand - 1] = ARM_OUT + (255,)
        for y in range(hand, shoulder + 1):
            up = shoulder - y
            mid = ARM_CUFF if up == 2 else ARM_SLEEVE if up < 2 else ARM_SHADE if y == hand else ARM_SKIN
            side = ARM_CUFF if up <= 2 else ARM_SHADE
            for x in range(3):
                px[x0 + x, y] = (mid if x == 1 else side if x == inner else ARM_OUT) + (255,)
    if d in ('down', 'up'):
        arm(1, 2)
        arm(12, 0)
    else:   # from the side: the near arm, up past the ear (in front of the face it looked wrong)
        arm(6, 0) if d == 'right' else arm(7, 2)
    return im


def slice_bodies(src, out, made):
    base = Image.open(os.path.join(src, PREFIX + 'Farmer Base.png')).convert('RGBA')
    bodies = {}
    for name, i in BODIES.items():
        ox, oy = (i % 4) * 288, (i // 4) * 672
        im = Image.new('RGBA', (64, 32 * 12))
        for r, d in enumerate(ROWS):
            src_d = 'right' if d == 'left' else d
            for c, f in enumerate(WALK[src_d]):
                cells = [frame(base, ox, oy, f), frame(base, ox, oy, f, 96)]
                for k, cell in enumerate(cells):
                    if d == 'left':
                        cell = ImageOps.mirror(cell)
                    im.alpha_composite(cell, (c * 16, (k * 4 + r) * 32))
                # carrying: both arms straight up (the side views: the near one), hands over the head
                im.alpha_composite(raised_arms(d, head_top(frame(base, ox, oy, f))), (c * 16, (8 + r) * 32))
        save(im, os.path.join(out, 'bodies', name + '.png'), made)
        bodies[name] = im
    return bodies


def slice_pants(src, out, made):
    sheet = Image.open(os.path.join(src, PREFIX + 'Pants.png')).convert('RGBA')
    for p in range((sheet.size[0] // 192) * (sheet.size[1] // 688)):
        bx, by = p % 10 * 192, p // 10 * 688
        im = Image.new('RGBA', (64, 32 * 8))
        for fit in (0, 1):   # 0: the regular body, 1: the female one (bodies named female*)
            for r, d in enumerate(ROWS):
                for c, f in enumerate(WALK['right' if d == 'left' else d]):
                    cell = frame(sheet, bx + fit * 96, by, f)
                    if d == 'left':
                        cell = ImageOps.mirror(cell)
                    im.alpha_composite(cell, (c * 16, (fit * 4 + r) * 32))
        if not empty(im):
            save(im, os.path.join(out, 'pants', f'pants_{p:02d}.png'), made)


def pants_variants(out, made):
    """More pants: patterned versions of the grey (tintable) ones - stripes,
    plaid, a belt, cuffs - drawn in their greys, so they still take any colour.
    Written as pants_<NN>_<pattern>.png next to the one they're made from."""
    d = os.path.join(out, 'pants')

    def lum(p):
        return int(0.3 * p[0] + 0.59 * p[1] + 0.11 * p[2])

    def shade(p, k):
        v = max(0, min(255, int(lum(p) * k)))
        return (v, v, v, 255)

    def stripes(px, cx, cy, x, y, cell):
        if x % 2 == 0:
            return shade(px, 0.8)

    def plaid(px, cx, cy, x, y, cell):
        a, b = x % 3 == 0, y % 3 == 0
        if a and b:
            return shade(px, 0.62)
        if a or b:
            return shade(px, 0.8)

    def belt(px, cx, cy, x, y, cell):
        top = cell['top'][x]
        if top is not None and y in (top, top + 1):
            return shade(px, 0.45) if not (cell['row'] == 0 and x in (7, 8) and y == top) else (236, 236, 236, 255)

    def cuffs(px, cx, cy, x, y, cell):
        bot = cell['bot'][x]
        if bot is not None and y == bot:
            return shade(px, 1.12)
        if bot is not None and y == bot - 1:
            return shade(px, 0.72)

    for f in sorted(os.listdir(d)):
        if not f.endswith('.png') or f.count('_') != 1:
            continue
        base = Image.open(os.path.join(d, f)).convert('RGBA')
        px = base.load()
        opaque = [px[x, y] for y in range(base.size[1]) for x in range(base.size[0]) if px[x, y][3]]
        if not opaque or any(max(p[:3]) - min(p[:3]) > 24 for p in opaque):
            continue   # coloured art: left as it is
        for name, fn in (('stripes', stripes), ('plaid', plaid), ('belt', belt), ('cuffs', cuffs)):
            im = base.copy()
            q = im.load()
            for cy in range(base.size[1] // 32):
                for cx in range(4):
                    fill = lambda x, y: px[cx * 16 + x, cy * 32 + y][3] and lum(px[cx * 16 + x, cy * 32 + y]) >= 110
                    cell = {'row': cy % 4,
                            'top': [next((y for y in range(32) if fill(x, y)), None) for x in range(16)],
                            'bot': [next((y for y in range(31, -1, -1) if fill(x, y)), None) for x in range(16)]}
                    for y in range(32):
                        for x in range(16):
                            if fill(x, y):
                                v = fn(px[cx * 16 + x, cy * 32 + y], cx, cy, x, y, cell)
                                if v:
                                    q[cx * 16 + x, cy * 32 + y] = v
            save(im, os.path.join(d, f[:-4] + '_' + name + '.png'), made)


def slice_cells(sheet_name, out_dir, prefix, cw, ch, per_row, cells_each, src, out, made, keep=None):
    path = os.path.join(src, PREFIX + sheet_name)
    if not os.path.exists(path):
        return False
    sheet = Image.open(path).convert('RGBA')
    across = per_row
    rows = sheet.size[1] // (ch * cells_each)
    for i in range(across * rows):
        x, y = i % across * cw, i // across * ch * cells_each
        im = sheet.crop((x, y, x + cw, y + ch * cells_each))
        if keep:
            im = keep(im)
        if not empty(im):
            save(im, os.path.join(out, out_dir, f'{prefix}_{i:03d}.png'), made)
    return True


def slice_hair(src, out, made):
    """The rip packs two files side by side: hairstyles.png (left 128 px, 3
    cells a style: down, right, up) and hairstyles2.png (right 128 px, 4
    cells: down, right, up, left)."""
    sheet = Image.open(os.path.join(src, PREFIX + 'Hairstyles.png')).convert('RGBA')
    n = 0
    for x0, cells in ((0, 3), (128, 4)):
        for by in range(0, sheet.size[1] - 32 * cells + 1, 32 * cells):
            for c in range(8):
                im = sheet.crop((x0 + c * 16, by, x0 + c * 16 + 16, by + 32 * cells))
                if not empty(im):
                    save(im, os.path.join(out, 'hair', f'hair_{n:03d}.png'), made)
                n += 1


def plain_shirt(bodies, out, made):
    """A plain shirt: the male body's chest (8x8 at 4,14, every direction) in greys."""
    body = bodies['male']
    im = Image.new('RGBA', (8, 32))
    for r in range(4):
        cell = body.crop((4, r * 32 + 14, 12, r * 32 + 22))
        px = cell.load()
        for y in range(8):
            for x in range(8):
                rr, g, b, a = px[x, y]
                if a:
                    v = int(0.3 * rr + 0.59 * g + 0.11 * b)
                    px[x, y] = (v, v, v, 255)
        im.alpha_composite(cell, (0, r * 8))
    save(im, os.path.join(out, 'shirts', 'shirt_plain.png'), made)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[1])
    ap.add_argument('--src', default=os.path.join(os.path.expanduser('~'), 'Downloads'))
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'wardrobe'))
    a = ap.parse_args()
    made = []
    bodies = slice_bodies(a.src, a.out, made)
    slice_pants(a.src, a.out, made)
    pants_variants(a.out, made)
    slice_hair(a.src, a.out, made)
    slice_cells('Hats.png', 'hats', 'hat', 20, 20, 12, 4, a.src, a.out, made)
    # accessories: down and side; nothing on the side means it only shows from the front
    slice_cells('Accessories.png', 'accessories', 'acc', 16, 16, 8, 2, a.src, a.out, made)
    shirts = slice_cells('Shirts.png', 'shirts', 'shirt', 8, 8, 16, 4, a.src, a.out, made,
                         keep=None)
    if not shirts:
        plain_shirt(bodies, a.out, made)
    print(f'{len(made)} PNGs -> {os.path.normpath(a.out)}' + ('' if shirts else ' (no Shirts sheet: made shirt_plain only)'))


if __name__ == '__main__':
    main()
