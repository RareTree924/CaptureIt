"""gemini_test.py - try Gemini 2.5 Flash as the pawn shop's "eyes": boxes, outlines and names in one call.

Usage (from a terminal, with Pillow available):
    python tools/gemini_test.py photo.jpg [more.jpg ...]

The API key is read from the GEMINI_API_KEY environment variable, or from the first line of
tools/gemini_key.txt (a free key from Google AI Studio; keep that file out of backups and sharing).

What it does for each photo, the way the ESP32-CAM will:
  1. takes the centre square and scales it to 640x640 (the CAM's photo) and 480x480 (what the S3 draws)
  2. sends it to Gemini with thinking turned off and asks for box + outline + name of every object
  3. prints each object, how long the call took, and what format the outline came back in
  4. writes <photo>_gemini.png (boxes, outlines and names drawn on the 480x480 photo),
     <photo>_gemini_outline.png (the 1-bit border bitmap the S3 would show) and <photo>_gemini.json (raw reply)
"""
import base64
import io
import json
import os
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageOps

MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")   # what the CAM uses; 2.5 (real masks) is closed to new accounts
POLY_POINTS = int(os.environ.get("GEMINI_POLY", "0"))         # > 0: also ask for each object's outline as this many points
MAX_OBJECTS = 10
OUT = 480          # the S3's picture size
SEND = 640         # what the CAM sends to the AI

if POLY_POINTS:
    PROMPT = (
        f"Detect the distinct physical objects in this photo (at most {MAX_OBJECTS}). "
        "Ignore the table, floor, walls and hands. "
        'Output a JSON list where each entry has the 2D bounding box in the key "box_2d" '
        "([ymin, xmin, ymax, xmax] normalized to 0-1000), a text label in the key \"label\", and the "
        f'object\'s outline in the key "outline": exactly {POLY_POINTS} points [y, x] normalized to 0-1000, '
        "going around the object's visible edge in order, tracing its real shape closely (not its box). "
        "Use a specific label, the way you would write it in an eBay search (2-5 words, include brand or "
        "model when you can read it)."
    )
else:
    PROMPT = (
        f"Detect the distinct physical objects in this photo (at most {MAX_OBJECTS}). "
        "Ignore the table, floor, walls and hands. "
        'Output a JSON list where each entry has the 2D bounding box in the key "box_2d" '
        "([ymin, xmin, ymax, xmax] normalized to 0-1000), a text label in the key \"label\" (a specific name, "
        "the way you would write it in an eBay search: 2-5 words, with the brand or model when you can read it) "
        "and what kind of thing it is in the key \"kind\" (1-2 plain everyday words, no brand, e.g. \"sandal\", "
        "\"circuit board\", \"phone\"). "
        'Give each entry "new_price": what it costs new in a store today (for something no longer sold, '
        'what a similar one costs new), and "value": what this exact thing sells for used in the condition '
        "you can see - something that looks new or barely used keeps about 50-70% of its new price, so do not "
        "low-ball it. Both in Canadian dollars, numbers only, for the whole thing (not a part or accessory of it). "
        'And exactly 5 traits in the key "traits": a list of {"t": a trait in 1-2 words, Title Case, '
        'at most 14 characters, "x": what it does to the value, 0.7 to 1.6, 1.0 = ordinary}. '
        "The first trait is how good the photo of this thing is. The photo comes from a cheap 2-megapixel "
        "OV2640 camera module (ESP32-CAM), cropped to 640x640 JPEG: some softness, noise, JPEG blur and dull "
        "colour are normal for it and are not flaws. Judge the photo against the best this camera can do: "
        'in focus for it, well framed and well lit is good (e.g. "Crisp Shot" 1.4, "Well Framed" 1.3, '
        '"Good Light" 1.2); only call it bad when it is much worse than this camera\'s usual (e.g. '
        '"Motion Blur" 0.8, "Too Dark" 0.8, "Cut Off" 0.8). The other 4 traits describe the thing '
        'itself: its condition, material, features, brand or rarity (e.g. "Like New" 1.3, "Vintage" 1.4, '
        '"Leather" 1.2, "Name Brand" 1.3, "Worn" 0.9, "Scratched" 0.8); most are 1.0 or more, '
        "lower only for a flaw you can clearly see."
    )

