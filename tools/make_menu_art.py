#!/usr/bin/env python3
"""
Draws the title screen art into assets/ui/ as PNGs:

  title_sky.png      480x480  sky, far mountains, hills and a tree line (opaque)
  title_logo.png     the "CaptureIt" logo wrapped in vines (transparent background)
  cloud_1..4.png     clouds that drift across the sky
  vine_1..4.png      vine strands that hang from the logo and sway

Everything is pixel art drawn at half size and doubled, so it matches the
game's chunky look. The firmware only copies these pixels (see TITLE SCREEN in
main.c) — to change the look, edit this script and run it again, or paint over
the PNGs in any editor. They're turned into RGB565 at build time like every
other sprite (tools/png_to_rgb565.py); fully transparent pixels become
0x0000, the see-through colour.

The strand anchors (where the vines hang from the logo) are printed at the
end — if they move, copy them into k_title_strands[] in main.c.

Run with the ESP-IDF Python (it has Pillow):
  python tools/make_menu_art.py [--preview out.png]
"""
import argparse
import math
import os
import random

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'assets', 'ui')
SCALE = 2          # art is drawn at half size, then every pixel is doubled
W = H = 480 // SCALE


# ---------------------------------------------------------------- helpers

def lerp(a, b, t):
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def up(img):
    return img.resize((img.width * SCALE, img.height * SCALE), Image.NEAREST)


def save(img, name):
    os.makedirs(OUT, exist_ok=True)
    up(img).save(os.path.join(OUT, name))


def dilate(s, r=1):
    out = set(s)
    for x, y in s:
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                out.add((x + dx, y + dy))
    return out


# ---------------------------------------------------------------- the sky

def ridge(x, seed, parts):
    return sum(a * math.sin(x * f + seed * p) for a, f, p in parts)


