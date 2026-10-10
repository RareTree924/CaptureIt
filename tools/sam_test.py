"""sam_test.py - try SAM 3 on Roboflow for the CAM's object masks.

Usage:
    python tools/sam_test.py photo.jpg [more.jpg ...]

Keys: GEMINI_API_KEY and ROBOFLOW_API_KEY from the CAM's secrets.h (never printed).

For each photo, like the CAM: the centre square at 640x640 goes to Gemini for names + boxes
(gemini_test.py's prompt), then to SAM 3 two ways:
  PVS  one request per object, the object's box as the prompt (sam3/visual_segment)
  PCS  one request for all, the names as text prompts (sam3/concept_segment)
Writes <photo>_pvs.png and <photo>_pcs.png (masks over the 480x480 photo), and the raw
replies as <photo>_pvs.json / <photo>_pcs.json.
"""
import base64
import io
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw, ImageOps

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gemini_test as g  # noqa: E402

SECRETS = r"C:\projects\ESP32CamFirmware\main\secrets.h"
SEND, OUT = g.SEND, g.OUT
ROBOFLOW = "https://serverless.roboflow.com/sam3/"


def secret(name):
    with open(SECRETS, encoding="utf-8-sig") as f:
        m = re.search(r'^#define\s+' + name + r'\s+"([^"]*)"', f.read(), re.M)
    if not m or not m.group(1):
        sys.exit(f"{name} is empty in secrets.h")
    return m.group(1)


def post(endpoint, key, body):
    req = urllib.request.Request(ROBOFLOW + endpoint, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            raw = r.read()
            status = r.status
    except urllib.error.HTTPError as e:
        raw, status = e.read(), e.code
    return status, raw, time.time() - t0


def polygons(node):
    """Every list of [x, y] pairs (3+ points) anywhere in a reply."""
    found = []
    if isinstance(node, list):
        if len(node) >= 3 and all(isinstance(p, (list, tuple)) and len(p) == 2 and
                                  all(isinstance(v, (int, float)) for v in p) for p in node):
            return [node]
        for x in node:
            found += polygons(x)
    elif isinstance(node, dict):
        for v in node.values():
            found += polygons(v)
    return found


def draw(photo480, groups, path):
    """groups: list of (label, [polygons in 640 px])."""
    canvas = photo480.convert("RGBA")
    over = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(over)
    k = OUT / SEND
    for i, (label, polys) in enumerate(groups):
        col = g.COLOURS[i % len(g.COLOURS)]
        for poly in polys:
            pts = [(x * k, y * k) for x, y in poly]
            d.polygon(pts, fill=col + (90,), outline=col + (255,))
        if polys:
            x0 = min(x for poly in polys for x, _ in poly) * k
            y0 = min(y for poly in polys for _, y in poly) * k
            d.text((x0 + 2, max(0, y0 - 11)), label, fill=col + (255,))
    Image.alpha_composite(canvas, over).convert("RGB").save(path)


def run(path, gkey, rkey):
    base = os.path.splitext(path)[0]
    img = g.centre_square(ImageOps.exif_transpose(Image.open(path)).convert("RGB"))
    send = img.resize((SEND, SEND), Image.LANCZOS)
    buf = io.BytesIO()
    send.save(buf, "JPEG", quality=80)
    jpeg_b64 = base64.b64encode(buf.getvalue()).decode()
    show = img.resize((OUT, OUT), Image.LANCZOS)
    print(f"\n=== {path}")

    text, dt, _ = g.call_gemini(gkey, buf.getvalue())
    objs = [o for o in g.parse_objects(text) if isinstance(o.get("box_2d"), list) and len(o["box_2d"]) == 4]
    print(f"Gemini: {len(objs)} objects in {dt:.1f} s")
    image = {"type": "base64", "value": jpeg_b64}

    # PVS: one request per box (centre-anchored, 640 px)
    groups, raws, t_all = [], [], time.time()
    for o in objs:
        ymin, xmin, ymax, xmax = (v * SEND / 1000 for v in o["box_2d"])
        body = {"image": image, "prompts": {"prompts": [{"box": {"x": (xmin + xmax) / 2, "y": (ymin + ymax) / 2,
                                                                "width": xmax - xmin, "height": ymax - ymin}}]},
                "multimask_output": False, "format": "polygon"}
        st, raw, t = post("visual_segment", rkey, body)
        try:
            rep = json.loads(raw)
        except ValueError:
            rep = {"raw": raw[:500].decode(errors="replace")}
        raws.append(rep)
        polys = polygons(rep) if st == 200 else []
        pts = sum(len(p) for p in polys)
        print(f"  PVS '{o.get('label')}': HTTP {st}, {len(raw) // 1024} KB, {t:.1f} s, {len(polys)} polygon(s), {pts} points"
              + ("" if st == 200 else f"  {raw[:200]!r}"))
        groups.append((str(o.get("label", "?")), polys))
    print(f"  PVS total {time.time() - t_all:.1f} s for {len(objs)} requests")
    json.dump(raws, open(base + "_pvs.json", "w"), indent=1)
    draw(show, groups, base + "_pvs.png")

    # PCS: one request, the kinds as text prompts (SAM 3 finds nothing for long brand-style names)
    print("  kinds: " + ", ".join(f"{o.get('label')} -> {o.get('kind')}" for o in objs))
    labels = list(dict.fromkeys(str(o.get("kind") or o.get("label", "")) for o in objs))
    body = {"image": image, "prompts": [{"type": "text", "text": lb} for lb in labels],
            "output_prob_thresh": 0.5, "format": "polygon"}
    st, raw, t = post("concept_segment", rkey, body)
    try:
        rep = json.loads(raw)
    except ValueError:
        rep = {"raw": raw[:500].decode(errors="replace")}
    json.dump(rep, open(base + "_pcs.json", "w"), indent=1)
    print(f"  PCS ({len(labels)} text prompts): HTTP {st}, {len(raw) // 1024} KB, {t:.1f} s"
          + ("" if st == 200 else f"  {raw[:300]!r}"))
    if st == 200:
        # per-prompt results if the reply has them, else everything as one group
        per = rep.get("prompt_results") if isinstance(rep, dict) else None
        if isinstance(per, list) and len(per) == len(labels):
            pg = [(lb, polygons(r)) for lb, r in zip(labels, per)]
        else:
            pg = [("all", polygons(rep))]
        for lb, polys in pg:
            print(f"    '{lb}': {len(polys)} polygon(s)")
        draw(show, pg, base + "_pcs.png")
        print(f"    reply keys: {list(rep.keys()) if isinstance(rep, dict) else type(rep).__name__}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    gk, rk = secret("GEMINI_API_KEY"), secret("ROBOFLOW_API_KEY")
    for p in sys.argv[1:]:
        run(p, gk, rk)
