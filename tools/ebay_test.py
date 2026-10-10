"""ebay_test.py - check the eBay keys and see what a price search returns, the way the ESP32-CAM will do it.

Usage:
    python tools/ebay_test.py "Panasonic cordless handset" ["another search" ...]

Reads EBAY_CLIENT_ID, EBAY_CLIENT_SECRET and EBAY_MARKETPLACE from the CAM's secrets.h
(C:/projects/ESP32CamFirmware/main/secrets.h). The keys are never printed.

For each search: gets an application token (once), searches active fixed-price listings
(Browse API item_summary/search), and prints the prices, the middle price and the typical
range, the reply size and the timings.
"""
import base64
import json
import os
import re
import statistics
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

SECRETS = r"C:\projects\ESP32CamFirmware\main\secrets.h"
LIMIT = 20


def secret(name):
    with open(SECRETS, encoding="utf-8-sig") as f:
        m = re.search(r'^#define\s+' + name + r'\s+"([^"]*)"', f.read(), re.M)
    if not m or not m.group(1):
        sys.exit(f"{name} is empty in secrets.h - fill it in first")
    return m.group(1)


def get_token(cid, csecret):
    basic = base64.b64encode(f"{cid}:{csecret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "client_credentials",
                                   "scope": "https://api.ebay.com/oauth/api_scope"}).encode()
    req = urllib.request.Request("https://api.ebay.com/identity/v1/oauth2/token", data=body, method="POST",
                                 headers={"Content-Type": "application/x-www-form-urlencoded",
                                          "Authorization": "Basic " + basic})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"token request failed: HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")
    print(f"token: OK in {time.time() - t0:.1f} s, valid {d.get('expires_in')} s, {len(d['access_token'])} chars")
    return d["access_token"]


def search(token, market, q):
    params = urllib.parse.urlencode({"q": q, "limit": LIMIT, "filter": "buyingOptions:{FIXED_PRICE}"})
    req = urllib.request.Request("https://api.ebay.com/buy/browse/v1/item_summary/search?" + params,
                                 headers={"Authorization": "Bearer " + token,
                                          "X-EBAY-C-MARKETPLACE-ID": market})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
    except urllib.error.HTTPError as e:
        print(f"  search failed: HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")
        return
    dt = time.time() - t0
    d = json.loads(raw)
    items = d.get("itemSummaries", [])
    prices = []
    cur = None
    for it in items:
        p = it.get("price") or {}
        try:
            prices.append(float(p["value"]))
            cur = p.get("currency", cur)
        except (KeyError, ValueError):
            pass
    print(f'\n"{q}" on {market}: {d.get("total", 0)} listings in total, {len(items)} returned, '
          f"reply {len(raw) // 1024} KB in {dt:.1f} s")
    for it in items[:5]:
        print(f'  {it.get("price", {}).get("value", "?"):>9} {it.get("price", {}).get("currency", "")}  '
              f'{it.get("condition", "")[:12]:12}  {it.get("title", "")[:60]}')
    if prices:
        prices.sort()
        q1, q3 = (statistics.quantiles(prices, n=4)[0], statistics.quantiles(prices, n=4)[2]) if len(prices) >= 4 else (prices[0], prices[-1])
        print(f"  prices: {', '.join(f'{p:g}' for p in prices)}")
        print(f"  -> middle {statistics.median(prices):.2f} {cur}, typical {q1:.2f} - {q3:.2f}")
    # what the CAM will look for in the raw text instead of parsing it all
    hits = re.findall(rb'"price":\{"value":"([0-9.]+)","currency":"([A-Z]{3})"', raw)
    print(f'  raw-text scan finds {len(hits)} "price" values (the CAM does it this way)')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    cid, csec, market = secret("EBAY_CLIENT_ID"), secret("EBAY_CLIENT_SECRET"), secret("EBAY_MARKETPLACE")
    tok = get_token(cid, csec)
    for q in sys.argv[1:]:
        search(tok, market, q)