def draw_sky():
    img = Image.new('RGB', (W, H))
    px = img.load()
    # sky: hard pixel-art bands, checkerboard-dithered where two meet
    bands = [(52, 116, 210), (64, 132, 222), (80, 150, 232), (98, 168, 240),
             (120, 186, 246), (146, 204, 250), (176, 222, 252), (204, 236, 253)]
    horizon = 168
    band_h = horizon / len(bands)
    for y in range(H):
        for x in range(W):
            f = y / band_h
            i = min(int(f), len(bands) - 1)
            c = bands[i]
            if f - int(f) > 0.8 and i + 1 < len(bands) and (x + y) % 2 == 0:
                c = bands[i + 1]
            px[x, y] = c

    # far mountains: soft blue, lit on one side, a little snow on the peaks
    far = [(9, 0.045, 1.0), (5, 0.11, 2.3), (2.5, 0.23, 0.7)]
    for x in range(W):
        top = int(150 - ridge(x, 1, far))
        slope = ridge(x + 1, 1, far) - ridge(x - 1, 1, far)
        for y in range(max(top, 0), H):
            d = y - top
            if d < 2 and top < 141:
                c = (236, 244, 252)
            elif slope > 0:
                c = (150, 184, 224)
            else:
                c = (128, 164, 210)
            if d > 18:
                c = lerp(c, (160, 196, 230), 0.4)
            px[x, y] = c

    # rolling hills, two rows, darker and greener toward the front
    def hills(base, parts, seed, lit, body, shade):
        for x in range(W):
            top = int(base - ridge(x, seed, parts))
            slope = ridge(x + 1, seed, parts) - ridge(x - 1, seed, parts)
            for y in range(max(top, 0), H):
                d = y - top
                if d == 0 or (d < 3 and slope > 0):
                    c = lit
                elif slope < -0.3 and d < 6 and (x + y) % 2 == 0:
                    c = shade
                else:
                    c = body
                px[x, y] = c
    hills(186, [(6, 0.03, 0.4), (3, 0.09, 1.7)], 3, (138, 200, 132), (98, 170, 112), (80, 150, 100))
    hills(202, [(5, 0.05, 2.1), (3, 0.13, 0.3)], 7, (126, 196, 88), (84, 160, 70), (66, 138, 60))

    # tree line: overlapping round canopies along the bottom
    rnd = random.Random(7)
    trees = []
    x = -8
    while x < W + 8:
        trees.append((x, 214 + rnd.randint(-6, 6), rnd.randint(9, 14)))
        x += rnd.randint(10, 16)
    for cx, cy, r in sorted(trees, key=lambda t: t[1]):
        for y in range(cy - r - 1, H):
            for x in range(cx - r - 1, cx + r + 2):
                if not (0 <= x < W and 0 <= y < H):
                    continue
                dx, dy = x - cx, y - cy
                inside = abs(dx) <= r if y > cy else dx * dx + dy * dy <= r * r   # canopies run down off screen
                if not inside:
                    continue
                if (dx * dx + dy * dy > (r - 1) ** 2) and y <= cy:
                    c = (30, 80, 44)                       # outline
                elif dx < 0 and dy < -r // 3 and dx * dx + dy * dy < (r * 0.8) ** 2:
                    c = (92, 166, 76)                      # lit top-left
                elif dx > r // 3 or y > cy + 2:
                    c = (36, 96, 52)
                else:
                    c = (54, 126, 62)
                if y > cy + 8 and (x // 2 + y // 2) % 2 == 0:
                    c = (32, 86, 48)
                px[x, y] = c
    return img


# ---------------------------------------------------------------- clouds

def draw_cloud(seed, w, h, puffs):
    rnd = random.Random(seed)
    circles = []
    for i in range(puffs):
        t = (i + 0.5) / puffs
        r = rnd.uniform(0.28, 0.46) * h * (1.25 - abs(t - 0.5))
        circles.append((6 + t * (w - 12), h - 3 - r * rnd.uniform(0.75, 1.05), r))
    flat = h - 4                                          # clouds sit on a flat-ish bottom
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    px = img.load()

    def inside(x, y):
        return y <= flat and any((x - cx) ** 2 + (y - cy) ** 2 <= r * r for cx, cy, r in circles)

    for y in range(h):
        for x in range(w):
            if not inside(x + 0.5, y + 0.5):
                continue
            frac = y / h
            if not inside(x + 0.5, y - 0.5) and frac < 0.55:
                c = (255, 255, 255)
            elif not inside(x + 0.5, y + 2.5) or frac > 0.78:
                c = (180, 206, 242)
            elif frac > 0.6:
                c = (212, 228, 250)
            else:
                c = (242, 248, 255)
            for cx, cy, r in circles:                     # the lower-right of each puff is a little shaded
                dx, dy = x + 0.5 - cx, y + 0.5 - cy
                if dx * dx + dy * dy <= r * r and dy > r * 0.35 and dx > -r * 0.2 and c == (242, 248, 255):
                    c = (226, 238, 252)
            px[x, y] = c + (255,)
    return img


# ---------------------------------------------------------------- the logo

LOGO_W, LOGO_H = 236, 84
TEXT = 'CaptureIt'
FONT_FILES = ('C:/Windows/Fonts/seguibl.ttf', 'C:/Windows/Fonts/ariblk.ttf')   # a heavy font, drawn without smoothing
FONT_SIZE = 40
TEXT_TOP = 16             # top of the tallest letter

VINE_DARK, VINE, VINE_LIT, VINE_EDGE = (44, 104, 38), (78, 152, 52), (136, 198, 82), (22, 56, 22)
LEAF, LEAF_LIT, LEAF_DARK, LEAF_EDGE = (86, 168, 58), (152, 214, 98), (58, 128, 46), (24, 64, 26)


def text_mask():
    """The logo's letters as a set of pixels: each letter drawn on its own,
    bobbed up/down and tilted a little so the word looks hand-made."""
    font = next((ImageFont.truetype(f, FONT_SIZE) for f in FONT_FILES if os.path.exists(f)), None)
    if font is None:
        font = ImageFont.load_default()
    bob = [1, -1, 0, -2, 1, -1, 0, -2, 1]
    tilt = [-4, 3, -2, 4, -3, 2, -4, 3, -2]
    x = (LOGO_W - font.getlength(TEXT) - 2 * (len(TEXT) - 1)) / 2
    top = min(font.getbbox(ch)[1] for ch in TEXT)
    m = set()
    for i, ch in enumerate(TEXT):
        adv = font.getlength(ch)
        g = Image.new('L', (int(adv) + 16, FONT_SIZE + 24), 0)
        d = ImageDraw.Draw(g)
        d.fontmode = '1'                                  # hard pixel edges
        d.text((8, 8), ch, font=font, fill=255)
        g = g.rotate(tilt[i % len(tilt)], resample=Image.NEAREST, center=(8 + adv / 2, 8 + FONT_SIZE * 0.6))
        gx, gy = int(round(x)) - 8, TEXT_TOP - top - 8 + bob[i % len(bob)]
        gp = g.load()
        for yy in range(g.height):
            for xx in range(g.width):
                if gp[xx, yy] > 127:
                    m.add((gx + xx, gy + yy))
        x += adv + 2
    xs = [p[0] for p in m]
    ys = [p[1] for p in m]
    return m, min(xs), max(xs), min(ys), max(ys)


def draw_logo():
    img = Image.new('RGBA', (LOGO_W, LOGO_H), (0, 0, 0, 0))
    px = img.load()
    tm, tx0, tx1, ty0, ty1 = text_mask()
    rnd = random.Random(5)

    def put(p, c):
        if 0 <= p[0] < LOGO_W and 0 <= p[1] < LOGO_H:
            px[p] = c + (255,)

    # Two vines: one along the top of the word, one along the bottom. Each
    # dips into the letters and back out — in front where it dips in, behind
    # where it pulls away — so it wraps the word without hiding it.
    vines = [  # base y, amplitude, period, phase, which way is "out" (-1 up, 1 down)
        (ty0 + 3, 4.5, 31.0, 0.4, -1),
        (ty1 - 5, 4.5, 29.0, 2.1, 1),
    ]
    back, front = {}, {}
    leaves = []                                            # x, y, angle, size, layer
    for base, amp, period, phase, out in vines:
        prev_leaf = -99.0
        x = tx0 - 12.0
        while x < tx1 + 12:
            y = base + amp * math.sin(2 * math.pi * x / period + phase)
            layer = front if (y - base) * -out > 0 else back
            for oy in (-1, 0, 1):
                layer[(int(round(x)), int(round(y)) + oy)] = VINE_LIT if oy < 0 else VINE if oy == 0 else VINE_DARK
            if x - prev_leaf > 6 + rnd.random() * 4:
                prev_leaf = x
                side = out if rnd.random() < 0.8 else -out   # mostly pointing away from the word
                ang = side * math.pi / 2 + rnd.uniform(-0.9, 0.9)
                leaves.append((x, y + side * 1.2, ang, rnd.uniform(2.4, 3.4), front if side == out else layer))
            x += 0.25
        # each end curls round into a little loop
        for end, direction in ((tx0 - 12.0, -1), (tx1 + 12.0, 1)):
            y0 = base + amp * math.sin(2 * math.pi * end / period + phase)
            for k in range(40):
                a = k / 40 * 1.7 * math.pi
                r = 4.5 - k * 0.07
                back[(int(round(end + direction * r * math.sin(a))), int(round(y0 - out * (r - r * math.cos(a)))))] = VINE

    # strands hang from the bottom vine's low points — not all of them, so they're uneven
    base, amp, period, phase, out = vines[1]
    anchors = []
    k = 0
    while True:
        x = ((0.25 - phase / (2 * math.pi)) + k) * period
        k += 1
        if x < tx0 - 6:
            continue
        if x > tx1 + 6:
            break
        if k % 4 != 2:
            anchors.append((int(round(x)), int(round(base + amp)) + 1))

    def stroke(layer):
        for p in dilate(set(layer)) - set(layer):
            put(p, VINE_EDGE)
        for p, c in layer.items():
            put(p, c)

    def leaf(x, y, ang, size):
        ca, sa = math.cos(ang), math.sin(ang)
        pts = {}
        for yy in range(int(y - size * 2) - 1, int(y + size * 2) + 2):
            for xx in range(int(x - size * 2) - 1, int(x + size * 2) + 2):
                dx, dy = xx + 0.5 - x, yy + 0.5 - y
                u = dx * ca + dy * sa                       # along the leaf from the stem
                v = -dx * sa + dy * ca
                if 0 <= u <= size * 2:
                    half = size * 0.62 * math.sin(math.pi * u / (size * 2))
                    if abs(v) <= half:
                        pts[(xx, yy)] = LEAF_LIT if v < -half * 0.2 else (LEAF_DARK if v > half * 0.55 else LEAF)
        for p in dilate(set(pts)) - set(pts):
            if 0 <= p[0] < LOGO_W and 0 <= p[1] < LOGO_H and px[p][3] == 0:
                put(p, LEAF_EDGE)
        for p, c in pts.items():
            put(p, c)

    stroke(back)
    for lf in leaves:
        if lf[4] is back:
            leaf(*lf[:4])

    # the letters: drop shadow, dark outline, banded warm fill with a bevel
    outline = dilate(tm)
    for p in {(x + 2, y + 2) for x, y in outline} - outline:
        put(p, (46, 24, 14))
    for p in outline - tm:
        put(p, (72, 36, 18))
    fills = [(255, 240, 168), (255, 224, 118), (252, 200, 82), (246, 174, 62),
             (232, 146, 50), (212, 120, 42), (184, 94, 36), (158, 74, 30)]
    for (x, y) in tm:
        c = fills[min((y - ty0) * len(fills) // (ty1 - ty0 + 1), len(fills) - 1)]
        if (x, y - 1) not in tm:
            c = (255, 251, 226)                            # lit top edge
        elif (x, y + 1) not in tm or (x + 1, y + 1) not in tm:
            c = (132, 60, 26)                              # shaded bottom edge
        elif (x - 1, y) not in tm:
            c = lerp(c, (255, 255, 232), 0.4)              # lit left edge
        put((x, y), c)

    stroke(front)
    for lf in leaves:
        if lf[4] is front:
            leaf(*lf[:4])

    # little flowers on the vines, just outside the letters
    for fx, vi in ((tx0 + 10, 0), (tx0 + 62, 1), (tx0 + 118, 0), (tx0 + 170, 1), (tx1 - 8, 0)):
        base, amp, period, phase, out = vines[vi]
        fy = int(round(base + amp * math.sin(2 * math.pi * fx / period + phase))) + out * 2
        fx = int(fx)
        petal = (255, 178, 208) if vi else (255, 250, 250)
        for dx, dy in ((-1, -1), (1, -1), (-1, 1), (1, 1), (0, -2), (0, 2), (-2, 0), (2, 0)):
            put((fx + dx, fy + dy), (126, 62, 86))
        for dx, dy in ((0, -1), (-1, 0), (1, 0), (0, 1)):
            put((fx + dx, fy + dy), petal)
        put((fx, fy), (255, 214, 72))
    return img, anchors


def draw_strand(seed, length):
    """A vine hanging straight down, leaves either side; its top row joins the logo's vine."""
    w = 13
    img = Image.new('RGBA', (w, length), (0, 0, 0, 0))
    px = img.load()
    rnd = random.Random(seed)
    mid = w // 2

    def wx(y):
        return mid + int(round(0.8 * math.sin(y / 5.0 + seed)))

    pts = {}
    for y in range(length):
        pts[(wx(y), y)] = VINE
        pts[(wx(y) + 1, y)] = VINE_DARK
    for p in dilate(set(pts)) - set(pts):
        if 0 <= p[0] < w and 0 <= p[1] < length:
            px[p] = VINE_EDGE + (255,)
    for p, c in pts.items():
        px[p] = c + (255,)
    side = rnd.choice((-1, 1))
    y = 4
    while y < length - 3:
        for yy in range(-2, 3):                            # a little leaf off to one side
            for xx in range(1, 5):
                if abs(yy - xx * 0.35) <= 1.6 - xx * 0.2:
                    p = (wx(y) + (xx + 1 if side > 0 else -xx), y + yy)
                    if 0 <= p[0] < w and 0 <= p[1] < length:
                        px[p] = (LEAF_LIT if yy < 0 else LEAF) + (255,)
        side = -side
        y += rnd.randint(4, 6)
    for dx, dy in ((0, 0), (1, 0), (0, -1), (1, -1)):   # a bud at the tip
        p = (wx(length - 1) + dx, length - 1 + dy)
        if 0 <= p[0] < w:
            px[p] = LEAF_LIT + (255,)
    return img


# ---------------------------------------------------------------- preview

LOGO_Y = 36   # where main.c puts the logo (TITLE_LOGO_Y)


def preview(path, sky, logo, clouds, strands, anchors):
    """A mock-up of the main menu (buttons roughly as main.c draws them)."""
    img = up(sky).convert('RGBA')
    for c, x, y in ((clouds[0], 20, 24), (clouds[1], 300, 10), (clouds[2], 150, 200), (clouds[3], 380, 130)):
        img.alpha_composite(up(c), (x, y))
    lx = (480 - LOGO_W * SCALE) // 2
    for i, (ax, ay) in enumerate(anchors):
        s = up(strands[i % len(strands)])
        img.alpha_composite(s, (lx + ax * SCALE - s.width // 2, LOGO_Y + ay * SCALE - 2))
    img.alpha_composite(up(logo), (lx, LOGO_Y))
    d = ImageDraw.Draw(img)
    for i, label in enumerate(('Play', 'Customize')):
        x, y, w, h = 130, 300 + i * 80, 220, 62
        d.rounded_rectangle((x, y, x + w, y + h), 10, fill=(84, 40, 16))
        d.rounded_rectangle((x + 3, y + 3, x + w - 3, y + h - 3), 8, fill=(222, 150, 70))
        d.rectangle((x + 8, y + 5, x + w - 8, y + 7), fill=(250, 208, 140))
        d.text((x + w // 2 - 20, y + 24), label, fill=(255, 244, 214))
    img.convert('RGB').save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview', help='also write a mock-up of the main menu here')
    args = ap.parse_args()

    sky = draw_sky()
    save(sky, 'title_sky.png')
    clouds = [draw_cloud(1, 58, 22, 5), draw_cloud(2, 42, 17, 4), draw_cloud(3, 74, 26, 6), draw_cloud(4, 32, 14, 3)]
    for i, c in enumerate(clouds):
        save(c, f'cloud_{i + 1}.png')
    logo, anchors = draw_logo()
    save(logo, 'title_logo.png')
    strands = [draw_strand(1, 34), draw_strand(2, 50), draw_strand(3, 24), draw_strand(4, 42)]
    for i, s in enumerate(strands):
        save(s, f'vine_{i + 1}.png')
    print(f'logo {LOGO_W * SCALE}x{LOGO_H * SCALE} px; strand anchors for k_title_strands[] (x, y inside the logo, strand):')
    for i, (ax, ay) in enumerate(anchors):
        print(f'    {{ {ax * SCALE}, {ay * SCALE}, {i % len(strands)} }},')
    if args.preview:
        preview(args.preview, sky, logo, clouds, strands, anchors)
        print('preview ->', args.preview)


if __name__ == '__main__':
    main()
