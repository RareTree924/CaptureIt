#!/usr/bin/env python3
"""
One-off: cuts the Stardew Valley monster sheet (Spriters Resource rip in
Downloads: "PC _ Computer - Stardew Valley - Monsters - Monsters.png") into
assets/monsters/<id>.c — the Monsters tab's exact format (main/monsters.h,
with its "// MONSTERS-EDITOR {json}" line so the tab opens them again) — and
the weapons sheet ("... Miscellaneous - Weapons.png") into weapon items, and
the drops they need that the game didn't have yet (slime, bug meat, bat wing,
the essences, ores, coal...) from the objects sheet ("... Harvested Crops,
Seed Packets, Minerals, Food, Equipment, & Miscell...png").

  python tools/slice_monsters.py --preview out.png    draws every monster's animations
  python tools/slice_monsters.py --write [--force]    writes the files (--force: over existing ones)

Sheet layout (the rip): blocks of 4 frames, 16 px apart, starting at x = 0,
74, 148, 222, 296, 370, 444, 518, 592; each block's rows are the walk down,
right, up, left, then death frames, then the bits it leaves (particles). A
frame is cut as the rows' own height and stood bottom-aligned in its box.
Hiders (rock crabs, bushes, sticks): each row's first frame is the disguise.
Bats: row 1's first frame is the bat hanging asleep. The top-left rocks are
left out (projectiles / rock crab pieces), and the monsters whose frames
aren't laid out like this (serpent, pepper rex, blue squid, spider, slimes,
skulls, faces, masks, the boxes...) are on the Needs You list for the
Monsters tab. Names, stats and abilities are Stardew's (approximately), or
a best guess where the sheet doesn't say which monster it is (also on Needs You).
"""
import argparse, json, os, sys
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DL = os.path.join(os.path.expanduser('~'), 'Downloads')
SHEET = os.path.join(DL, 'PC _ Computer - Stardew Valley - Monsters - Monsters.png')
WEAPONS = os.path.join(DL, 'PC _ Computer - Stardew Valley - Miscellaneous - Weapons.png')
OBJECTS_PREFIX = 'PC _ Computer - Stardew Valley - Miscellaneous - Harvested Crops'
MON_DIR = os.path.join(ROOT, 'assets', 'monsters')
ITEM_DIR = os.path.join(ROOT, 'assets', 'items')

SEQS = ['down', 'right', 'up', 'left', 'rest', 'wake', 'death', 'attack_down', 'attack_right', 'attack_up', 'attack_left']
ABIL = ['flies', 'hides', 'hops', 'erratic', 'charges', 'revives', 'heals', 'straight', 'keeps_off', 'ghostly', 'shoots']   # monsters.h MON_* bit order
SEQ_MAX, FRAME_MAX, PART, PROJ, PROJ_FRAMES = 8, 32, 16, 16, 4


def R(x, y0, y1, cols=(0, 1, 2, 3), fw=16):
    """One row of a block: its frames' cells (x, y, w, h)."""
    return [(x + fw * c, y0, fw, y1 - y0) for c in cols]


def crab(x, rows, death, parts):
    """A hider whose rows each start with its disguise (rock crabs, bushes, sticks, stumps)."""
    d, r, u, l = [R(x, *rw) for rw in rows]
    return dict(rest=[d[0]], wake=[d[0], d[1]], down=d[1:], right=r[1:], up=u[1:], left=l[1:], death=R(x, *death), parts=parts)


def bat(x, rows, parts):
    d, r, u, l = [R(x, *rw) for rw in rows]
    return dict(rest=[r[0]], wake=[r[0], d[0]], down=d, right=r[1:], up=u, left=l, parts=parts)


def walk4(x, rows, fw=16, cols=(0, 1, 2, 3)):
    d, r, u, l = [R(x, *rw, cols=cols, fw=fw) for rw in rows]
    return dict(down=d, right=r, up=u, left=l)


def S(hp, dmg, df, spd, xp, wake=5, ab=(), drops=(), ms=150, sound='', shot=None):
    """shot = (damage, speed in quarter px a tick, every ms, from tiles): it shoots (and gets 'shoots')."""
    ab = list(ab) + (['shoots'] if shot and 'shoots' not in ab else [])
    st = dict(hp=hp, damage=dmg, defense=df, speed=spd, xp=xp, wake=wake, abilities=ab, drops=[dict(item=i, chance=c, min=a, max=b) for i, c, a, b in drops], frameMs=ms, sound=sound)
    st['shot'] = shot or (0, 0, 0, 0)
    return st


# A monster's shot: the sheet's fireballs (4 frames, 8x8), or one of its own bits spun round.
FIREBALL = [(223 + 8 * k, 1390, 8, 8) for k in range(4)]


def fire(tint=None):
    return dict(cells=FIREBALL, tint=tint)


def bone(x):
    return dict(piece=(x, 729, 64, 16), spin=True)


FLY_ROWS = [(292, 305), (308, 320), (323, 338), (340, 352)]
CRAB_ROWS = [(607, 625), (631, 649), (655, 673), (679, 697)]
BUSH_ROWS = [(750, 769), (774, 793), (798, 817), (822, 841)]
BAT_ROWS = [(896, 908), (920, 933), (944, 956), (968, 980)]
BAT2_ROWS = [(1011, 1024), (1036, 1049), (1060, 1072), (1084, 1096)]
SKEL_ROWS = [(605, 634), (637, 666), (669, 698)]


def skel(x, extra):
    d, r, u = [R(x, *rw) for rw in SKEL_ROWS]
    return dict(down=d, right=r, up=u, death=R(x, 701, 729), attack_down=R(x, *extra), parts=(x, 729, 64, 16))


def shadow(x, rows, death, wake_rows, parts):
    m = walk4(x, rows)
    if death: m['death'] = R(x, *death)
    if wake_rows:   # rising out of a puddle: the puddles, then the row of it getting up (backwards when it dies)
        w = []
        for rw, cols in wake_rows: w += R(x, *rw, cols=cols)
        m['wake'], m['rest'], m['death'] = w, [w[0]], list(reversed(w))
    m['parts'] = parts
    return m


