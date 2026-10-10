"""The Debug Panel's little web server: debugPanel.html (project root) in a Chrome app window, talking to
the game through the DEV LINK (tools/devlink.py's background server, which holds the USB port).

    pythonw tools/debug_panel.py          start it (if it isn't already) and open the panel
    python  tools/debug_panel.py --no-open

A browser page can't open a serial port or devlink's socket, so this sits in between on
http://127.0.0.1:7767/. Start / Stop / Reset / Flash run devlink.py as a windowless child and the panel
shows its output. With no page asking anything for IDLE_EXIT_S it quits by itself (the window closed).
"""
import base64, glob, json, os, re, subprocess, sys, threading, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import devlink  # noqa: E402

HTTP_PORT = 7767
PAGE = os.path.join(devlink.PROJECT, "debugPanel.html")
ASSETS = os.path.join(devlink.PROJECT, "assets")
CHROME = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
IDLE_EXIT_S = 90
LINK_OPS = {"start": ["start"], "stop": ["stop"], "reset": ["reset"], "flash": ["flash"], "build_flash": ["flash", "--build"]}

_last_hit = time.time()
_job = {"name": "", "running": False, "ok": None, "log": []}
_job_lock = threading.Lock()


def python_for_devlink():
    """devlink needs pyserial: ESP-IDF's python has it (python.exe — it's started without a window)."""
    return devlink.IDF_PY if os.path.exists(devlink.IDF_PY) else sys.executable.replace("pythonw.exe", "python.exe")


def run_job(name, args):
    with _job_lock:
        if _job["running"]:
            return False
        _job.update(name=name, running=True, ok=None, log=[f"> devlink.py {' '.join(args)}"])

    def go():
        try:
            p = subprocess.Popen([python_for_devlink(), os.path.join(HERE, "devlink.py")] + args, cwd=devlink.PROJECT,
                                 stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                 creationflags=devlink.NO_WINDOW, text=True, encoding="utf-8", errors="replace")
            for line in p.stdout:
                with _job_lock:
                    _job["log"].append(line.rstrip("\n"))
                    del _job["log"][:-400]
            ok = p.wait() == 0
        except Exception as e:
            with _job_lock:
                _job["log"].append(f"error: {e}")
            ok = False
        with _job_lock:
            _job.update(running=False, ok=ok)
            _job["log"].append("done" if ok else "FAILED")

    threading.Thread(target=go, daemon=True).start()
    return True


# ---------------------------------------------------------------- assets -> catalog
_catalog = {"key": None, "data": None}


def _arrays(src):
    """name -> the text inside { } of every `static const uint16_t NAME[...] = { ... };`"""
    return {m.group(1): m.group(2) for m in re.finditer(r"static const uint16_t (\w+)\[\d*\]\s*=\s*\{([^}]*)\}", src)}


def _items_in(path, src):
    arrays, out = None, []
    attrs = {m.group(1): re.findall(r'\{\s*"([^"]+)"\s*,\s*(-?\d+)\s*\}', m.group(2))
             for m in re.finditer(r"static const item_attr_t (\w+)\[\]\s*=\s*\{(.*?)\n\};", src, re.S)}
    for m in re.finditer(r"const item_asset_t k_item_\w+\s*=\s*\{(.*?)\n\};", src, re.S):
        body = m.group(1)
        iid = re.search(r'\.id\s*=\s*"([^"]+)"', body)
        if not iid:
            continue
        name = re.search(r'\.display_name\s*=\s*"((?:[^"\\]|\\.)*)"', body)
        stack = re.search(r"\.max_stack\s*=\s*(\d+)", body)
        pas = re.search(r"\.passive\s*=\s*\{([^}]*)\}", body)
        it = {"id": iid.group(1), "name": name.group(1) if name else iid.group(1), "stack": int(stack.group(1)) if stack else 1,
              "file": os.path.relpath(path, ASSETS).replace("\\", "/"), "w": 0, "h": 0, "px": ""}
        am = re.search(r"\.attrs\s*=\s*(\w+)", body)
        it["attrs"] = {k: int(v) for k, v in attrs.get(am.group(1), [])} if am else {}
        if pas:
            w, h, pix = (re.search(r"\.w\s*=\s*(\d+)", pas.group(1)), re.search(r"\.h\s*=\s*(\d+)", pas.group(1)),
                         re.search(r"\.pixels\s*=\s*(\w+)", pas.group(1)))
            if w and h and pix:
                if arrays is None:
                    arrays = _arrays(src)
                vals = re.findall(r"0x([0-9a-fA-F]{1,4})", arrays.get(pix.group(1), ""))
                n = int(w.group(1)) * int(h.group(1))
                if len(vals) >= n:   # the first frame, as 4 hex digits a pixel
                    it.update(w=int(w.group(1)), h=int(h.group(1)), px="".join(v.zfill(4) for v in vals[:n]))
        out.append(it)
    return out


def _editor_json(src, tag):
    m = re.search(r"// " + tag + r" (\{.*\})", src)
    try:
        return json.loads(m.group(1)) if m else {}
    except ValueError:
        return {}


