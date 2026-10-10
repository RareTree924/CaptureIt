"""PC side of the S3's DEV LINK (main.c, DEV_LINK_ENABLED in game_config.h).

The board takes text commands over its USB serial port while audio is off.
Opening the port resets the board, so one background server keeps it open
and everything else talks to that server:

    python tools/devlink.py serve [PORT] [--take]  keep the port open (logs to tools/devlink.log);
                                                --take closes an ESP-IDF monitor that has the port
    python tools/devlink.py start [PORT]        serve in the background (if it isn't already), wait for the board
    python tools/devlink.py wait [SECS]         wait until the board answers (after a reset / flash)
    python tools/devlink.py flash [--build]     stop the server, (build,) flash, start it again, wait for the board
    python tools/devlink.py load [N]            on the title screen: load save N (default 1), wait till in game
    python tools/devlink.py cmd "state"         any DEV LINK command; prints the @@ answer lines
    python tools/devlink.py shot out.png        screenshot
    python tools/devlink.py tap X Y [MS]
    python tools/devlink.py put LOCAL REMOTE    copy a file onto the SD card (REMOTE: /sdcard/...)
    python tools/devlink.py get REMOTE LOCAL
    python tools/devlink.py log [N]             the last N lines the board printed
    python tools/devlink.py stop                stop the server (flash does this itself)

Any python works: without pyserial / Pillow it re-runs itself with ESP-IDF's
(IDF_PY below). PORT defaults to the Espressif USB device (VID 303A), else COM3.
"""
import base64, os, socket, subprocess, sys, threading, time, json

HOST, PORT = "127.0.0.1", 7766
HERE = os.path.dirname(os.path.abspath(__file__))
PROJECT = os.path.dirname(HERE)
LOG = os.path.join(HERE, "devlink.log")
END_CMDS = ("shot", "get ", "state", "ls ", "prof", "psram", "stacks", "items")    # answers end with @@END (so do END_WHOLE)
END_WHOLE = ("npc", "npc list", "crops", "crops list", "machines", "machines list")
IDF_PY = r"C:\Espressif\tools\python\v6.1\venv\Scripts\python.exe"
IDF_PROFILE = r"C:\Espressif\tools\Microsoft.v6.1.PowerShell_profile.ps1"
ESPRESSIF_VID = 0x303A
# Every program devlink starts runs without a window of its own: started from a process with no
# visible console (the background server, an editor's terminal), Windows would otherwise pop one
# up on screen for each PowerShell / taskkill / esptool run.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def own_output():
    """Hand a windowless child our stdout/stderr explicitly: it gets a hidden console of its own, and
    would print into that (and be lost) instead of to whoever ran devlink."""
    try:
        sys.stdout.flush(); sys.stderr.flush()
        return {"stdin": subprocess.DEVNULL, "stdout": sys.stdout.fileno(), "stderr": sys.stderr.fileno()}
    except (AttributeError, OSError, ValueError):   # no stdout (pythonw)
        return {}


def need(*mods):
    """Re-run this command with ESP-IDF's python if this one lacks a module it needs."""
    try:
        for m in mods:
            __import__(m)
    except ImportError:
        if os.path.normcase(sys.executable) != os.path.normcase(IDF_PY) and os.path.exists(IDF_PY):
            sys.exit(subprocess.call([IDF_PY, os.path.abspath(__file__)] + sys.argv[1:], creationflags=NO_WINDOW, **own_output()))
        raise


def find_port():
    import serial.tools.list_ports
    for p in serial.tools.list_ports.comports():
        if p.vid == ESPRESSIF_VID:
            return p.device
    return "COM3"


def monitors_on(port):
    """(pid, command line) of ESP-IDF monitors (VS Code's included) that have `port` open."""
    ps = ("Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'idf_monitor|esp_idf_monitor' } | "
          "ForEach-Object { \"$($_.ProcessId)`t$($_.CommandLine)\" }")
    try:
        out = subprocess.run(["powershell", "-NoProfile", "-Command", ps], capture_output=True, text=True, timeout=30, creationflags=NO_WINDOW).stdout
    except Exception:
        return []
    found = []
    for line in out.splitlines():
        pid, _, cl = line.partition("\t")
        if pid.strip().isdigit() and f"-p {port}".lower() in cl.lower():
            found.append((int(pid), cl.strip()))
    return found


