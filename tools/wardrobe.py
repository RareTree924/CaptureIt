#!/usr/bin/env python3
"""
The wardrobe: everyone's looks (the player and the market's visitors) are
put together from layers, the way Stardew Valley draws its farmer. The art
is in assets/wardrobe/ (see its README.md; tools/slice_stardew.py cut the
Stardew sheets into it). png_to_rgb565.py imports this at build time and
writes wardrobe_gen.h from it; main.c's WARDROBE section stacks the layers
into a character's frames, in its colours.

Each PNG becomes an ITEM: its colours as SHADES (RGB565 + OKLab), each pixel
a shade (0 = see-through), and what a shade is:
    keep     drawn as it is (eyes, boots, a hat's colours)
    tint     takes the item's colour (hair, shirt, pants; grey accessories
             like beards take the hair's)
    skin     a body's skin tones (its most-used colour and its shading ramp)
    sleeve   a body's arm colours that aren't on its body: the sleeves,
             which take the shirt's colour
A colour change moves every shade of a part from the part's middle shade
onto the new colour in OKLab (recolor()): shading, highlights and outlines
stay put. recolor(), random_outfit() and compose() are copies of
ward_shade_565(), ward_random() and ward_compose() in main.c - keep them in
step, so the preview draws what the board does.

Preview (no build needed):
    python tools/wardrobe.py --preview out.png [--seeds N | --seed S ...]
"""
import os
import json
import math
import argparse

try:
    from PIL import Image, ImageOps
except ImportError:
    Image = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', 'assets', 'wardrobe')

# kind: (folder, cell w, cell h, columns, rows it may have)
KINDS = {
    'bodies':      ('bodies', 16, 32, 4, (12,)),       # body, arms, raised arms x (down, right, left, up)
    'pants':       ('pants', 16, 32, 4, (4, 8)),       # (down, right, left, up); 8: a second fit for female* bodies
    'shirts':      ('shirts', 8, 8, 1, (4,)),          # down, right, left, up
    'hair':        ('hair', 16, 32, 1, (3, 4)),        # down, right, up, [left] (none: right mirrored)
    'hats':        ('hats', 20, 20, 1, (4,)),          # down, right, left, up
    'accessories': ('accessories', 16, 16, 1, (1, 2)), # down, right (left: mirrored); none from behind
}
P_KEEP, P_TINT, P_SKIN, P_SLEEVE = range(4)
# Who wears an item (assets/wardrobe/genders.json, set in Game Tools' Wardrobe tab):
# every list goes male, neutral, female (Customize's pages); a shopper is male or
# female and wears their own and the neutral ones. Untagged = neutral, except a
# body: female if its name starts with "female", else male.
G_MALE, G_NEUTRAL, G_FEMALE = 0, 1, 2
GENDERS_FILE = 'genders.json'
G_OF_TAG = {'m': G_MALE, 'n': G_NEUTRAL, 'f': G_FEMALE}
PART_NAMES = ('keep', 'tint', 'skin', 'sleeve')
HEAD_TOP = 4        # where a Stardew body's head starts: layers move with a frame's head (its bob)
CANVAS_W, CANVAS_H, BOX_X, BOX_Y = 20, 36, 2, 4   # a composed frame; the 16x32 body box sits at (2, 4) in it
SHIRT_X, SHIRT_Y, HAT_X, HAT_Y, ACC_Y = 4, 14, -2, -4, 2   # layer offsets from the body box (+ bob)
Q = 4096


# ---------------------------------------------------------------- colour maths
def _to_lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def _to_srgb(x):
    x = max(0.0, min(1.0, x))
    return 12.92 * x if x <= 0.0031308 else 1.055 * x ** (1 / 2.4) - 0.055


def oklab(rgb):
    r, g, b = (_to_lin(v) for v in rgb)
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l, m, s = (math.copysign(abs(v) ** (1 / 3), v) for v in (l, m, s))
    return (0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
            1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
            0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s)


