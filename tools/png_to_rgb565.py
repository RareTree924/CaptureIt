#!/usr/bin/env python3
"""
Converts the game's PNGs into row-major RGB565 C headers, one .h per PNG,
named after the PNG file (sanitized to a valid C identifier):

  <in-dir>/*.png                    sprites, by file name ("char_wave_1")
  <in-dir>/ui/*.png                 title screen art, as "ui_<name>" ("ui_title_sky")
  <in-dir>/characters/<who>/*.png   one folder per playable character, each
                                    holding that character's walking and holding
                                    frames (char_down_1.png ... char_held_right_4.png)
  <in-dir>/fx/*.png                 effects drawn see-through (rain), as "fx_<name>":
                                    the RGB565 pixels plus a second array, fx_<name>_a,
                                    with each pixel's alpha (0 = not drawn, 255 = solid)

sprites_gen.h then includes them all and lists them in two tables:
k_sprite_assets (sprites + ui art, by name) and k_character_assets (one entry
per character folder, in name order, each with its own list of frames).

Run automatically by CMake before every build (see main/CMakeLists.txt)
-- you should never need to run this by hand.

Requires Pillow:  pip install pillow --break-system-packages
"""
import os
import re
import sys
import argparse
from PIL import Image


def sanitize(name: str) -> str:
    """Turns a filename stem into a valid C identifier."""
    name = re.sub(r'[^0-9a-zA-Z_]', '_', name)
    if name[0].isdigit():
        name = '_' + name
    return name


def convert_one(png_path: str, out_dir: str, name: str) -> tuple[str, int, int]:
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    pixels = img.load()
    out_path = os.path.join(out_dir, name + '.h')

    values = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a < 128:
                rgb565 = 0x0000   # the game draws sprites with 0x0000 as transparent
            else:
                # standard RGB565 pack: 5 bits R, 6 bits G, 5 bits B
                rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            values.append(str(rgb565))

    lines = [
        f'// AUTO-GENERATED from {os.path.basename(png_path)} — do not edit by hand.',
        '#pragma once',
        '#include <stdint.h>',
        f'#define {name.upper()}_W {w}',
        f'#define {name.upper()}_H {h}',
        f'static const uint16_t {name}[{w * h}] = {{',
    ]
    for i in range(0, len(values), 16):
        lines.append('    ' + ', '.join(values[i:i + 16]) + ',')
    lines.append('};')

    text = '\n'.join(lines) + '\n'
    old = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            old = f.read()
    if old != text:                      # unchanged art doesn't make main.c recompile
        with open(out_path, 'w') as f:
            f.write(text)
    return name, w, h