def catalog():
    files = sorted(glob.glob(os.path.join(ASSETS, "*", "*.c")))
    key = tuple((f, os.path.getmtime(f)) for f in files)
    if _catalog["key"] == key:
        return _catalog["data"]
    items, animals, crops = [], [], []
    for f in files:
        sub = os.path.basename(os.path.dirname(f))
        if sub not in ("items", "crops", "animals", "machines", "buildings"):
            continue
        with open(f, encoding="utf-8", errors="replace") as fh:
            src = fh.read()
        items += _items_in(f, src)
        base = os.path.splitext(os.path.basename(f))[0]
        if sub == "animals":
            j = _editor_json(src, "ANIMALS-EDITOR")
            animals.append({"id": base, "name": j.get("name", base), "colours": [c.get("name", "") for c in j.get("colours", [])] or ["Normal"],
                            "product": j.get("product", ""), "tool": j.get("tool", "")})
        elif sub == "crops":
            j = _editor_json(src, "CROPS-EDITOR")
            crops.append({"id": base, "name": j.get("name", base), "growDays": j.get("growDays"), "regrows": j.get("regrows")})
    seen, uniq = set(), []
    for it in items:   # an animal file's item and its own may share an id: keep the first
        if it["id"] not in seen:
            seen.add(it["id"]); uniq.append(it)
    _catalog.update(key=key, data={"items": uniq, "animals": animals, "crops": crops})
    return _catalog["data"]


# ---------------------------------------------------------------- http
def link_request(req, timeout=60):
    if not devlink.server_up():
        return {"ok": False, "lines": ["@@ERR the dev link isn't started"]}
    try:
        return devlink.request(req, timeout=timeout)
    except OSError as e:
        return {"ok": False, "lines": [f"@@ERR dev link: {e}"]}


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except OSError:
            pass

    def _body(self):
        n = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(n) or b"{}") if n else {}

    def do_GET(self):
        global _last_hit
        _last_hit = time.time()
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html", "/debugPanel.html"):
            with open(PAGE, "rb") as f:
                return self._send(200, f.read(), "text/html; charset=utf-8")
        if u.path == "/favicon.ico":
            p = os.path.join(HERE, "debugPanel.ico")
            if os.path.exists(p):
                with open(p, "rb") as f:
                    return self._send(200, f.read(), "image/x-icon")
            return self._send(404, b"", "text/plain")
        if u.path == "/api/status":
            up = devlink.server_up()
            board = False
            if up and not _job["running"]:
                try:
                    board = any(a.startswith("@@OK pong") for a in devlink.cmd("ping", timeout=1.5)["lines"])
                except OSError:
                    pass
            with _job_lock:
                job = dict(_job, log=_job["log"][-200:])
            return self._send(200, {"server": up, "board": board, "job": job})
        if u.path == "/api/catalog":
            return self._send(200, catalog())
        if u.path == "/api/log":
            n = int(q.get("n", ["80"])[0])
            if devlink.server_up():
                return self._send(200, link_request({"kind": "log", "n": n}))
            try:
                with open(devlink.LOG, encoding="utf-8", errors="replace") as f:
                    return self._send(200, {"ok": True, "lines": [l.rstrip("\n") for l in f.readlines()[-n:]]})
            except OSError:
                return self._send(200, {"ok": True, "lines": []})
        return self._send(404, {"ok": False, "lines": ["not found"]})

    def do_POST(self):
        global _last_hit
        _last_hit = time.time()
        u = urlparse(self.path)
        try:
            b = self._body()
        except ValueError:
            return self._send(400, {"ok": False, "lines": ["bad json"]})
        if u.path == "/api/link":
            op = b.get("op", "")
            if op not in LINK_OPS:
                return self._send(400, {"ok": False, "lines": ["bad op"]})
            started = run_job(op, LINK_OPS[op])
            return self._send(200, {"ok": started, "lines": [] if started else ["something else is still running"]})
        if _job["running"]:
            return self._send(200, {"ok": False, "lines": [f"@@ERR wait — {_job['name']} is still running"]})
        if u.path == "/api/cmd":
            line = str(b.get("line", "")).strip()
            if not line or "\n" in line:
                return self._send(400, {"ok": False, "lines": ["@@ERR one command"]})
            req = {"kind": "cmd", "line": line, "timeout": float(b.get("timeout", 20))}
            if b.get("end"):
                req["end"] = list(b["end"])
            return self._send(200, link_request(req, timeout=req["timeout"] + 10))
        if u.path == "/api/put":
            req = {"kind": "put", "remote": b.get("remote", ""), "data": b.get("data", "")}
            return self._send(200, link_request(req, timeout=600))
        if u.path == "/api/get":
            r = link_request({"kind": "cmd", "line": "get " + b.get("remote", ""), "timeout": 120}, timeout=130)
            data = b"".join(base64.b64decode(a[4:]) for a in r.get("lines", []) if a.startswith("@@D "))
            ok = r.get("ok") and any(a.startswith("@@END") for a in r.get("lines", []))
            return self._send(200, {"ok": bool(ok), "data": base64.b64encode(data).decode(),
                                    "lines": [a for a in r.get("lines", []) if not a.startswith("@@D ")]})
        if u.path == "/api/quit":
            self._send(200, {"ok": True, "lines": []})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        return self._send(404, {"ok": False, "lines": ["not found"]})


def already_running():
    import socket
    try:
        socket.create_connection(("127.0.0.1", HTTP_PORT), timeout=1).close()
        return True
    except OSError:
        return False


def open_window():
    url = f"http://127.0.0.1:{HTTP_PORT}/"
    if os.path.exists(CHROME):
        subprocess.Popen([CHROME, f"--app={url}", "--window-size=1500,960"], creationflags=devlink.NO_WINDOW, close_fds=True)
    else:
        import webbrowser
        webbrowser.open(url)


def main():
    if already_running():
        if "--no-open" not in sys.argv:
            open_window()
        return 0
    srv = ThreadingHTTPServer(("127.0.0.1", HTTP_PORT), Handler)
    srv.daemon_threads = True

    def idle_watch():
        while True:
            time.sleep(5)
            if not _job["running"] and time.time() - _last_hit > IDLE_EXIT_S:
                srv.shutdown(); return

    threading.Thread(target=idle_watch, daemon=True).start()
    if "--no-open" not in sys.argv:
        open_window()
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