def oklab_q(rgb):
    return tuple(round(v * Q) for v in oklab(rgb))


def _oklab_lin(L, a, b):
    l = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    return (4.0767416621 * l - 3.3077115913 * m + 0.2309699292 * s,
            -1.2684380046 * l + 2.6097574011 * m - 0.3413193965 * s,
            -0.0041960863 * l - 0.7034186147 * m + 1.7076147010 * s)


def oklab_to_rgb(L, a, b):
    """OKLab -> 8-bit sRGB; out-of-gamut colours lose chroma (not lightness) till they fit."""
    L = max(0.0, min(1.0, L))
    k = 1.0
    for _ in range(12):
        r, g, bb = _oklab_lin(L, a * k, b * k)
        if min(r, g, bb) >= -0.0005 and max(r, g, bb) <= 1.0005:
            break
        k *= 0.82
    else:
        r, g, bb = _oklab_lin(L, 0.0, 0.0)
    return tuple(int(round(_to_srgb(v) * 255)) for v in (r, g, bb))


def hue_diff(h1, h2):
    d = (h1 - h2) % (2 * math.pi)
    return d - 2 * math.pi if d > math.pi else d


def rgb565(rgb):
    r, g, b = rgb
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb_of565(v):
    return (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3)


SHADOW_WARM, SHADOW_COOL, HIGHLIGHT = math.radians(350), math.radians(265), math.radians(100)


def recolor(shade, ref, target):
    """Shade (rgb565, part, L, a, b) of a part whose middle shade is ref
    (L, a, b, hi) in colour target (L, a, b), all OKLab x Q: ward_shade_565()
    in main.c. The middle becomes the target; darker shades keep their
    darkness as a ratio of it (outlines stay dark), lighter ones their step
    up (squeezed under white); chroma keeps its ratio to the middle's;
    shadows lean red-purple (warm colours) or blue, highlights yellow."""
    L, a, b = (v / Q for v in shade[2:])
    Lr, ar, br, hi = (v / Q for v in ref)
    Lt, at, bt = (v / Q for v in target)
    Lt = min(max(Lt, 0.08), 0.96)
    if L <= Lr:
        L2 = Lt * L / max(Lr, 0.02)
    else:
        k = min(1.0, (0.97 - Lt) / max(hi - Lr, 0.02))
        L2 = min(0.98, Lt + (L - Lr) * max(k, 0.3))
    C, Cr, Ct = math.hypot(a, b), math.hypot(ar, br), math.hypot(at, bt)
    f = min(1.6, max(0.25, (C + 0.02) / (Cr + 0.02)))
    ht = math.atan2(bt, at)
    if L2 < Lt:
        w = (Lt - L2) / max(Lt, 0.05)
        hd = math.degrees(ht) % 360
        anchor = SHADOW_WARM if hd <= 110 or hd >= 330 else SHADOW_COOL
    else:
        w = (L2 - Lt) / max(1 - Lt, 0.05)
        anchor = HIGHLIGHT
    d = hue_diff(anchor, ht)
    lim = math.radians(20)
    h2 = ht + max(-lim, min(lim, d)) * min(1.0, w)
    C2 = Ct * f
    return oklab_to_rgb(L2, C2 * math.cos(h2), C2 * math.sin(h2))


# ---------------------------------------------------------------- items
class Item:
    pass