# ------------------------------------------------------------------ the monsters
MONSTERS = [
    # ---- crabs and other things that hide ----
    ('rock_crab', 'Rock Crab', crab(0, CRAB_ROWS, (709, 729), (0, 730, 64, 8)),
     S(30, 5, 1, 5, 4, wake=2, ab=['hides'], drops=[('crab', 15, 1, 1), ('stone', 40, 1, 2), ('cherry_bomb', 5, 1, 1)])),
    ('iridium_crab', 'Iridium Crab', crab(74, [(605, 625), (629, 649), (653, 673), (677, 697)], (709, 729), (74, 730, 64, 8)),
     S(240, 15, 3, 5, 20, wake=2, ab=['hides'], drops=[('crab', 25, 1, 1), ('iridium_ore', 20, 1, 2)])),
    ('lava_crab', 'Lava Crab', crab(148, CRAB_ROWS, (709, 729), (148, 730, 64, 8)),
     S(120, 15, 3, 5, 12, wake=2, ab=['hides'], drops=[('crab', 15, 1, 1), ('fire_quartz', 5, 1, 1), ('coal', 25, 1, 1)])),
    ('truffle_crab', 'Truffle Crab', crab(222, CRAB_ROWS, (709, 729), (222, 730, 64, 8)),
     S(360, 12, 2, 5, 15, wake=2, ab=['hides'], drops=[('truffle', 75, 1, 1), ('crab', 15, 1, 1)])),
    ('bush_lurker', 'Bush Lurker', crab(0, BUSH_ROWS, (853, 873), (0, 874, 64, 8)),
     S(80, 10, 1, 6, 10, wake=2, ab=['hides'], drops=[('wood', 40, 1, 3), ('bug_meat', 25, 1, 1)])),
    ('wilderness_golem', 'Wilderness Golem', crab(74, BUSH_ROWS, (846, 873), (74, 874, 64, 8)),
     S(150, 12, 2, 5, 12, wake=2, ab=['hides'], drops=[('wood', 60, 2, 5), ('hardwood', 15, 1, 1)])),
    ('stick_bug', 'Stick Bug', crab(148, BUSH_ROWS, (846, 873), (148, 874, 64, 8)),
     S(120, 12, 1, 6, 12, wake=2, ab=['hides'], drops=[('wood', 50, 1, 3), ('bug_meat', 40, 1, 1)])),
    ('mushroom_lurker', 'Mushroom Lurker', crab(222, [(747, 769), (771, 793), (795, 817), (819, 841)], (843, 865), (222, 867, 64, 14)),
     S(100, 12, 1, 5, 12, wake=2, ab=['hides'], drops=[('red_mushroom', 25, 1, 1), ('purple_mushroom', 10, 1, 1)])),
    # ---- flies and bugs ----
    ('cave_fly', 'Cave Fly', dict(**walk4(0, FLY_ROWS), parts=(0, 355, 32, 16)),
     S(22, 6, 0, 7, 10, wake=7, ab=['flies', 'erratic'], drops=[('bug_meat', 50, 1, 1)], ms=80)),
    ('frost_fly', 'Frost Fly', dict(**walk4(74, FLY_ROWS), parts=(74, 355, 32, 16)),
     S(45, 9, 0, 7, 12, wake=7, ab=['flies', 'erratic'], drops=[('bug_meat', 50, 1, 1), ('frozen_tear', 3, 1, 1)], ms=80)),
    ('lava_fly', 'Lava Fly', dict(**walk4(148, FLY_ROWS), parts=(148, 355, 32, 16)),
     S(70, 12, 1, 8, 14, wake=7, ab=['flies', 'erratic'], drops=[('bug_meat', 50, 1, 1), ('fire_quartz', 3, 1, 1)], ms=80)),
    ('mutant_fly', 'Mutant Fly', dict(**walk4(222, FLY_ROWS), parts=(222, 355, 32, 16)),
     S(50, 14, 0, 8, 15, wake=7, ab=['flies', 'erratic'], drops=[('bug_meat', 60, 1, 2), ('slime', 30, 1, 2)], ms=80)),
    ('bug', 'Bug', dict(right=R(0, 381, 392), down=R(0, 402, 416), death=R(0, 429, 439, cols=(0, 1)), parts=(0, 441, 32, 16)),
     S(1, 8, 0, 6, 1, wake=8, ab=['straight'], drops=[('bug_meat', 25, 1, 1)], ms=90)),
    ('armored_bug', 'Armored Bug', dict(right=R(74, 380, 392), down=R(74, 401, 416), death=R(74, 428, 439, cols=(0, 1)), parts=(74, 441, 32, 16)),
     S(30, 15, 6, 6, 4, wake=8, ab=['straight'], drops=[('bug_meat', 40, 1, 1)], ms=90)),
    ('fire_bug', 'Fire Bug', dict(right=R(148, 380, 392), down=R(148, 402, 416), death=R(148, 428, 439, cols=(0, 1)), parts=(148, 441, 32, 16)),
     S(20, 12, 1, 7, 4, wake=8, ab=['straight'], drops=[('bug_meat', 30, 1, 1), ('coal', 15, 1, 1)], ms=90)),
    ('grub', 'Grub', dict(down=R(0, 467, 483), right=R(0, 497, 506), up=R(0, 515, 531), left=R(0, 545, 554), death=R(0, 563, 585), parts=(0, 586, 64, 10)),
     S(20, 4, 0, 4, 3, wake=5, drops=[('bug_meat', 50, 1, 1)], ms=140)),
    ('mutant_grub', 'Mutant Grub', dict(down=R(74, 466, 483), right=R(74, 496, 506), up=R(74, 513, 531), left=R(74, 544, 554), death=R(74, 563, 585), parts=(74, 586, 64, 10)),
     S(52, 10, 0, 5, 6, wake=5, drops=[('bug_meat', 60, 1, 2), ('slime', 20, 1, 1)], ms=140)),
    ('cave_moth', 'Cave Moth', dict(down=R(148, 469, 482), right=R(148, 492, 507), up=R(148, 516, 529), left=R(148, 540, 555), parts=(148, 575, 64, 21)),
     S(40, 8, 0, 7, 8, wake=7, ab=['flies', 'erratic'], drops=[('bug_meat', 50, 1, 1)], ms=80)),
    ('cave_wasp', 'Cave Wasp', dict(down=R(222, 467, 482), right=R(222, 491, 506), up=R(222, 516, 531), left=R(222, 539, 554), parts=(222, 575, 64, 21)),
     S(60, 12, 0, 8, 10, wake=7, ab=['flies', 'charges'], drops=[('bug_meat', 40, 1, 1), ('honey', 10, 1, 1)], ms=80)),
    ('dust_sprite', 'Dust Sprite', dict(down=R(296, 470, 483), parts=(296, 484, 32, 17)),
     S(40, 6, 0, 11, 2, wake=6, ab=['hops'], drops=[('coal', 50, 1, 2)], ms=90)),
    # ---- bats ----
    ('bat', 'Bat', bat(0, BAT_ROWS, (0, 982, 32, 16)),
     S(24, 6, 0, 7, 3, wake=6, ab=['flies', 'hides'], drops=[('bat_wing', 33, 1, 1)], ms=90)),
    ('shadow_bat', 'Shadow Bat', bat(74, [(891, 908), (915, 934), (939, 956), (963, 980)], (74, 982, 32, 16)),
     S(55, 10, 0, 8, 8, wake=6, ab=['flies', 'hides'], drops=[('bat_wing', 40, 1, 1), ('void_essence', 10, 1, 1)], ms=90)),
    ('frost_bat', 'Frost Bat', bat(148, [(895, 908), (920, 933), (944, 956), (968, 980)], (148, 982, 32, 16)),
     S(36, 7, 0, 7, 7, wake=6, ab=['flies', 'hides'], drops=[('bat_wing', 33, 1, 1), ('frozen_tear', 5, 1, 1)], ms=90)),
    ('lava_bat', 'Lava Bat', bat(222, [(892, 909), (920, 933), (944, 956), (968, 980)], (222, 982, 32, 16)),
     S(80, 15, 0, 8, 15, wake=6, ab=['flies', 'hides'], drops=[('bat_wing', 40, 1, 1), ('fire_quartz', 5, 1, 1)], ms=90)),
    ('blood_bat', 'Blood Bat', bat(0, BAT2_ROWS, (0, 1098, 32, 16)),
     S(120, 18, 0, 8, 15, wake=6, ab=['flies', 'hides'], drops=[('bat_wing', 40, 1, 2)], ms=90)),
    ('iridium_bat', 'Iridium Bat', bat(74, [(1007, 1024), (1036, 1049), (1060, 1072), (1084, 1096)], (74, 1098, 32, 16)),
     S(300, 25, 0, 9, 22, wake=7, ab=['flies', 'hides'], drops=[('bat_wing', 50, 1, 2), ('iridium_ore', 10, 1, 1)], ms=90)),
    # ---- shadows ----
    ('shadow_brute', 'Shadow Brute', dict(**walk4(222, [(95, 118), (119, 142), (143, 166), (167, 190)]), death=R(222, 195, 212), attack_down=R(222, 215, 243), parts=(222, 246, 64, 8)),
     S(160, 18, 2, 6, 15, wake=6, drops=[('void_essence', 75, 1, 2), ('coal', 10, 1, 1)])),
    ('shadow_shaman', 'Shadow Shaman', dict(**walk4(296, [(94, 118), (118, 142), (142, 166), (166, 190)]), death=R(296, 195, 212), attack_down=R(296, 213, 243), parts=(296, 246, 64, 8), proj=fire('purple')),
     S(80, 15, 1, 5, 15, wake=7, ab=['heals', 'keeps_off'], drops=[('void_essence', 75, 1, 2)], shot=(15, 14, 3000, 7))),
    ('shadow_lurker', 'Shadow Lurker', shadow(370, [(93, 117), (117, 141), (141, 165), (165, 189)], None, [((205, 212), (1, 2, 3)), ((213, 243), (0, 1, 2, 3))], (370, 246, 64, 8)),
     S(140, 16, 1, 6, 14, wake=4, ab=['hides'], drops=[('void_essence', 60, 1, 1)])),
    ('shadow_cat', 'Shadow Cat', shadow(444, [(94, 118), (118, 142), (142, 166), (166, 190)], None, [((205, 212), (1, 2, 3)), ((214, 243), (0, 1, 2, 3))], (444, 246, 64, 8)),
     S(120, 14, 1, 8, 14, wake=4, ab=['hides', 'charges'], drops=[('void_essence', 60, 1, 1)])),
    ('shadow_guy', 'Shadow Guy', dict(**walk4(0, [(1126, 1155), (1158, 1187), (1190, 1219), (1222, 1251)]),
                                     **{'attack_' + k: v for k, v in walk4(0, [(1254, 1283), (1286, 1315), (1318, 1347), (1350, 1379)]).items()}),
     S(180, 18, 2, 6, 16, wake=6, ab=['charges'], drops=[('void_essence', 60, 1, 2)])),
    ('shadow_girl', 'Shadow Girl', dict(**walk4(74, [(1123, 1155), (1155, 1187), (1187, 1219), (1219, 1251)]),
                                       **{'attack_' + k: v for k, v in walk4(74, [(1254, 1283), (1286, 1315), (1318, 1347), (1350, 1379)]).items()}),
     S(160, 16, 1, 7, 16, wake=6, ab=['charges'], drops=[('void_essence', 60, 1, 2)])),
    # ---- mummies, skeletons, ghosts ----
    ('mummy', 'Mummy', dict(**walk4(514, [(93, 121), (125, 152), (157, 184), (189, 216)]), death=R(514, 225, 247)),
     S(260, 30, 0, 5, 15, wake=6, ab=['revives'], drops=[('cloth', 10, 1, 1), ('bone_fragment', 30, 1, 2), ('solar_essence', 25, 1, 1)])),
    ('mummy_dangerous', 'Mummy (dangerous)', dict(**walk4(588, [(93, 121), (125, 152), (157, 184), (189, 216)]), death=R(588, 225, 247)),
     S(600, 40, 1, 6, 25, wake=6, ab=['revives'], drops=[('cloth', 15, 1, 1), ('solar_essence', 40, 1, 2)])),
    ('skeleton', 'Skeleton', dict(**skel(296, (765, 794)), proj=bone(296)),
     S(140, 10, 1, 6, 8, wake=6, drops=[('bone_fragment', 50, 1, 2)], shot=(10, 18, 2600, 6))),
    ('skeleton_dangerous', 'Skeleton (dangerous)', dict(**skel(370, (765, 794)), proj=bone(370)),
     S(400, 25, 2, 7, 18, wake=6, drops=[('bone_fragment', 60, 1, 3), ('solar_essence', 15, 1, 1)], shot=(20, 20, 2200, 6))),
    ('skeleton_mage', 'Skeleton Mage', dict(**skel(444, (762, 794)), proj=fire()),
     S(80, 15, 1, 5, 14, wake=8, ab=['keeps_off'], drops=[('bone_fragment', 40, 1, 2), ('solar_essence', 30, 1, 1)], shot=(15, 16, 2200, 8))),
    ('skeleton_mage_dangerous', 'Skeleton Mage (dangerous)', dict(**skel(518, (762, 794)), proj=fire('ice')),
     S(250, 30, 2, 5, 22, wake=8, ab=['keeps_off'], drops=[('bone_fragment', 50, 1, 2), ('solar_essence', 40, 1, 2)], shot=(25, 18, 1900, 8))),
    ('ghost', 'Ghost', dict(**walk4(370, [(292, 314), (316, 339), (340, 363), (364, 387)]), death=R(370, 387, 410)),
     S(96, 10, 0, 6, 15, wake=7, ab=['flies', 'ghostly'], drops=[('solar_essence', 70, 1, 1)])),
    ('putrid_ghost', 'Putrid Ghost', dict(**walk4(296, [(292, 314), (316, 339), (340, 363), (364, 387)]), death=R(296, 387, 410)),
     S(200, 20, 0, 6, 20, wake=7, ab=['flies', 'ghostly'], drops=[('solar_essence', 70, 1, 2), ('slime', 30, 1, 2)])),
    # ---- fire ----
    ('magma_sprite', 'Magma Sprite', dict(**walk4(296, [(805, 821), (821, 837), (837, 853), (853, 869)], cols=range(7)), parts=(296, 869, 112, 15)),
     S(150, 15, 0, 7, 15, wake=7, ab=['flies', 'erratic'], drops=[('coal', 40, 1, 2), ('fire_quartz', 8, 1, 1)], ms=90)),
    ('magma_sparker', 'Magma Sparker', dict(**walk4(418, [(805, 821), (821, 837), (837, 853), (853, 869)], cols=range(7)), parts=(418, 869, 112, 15), proj=fire()),
     S(150, 15, 0, 8, 15, wake=7, ab=['flies', 'charges'], drops=[('coal', 40, 1, 2), ('fire_quartz', 8, 1, 1)], ms=90, shot=(12, 22, 1600, 7))),
    # ---- shooters ----
    ('lava_lurk', 'Lava Lurk', dict(rest=R(148, 1395, 1408, cols=(0, 1)), wake=R(148, 1395, 1408, cols=(2, 3)) + R(148, 1408, 1422, cols=(0,)),
                                    down=R(148, 1408, 1422, cols=(0, 1, 2)), attack_down=R(148, 1408, 1422, cols=(3,)),
                                    death=list(reversed(R(148, 1395, 1408))), proj=fire()),
     S(100, 15, 1, 0, 20, wake=7, ab=['hides'], drops=[('coal', 50, 1, 2), ('fire_quartz', 10, 1, 1)], ms=160, shot=(15, 18, 2400, 8))),
    ('dwarvish_sentry', 'Dwarvish Sentry', dict(down=[(280, 1389, 16, 16)], proj=fire()),
     S(80, 10, 2, 3, 15, wake=8, ab=['flies', 'keeps_off'], drops=[('iron_ore', 30, 1, 2), ('coal', 30, 1, 1)], shot=(12, 18, 1800, 8))),
    ('frost_sentry', 'Frost Sentry', dict(down=[(264, 1405, 16, 16)], proj=fire('ice')),
     S(80, 10, 2, 3, 15, wake=8, ab=['flies', 'keeps_off'], drops=[('frozen_tear', 15, 1, 1), ('iron_ore', 25, 1, 2)], shot=(12, 18, 1800, 8))),
    ('shadow_sentry', 'Shadow Sentry', dict(down=[(264, 1389, 16, 16)], proj=fire('purple')),
     S(100, 12, 2, 3, 18, wake=8, ab=['flies', 'keeps_off'], drops=[('void_essence', 30, 1, 1), ('gold_ore', 15, 1, 1)], shot=(15, 18, 1800, 8))),
    ('iron_sentry', 'Iron Sentry', dict(down=[(280, 1405, 16, 16)], proj=fire('grey')),
     S(140, 12, 4, 2, 18, wake=8, ab=['flies', 'keeps_off'], drops=[('iron_ore', 50, 1, 3)], shot=(14, 16, 2000, 8))),
]

