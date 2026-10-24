"""One-off: cuts the food pictures in Downloads ("food (1).png" .. "food (7).png",
16x16 cells) into food items, assets/items/<id>.c (Item Editor format: "food 1",
a price), and writes the real Stardew Valley recipe of each to
Downloads/stardew_food_recipes.txt — what to add to the game to cook them.

The KITCHEN (main.c; a map object with the "kitchen" action) lists every item
with "food" 1. A food with "cook:<item id>" N attributes takes those from the
bag to make; none (all of them, for now) = free.

    python tools/slice_food.py [--preview out.png] [--write] [--force] [--recipes]

FOODS: (picture number, row, column), id, name, Stardew's sell price, how it's made.
"""
import argparse, os
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DL = os.path.join(os.path.expanduser('~'), 'Downloads')
FOOD_TYPE = 32   # pipeline_msgs.h CAM_TYPES "food" (types2 bit 1)

C = 'Cooking: '   # made in a kitchen in Stardew
FOODS = [
    ((1, 0, 0), 'jelly', 'Jelly', 160, 'Not cooked: a Preserves Jar + any fruit (sells for 2x the fruit + 50).'),
    ((1, 0, 1), 'salad', 'Salad', 110, C + 'Leek, Dandelion, Vinegar'),
    ((2, 0, 0), 'seafoam_pudding', 'Seafoam Pudding', 300, C + 'Flounder, Midnight Carp, Squid Ink'),
    ((2, 0, 1), 'pickles', 'Pickles', 150, 'Not cooked: a Preserves Jar + any vegetable (sells for 2x the vegetable + 50).'),
    ((3, 0, 0), 'parsnip_soup', 'Parsnip Soup', 120, C + 'Parsnip, Milk, Vinegar'),
    ((3, 0, 1), 'plum_pudding', 'Plum Pudding', 260, C + 'Wild Plum x2, Wheat Flour, Sugar'),
    ((3, 0, 2), 'coleslaw', 'Coleslaw', 345, C + 'Red Cabbage, Vinegar, Mayonnaise'),
    ((3, 0, 3), 'omelet', 'Omelet', 125, C + 'Egg, Milk'),
    ((3, 0, 4), 'cranberry_sauce', 'Cranberry Sauce', 120, C + 'Cranberries, Sugar'),
    ((3, 0, 5), 'rice_pudding', 'Rice Pudding', 260, C + 'Milk, Sugar, Rice'),
    ((3, 0, 6), 'kebab', 'Kebab', 150, 'Not in Stardew Valley (a made-up one) - suggested: any meat or fish, Hot Pepper, Onion.'),
    ((3, 0, 7), 'meatloaf', 'Meatloaf', 200, 'Not in Stardew Valley (a made-up one) - suggested: Egg, Wheat Flour, Tomato.'),
    ((3, 1, 0), 'vegetable_medley', 'Vegetable Medley', 120, C + 'Tomato, Beet'),
    ((3, 1, 1), 'bread', 'Bread', 60, C + 'Wheat Flour'),
    ((3, 1, 2), 'pina_colada', 'Pina Colada', 300, 'Not cooked: bought at the Ginger Island resort bar. (Made from Pineapple and Coconut.)'),
    ((3, 1, 3), 'hashbrowns', 'Hashbrowns', 120, C + 'Potato, Oil'),
    ((3, 1, 4), 'pizza', 'Pizza', 300, C + 'Wheat Flour, Tomato, Cheese'),
    ((3, 1, 5), 'fried_mushroom', 'Fried Mushroom', 200, C + 'Common Mushroom, Morel, Oil'),
    ((3, 1, 6), 'farmers_lunch', "Farmer's Lunch", 150, C + 'Omelet, Parsnip'),
    ((3, 1, 7), 'fried_calamari', 'Fried Calamari', 150, C + 'Squid, Wheat Flour, Oil'),
    ((4, 0, 0), 'maple_bar', 'Maple Bar', 300, C + 'Maple Syrup, Sugar, Wheat Flour'),
    ((5, 0, 0), 'green_tea', 'Green Tea', 100, 'Not cooked: a Keg + Tea Leaves.'),
    ((6, 0, 0), 'stir_fry', 'Stir Fry', 335, C + 'Cave Carrot, Common Mushroom, Kale, Oil'),
    ((6, 0, 1), 'survival_burger', 'Survival Burger', 180, C + 'Bread, Cave Carrot, Eggplant'),
    ((6, 0, 2), 'dish_o_the_sea', "Dish O' The Sea", 220, C + 'Sardine x2, Hashbrowns'),
    ((6, 0, 3), 'magic_rock_candy', 'Magic Rock Candy', 5000, 'Not cooked: traded at the Desert Trader for 3 Prismatic Shards (Thursdays), or found in the Skull Cavern.'),
    ((6, 0, 4), 'red_plate', 'Red Plate', 400, C + 'Red Cabbage, Radish'),
]
# food (7).png: 23 across, 2 down
_SEVEN = [
    ('pale_broth', 'Pale Broth', 150, C + 'White Algae x2'),
    ('fried_egg', 'Fried Egg', 35, C + 'Egg (any)'),
    ('cheese_cauliflower', 'Cheese Cauliflower', 300, C + 'Cauliflower, Cheese'),
    ('bruschetta', 'Bruschetta', 210, C + 'Bread, Oil, Tomato'),
    ('glazed_yams', 'Glazed Yams', 200, C + 'Yam, Sugar'),
    ('baked_fish', 'Baked Fish', 100, C + 'Sunfish, Bream, Wheat Flour'),
    ('bean_hotpot', 'Bean Hotpot', 100, C + 'Green Bean x2'),
    ('super_meal', 'Super Meal', 220, C + 'Bok Choy, Cranberries, Artichoke'),
    ('complete_breakfast', 'Complete Breakfast', 350, C + 'Fried Egg, Milk, Hashbrowns, Pancakes'),
    ('crispy_bass', 'Crispy Bass', 150, C + 'Largemouth Bass, Wheat Flour, Oil'),
    ('shrimp_cocktail', 'Shrimp Cocktail', 160, C + 'Tomato, Shrimp, Wild Horseradish'),
    ('fiddlehead_risotto', 'Fiddlehead Risotto', 350, C + 'Oil, Fiddlehead Fern, Garlic'),
    ('salmon_dinner', 'Salmon Dinner', 300, C + 'Salmon, Amaranth, Kale'),
    ('pumpkin_pie', 'Pumpkin Pie', 385, C + 'Pumpkin, Wheat Flour, Milk, Sugar'),
    ('algae_soup', 'Algae Soup', 100, C + 'Green Algae x4'),
    ('fried_eel', 'Fried Eel', 120, C + 'Eel, Oil'),
    ('escargot', 'Escargot', 125, C + 'Snail, Garlic'),
    ('spaghetti', 'Spaghetti', 120, C + 'Wheat Flour, Tomato'),
    ('pancakes', 'Pancakes', 80, C + 'Wheat Flour, Egg'),
    ('roots_platter', 'Roots Platter', 100, C + 'Cave Carrot, Winter Root'),
    ('fish_taco', 'Fish Taco', 500, C + 'Tuna, Tortilla, Red Cabbage, Mayonnaise'),
    ('crab_cakes', 'Crab Cakes', 275, C + 'Crab, Wheat Flour, Egg, Oil'),
    ('eggplant_parmesan', 'Eggplant Parmesan', 200, C + 'Eggplant, Tomato'),
    ('poppyseed_muffin', 'Poppyseed Muffin', 250, C + 'Poppy, Wheat Flour, Sugar'),
    ('chowder', 'Chowder', 135, C + 'Clam, Milk'),
    ('trout_soup', 'Trout Soup', 100, C + 'Rainbow Trout, Green Algae'),
    ('chocolate_cake', 'Chocolate Cake', 200, C + 'Wheat Flour, Sugar, Egg'),
    ('pink_cake', 'Pink Cake', 480, C + 'Melon, Wheat Flour, Sugar, Egg'),
    ('rhubarb_pie', 'Rhubarb Pie', 400, C + 'Rhubarb, Wheat Flour, Sugar'),
    ('roasted_hazelnuts', 'Roasted Hazelnuts', 270, C + 'Hazelnut x3'),
    ('lobster_bisque', 'Lobster Bisque', 205, C + 'Lobster, Milk'),
    ('carp_surprise', 'Carp Surprise', 150, C + 'Carp x4'),
    ('spicy_eel', 'Spicy Eel', 175, C + 'Eel, Hot Pepper'),
    ('sashimi', 'Sashimi', 75, C + 'Any Fish'),
    ('maki_roll', 'Maki Roll', 220, C + 'Any Fish, Seaweed, Rice'),
    ('tortilla', 'Tortilla', 50, C + 'Corn'),
    ('fruit_salad', 'Fruit Salad', 450, C + 'Blueberry, Melon, Apricot'),
    ('autumns_bounty', "Autumn's Bounty", 350, C + 'Yam, Pumpkin'),
    ('ginger_ale', 'Ginger Ale', 200, C + 'Ginger x3, Sugar'),
    ('ice_cream', 'Ice Cream', 120, C + 'Milk, Sugar'),
    ('blueberry_tart', 'Blueberry Tart', 150, C + 'Blueberry, Wheat Flour, Sugar, Egg'),
    ('radish_salad', 'Radish Salad', 300, C + 'Oil, Vinegar, Radish'),
    ('pumpkin_soup', 'Pumpkin Soup', 300, C + 'Pumpkin, Milk'),
    ('stuffing', 'Stuffing', 165, C + 'Bread, Cranberries, Hazelnut'),
    ('fish_stew', 'Fish Stew', 175, C + 'Crayfish, Mussel, Periwinkle, Tomato'),
    ('moss_soup', 'Moss Soup', 80, C + 'Moss x20'),
]