def _ref(labs):
    """A part's middle shade: (L, a, b, hi) x Q from its pixels' OKLab."""
    v = sorted(labs)
    if not v:
        return (Q // 2, 0, 0, Q // 2)
    Lm = v[len(v) // 2][0]
    hi = v[min(len(v) - 1, int(len(v) * 0.97))][0]
    mid = [c for c in v if abs(c[0] - Lm) <= 0.12] or v
    return (round(Lm * Q), round(sum(c[1] for c in mid) / len(mid) * Q),
            round(sum(c[2] for c in mid) / len(mid) * Q), round(hi * Q))


def load_item(path, kind):
    """One PNG of a kind -> Item, or raises ValueError (why it's left out)."""
    _, cw, ch, cols, rows_ok = KINDS[kind]
    im = Image.open(path).convert('RGBA')
    w, h = im.size
    if w != cw * cols or h % ch or h // ch not in rows_ok:
        raise ValueError(f'is {w}x{h}: a {kind} PNG is {cw * cols} wide and {" or ".join(str(r * ch) for r in rows_ok)} tall')
    px = im.load()
    it = Item()
    it.name = os.path.splitext(os.path.basename(path))[0]
    it.kind, it.w, it.h, it.cw, it.ch = kind, w, h, cw, ch
    colours, counts, rows_of = {}, {}, {}
    grid = []
    for y in range(h):
        row = []
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 128 or rgb565((r, g, b)) == 0:   # (0x0000 is see-through on the board)
                row.append(None)
                continue
            c = (r, g, b)
            row.append(c)
            counts[c] = counts.get(c, 0) + 1
            rows_of.setdefault(c, set()).add(y // ch)
        grid.append(row)
    lab = {c: oklab(c) for c in counts}
    part = {}
    if kind == 'bodies':
        body = [c for c in counts if any(r < 4 for r in rows_of[c])]
        main = max(body, key=lambda c: sum(1 for y in range(4 * ch) for x in range(w) if grid[y][x] == c)) if body else None

        def ramp(c):   # the skin's shading ramp: nearly the same (a, b) / L and hue as its main tone
            L1, a1, b1 = lab[c]
            L2, a2, b2 = lab[main]
            d = math.hypot(a1 / max(L1, .05) - a2 / max(L2, .05), b1 / max(L1, .05) - b2 / max(L2, .05))
            return d <= 0.2 and math.hypot(a1, b1) >= 0.025 and \
                abs(hue_diff(math.atan2(b1, a1), math.atan2(b2, a2))) <= math.radians(40)
        for c in counts:
            part[c] = P_SKIN if main and c in body and ramp(c) else P_KEEP if c in body else \
                P_SKIN if main and ramp(c) else P_SLEEVE
    elif kind == 'hats':
        part = {c: P_KEEP for c in counts}
    elif kind == 'accessories':   # grey art (beards) takes the hair's colour; coloured art stays
        grey = sum(math.hypot(*lab[c][1:]) * n for c, n in counts.items()) / max(1, sum(counts.values())) < 0.035
        part = {c: P_TINT if grey else P_KEEP for c in counts}
    else:
        part = {c: P_TINT for c in counts}
    shades, ix = [], {}
    for c in sorted(counts, key=lambda c: (part[c], lab[c][0])):
        ix[c] = len(shades)
        shades.append((rgb565(c), part[c]) + tuple(round(v * Q) for v in lab[c]))
    if len(shades) > 255:
        raise ValueError(f'has {len(shades)} colours: the most is 255')
    it.shades = shades
    it.map = [0 if c is None else ix[c] + 1 for row in grid for c in row]
    it.refs = [_ref([lab[c] for c in counts for _ in range(counts[c]) if part[c] == p]) for p in range(4)]
    it.fit2 = kind == 'bodies' and it.name.lower().startswith('female')
    # grey art (Stardew's pants, hair, beards): made to take a colour; coloured art (most shirts) looks its own
    it.grey = sum(math.hypot(*lab[c][1:]) * n for c, n in counts.items()) / max(1, sum(counts.values())) < 0.035
    it.bob = None
    if kind == 'bodies':   # each frame's head, down from a Stardew body's: the layers above move with it
        it.bob = []
        for r in range(4):
            for c in range(4):
                top = next((y for y in range(ch) if any(grid[r * ch + y][c * cw + x] for x in range(cw))), HEAD_TOP)
                it.bob.append(top - HEAD_TOP)
    return it


def load_genders(root=ROOT, warn=print):
    """genders.json: {folder: {item name: "m" | "n" | "f"}} ({} if there's none yet)."""
    path = os.path.join(root, GENDERS_FILE)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            data = json.load(f)
        return {k: v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}
    except (OSError, ValueError) as e:
        warn(f'wardrobe/{GENDERS_FILE}: {e} - every item counts as neutral')
        return {}


def load_wardrobe(root=ROOT, warn=print):
    """{kind: [Item, ...]}, each list male, then neutral, then female, by name within those."""
    tags = load_genders(root, warn)
    out = {}
    for kind, (folder, *_rest) in KINDS.items():
        d = os.path.join(root, folder)
        items = []
        for f in sorted(os.listdir(d)) if os.path.isdir(d) else []:
            if not f.lower().endswith('.png'):
                continue
            try:
                it = load_item(os.path.join(d, f), kind)
            except ValueError as e:
                warn(f'wardrobe/{folder}/{f} {e} - left out')
                continue
            default = (G_FEMALE if it.name.lower().startswith('female') else G_MALE) if kind == 'bodies' else G_NEUTRAL
            it.gender = G_OF_TAG.get(tags.get(folder, {}).get(it.name), default)
            items.append(it)
        items.sort(key=lambda it: (it.gender, it.name))
        out[kind] = items
    return out


# ---------------------------------------------------------------- what people wear
# (r, g, b) of the middle shade, weight. Emitted into the board's tables, so change them here only.
SKIN = (   # lightest to darkest
    ((255, 214, 180), 3), ((249, 174, 137), 4), ((228, 160, 118), 4), ((206, 134, 92), 3),
    ((168, 102, 66), 3), ((128, 76, 50), 3), ((92, 54, 38), 2),
)
HAIR = (   # black, dark brown, brown, chestnut, auburn, ginger, strawberry, golden, dark blond, platinum, grey, white
    ((38, 31, 36), 8), ((68, 44, 31), 9), ((106, 66, 40), 8), ((132, 64, 38), 5), ((150, 54, 36), 4),
    ((196, 94, 42), 5), ((214, 142, 98), 3), ((224, 178, 88), 7), ((172, 132, 74), 5), ((232, 222, 182), 3),
    ((148, 146, 150), 3), ((214, 214, 220), 3),
    # dyed: blue, pink, purple, green, red
    ((66, 106, 192), 1), ((226, 110, 170), 1), ((132, 82, 182), 1), ((72, 152, 102), 1), ((190, 34, 44), 1),
)
TOPS = (
    ((236, 236, 230), 4), ((232, 220, 190), 3), ((180, 180, 184), 3), ((120, 122, 128), 3), ((66, 68, 74), 3),
    ((42, 40, 46), 3), ((196, 50, 48), 4), ((150, 32, 52), 3), ((232, 112, 92), 3), ((226, 130, 50), 3),
    ((210, 170, 62), 3), ((236, 206, 82), 2), ((122, 130, 62), 3), ((128, 176, 72), 2), ((62, 142, 72), 3),
    ((42, 92, 62), 3), ((42, 140, 140), 3), ((142, 210, 182), 2), ((112, 170, 226), 3), ((62, 102, 200), 4),
    ((38, 52, 102), 3), ((82, 72, 162), 2), ((132, 72, 172), 2), ((182, 152, 222), 2), ((230, 142, 182), 2),
    ((190, 62, 142), 2), ((122, 82, 52), 3), ((190, 150, 102), 3), ((112, 42, 52), 2), ((82, 112, 162), 3),
)
BOTTOMS = (
    ((62, 92, 150), 4), ((42, 58, 102), 4), ((112, 142, 190), 2), ((42, 42, 48), 4), ((72, 74, 82), 3),
    ((122, 122, 128), 2), ((186, 166, 118), 3), ((160, 122, 78), 2), ((102, 72, 50), 3), ((98, 102, 62), 2),
    ((42, 46, 82), 2), ((222, 212, 188), 1), ((112, 38, 50), 1), ((48, 84, 58), 1), ((92, 62, 132), 1),
)
PALETTES = (('skin', SKIN), ('hair', HAIR), ('tops', TOPS), ('bottoms', BOTTOMS))
ACC_PER_MILLE, HAT_PER_MILLE = 250, 180   # a visitor wears an accessory / a hat


class Rng:
    """ward_rand() in main.c: the same numbers from the same seed."""
    def __init__(self, seed):
        s = seed & 0xFFFFFFFF          # stirred first: seeds close together look nothing alike
        s ^= s >> 16
        s = (s * 0x7FEB352D) & 0xFFFFFFFF
        s ^= s >> 15
        s = (s * 0x846CA68B) & 0xFFFFFFFF
        s ^= s >> 16
        self.s = s

    def next(self):
        self.s = (self.s * 1664525 + 1013904223) & 0xFFFFFFFF
        return self.s >> 8


def _pick(rng, pal):
    """A weighted pick from a palette (OKLab ints), a little different each time."""
    tot = sum(w for _, w in pal)
    r = rng.next() % tot
    for (L, a, b), w in pal:
        if r < w:
            break
        r -= w
    dl = (rng.next() % 61) - 30                  # lightness +-0.03 (x1000)
    dc = 90 + rng.next() % 21                    # chroma 90..110 %
    dh = math.radians((rng.next() % 13) - 6)     # hue +-6 degrees
    ca, sa = math.cos(dh), math.sin(dh)
    return (L + int(dl * Q / 1000), int((a * ca - b * sa) * dc / 100), int((a * sa + b * ca) * dc / 100))


def _dist(c1, c2):
    return math.sqrt(sum((u - v) ** 2 for u, v in zip(c1, c2))) / Q


class Outfit:
    """Item indexes (-1: none), colours (OKLab ints; None: the art's own) and who (G_MALE / G_FEMALE)."""
    def __init__(self, **kw):
        self.body = self.hair = self.shirt = self.pants = 0
        self.acc = self.hat = -1
        self.gender = G_MALE
        self.skin = self.hair_c = self.shirt_c = self.pants_c = None
        self.__dict__.update(kw)


def random_outfit(seed, wd):
    """A visitor's outfit from their seed: ward_random() in main.c."""
    rng = Rng(seed)
    P = {name: [(oklab_q(rgb), w) for rgb, w in pal] for name, pal in PALETTES}
    n = {k: len(v) for k, v in wd.items()}
    o = Outfit()
    o.gender = G_MALE if rng.next() % 2 == 0 else G_FEMALE

    def item(kind, r):   # one of theirs or a neutral one (any, if there's none); -1: the kind's empty
        ok = [i for i, it in enumerate(wd[kind]) if it.gender in (G_NEUTRAL, o.gender)] or list(range(n[kind]))
        return ok[r % len(ok)] if ok else -1
    o.body = max(0, item('bodies', rng.next()))
    o.hair = max(0, item('hair', rng.next()))
    o.shirt = max(0, item('shirts', rng.next()))
    o.pants = max(0, item('pants', rng.next()))
    pick, chance = rng.next(), rng.next()   # (always both: the same numbers follow, worn or not)
    o.acc = item('accessories', pick) if chance % 1000 < ACC_PER_MILLE else -1
    pick, chance = rng.next(), rng.next()
    o.hat = item('hats', pick) if chance % 1000 < HAT_PER_MILLE else -1

    def pick(name, away=None, d=0.0):
        c = _pick(rng, P[name])
        for _ in range(6):
            if away is None or _dist(c, away) >= d:
                break
            c = _pick(rng, P[name])
        return c
    o.skin = pick('skin')
    o.hair_c = pick('hair')
    o.shirt_c = pick('tops', o.hair_c, 0.08)
    o.pants_c = pick('bottoms', o.shirt_c, 0.12)
    if wd['shirts'] and not wd['shirts'][o.shirt].grey:
        o.shirt_c = None   # a coloured shirt: worn as drawn (its colour was picked all the same: the same numbers follow)
    return o


# ---------------------------------------------------------------- stacking the layers
ROW_OF_DIR = {'down': 0, 'up': 3, 'left': 2, 'right': 1}   # the game's directions -> the strips' rows
GAME_DIRS = ('down', 'up', 'left', 'right')                 # player_dir_t order


def _lut(item, targets):
    """Shade + 1 -> (r, g, b) for an item, targets: {part: colour or None (as drawn)}."""
    lut = [None]
    for sh in item.shades:
        t = targets.get(sh[1])
        lut.append(rgb_of565(sh[0]) if t is None else recolor(sh, item.refs[sh[1]], t))
    return lut


def _ref_colour(ref):
    return ref[:3]


def compose(o, wd, held=False):
    """The 16 frames [dir * 4 + frame] (player_dir_t order) as CANVAS_H rows of (r,g,b) / None: ward_compose()."""
    body = wd['bodies'][o.body]
    shirt = wd['shirts'][o.shirt] if wd['shirts'] else None
    shirt_c = o.shirt_c if o.shirt_c is not None else (_ref_colour(shirt.refs[P_TINT]) if shirt else None)
    layers = {   # item, its look-up table
        'body': (body, _lut(body, {P_SKIN: o.skin, P_SLEEVE: shirt_c})),
        'pants': (wd['pants'][o.pants], _lut(wd['pants'][o.pants], {P_TINT: o.pants_c})) if wd['pants'] else None,
        'shirt': (shirt, _lut(shirt, {P_TINT: o.shirt_c})) if shirt else None,
        'hair': (wd['hair'][o.hair], _lut(wd['hair'][o.hair], {P_TINT: o.hair_c})) if wd['hair'] else None,
        'acc': (wd['accessories'][o.acc], _lut(wd['accessories'][o.acc], {P_TINT: o.hair_c})) if o.acc >= 0 else None,
        'hat': (wd['hats'][o.hat], _lut(wd['hats'][o.hat], {})) if o.hat >= 0 else None,
    }
    out = []
    for d in GAME_DIRS:
        r = ROW_OF_DIR[d]
        for f in range(4):
            cv = [[None] * CANVAS_W for _ in range(CANVAS_H)]
            dy = body.bob[r * 4 + f]

            def blit(layer, cx, cy, x0, y0, mirror=False):
                if not layer:
                    return
                it, lut = layer
                for y in range(it.ch):
                    for x in range(it.cw):
                        v = it.map[(cy * it.ch + y) * it.w + cx * it.cw + (it.cw - 1 - x if mirror else x)]
                        X, Y = x0 + x, y0 + y
                        if v and 0 <= X < CANVAS_W and 0 <= Y < CANVAS_H:
                            cv[Y][X] = lut[v]
            blit(layers['body'], f, r, BOX_X, BOX_Y)
            if layers['pants']:
                fit = 4 if body.fit2 and layers['pants'][0].h // 32 == 8 else 0
                blit(layers['pants'], f, fit + r, BOX_X, BOX_Y)
            blit(layers['shirt'], 0, r, BOX_X + SHIRT_X, BOX_Y + SHIRT_Y + dy)
            if layers['acc'] and d != 'up':
                acc = layers['acc'][0]
                side = acc.h // acc.ch > 1
                if d == 'down' or side:
                    blit(layers['acc'], 0, 0 if d == 'down' else 1, BOX_X, BOX_Y + ACC_Y + dy, d == 'left')
            if layers['hair']:
                hair = layers['hair'][0]
                own_left = d == 'left' and hair.h // hair.ch > 3
                blit(layers['hair'], 0, 3 if own_left else {'down': 0, 'right': 1, 'left': 1, 'up': 2}[d],
                     BOX_X, BOX_Y + dy, d == 'left' and not own_left)
            blit(layers['hat'], 0, r, BOX_X + HAT_X, BOX_Y + HAT_Y + dy)
            blit(layers['body'], f, (8 if held else 4) + r, BOX_X, BOX_Y)   # the arms, over the shirt and the hat
            out.append(cv)
    return out


# ---------------------------------------------------------------- the build: wardrobe_gen.h
def emit(out_dir, root=ROOT, warn=print):
    """Writes wardrobe_gen.h (all items + palettes) into out_dir; returns {kind: count}."""
    wd = load_wardrobe(root, warn)
    if not wd['bodies']:
        warn('wardrobe: no bodies (assets/wardrobe/bodies/*.png) - everyone is drawn as a placeholder')
    t = ['// AUTO-GENERATED by tools/wardrobe.py from assets/wardrobe/ - do not edit by hand.',
         '#pragma once',
         '#include <stdint.h>',
         f'#define WARD_Q {Q}',
         '#define WARD_P_KEEP 0      // drawn as it is',
         '#define WARD_P_TINT 1      // takes the item\'s colour',
         '#define WARD_P_SKIN 2      // a body\'s skin',
         '#define WARD_P_SLEEVE 3    // a body\'s sleeves: the shirt\'s colour',
         f'#define WARD_G_MALE {G_MALE}       // an item\'s gender: every list is male, neutral, female',
         f'#define WARD_G_NEUTRAL {G_NEUTRAL}',
         f'#define WARD_G_FEMALE {G_FEMALE}',
         f'#define WARD_CANVAS_W {CANVAS_W}',
         f'#define WARD_CANVAS_H {CANVAS_H}',
         f'#define WARD_BOX_X {BOX_X}',
         f'#define WARD_BOX_Y {BOX_Y}',
         f'#define WARD_SHIRT_X {SHIRT_X}',
         f'#define WARD_SHIRT_Y {SHIRT_Y}',
         f'#define WARD_HAT_X {HAT_X}',
         f'#define WARD_HAT_Y {HAT_Y}',
         f'#define WARD_ACC_Y {ACC_Y}',
         f'#define WARD_ACC_PER_MILLE {ACC_PER_MILLE}',
         f'#define WARD_HAT_PER_MILLE {HAT_PER_MILLE}',
         'typedef struct { uint16_t rgb; uint8_t part; int16_t L, a, b; } ward_shade_t;',
         'typedef struct { int16_t L, a, b, hi; } ward_ref_t;   // a part\'s middle shade (hi: its lightest\'s L)',
         'typedef struct {',
         '    const char         *name;',
         '    uint16_t            w, h;     // the PNG',
         '    uint8_t             cw, ch;   // one cell (frame) of it',
         '    uint8_t             nshades;',
         '    uint8_t             fit2;     // a body: wears the pants\' second fit (rows 4-7) when they have one',
         '    uint8_t             gender;   // WARD_G_*: who wears it (genders.json)',
         '    uint8_t             grey;     // grey art (made to take a colour); else coloured (shoppers wear such a shirt as drawn)',
         '    const ward_shade_t *shades;',
         '    ward_ref_t          refs[4];  // per WARD_P_*',
         '    const int8_t       *bob;      // a body: [row * 4 + frame], how far its head is below a Stardew one\'s',
         '    const uint8_t      *map;      // w * h: 0 = see-through, else shade + 1',
         '} ward_item_t;',
         'typedef struct { int16_t L, a, b; uint8_t w; } ward_swatch_t;']
    for name, pal in PALETTES:
        t.append(f'static const ward_swatch_t k_ward_pal_{name}[] = {{')
        for i in range(0, len(pal), 4):
            t.append('    ' + ' '.join('{ %d, %d, %d, %d },' % (*oklab_q(rgb), w) for rgb, w in pal[i:i + 4]))
        t.append('};')
    counts = {}
    for kind, items in wd.items():
        for i, it in enumerate(items):
            p = f'ward_{kind}_{i}'
            t.append(f'// {kind}/{it.name}.png')
            t.append(f'static const ward_shade_t {p}_sh[{max(1, len(it.shades))}] = {{ ' +
                     ' '.join('{ 0x%04X, %d, %d, %d, %d },' % s for s in it.shades) + ' };')
            if it.bob:
                t.append(f'static const int8_t {p}_bob[16] = {{ {", ".join(str(v) for v in it.bob)} }};')
            t.append(f'static const uint8_t {p}_map[{len(it.map)}] = {{')
            for k in range(0, len(it.map), 64):
                t.append('    ' + ','.join(str(v) for v in it.map[k:k + 64]) + ',')
            t.append('};')
        t.append(f'static const ward_item_t k_ward_{kind}[] = {{')
        for i, it in enumerate(items):
            p = f'ward_{kind}_{i}'
            refs = ', '.join('{ %d, %d, %d, %d }' % r for r in it.refs)
            t.append(f'    {{ "{it.name}", {it.w}, {it.h}, {it.cw}, {it.ch}, {len(it.shades)}, {int(it.fit2)}, {it.gender}, {int(it.grey)}, {p}_sh, '
                     f'{{ {refs} }}, {p + "_bob" if it.bob else "NULL"}, {p}_map }},')
        if not items:
            t.append('    { "none", 0, 0, 1, 1, 0, 0, 1, 0, NULL, { { 0 } }, NULL, NULL },')
        t.append('};')
        t.append(f'#define WARD_N_{kind.upper()} {len(items)}')
        counts[kind] = len(items)
    text = '\n'.join(t) + '\n'
    path = os.path.join(out_dir, 'wardrobe_gen.h')
    old = open(path, encoding='utf-8').read() if os.path.exists(path) else None
    if old != text:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(text)
    return counts


# ---------------------------------------------------------------- preview
def preview(out, seeds, root=ROOT, frames=(0, 1, 8, 12, 4), held=False):
    wd = load_wardrobe(root)
    S = 4
    cw, ch = (CANVAS_W * len(frames) + 4) * S, (CANVAS_H + 2) * S
    per_row = 6
    rows = (len(seeds) + per_row - 1) // per_row
    sheet = Image.new('RGB', (per_row * cw, rows * ch), (72, 104, 72))
    for i, s in enumerate(seeds):
        fr = compose(random_outfit(s, wd), wd, held)
        for j, k in enumerate(frames):
            im = Image.new('RGBA', (CANVAS_W, CANVAS_H))
            for y in range(CANVAS_H):
                for x in range(CANVAS_W):
                    if fr[k][y][x]:
                        im.putpixel((x, y), fr[k][y][x] + (255,))
            im = im.resize((CANVAS_W * S, CANVAS_H * S), Image.NEAREST)
            sheet.paste(im, ((i % per_row) * cw + j * CANVAS_W * S, (i // per_row) * ch), im)
    sheet.save(out)


def main():
    ap = argparse.ArgumentParser(description='The wardrobe: preview random people (as the market visitors are made)')
    ap.add_argument('--preview', metavar='PNG', required=True)
    ap.add_argument('--seeds', type=int, default=24, help='people to draw (seeds 1..N)')
    ap.add_argument('--seed', type=lambda v: int(v, 0), action='append',
                    help='a visitor\'s seed (as "npc list" on the dev link prints it); repeatable')
    ap.add_argument('--held', action='store_true', help='carrying something (arms up)')
    a = ap.parse_args()
    preview(a.preview, a.seed or range(1, a.seeds + 1), held=a.held)
    print('wrote', a.preview)


if __name__ == '__main__':
    main()