# Their names, stats or abilities are guesses (the sheet doesn't say): Needs You asks.
GUESSED = {'shadow_sentry', 'frost_sentry', 'iron_sentry', 'iridium_crab', 'truffle_crab', 'bush_lurker', 'mushroom_lurker', 'frost_fly', 'lava_fly', 'armored_bug', 'fire_bug', 'cave_moth',
           'cave_wasp', 'shadow_bat', 'blood_bat', 'shadow_lurker', 'shadow_cat', 'shadow_guy', 'shadow_girl', 'putrid_ghost', 'wilderness_golem'}

# ------------------------------------------------------------------ drops the game didn't have (objects sheet: index -> 24 a row)
DROPS = [  # id, name, sheet index, sell price, about
    ('slime', 'Slime', 766, 5, 'What slimes and mutant things leave.'),
    ('bug_meat', 'Bug Meat', 684, 8, 'Bait, or crafting.'),
    ('bat_wing', 'Bat Wing', 767, 15, 'Dropped by bats.'),
    ('solar_essence', 'Solar Essence', 768, 40, 'The glowing essence of a ghost or a mummy.'),
    ('void_essence', 'Void Essence', 769, 50, 'Left by shadow creatures.'),
    ('bone_fragment', 'Bone Fragment', 881, 12, 'A piece of a skeleton.'),
    ('coal', 'Coal', 382, 15, 'Burns hot: smelting, crafting.'),
    ('copper_ore', 'Copper Ore', 378, 5, 'A common ore.'),
    ('iron_ore', 'Iron Ore', 380, 10, 'A fairly common ore.'),
    ('gold_ore', 'Gold Ore', 384, 25, 'A precious ore.'),
    ('iridium_ore', 'Iridium Ore', 386, 100, 'An exotic ore with many curious properties.'),
    ('cherry_bomb', 'Cherry Bomb', 286, 50, 'A small bomb (it doesn\'t go off yet).'),
    ('squid_ink', 'Squid Ink', 814, 110, 'Squid ink.'),
]