COLOURS = [(255, 64, 64), (64, 200, 64), (80, 120, 255), (255, 200, 0), (255, 0, 255),
           (0, 220, 220), (255, 128, 0), (160, 80, 255), (128, 255, 128), (255, 128, 160)]


def get_key():
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gemini_key.txt")
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.readline().strip()
    sys.exit("No API key: set GEMINI_API_KEY or put the key on the first line of tools/gemini_key.txt")


def centre_square(img):
    w, h = img.size
    s = min(w, h)
    return img.crop(((w - s) // 2, (h - s) // 2, (w - s) // 2 + s, (h - s) // 2 + s))


def call_gemini(key, jpeg_bytes):
    body = {
        "contents": [{"parts": [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(jpeg_bytes).decode()}},
            {"text": PROMPT},
        ]}],
        "generationConfig": {
            "response_mime_type": "application/json",
            **({"response_schema": {   # forces the outline into every entry (asked plainly, it's skipped)
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "box_2d": {"type": "ARRAY", "items": {"type": "INTEGER"}},
                        "label": {"type": "STRING"},
                        "outline": {"type": "ARRAY", "items": {"type": "ARRAY", "items": {"type": "INTEGER"}}},
                    },
                    "required": ["box_2d", "label", "outline"],
                },
            }} if POLY_POINTS else {}),
            "thinkingConfig": {"thinkingBudget": 0},   # Google: best segmentation with thinking off
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "x-goog-api-key": key})
    t0 = time.time()
    for attempt in range(4):                           # the CAM will retry busy errors the same way
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = r.read()
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503) and attempt < 3:
                print(f"  HTTP {e.code} (busy), retrying in {2 << attempt} s ...")
                time.sleep(2 << attempt)
                continue
            sys.exit(f"Gemini returned HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")
    dt = time.time() - t0
    reply = json.loads(raw)
    try:
        text = reply["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        sys.exit("Unexpected reply: " + json.dumps(reply)[:800])
    return text, dt, len(raw)


def parse_objects(text):
    text = text.strip()
    if text.startswith("```"):                       # tolerate a markdown fence
        text = text.strip("`")
        text = text[text.find("\n") + 1:] if text.lower().startswith("json") else text
    data = json.loads(text)
    return data if isinstance(data, list) else [data]


def box_to_px(box, size):
    ymin, xmin, ymax, xmax = box                      # Gemini: y first, 0-1000
    x1 = max(0, min(size, round(xmin * size / 1000)))
    y1 = max(0, min(size, round(ymin * size / 1000)))
    x2 = max(0, min(size, round(xmax * size / 1000)))
    y2 = max(0, min(size, round(ymax * size / 1000)))
    return x1, y1, x2, y2


def mask_image(obj, box_px, size):
    """Returns (kind, full-size 'L' mask 0/255 or None). Handles PNG probability maps and polygons."""
    m = obj.get("mask")
    x1, y1, x2, y2 = box_px
    bw, bh = x2 - x1, y2 - y1
    full = Image.new("L", (size, size), 0)
    poly = obj.get("outline")
    if isinstance(poly, list) and len(poly) >= 3 and all(isinstance(p, (list, tuple)) and len(p) == 2 for p in poly):
        pts = [(p[1] * size / 1000, p[0] * size / 1000) for p in poly]   # [y, x] like box_2d
        ImageDraw.Draw(full).polygon(pts, fill=255)
        return f"polygon {len(poly)} pts", full
    if bw < 2 or bh < 2 or not m:
        return "none", None
    if isinstance(m, str) and m.lstrip().startswith("{"):   # Gemini 3.x: {"shape": [h, w], "point": [y, x]}
        try:
            info = json.loads(m)
            return "point-only", info.get("point")
        except ValueError:
            return "unknown", None
    if isinstance(m, str):                            # "data:image/png;base64,...."
        b64 = m.split(",", 1)[1] if m.startswith("data:") else m
        try:
            png = Image.open(io.BytesIO(base64.b64decode(b64))).convert("L")
        except Exception:
            return "bad-png", None
        png = png.resize((bw, bh), Image.BILINEAR).point(lambda v: 255 if v > 127 else 0)
        full.paste(png, (x1, y1))
        return "png", full
    if isinstance(m, list) and m and isinstance(m[0], (list, tuple)):   # [[x, y], ...] 0-1000
        pts = [(p[0] * size / 1000, p[1] * size / 1000) for p in m]
        ImageDraw.Draw(full).polygon(pts, fill=255)
        return "polygon", full
    return "unknown", None


def border_of(mask):
    """1-pixel border of a 0/255 mask: the mask minus itself shrunk by one pixel."""
    return ImageChops.subtract(mask, mask.filter(ImageFilter.MinFilter(3)))


def run(path, key):
    base = os.path.splitext(path)[0]
    img = centre_square(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))   # phones store photos sideways + a rotation tag
    send = img.resize((SEND, SEND), Image.LANCZOS)
    buf = io.BytesIO()
    send.save(buf, "JPEG", quality=80)
    show = img.resize((OUT, OUT), Image.LANCZOS)
    print(f"\n=== {path}: sending {SEND}x{SEND} JPEG, {len(buf.getvalue()) // 1024} KB to {MODEL}")

    text, dt, nbytes = call_gemini(key, buf.getvalue())
    with open(base + "_gemini.json", "w", encoding="utf-8") as f:
        f.write(text)
    objs = parse_objects(text)
    print(f"reply: {nbytes // 1024} KB in {dt:.1f} s, {len(objs)} object(s)")

    canvas = show.copy()
    draw = ImageDraw.Draw(canvas, "RGBA")
    outline_bits = Image.new("L", (OUT, OUT), 0)
    for i, o in enumerate(objs[:25]):
        colour = COLOURS[i % len(COLOURS)]
        label = str(o.get("label", "?"))
        box = o.get("box_2d")
        if not box or len(box) != 4:
            print(f"  {i + 1:2d}. {label!r}: no box")
            continue
        bpx = box_to_px(box, OUT)
        kind, mask = mask_image(o, bpx, OUT)
        area = (bpx[2] - bpx[0]) * (bpx[3] - bpx[1]) * 100 // (OUT * OUT)
        print(f"  {i + 1:2d}. {label!r}: box {bpx}, {area}% of photo, outline = {kind}")
        if kind == "point-only":
            px = mask                                  # [y, x] in the 640 frame the model saw
            if px and len(px) == 2:
                cx, cy = px[1] * OUT / SEND, px[0] * OUT / SEND
                draw.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=colour + (255,))
        elif mask is not None:
            tint = Image.new("RGBA", (OUT, OUT), colour + (90,))
            canvas.paste(tint, (0, 0), mask)
            outline_bits = ImageChops.lighter(outline_bits, border_of(mask))
        draw.rectangle(bpx, outline=colour + (255,), width=2)
        draw.text((bpx[0] + 3, bpx[1] + 2), f"{i + 1} {label}", fill=colour + (255,))
    canvas.save(base + "_gemini.png")
    outline_bits.point(lambda v: 255 if v else 0).save(base + "_gemini_outline.png")
    print(f"wrote {base}_gemini.png, {base}_gemini_outline.png, {base}_gemini.json")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    k = get_key()
    for p in sys.argv[1:]:
        run(p, k)