def take_port(port):
    """Closes the monitors holding `port`. True if there were any."""
    mons = monitors_on(port)
    for pid, _ in mons:
        subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True, creationflags=NO_WINDOW)
    if mons:
        print(f"devlink: closed {len(mons)} monitor(s) on {port}", flush=True)
        time.sleep(0.5)
    return bool(mons)


def remote(p):
    """A path on the board. Git Bash turns a bare /sdcard/... argument into C:/Program Files/Git/sdcard/...
    before python sees it — take it back."""
    p = p.replace("\\", "/")
    i = p.find("/sdcard")
    return p[i:] if i > 0 and ":" in p[:i] else p


def server_up():
    try:
        socket.create_connection((HOST, PORT), timeout=1).close()
        return True
    except OSError:
        return False


# ---------------------------------------------------------------- server
def serve(port_name, take=False):
    import serial
    ser = serial.Serial()
    ser.port, ser.baudrate, ser.timeout = port_name, 115200, 0.2
    ser.dtr = False
    ser.rts = False
    try:
        ser.open()
    except serial.SerialException:
        mons = monitors_on(port_name)
        if not mons:
            raise
        if not take:
            print(f"devlink: {port_name} is busy — held by an ESP-IDF monitor:", flush=True)
            for pid, cl in mons:
                print(f"  pid {pid}: {cl[:120]}", flush=True)
            print("run again with --take to close it", flush=True)
            sys.exit(3)
        take_port(port_name)
        ser.open()
    answers, cond, log_lock = [], threading.Condition(), threading.Lock()
    logf = open(LOG, "a", encoding="utf-8", errors="replace")
    stop = threading.Event()

    def reader():
        buf = b""
        while not stop.is_set():
            try:
                chunk = ser.read(4096)
            except Exception as e:  # unplugged / reset
                time.sleep(0.5)
                continue
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                line = raw.decode("utf-8", "replace").rstrip("\r")
                i = line.find("@@")
                if i >= 0:
                    with cond:
                        answers.append(line[i:])
                        cond.notify_all()
                    if not line[i:].startswith(("@@R ", "@@D ", "@@K ")):
                        with log_lock:
                            logf.write(line + "\n"); logf.flush()
                else:
                    with log_lock:
                        logf.write(line + "\n"); logf.flush()

    threading.Thread(target=reader, daemon=True).start()

    def send(line):
        ser.write((line + "\n").encode())

    def wait(pred, timeout):
        """Collect answer lines until pred(line) is true (that line included)."""
        got, t_end = [], time.time() + timeout
        with cond:
            while True:
                while answers:
                    a = answers.pop(0)
                    got.append(a)
                    if pred(a):
                        return got, True
                left = t_end - time.time()
                if left <= 0:
                    return got, False
                cond.wait(left)

    def handle(req):
        kind = req.get("kind")
        with cond:
            answers.clear()
        if kind == "cmd":
            line = req["line"]
            ends = line.startswith(END_CMDS) or line.strip() in END_WHOLE   # other npc commands answer one @@OK line
            last = tuple(req["end"]) if req.get("end") else ("@@END", "@@ERR") if ends else None   # "end": the caller says what ends it
            send(line)
            got, ok = wait((lambda a: a.startswith(last)) if last else (lambda a: True), req.get("timeout", 20))
            return {"ok": ok, "lines": got}
        if kind == "put":
            data = base64.b64decode(req["data"])
            send(f"put {req['remote']} {len(data)}")
            got, ok = wait(lambda a: a.startswith(("@@OK", "@@ERR")), 10)
            if not ok or not got[-1].startswith("@@OK"):
                return {"ok": False, "lines": got}
            CH = 768
            for off in range(0, len(data), CH):
                send("d " + base64.b64encode(data[off:off + CH]).decode())
                got, ok = wait(lambda a: a.startswith(("@@K", "@@ERR")), 10)
                if not ok or got[-1].startswith("@@ERR"):
                    return {"ok": False, "lines": got, "at": off}
            send("end")
            got, ok = wait(lambda a: a.startswith(("@@OK", "@@ERR")), 20)
            return {"ok": ok and got[-1].startswith("@@OK"), "lines": got}
        if kind == "log":
            with log_lock:
                with open(LOG, encoding="utf-8", errors="replace") as f:
                    lines = f.readlines()[-req.get("n", 60):]
            return {"ok": True, "lines": [l.rstrip("\n") for l in lines]}
        if kind == "stop":
            stop.set()
            return {"ok": True, "lines": []}
        return {"ok": False, "lines": ["bad request"]}

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((HOST, PORT))
    srv.listen(4)
    srv.settimeout(0.5)
    print(f"devlink: serving {port_name} on {HOST}:{PORT}", flush=True)
    while not stop.is_set():
        try:
            conn, _ = srv.accept()
        except socket.timeout:
            continue
        with conn:
            data = b""
            while not data.endswith(b"\n"):
                part = conn.recv(1 << 20)
                if not part:
                    break
                data += part
            try:
                resp = handle(json.loads(data))
            except Exception as e:
                resp = {"ok": False, "lines": [f"server error: {e}"]}
            try:
                conn.sendall((json.dumps(resp) + "\n").encode())
            except OSError:
                pass   # the client went away (stopped mid-command): keep serving
    ser.close()
    logf.close()