# ------------------------------------------------------------------ weapons: Stardew's (the wiki's Weapons table)
# (sheet index, id, name, kind 0 sword / 1 dagger / 2 club, min, max, speed, crit % x10, crit power %, defense, weight, buy price or 0)
def W(i, iid, n, k, lo, hi, sp=0, cr=20, cp=0, df=0, wt=0, buy=0):
    return (i, iid, n, k, lo, hi, sp, cr, cp, df, wt, buy)


WEAPON_LIST = [
    W(0, 'rusty_sword', 'Rusty Sword', 0, 2, 5, buy=450), W(1, 'silver_saber', 'Silver Saber', 0, 8, 15, df=1),
    W(2, 'dark_sword', 'Dark Sword', 0, 30, 45, sp=-5, cr=40, wt=5), W(3, 'holy_blade', 'Holy Blade', 0, 20, 27, sp=4, df=2),
    W(4, 'galaxy_sword', 'Galaxy Sword', 0, 60, 80, sp=4), W(5, 'bone_sword', 'Bone Sword', 0, 20, 30, sp=4, wt=2),
    W(6, 'iron_edge', 'Iron Edge', 0, 12, 25, sp=-2, df=1, wt=3, buy=4000), W(7, 'templars_blade', "Templar's Blade", 0, 22, 29, cr=0, df=1),
    W(8, 'obsidian_edge', 'Obsidian Edge', 0, 30, 45, sp=-1, cp=10), W(9, 'lava_katana', 'Lava Katana', 0, 55, 64, cr=15, cp=25, df=3, wt=3),
    W(10, 'claymore', 'Claymore', 0, 20, 32, sp=-4, df=2, wt=3, buy=7000), W(11, 'steel_smallsword', 'Steel Smallsword', 0, 4, 8, sp=2, buy=1300),
    W(12, 'wooden_blade', 'Wooden Blade', 0, 3, 7, buy=250), W(13, 'insect_head', 'Insect Head', 0, 20, 30, sp=2, cr=40),
    W(14, 'neptunes_glaive', "Neptune's Glaive", 0, 18, 35, sp=-1, df=2, wt=4), W(15, 'forest_sword', 'Forest Sword', 0, 8, 18, sp=2, df=1),
    W(16, 'carving_knife', 'Carving Knife', 1, 1, 3, cr=40), W(17, 'iron_dirk', 'Iron Dirk', 1, 2, 4, cr=30),
    W(18, 'burglars_shank', "Burglar's Shank", 1, 7, 12, cr=40, cp=25), W(19, 'shadow_dagger', 'Shadow Dagger', 1, 10, 20, cr=40),
    W(20, 'elf_blade', 'Elf Blade', 1, 3, 5, cr=40), W(21, 'crystal_dagger', 'Crystal Dagger', 1, 4, 10, cr=30, cp=50, wt=5),
    W(22, 'wind_spire', 'Wind Spire', 1, 1, 5, cp=10, wt=5), W(23, 'galaxy_dagger', 'Galaxy Dagger', 1, 30, 40, sp=1, wt=5),
    W(24, 'wood_club', 'Wood Club', 2, 9, 16), W(25, 'alexs_bat', "Alex's Bat", 2, 40, 55, sp=-2),
    W(26, 'lead_rod', 'Lead Rod', 2, 18, 27, sp=-4), W(27, 'wood_mallet', 'Wood Mallet', 2, 15, 24, sp=2, wt=2),
    W(28, 'the_slammer', 'The Slammer', 2, 40, 55, sp=-2), W(29, 'galaxy_hammer', 'Galaxy Hammer', 2, 70, 90, sp=2, wt=5),
    W(30, 'sams_old_guitar', "Sam's Old Guitar", 2, 40, 55, sp=-2), W(31, 'femur', 'Femur', 2, 6, 11, sp=2),
    W(35, 'elliotts_pencil', "Elliott's Pencil", 1, 24, 30, cr=60), W(36, 'marus_wrench', "Maru's Wrench", 2, 40, 55, sp=-2),
    W(37, 'harveys_mallet', "Harvey's Mallet", 2, 40, 55, sp=-2), W(38, 'pennys_fryer', "Penny's Fryer", 2, 40, 55, sp=-2),
    W(39, 'leahs_whittler', "Leah's Whittler", 0, 30, 45, sp=-1, cp=10), W(40, 'abbys_planchette', "Abby's Planchette", 1, 24, 30, cr=60),
    W(41, 'sebs_lost_mace', "Seb's Lost Mace", 2, 40, 55, sp=-2), W(42, 'haleys_iron', "Haley's Iron", 0, 30, 45, sp=-1, cp=10),
    W(43, 'pirates_sword', "Pirate's Sword", 0, 8, 14, sp=2), W(44, 'cutlass', 'Cutlass', 0, 9, 17, sp=2, buy=1500),
    W(45, 'wicked_kris', 'Wicked Kris', 1, 24, 30, cr=60), W(46, 'kudgel', 'Kudgel', 2, 27, 40, sp=-1, cp=50, wt=2),
    W(48, 'yeti_tooth', 'Yeti Tooth', 0, 26, 42, cp=10, df=4), W(49, 'rapier', 'Rapier', 0, 15, 25, sp=2, cr=30),
    W(50, 'steel_falchion', 'Steel Falchion', 0, 28, 46, sp=4, cp=20), W(51, 'broken_trident', 'Broken Trident', 1, 15, 26),
    W(52, 'tempered_broadsword', 'Tempered Broadsword', 0, 29, 44, sp=-3, df=3, wt=3),
    W(54, 'dwarf_sword', 'Dwarf Sword', 0, 65, 75, sp=2, df=4), W(55, 'dwarf_hammer', 'Dwarf Hammer', 2, 75, 85, df=2, wt=5),
    W(56, 'dwarf_dagger', 'Dwarf Dagger', 1, 32, 38, sp=1, cr=30, df=6, wt=5),
    W(57, 'dragontooth_cutlass', 'Dragontooth Cutlass', 0, 75, 90, cp=50), W(58, 'dragontooth_club', 'Dragontooth Club', 2, 80, 100, cp=50, wt=3),
    W(59, 'dragontooth_shiv', 'Dragontooth Shiv', 1, 40, 50, cr=50, cp=100, wt=5), W(60, 'ossified_blade', 'Ossified Blade', 0, 26, 42, sp=-2, df=1, wt=2),
    W(61, 'iridium_needle', 'Iridium Needle', 1, 20, 35, cr=100, cp=200), W(62, 'infinity_blade', 'Infinity Blade', 0, 80, 100, sp=4, df=2),
    W(63, 'infinity_gavel', 'Infinity Gavel', 2, 100, 120, sp=2, df=1, wt=5), W(64, 'infinity_dagger', 'Infinity Dagger', 1, 50, 70, sp=1, cr=60, df=3, wt=5),
    W(65, 'meowmere', 'Meowmere', 0, 20, 20, sp=4, wt=2),
]
# (47, 53, 66 are scythes — the game has those already)
# Slingshots: (sheet index, id, name, multiplier, buy price or 0) — they shoot what's put in them (main.c PROJECTILES)
SLINGSHOTS = [(32, 'slingshot', 'Slingshot', 1, 500), (33, 'master_slingshot', 'Master Slingshot', 2, 3000), (34, 'galaxy_slingshot', 'Galaxy Slingshot', 4, 0)]