def convert_fx(png_path: str, out_dir: str, name: str) -> tuple[str, int, int]:
    """Like convert_one(), but keeps the alpha channel (fx_<name>_a) so the
    game can blend semi-see-through effect art instead of cutting it off at 50%."""
    img = Image.open(png_path).convert('RGBA')
    w, h = img.size
    pixels = img.load()
    out_path = os.path.join(out_dir, name + '.h')
    rgb, alpha = [], []
    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            rgb.append(str(((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3) if a else 0))
            alpha.append(str(a))
    lines = [
        f'// AUTO-GENERATED from fx/{os.path.basename(png_path)} — do not edit by hand.',
        '#pragma once',
        '#include <stdint.h>',
        f'#define {name.upper()}_W {w}',
        f'#define {name.upper()}_H {h}',
        f'static const uint16_t {name}[{w * h}] = {{',
    ]
    for i in range(0, len(rgb), 16):
        lines.append('    ' + ', '.join(rgb[i:i + 16]) + ',')
    lines += ['};', f'static const uint8_t {name}_a[{w * h}] = {{']
    for i in range(0, len(alpha), 16):
        lines.append('    ' + ', '.join(alpha[i:i + 16]) + ',')
    lines.append('};')
    text = '\n'.join(lines) + '\n'
    old = None
    if os.path.exists(out_path):
        with open(out_path) as f:
            old = f.read()
    if old != text:
        with open(out_path, 'w') as f:
            f.write(text)
    return name, w, h


def pngs(folder: str) -> list[str]:
    if not os.path.isdir(folder):
        return []
    return sorted(f for f in os.listdir(folder) if f.lower().endswith('.png'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in-dir', required=True)
    ap.add_argument('--out-dir', required=True)
    args = ap.parse_args()

    os.makedirs(args.out_dir, exist_ok=True)
    sprites = []      # (C name, lookup name, w, h)
    for fname in pngs(args.in_dir):
        stem = os.path.splitext(fname)[0]
        n, w, h = convert_one(os.path.join(args.in_dir, fname), args.out_dir, sanitize(stem))
        sprites.append((n, n, w, h))
    ui_dir = os.path.join(args.in_dir, 'ui')
    for fname in pngs(ui_dir):
        n, w, h = convert_one(os.path.join(ui_dir, fname), args.out_dir, 'ui_' + sanitize(os.path.splitext(fname)[0]))
        sprites.append((n, n, w, h))

    fx = []           # C names of the effect headers (fx/)
    for fname in pngs(os.path.join(args.in_dir, 'fx')):
        n, _, _ = convert_fx(os.path.join(args.in_dir, 'fx', fname), args.out_dir, 'fx_' + sanitize(os.path.splitext(fname)[0]))
        fx.append(n)

    characters = []   # (folder name, C name of its table, [(C name, lookup name, w, h)])
    char_root = os.path.join(args.in_dir, 'characters')
    if os.path.isdir(char_root):
        for who in sorted(os.listdir(char_root)):
            folder = os.path.join(char_root, who)
            if not os.path.isdir(folder):
                continue
            frames = []
            for fname in pngs(folder):
                stem = os.path.splitext(fname)[0]
                n, w, h = convert_one(os.path.join(folder, fname), args.out_dir,
                                      'chr_' + sanitize(who) + '__' + sanitize(stem))
                frames.append((n, sanitize(stem), w, h))
            if frames:
                characters.append((who, 'k_chr_' + sanitize(who), frames))
            else:
                print(f'characters/{who}: no PNGs - skipped')

    # One umbrella header so main.c only needs a single #include for everything,
    # plus name -> pixels tables so code can look art up by file name
    # (e.g. "char_held_up_2") without an #ifdef per possible sprite.
    text = ['// AUTO-GENERATED — includes every converted sprite. Do not edit by hand.',
            '#pragma once',
            '#include <stddef.h>',
            '#include <stdint.h>']
    for n, _, _, _ in sprites:
        text.append(f'#include "{n}.h"')
    for _, _, frames in characters:
        for n, _, _, _ in frames:
            text.append(f'#include "{n}.h"')
    for n in fx:
        text.append(f'#include "{n}.h"')
    text += ['',
             'typedef struct { const char *name; const uint16_t *pixels; uint16_t w, h; } sprite_asset_t;',
             '',
             '// Every converted sprite (and ui/ art as "ui_<name>"), by PNG file name. Ends with a NULL-name entry.',
             'static const sprite_asset_t k_sprite_assets[] = {']
    for n, look, _, _ in sprites:
        text.append(f'    {{ "{look}", {n}, {n.upper()}_W, {n.upper()}_H }},')
    text += ['    { NULL, NULL, 0, 0 },', '};', '']
    for who, table, frames in characters:
        text.append(f'// assets/characters/{who}/')
        text.append(f'static const sprite_asset_t {table}[] = {{')
        for n, look, _, _ in frames:
            text.append(f'    {{ "{look}", {n}, {n.upper()}_W, {n.upper()}_H }},')
        text += ['    { NULL, NULL, 0, 0 },', '};', '']
    text += ['// One per folder in assets/characters/, by folder name. Ends with a NULL-name entry.',
             'typedef struct { const char *name; const sprite_asset_t *frames; } character_asset_t;',
             'static const character_asset_t k_character_assets[] = {']
    for who, table, _ in characters:
        label = who.replace(chr(92), '/').replace('"', "'")   # keep the C string literal valid
        text.append(f'    {{ "{label}", {table} }},')
    text += ['    { NULL, NULL },', '};', '']
    with open(os.path.join(args.out_dir, 'sprites_gen.h'), 'w') as f:
        f.write('\n'.join(text))

    print(f'Converted {len(sprites)} sprite PNG(s) and {len(characters)} character(s) '
          f'({sum(len(c[2]) for c in characters)} frames) -> {args.out_dir}')


if __name__ == '__main__':
    main()