# ---------------------------------------------------------------- client
def request(req, timeout=120):
    s = socket.create_connection((HOST, PORT), timeout=timeout)
    s.sendall((json.dumps(req) + "\n").encode())
    data = b""
    while not data.endswith(b"\n"):
        part = s.recv(1 << 20)
        if not part:
            break
        data += part
    s.close()
    return json.loads(data)


def cmd(line, timeout=20):
    return request({"kind": "cmd", "line": line, "timeout": timeout})


def shot(out_png):
    from PIL import Image
    r = request({"kind": "cmd", "line": "shot", "timeout": 30})
    w, h = 480, 480
    img = Image.new("RGB", (w, h), (255, 0, 255))
    px = img.load()
    rows = 0
    for a in r["lines"]:
        if a.startswith("@@SHOT"):
            _, w, h = a.split()[:3]
            w, h = int(w), int(h)
        elif a.startswith("@@R "):
            parts = a.split(" ", 2)
            try:
                y, raw = int(parts[1]), base64.b64decode(parts[2])
            except Exception:
                continue
            if len(raw) != w * 2:
                continue
            rows += 1
            for x in range(w):
                v = raw[2 * x] | raw[2 * x + 1] << 8
                px[x, y] = (((v >> 11) & 31) << 3, ((v >> 5) & 63) << 2, (v & 31) << 3)
    img.save(out_png)
    return rows


def wait_board(secs=30.0):
    """True once the board answers a ping (the server has to be up)."""
    t_end = time.time() + secs
    while time.time() < t_end:
        try:
            if any(a.startswith("@@OK pong") for a in cmd("ping", timeout=2)["lines"]):
                return True
        except OSError:
            pass
        time.sleep(0.5)
    return False


def start_server(port):
    """serve in a background process (logging to devlink.log), unless one's already up. It gets a hidden
    console (not DETACHED_PROCESS: then each program it starts would open a visible console window)."""
    if server_up():
        return True
    flags = NO_WINDOW | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    subprocess.Popen([sys.executable, os.path.abspath(__file__), "serve", port, "--take"], creationflags=flags,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
    for _ in range(40):
        if server_up():
            return True
        time.sleep(0.25)
    return False


def stop_server():
    if not server_up():
        return
    try:
        request({"kind": "stop"}, timeout=5)
    except OSError:
        pass
    for _ in range(20):   # it closes the port within a poll or two
        if not server_up():
            break
        time.sleep(0.25)
    time.sleep(0.5)


def flash(build=False):
    port = find_port()
    stop_server()
    take_port(port)
    if build:
        env = {k: v for k, v in os.environ.items() if k not in ("MSYSTEM", "MSYSTEM_PREFIX", "MINGW_PREFIX")}   # idf.py won't build from Git Bash
        r = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command",
                            f". '{IDF_PROFILE}' *> $null; Set-Location '{PROJECT}'; idf.py build; exit $LASTEXITCODE"], env=env, creationflags=NO_WINDOW, **own_output())
        if r.returncode:
            print("devlink: build failed"); return 2
    r = subprocess.run([IDF_PY, "-m", "esptool", "--chip", "esp32s3", "-p", port, "-b", "460800", "--before", "default-reset",
                        "--after", "hard-reset", "write-flash", "@flash_args"], cwd=os.path.join(PROJECT, "build"),
                       creationflags=NO_WINDOW, **own_output())
    if r.returncode:
        print("devlink: flash failed"); return 2
    if not start_server(port):
        print("devlink: flashed, but the server didn't start"); return 2
    ok = wait_board(30)
    print("devlink: flashed; board answering" if ok else "devlink: flashed; board not answering (audio on? Settings -> audio off)")
    return 0 if ok else 2