# ------------------------------------------------------------------ cutting
def load(path):
    if not os.path.exists(path):
        raise SystemExit(f'Not found: {path}')
    return Image.open(path).convert('RGBA')


def pack565(img):
    px = []
    for (r, g, b, a) in img.getdata():
        if a < 128:
            px.append(0)
            continue
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        px.append(0x0841 if v == 0 else v)
    return px


def build(sheet, mid, spec):
    """The monster's frames (deduplicated), seqs, box size and particles."""
    cells = [c for k in SEQS for c in spec.get(k, [])]
    fw = max(c[2] for c in cells)
    fh = max(c[3] for c in cells)
    if fw > FRAME_MAX or fh > FRAME_MAX:
        raise SystemExit(f'{mid}: frames {fw}x{fh} are bigger than {FRAME_MAX}')
    frames, keys, seqs, cell_of = [], {}, {}, []
    for k in SEQS:
        out = []
        for (x, y, w, h) in spec.get(k, [])[:SEQ_MAX]:
            spr = sheet.crop((x, y, x + w, y + h))
            if spr.getchannel('A').getbbox() is None:
                continue   # an empty cell
            box = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
            box.paste(spr, ((fw - w) // 2, fh - h))
            key = box.tobytes()
            if key not in keys:
                keys[key] = len(frames)
                frames.append(box)
                cell_of.append([x, y, w, h])
            out.append(keys[key])
        seqs[k] = out
    parts = []
    if spec.get('parts'):
        px, py, pw, ph = spec['parts']
        reg = sheet.crop((px, py, px + pw, py + ph))
        for (bx0, by0, bx1, by1) in pieces(reg)[:4]:
            p = reg.crop((bx0, by0, min(bx1, bx0 + PART), min(by1, by0 + PART)))
            box = Image.new('RGBA', (PART, PART), (0, 0, 0, 0))
            box.paste(p, ((PART - p.width) // 2, (PART - p.height) // 2))
            parts.append(box)
    proj = []
    pj = spec.get('proj')
    if pj and pj.get('cells'):
        for (x, y, w, h) in pj['cells'][:PROJ_FRAMES]:
            spr = tint(sheet.crop((x, y, x + w, y + h)), pj.get('tint'))
            box = Image.new('RGBA', (PROJ, PROJ), (0, 0, 0, 0))
            box.paste(spr, ((PROJ - w) // 2, (PROJ - h) // 2))
            proj.append(box)
    elif pj and pj.get('piece'):   # the biggest of its bits, spun a quarter at a time
        px, py, pw, ph = pj['piece']
        reg = sheet.crop((px, py, px + pw, py + ph))
        bb = pieces(reg)[0]
        spr = reg.crop((bb[0], bb[1], min(bb[2], bb[0] + PROJ), min(bb[3], bb[1] + PROJ)))
        for k in range(4 if pj.get('spin') else 1):
            r = spr.rotate(-90 * k, expand=True)
            box = Image.new('RGBA', (PROJ, PROJ), (0, 0, 0, 0))
            box.paste(r, ((PROJ - r.width) // 2, (PROJ - r.height) // 2))
            proj.append(box)
    return dict(fw=fw, fh=fh, frames=frames, seqs=seqs, parts=parts, cells=cell_of, proj=proj)


def tint(img, how):
    """A fireball's colours for an ice, a shadow or an iron shot."""
    if not how:
        return img
    out = img.copy()
    px = out.load()
    for y in range(out.height):
        for x in range(out.width):
            r, g, b, a = px[x, y]
            if how == 'ice':
                px[x, y] = (b, (g + b) // 2 + 20 if (g + b) // 2 + 20 < 256 else 255, r, a)
            elif how == 'purple':
                px[x, y] = (r * 3 // 4, b, r, a)
            elif how == 'grey':
                v = (r * 3 + g * 6 + b) // 10
                px[x, y] = (v, v, min(255, v + 12), a)
    return out


def pieces(img):
    """Bounding boxes of the separate bits in img (8-connected), biggest first."""
    w, h = img.size
    a = img.getchannel('A').load()
    seen = [[False] * w for _ in range(h)]
    boxes = []
    for y in range(h):
        for x in range(w):
            if a[x, y] < 128 or seen[y][x]:
                continue
            st = [(x, y)]
            seen[y][x] = True
            x0 = x1 = x
            y0 = y1 = y
            n = 0
            while st:
                cx, cy = st.pop()
                n += 1
                x0, x1, y0, y1 = min(x0, cx), max(x1, cx), min(y0, cy), max(y1, cy)
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        nx, ny = cx + dx, cy + dy
                        if 0 <= nx < w and 0 <= ny < h and not seen[ny][nx] and a[nx, ny] >= 128:
                            seen[ny][nx] = True
                            st.append((nx, ny))
            if n >= 3:
                boxes.append((n, (x0, y0, x1 + 1, y1 + 1)))
    boxes.sort(key=lambda b: -b[0])
    return [b for _, b in boxes]


def c_array(px):
    return '\n'.join('    ' + ', '.join(f'0x{v:04x}' for v in px[i:i + 12]) + ',' for i in range(0, len(px), 12))


def monster_c(mid, name, m, st):
    ab_bits = sum(1 << ABIL.index(a) for a in st['abilities'])
    meta = dict(name=name, fw=m['fw'], fh=m['fh'], frames=len(m['frames']), seqs=m['seqs'], frameMs=st['frameMs'],
                hp=st['hp'], damage=st['damage'], defense=st['defense'], speed=st['speed'], xp=st['xp'], wake=st['wake'],
                abilities=st['abilities'], drops=st['drops'], particles=len(m['parts']), sound=st['sound'],
                projectiles=len(m['proj']), projDamage=st['shot'][0], projSpeed=st['shot'][1], shootMs=st['shot'][2], shootTiles=st['shot'][3],
                sheet='Stardew Valley - Monsters.png', cells=m['cells'])
    fpx = [v for f in m['frames'] for v in pack565(f)]
    ppx = [v for p in m['parts'] for v in pack565(p)]
    seq_len = ', '.join(str(len(m['seqs'][k])) for k in SEQS)
    seq = ', '.join('{ ' + ', '.join(str(i) for i in m['seqs'][k]) + ' }' if m['seqs'][k] else '{ 0 }' for k in SEQS)
    out = [
        f'// AUTO-GENERATED by tools/slice_monsters.py (the Monsters tab\'s format) — "{name}"',
        f'// Lives in assets/monsters/ as {mid}.c — the file name is the monster id, keep it.',
        f'// {len(m["frames"])} frames of {m["fw"]}x{m["fh"]}, {len(m["parts"])} particles. Art: Stardew Valley\'s monster sheet (Downloads).',
        '// Everything here is const: it stays in flash (no RAM). RGB565, 0x0000 = see-through.',
        '// MONSTERS-EDITOR ' + json.dumps(meta, separators=(',', ':')),
        '#include "monsters.h"',
        '',
        f'static const uint16_t k_monster_{mid}_frames[{len(fpx)}] = {{',
        c_array(fpx),
        '};',
    ]
    if ppx:
        out += ['', f'static const uint16_t k_monster_{mid}_particles[{len(ppx)}] = {{', c_array(ppx), '};']
    jpx = [v for p in m['proj'] for v in pack565(p)]
    if jpx:
        out += ['', f'static const uint16_t k_monster_{mid}_proj[{len(jpx)}] = {{', c_array(jpx), '};']
    if st['drops']:
        out += ['', f'static const mon_drop_t k_monster_{mid}_drops[] = {{']
        out += [f'    {{ "{d["item"]}", {d["chance"]}, {d["min"]}, {d["max"]} }},' for d in st['drops']]
        out += ['};']
    out += [
        '',
        f'const monster_def_t k_monster_{mid} = {{',
        f'    .id = "{mid}",',
        f'    .name = "{name}",',
        f'    .fw = {m["fw"]}, .fh = {m["fh"]},',
        f'    .frame_count = {len(m["frames"])},',
        f'    .frames = k_monster_{mid}_frames,',
        f'    .seq_len = {{ {seq_len} }},',
        f'    .seq = {{ {seq} }},',
        f'    .frame_ms = {st["frameMs"]},',
        f'    .hp = {st["hp"]}, .damage = {st["damage"]}, .defense = {st["defense"]}, .speed_q = {st["speed"]}, .xp = {st["xp"]}, .wake_tiles = {st["wake"]},',
        f'    .abilities = 0x{ab_bits:04x},',
        f'    .particle_count = {len(m["parts"])},',
        f'    .particles = {f"k_monster_{mid}_particles" if ppx else "NULL"},',
        f'    .drop_count = {len(st["drops"])},',
        f'    .drops = {f"k_monster_{mid}_drops" if st["drops"] else "NULL"},',
        f'    .sound = "{st["sound"]}",',
        '    .sound_die = "",     // (its own sounds: "" = <id>_hit, _die, _wake, _attack)',
        '    .sound_wake = "",',
        '    .sound_attack = "",',
        f'    .proj_count = {len(m["proj"])},',
        f'    .proj = {f"k_monster_{mid}_proj" if jpx else "NULL"},',
        f'    .proj_damage = {st["shot"][0]}, .proj_speed_q = {st["shot"][1]}, .shoot_ms = {st["shot"][2]}, .shoot_tiles = {st["shot"][3]},',
        '};',
    ]
    return '\n'.join(out) + '\n'


def swing_frames(icon):
    """A weapon's swing art for TOOL SWING (main.c), the axe's layout: three 16x32 frames — facing down (the
    blade pointing down in front), facing up (raised, the blade up) and sideways (upright, the hilt at the
    bottom middle: the game turns it round the hands from behind the head to down in front). From the
    sheet's icon, which lies on the diagonal with its tip at the top right."""
    up = icon.rotate(45, resample=Image.NEAREST, expand=True)   # tip straight up
    up = up.crop(up.getchannel('A').point(lambda a: 255 if a >= 128 else 0).getbbox())
    if up.width > 16 or up.height > 30:
        k = min(16 / up.width, 30 / up.height)
        up = up.resize((max(1, int(up.width * k)), max(1, int(up.height * k))), Image.NEAREST)

    def place(img, bottom):
        f = Image.new('RGBA', (16, 32), (0, 0, 0, 0))
        f.paste(img, ((16 - img.width) // 2, bottom - img.height), img)
        return f
    down = up.transpose(Image.FLIP_TOP_BOTTOM)
    return [place(down, 32), place(up, 30), place(up, 32)]


def item_c(iid, name, icon, attrs, about, stack=99, art='Stardew Valley\'s objects sheet', use=None, use_ms=300):
    px = pack565(icon)
    upx = [v for f in (use or []) for v in pack565(f)]
    use_line = (f'    .use = {{ .w=16, .h=32, .frame_count={len(use)}, .interval_ms={use_ms}, .loop_count=0, .pixels=k_{iid}_use_pixels }},'
                if use else '    .use = { .frame_count = 0 },')
    use_arr = ['', f'static const uint16_t k_{iid}_use_pixels[{len(upx)}] = {{', c_array(upx), '};'] if use else []
    return '\n'.join([
        f'// AUTO-GENERATED by gameTools.html (Item Editor) — "{name}"',
        f'// Lives in assets/items/ as {iid}.c — the file name is the item id, keep it.',
        f'// Rebuild and it\'s in the game; maps drop it by the id "{iid}".',
        f'// {about} Art: {art} (tools/slice_monsters.py).',
        '#include "items.h"',
        '',
        f'static const uint16_t k_{iid}_passive_pixels[{len(px)}] = {{',
        c_array(px),
        '};',
        *use_arr,
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
        use_line,
        f'    .attrs = k_{iid}_attrs,',
        f'    .attr_count = {len(attrs)},',
        '};',
    ]) + '\n'


def objects_sheet():
    for f in os.listdir(DL):
        if f.startswith(OBJECTS_PREFIX) and f.lower().endswith('.png'):
            return load(os.path.join(DL, f))
    raise SystemExit('The objects sheet ("' + OBJECTS_PREFIX + '...png") is not in Downloads')


def cell16(sheet, idx, cols):
    x, y = (idx % cols) * 16, (idx // cols) * 16
    return sheet.crop((x, y, x + 16, y + 16))


def swing_preview(path):
    """Every weapon's three swing frames, side by side, 4x."""
    wsheet = load(WEAPONS)
    rows = [(n, swing_frames(cell16(wsheet, i, 8))) for i, iid, n, *_ in WEAPON_LIST]
    out = Image.new('RGBA', (8 * 60, ((len(rows) + 7) // 8) * 36), (90, 120, 90, 255))
    for k, (n, fr) in enumerate(rows):
        for j, f in enumerate(fr):
            out.alpha_composite(f, ((k % 8) * 60 + j * 18, (k // 8) * 36))
    out.resize((out.width * 3, out.height * 3), Image.NEAREST).save(path)
    print(f'{len(rows)} weapons\' swings -> {path}')


def preview(sheet, path):
    built = [(mid, name, build(sheet, mid, spec)) for mid, name, spec, st in MONSTERS]
    sc, rows = 3, []
    for mid, name, m in built:
        strip = [f for k in SEQS for f in [m['frames'][i] for i in m['seqs'][k]]] + m['parts'] + m['proj']
        rows.append((name, m, strip))
    W = max(len(s) * (FRAME_MAX + 2) for _, _, s in rows) + 160
    H = len(rows) * (FRAME_MAX + 4)
    out = Image.new('RGBA', (W, H), (60, 60, 70, 255))
    from PIL import ImageDraw
    d = ImageDraw.Draw(out)
    for r, (name, m, strip) in enumerate(rows):
        y = r * (FRAME_MAX + 4)
        d.text((2, y + 10), name, fill=(255, 255, 255, 255))
        for k, f in enumerate(strip):
            out.alpha_composite(f, (160 + k * (FRAME_MAX + 2), y + (FRAME_MAX - f.height)))
    out = out.resize((W * sc // 2, H * sc // 2), Image.NEAREST)
    out.save(path)
    print(f'{len(built)} monsters -> {path}')


def write(sheet, force):
    os.makedirs(MON_DIR, exist_ok=True)
    n = 0
    for mid, name, spec, st in MONSTERS:
        p = os.path.join(MON_DIR, mid + '.c')
        if os.path.exists(p) and not force:
            continue
        m = build(sheet, mid, spec)
        open(p, 'w', encoding='utf-8', newline='\n').write(monster_c(mid, name, m, st))
        n += 1
    print(f'{n} monsters written to assets/monsters/')
    obj = objects_sheet()
    cols = 24
    k = 0
    for iid, name, idx, price, about in DROPS:
        p = os.path.join(ITEM_DIR, iid + '.c')
        if os.path.exists(p):
            continue
        attrs = [('sellable', price)]
        if iid in ('copper_ore', 'iron_ore', 'gold_ore', 'iridium_ore', 'coal'):
            attrs.append(('mineral', 1))
        open(p, 'w', encoding='utf-8', newline='\n').write(item_c(iid, name, cell16(obj, idx, cols), attrs, about))
        k += 1
    print(f'{k} new drop items written to assets/items/')
    wsheet = load(WEAPONS)
    k = 0
    for idx, iid, name, kind, lo, hi, sp, cr, cp, df, wt, buy in WEAPON_LIST:
        p = os.path.join(ITEM_DIR, iid + '.c')
        if os.path.exists(p) and not force:
            continue
        attrs = [('tool', 1), ('weapon', (lo + hi) // 2), ('weapon_min', lo), ('weapon_max', hi), ('weapon_kind', kind), ('energy', 0)]
        attrs += [(a, v) for a, v in (('weapon_speed', sp), ('weapon_crit', cr), ('weapon_crit_power', cp), ('weapon_defense', df), ('weapon_weight', wt)) if v or a == 'weapon_crit']
        attrs.append(('sellable', max(10, (lo + hi) * 12)))
        if buy:
            attrs += [('buyable', buy), ('shop', 5)]
        kinds = ['A sword: a wide slash.', 'A dagger: quick, short stabs.', 'A club: slow, heavy blows.']
        extra = ''.join(f' {t}' for t, v in ((f'Speed {sp:+d}.', sp), (f'Defense +{df}.', df), (f'Weight +{wt}.', wt), (f'Crit power +{cp}%.', cp)) if v)
        icon = cell16(wsheet, idx, 8)
        open(p, 'w', encoding='utf-8', newline='\n').write(item_c(iid, name, icon, attrs,
                                                                   f'Weapon (COMBAT in main.c): {lo}-{hi} damage, crit {cr / 10:g}%.{extra} {kinds[kind]} Swing art: its icon turned (swing_frames()).',
                                                                   stack=1, art="Stardew Valley's weapons sheet", use=swing_frames(icon), use_ms=(220, 160, 300)[kind]))
        k += 1
    for idx, iid, name, mult, buy in SLINGSHOTS:
        p = os.path.join(ITEM_DIR, iid + '.c')
        if os.path.exists(p) and not force:
            continue
        attrs = [('slingshot', mult), ('weapon_kind', 3), ('sellable', 250 * mult)]
        if buy:
            attrs += [('buyable', buy), ('shop', 5)]
        open(p, 'w', encoding='utf-8', newline='\n').write(item_c(iid, name, cell16(wsheet, idx, 8), attrs,
                                                                   f'Slingshot (PROJECTILES in main.c): shoots whatever is dropped on it in the bag - stone, ore, coal, wood, anything - at {mult}x its Stardew ammo damage.',
                                                                   stack=1, art="Stardew Valley's weapons sheet"))
        k += 1
    print(f'{k} weapons and slingshots written to assets/items/')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview')
    ap.add_argument('--swings', help='draw every weapon\'s swing frames into this PNG')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--force', action='store_true')
    a = ap.parse_args()
    sheet = load(SHEET)
    if a.preview:
        preview(sheet, a.preview)
    if a.swings:
        swing_preview(a.swings)
    if a.write:
        write(sheet, a.force)
    if not a.preview and not a.write and not a.swings:
        ap.print_help()


if __name__ == '__main__':
    main()