def seven_cells():
    """food (7).png's non-empty cells, row by row (23 x 2; the last ones are blank)."""
    im = Image.open(os.path.join(DL, 'food (7).png')).convert('RGBA')
    cells = []
    for r in range(im.height // 16):
        for c in range(im.width // 16):
            if im.crop((c * 16, r * 16, c * 16 + 16, r * 16 + 16)).getchannel('A').getbbox():
                cells.append((7, r, c))
    return cells


def all_foods():
    seven = seven_cells()
    if len(seven) != len(_SEVEN):
        raise SystemExit(f'food (7).png has {len(seven)} pictures, the list has {len(_SEVEN)}')
    return FOODS + [(cell,) + f for cell, f in zip(seven, _SEVEN)]


def picture(cell):
    n, r, c = cell
    return Image.open(os.path.join(DL, f'food ({n}).png')).convert('RGBA').crop((c * 16, r * 16, c * 16 + 16, r * 16 + 16))


def pack565(img):
    px = []
    for (r, g, b, a) in img.getdata():
        if a < 128:
            px.append(0)
            continue
        v = ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
        px.append(0x0841 if v == 0 else v)
    return px


def item_c(fid, name, sell, how, icon):
    px = pack565(icon)
    rows = ['    ' + ', '.join(f'0x{v:04x}' for v in px[i:i + 12]) + ',' for i in range(0, len(px), 12)]
    attrs = [('sellable', sell), ('quality', 1), ('types2', 1 << (FOOD_TYPE - 31)), ('food', 1)]
    return '\n'.join([
        f'// AUTO-GENERATED by gameTools.html (Item Editor) — "{name}"',
        f'// Lives in assets/items/ as {fid}.c — the file name is the item id, keep it.',
        f'// Rebuild and it\'s in the game; maps drop it by the id "{fid}".',
        f'// A food: the kitchen makes it (KITCHEN in main.c; free until it has "cook:<item id>" N attributes).',
        f'// Stardew Valley: {how}',
        '#include "items.h"',
        '',
        f'static const uint16_t k_{fid}_passive_pixels[{len(px)}] = {{',
        *rows,
        '};',
        '',
        '',
        f'static const item_attr_t k_{fid}_attrs[] = {{',
        *[f'    {{ "{a}", {v} }},' for a, v in attrs],
        '};',
        '',
        f'const item_asset_t k_item_{fid} = {{',
        f'    .id = "{fid}",',
        f'    .display_name = "{name}",',
        '    .max_stack = 99,',
        f'    .passive = {{ .w=16, .h=16, .frame_count=1, .interval_ms=150, .loop_count=-1, .pixels=k_{fid}_passive_pixels }},',
        '    .use = { .frame_count = 0 },',
        f'    .attrs = k_{fid}_attrs,',
        f'    .attr_count = {len(attrs)},',
        '};',
    ]) + '\n'


def recipes_text(foods):
    cooked = [f for f in foods if f[4].startswith(C)]
    other = [f for f in foods if not f[4].startswith(C)]
    lines = ['CaptureIt foods - how Stardew Valley makes each one',
             '=' * 52,
             '',
             'Every food below is in the game now (assets/items/<id>.c) and the kitchen makes',
             'it for free. To make a recipe cost its ingredients, open the food in Game Tools\'',
             'Item Editor and add an attribute row per ingredient:  cook:<ingredient item id>  N',
             '(e.g. Pizza: cook:wheat_flour 1, cook:tomato 1, cook:cheese 1).',
             'Ingredients the game already has are marked [in game]; the rest are items to make.',
             '',
             f'COOKED IN A KITCHEN ({len(cooked)})',
             '-' * 30]
    have = {os.path.splitext(f)[0] for f in os.listdir(os.path.join(ROOT, 'assets', 'items')) if f.endswith('.c')}
    have |= {os.path.splitext(f)[0] + '_seeds' for f in os.listdir(os.path.join(ROOT, 'assets', 'crops')) if f.endswith('.c')}
    have |= {os.path.splitext(f)[0] for f in os.listdir(os.path.join(ROOT, 'assets', 'crops')) if f.endswith('.c')}
    def mark(part):
        base = part.strip()
        name = base.split(' x')[0].strip()
        iid = name.lower().replace("'", '').replace(' ', '_').replace('(any)', '').strip('_')
        return base + (' [in game]' if iid in have else '')
    for cell, fid, name, sell, how in sorted(cooked, key=lambda f: f[2]):
        parts = how[len(C):].split(', ')
        lines.append(f'{name}  ({fid}, sells for {sell}g)')
        lines.append('    ' + ', '.join(mark(p) for p in parts))
    lines += ['', f'NOT COOKED IN STARDEW ({len(other)})', '-' * 30]
    for cell, fid, name, sell, how in sorted(other, key=lambda f: f[2]):
        lines.append(f'{name}  ({fid}, sells for {sell}g)')
        lines.append('    ' + how)
    return '\n'.join(lines) + '\n'


def preview(foods, path):
    S, Cn = 4, 8
    rows = (len(foods) + Cn - 1) // Cn
    img = Image.new('RGBA', (Cn * 120, rows * (16 * S + 14)), (70, 100, 70, 255))
    d = ImageDraw.Draw(img)
    for k, f in enumerate(foods):
        x, y = (k % Cn) * 120, (k // Cn) * (16 * S + 14)
        img.alpha_composite(picture(f[0]).resize((16 * S, 16 * S), Image.NEAREST), (x + 28, y))
        d.text((x + 2, y + 16 * S + 1), f[2][:19], fill=(255, 255, 255, 255))
    img.save(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--preview')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--force', action='store_true')
    ap.add_argument('--recipes', action='store_true')
    a = ap.parse_args()
    foods = all_foods()
    if a.preview:
        preview(foods, a.preview)
        print('preview ->', a.preview)
    if a.write:
        for cell, fid, name, sell, how in foods:
            path = os.path.join(ROOT, 'assets', 'items', fid + '.c')
            if os.path.exists(path) and not a.force:
                print('kept (exists):', os.path.relpath(path, ROOT)); continue
            open(path, 'w', encoding='utf-8', newline='\n').write(item_c(fid, name, sell, how, picture(cell)))
            print('wrote', os.path.relpath(path, ROOT))
    if a.recipes:
        path = os.path.join(DL, 'stardew_food_recipes.txt')
        open(path, 'w', encoding='utf-8', newline='\r\n').write(recipes_text(foods))
        print('wrote', path)


if __name__ == '__main__':
    main()