def reset():
    """Restarts the board (back to the title screen) and the link with it."""
    port = find_port()
    stop_server()
    take_port(port)
    r = subprocess.run([IDF_PY, "-m", "esptool", "--chip", "esp32s3", "-p", port, "run"], capture_output=True, text=True, creationflags=NO_WINDOW)
    if r.returncode:
        print(r.stdout[-400:], r.stderr[-400:]); return 2
    if not start_server(port):
        print("devlink: reset, but the server didn't start"); return 2
    ok = wait_board(30)
    print("devlink: reset; board answering" if ok else "devlink: reset; board not answering")
    return 0 if ok else 2


def main(argv):
    if not argv:
        print(__doc__); return 1
    op = argv[0]
    if op == "reset":
        need("serial")
        return reset()
    if op == "serve":
        need("serial")
        args = [a for a in argv[1:] if not a.startswith("--")]
        serve(args[0] if args else find_port(), take="--take" in argv); return 0
    if op == "start":
        need("serial")
        if not start_server(argv[1] if len(argv) > 1 else find_port()):
            print("devlink: server didn't start (see: devlink.py serve)"); return 2
        ok = wait_board(30)
        print("devlink: board answering" if ok else "devlink: server up, board not answering (audio on?)")
        return 0 if ok else 2
    if op == "wait":
        ok = wait_board(float(argv[1]) if len(argv) > 1 else 30)
        print("board answering" if ok else "no answer"); return 0 if ok else 2
    if op == "flash":
        need("serial")
        return flash(build="--build" in argv)
    if op == "load":
        n = argv[1] if len(argv) > 1 else "1"
        r = cmd("load " + n)
        print("\n".join(r["lines"]))
        if not any(a.startswith("@@OK") for a in r["lines"]):
            return 2
        t_end = time.time() + 40
        while time.time() < t_end:
            st = [a for a in cmd("state", timeout=5)["lines"] if a.startswith("@@STATE")]
            if st and " loaded=1 " in st[0]:
                print(st[0]); return 0
            time.sleep(1)
        print("devlink: save didn't finish loading"); return 2
    if op == "stop":
        was = server_up()
        stop_server()
        print("devlink: stopped" if was else "devlink: wasn't running"); return 0
    if op == "cmd":
        r = cmd(" ".join(remote(a) for a in argv[1:]), timeout=float(os.environ.get("DEVLINK_TIMEOUT", "20")))
        print("\n".join(r["lines"]) or "(no answer)")
        return 0 if r["ok"] else 2
    if op == "shot":
        need("PIL")
        n = shot(argv[1] if len(argv) > 1 else "shot.png")
        print(f"rows {n}/480")
        return 0 if n == 480 else 2
    if op == "tap":
        r = cmd("tap " + " ".join(argv[1:])); print("\n".join(r["lines"])); return 0
    if op == "put":
        with open(argv[1], "rb") as f:
            data = f.read()
        t = time.time()
        r = request({"kind": "put", "remote": remote(argv[2]), "data": base64.b64encode(data).decode()}, timeout=600)
        print("\n".join(r["lines"][-2:]), f"({len(data)} bytes, {time.time() - t:.1f}s)")
        return 0 if r["ok"] else 2
    if op == "get":
        r = cmd("get " + remote(argv[1]), timeout=120)
        out = b"".join(base64.b64decode(a[4:]) for a in r["lines"] if a.startswith("@@D "))
        with open(argv[2], "wb") as f:
            f.write(out)
        print(r["lines"][-1] if r["lines"] else "(no answer)", len(out), "bytes")
        return 0 if r["ok"] else 2
    if op == "log":
        r = request({"kind": "log", "n": int(argv[1]) if len(argv) > 1 else 60})
        print("\n".join(r["lines"])); return 0
    print(__doc__); return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
