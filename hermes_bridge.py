#!/usr/bin/env python3
"""Hermes Pixel Office - jembatan v1.0 (hanya pustaka standar Python).

Menyajikan index.html, /feed (data agent), /chat (kirim instruksi) pada satu alamat.

Sumber data /feed (hook plugin Hermes ditumpuk di atas sumber lain agar status waktu nyata):
  1. HERMES_API_URL  : API server Hermes (GET /api/sessions), mis. http://127.0.0.1:8642
  2. HERMES_DB       : database sesi Hermes (SQLite, dibuka read-only). Bawaan ~/.hermes/state.db
  3. AGENT_OFFICE_URL: server agent-office (GET /state), mis. http://127.0.0.1:8113
  4. events.jsonl    : ditulis plugin Hermes (python3 install.py), bawaan ~/.hermes/hermes-pixel-office/

Chat: diteruskan ke HERMES_API_URL/v1/chat/completions (atau CHAT_URL bila diisi).

Keamanan (penting bila dibuka lewat domain publik / Cloudflare):
  Password: set BRIDGE_PASSWORD_HASH (disarankan) atau BRIDGE_PASSWORD. Buat hash dengan
            python3 hermes_bridge.py --set-password
  Pengunjung login sekali; sesi tetap aktif selama dipakai dan habis setelah
  BRIDGE_SESSION_MINUTES (bawaan 120) tanpa aktivitas, lalu harus memasukkan password lagi.
  Tanpa password, chat dimatikan kecuali BRIDGE_OPEN_CHAT=1 (tidak disarankan).
"""
import hashlib, hmac, html, json, os, secrets, sqlite3, threading, time, urllib.error, urllib.parse, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

VERSION = "1.1.0"
HERE = Path(__file__).resolve().parent


def hermes_home():
    return Path(os.environ.get("HERMES_HOME") or "~/.hermes").expanduser()


def _load_config():
    """Baca ~/.hermes/hermes-pixel-office/config.env (KEY=VALUE) tanpa menimpa env yang sudah ada."""
    f = hermes_home() / "hermes-pixel-office" / "config.env"
    try:
        for line in f.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except OSError:
        pass


_load_config()
ENV = os.environ.get
HOST = ENV("BRIDGE_HOST", "127.0.0.1")
PORT = int(ENV("BRIDGE_PORT", "8114"))
PASSWORD = ENV("BRIDGE_PASSWORD", "")
PASSWORD_HASH = ENV("BRIDGE_PASSWORD_HASH", "").strip()
SESSION_S = float(ENV("BRIDGE_SESSION_MINUTES", "120")) * 60
AUTH_ON = bool(PASSWORD or PASSWORD_HASH)
OPEN_CHAT = ENV("BRIDGE_OPEN_CHAT", "") == "1"
API = ENV("HERMES_API_URL", "").strip().rstrip("/")
API_KEY = ENV("HERMES_API_KEY", ENV("API_SERVER_KEY", "")).strip()
DB = Path(os.path.expanduser(ENV("HERMES_DB", str(hermes_home() / "state.db"))))
EVENTS = Path(os.path.expanduser(ENV("HERMES_EVENTS", str(hermes_home() / "hermes-pixel-office" / "events.jsonl"))))
AO = ENV("AGENT_OFFICE_URL", "").strip().rstrip("/")
CHAT_URL = ENV("CHAT_URL", "").strip()
RECENT_H = float(ENV("HERMES_RECENT_HOURS", "12"))   # sesi yang ditampilkan: aktif dalam N jam terakhir
ACTIVE_S = float(ENV("HERMES_ACTIVE_SECONDS", "90"))  # dianggap "bekerja" bila ada aktivitas dalam N detik
MAX_AGENTS = int(ENV("HERMES_MAX_AGENTS", "40"))


def source_mode():
    if API:
        return "api"
    if DB.exists():
        return "db"
    if AO:
        return "agent-office"
    if EVENTS.exists():
        return "events"
    return "none"


# ---------------------------------------------------------------- utilitas
def num(*vals):
    for v in vals:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            return v
        try:
            if v not in (None, ""):
                return float(v)
        except (TypeError, ValueError):
            pass
    return None


def ts(v):
    """Ubah waktu (epoch detik/milidetik atau ISO) menjadi epoch detik."""
    if v in (None, ""):
        return None
    n = num(v)
    if n is not None:
        return n / 1000.0 if n > 1e11 else n
    try:
        from datetime import datetime
        return datetime.fromisoformat(str(v).replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def short(s, n=90):
    s = " ".join(str(s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def agent_from_session(s, last_text="", last_tool="", last_ts=None):
    """Petakan satu sesi Hermes menjadi satu 'agent' di kantor pixel."""
    now = time.time()
    started = ts(s.get("started_at") or s.get("created_at"))
    ended = ts(s.get("ended_at"))
    last = last_ts or ts(s.get("last_active") or s.get("updated_at") or s.get("last_message_at")) or started
    if ended:
        state = "idle"
    elif last and now - last <= ACTIVE_S:
        state = "working"
    else:
        state = "idle"
    err = s.get("end_reason") or s.get("status")
    if isinstance(err, str) and err.lower() in ("error", "failed"):
        state = "error"
    sid = str(s.get("id") or s.get("session_id"))
    source = str(s.get("source") or s.get("platform") or "hermes")
    title = s.get("title") or s.get("name") or ("sesi " + sid[:6])
    tin = num(s.get("input_tokens"), s.get("prompt_tokens"))
    tout = num(s.get("output_tokens"), s.get("completion_tokens"))
    cost = num(s.get("actual_cost_usd"), s.get("estimated_cost_usd"), s.get("cost_usd"), s.get("cost"))
    return {
        "id": sid, "name": short(title, 24), "division": source, "role": str(s.get("model") or "Hermes"),
        "platform": source, "state": state, "tool": last_tool,
        "task": short(last_text) if state != "idle" else "",
        "metrics": {"input_tokens": tin, "output_tokens": tout,
                    "tool_calls": num(s.get("tool_call_count"), s.get("tool_calls")), "cost_usd": cost},
    }


# ---------------------------------------------------------------- sumber: database
def cols(con, table):
    return [r[1] for r in con.execute(f'PRAGMA table_info("{table}")')]


def feed_from_db():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=3)
    con.row_factory = sqlite3.Row
    try:
        sc = cols(con, "sessions")
        mc = cols(con, "messages") if "messages" in [r[0] for r in con.execute("select name from sqlite_master")] else []
        since = time.time() - RECENT_H * 3600
        order = "started_at" if "started_at" in sc else "rowid"
        rows = [dict(r) for r in con.execute(f"select * from sessions order by {order} desc limit 300")]
        mts = next((c for c in ("timestamp", "created_at", "ts") if c in mc), None)
        out = []
        for s in rows:
            sid = s.get("id")
            last_ts = last_text = last_tool = None
            if mc and mts:
                m = con.execute(f"select * from messages where session_id=? order by {mts} desc limit 12", (sid,)).fetchall()
                if m:
                    last_ts = ts(m[0][mts])
                    for r in m:
                        r = dict(r)
                        if not last_tool and r.get("tool_name"):
                            last_tool = r["tool_name"]
                        if not last_text and r.get("role") in ("assistant", "user") and r.get("content"):
                            last_text = r["content"]
                    last_text = last_text or ""
            ref = last_ts or ts(s.get("ended_at")) or ts(s.get("started_at"))
            if ref and ref < since and s.get("ended_at"):
                continue
            if mc and "tool_name" in mc and "tool_call_count" not in s:
                n = con.execute("select count(*) from messages where session_id=? and tool_name is not null", (sid,)).fetchone()[0]
                s["tool_call_count"] = n
            out.append(agent_from_session(s, last_text or "", last_tool or "", last_ts))
        out.sort(key=lambda a: (a["state"] == "idle", a["division"], a["name"]))
        return {"agents": out[:MAX_AGENTS], "source": "db"}
    finally:
        con.close()


# ---------------------------------------------------------------- sumber: API Hermes
def call(url, data=None, headers=None, timeout=10):
    req = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data is not None else "GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read()


def api_headers():
    return {"Authorization": "Bearer " + API_KEY} if API_KEY else {}


def feed_from_api():
    _, body = call(API + "/api/sessions?limit=100", headers=api_headers())
    j = json.loads(body)
    items = j if isinstance(j, list) else (j.get("sessions") or j.get("items") or j.get("data") or [])
    out = [agent_from_session(s) for s in items if isinstance(s, dict)]
    out.sort(key=lambda a: (a["state"] == "idle", a["division"], a["name"]))
    return {"agents": out[:MAX_AGENTS], "source": "api"}


def feed_from_ao():
    _, body = call(AO + "/state")
    return json.loads(body)


# ---------------------------------------------------------------- sumber: hook plugin (waktu nyata)
def read_events():
    """Gabungkan events.jsonl (ditulis plugin Hermes) menjadi status per sesi."""
    if not EVENTS.exists():
        return {}
    with open(EVENTS, "rb") as f:
        f.seek(0, 2)
        f.seek(max(0, f.tell() - 800000))
        raw = f.read().decode("utf-8", "replace")
    ag, now = {}, time.time()

    def get(sid, e):
        return ag.setdefault(sid, {"id": sid, "platform": e.get("platform") or "hermes", "role": "Hermes", "name": None,
                                   "state": "idle", "tool": "", "task": "", "tools": 0, "last": e.get("t") or 0,
                                   "ended": False, "open": 0, "err": False})

    for line in raw.splitlines()[-4000:]:
        try:
            e = json.loads(line)
        except ValueError:
            continue
        ev, t = e.get("event"), e.get("t") or 0
        if ev == "subagent_start":
            sid = str(e.get("child_session_id") or "")
            if not sid:
                continue
            parent = ag.get(str(e.get("parent_session_id") or ""))
            a = get(sid, {"t": t, "platform": parent["platform"] if parent else "hermes"})
            a.update(role=str(e.get("child_role") or "Subagent"), name=short(e.get("child_role") or "Subagent", 24),
                     task=short(e.get("child_goal"), 90), state="working", last=t, ended=False)
            continue
        sid = str(e.get("session_id") or e.get("child_session_id") or "")
        if not sid:
            continue
        a = get(sid, e)
        a["last"] = t
        if e.get("platform"):
            a["platform"] = e["platform"]
        if ev == "session_start":
            a.update(ended=False, state="idle", open=0, err=False)
        elif ev in ("session_end", "subagent_stop"):
            a.update(ended=True, state="idle", open=0, tool="", task="")
        elif ev == "tool_start":
            a.update(state="working", tool=str(e.get("tool_name") or ""), task=short(e.get("preview") or e.get("tool_name"), 90),
                     ended=False, err=False)
            a["open"] += 1
        elif ev == "tool_end":
            a["open"] = max(0, a["open"] - 1)
            a["tools"] += 1
            if e.get("status") not in (None, "ok", "success") or e.get("error_message"):
                a["err"] = True
                a["task"] = short(e.get("error_message") or "tool gagal", 90)
    out = {}
    for sid, a in ag.items():
        idle_for = now - a["last"]
        if a["ended"] or idle_for > RECENT_H * 3600:
            a["state"] = "idle"
        elif a["err"] and idle_for <= ACTIVE_S:
            a["state"] = "error"
        elif a["open"] > 0 and idle_for <= 600:
            a["state"] = "working"
        elif idle_for <= ACTIVE_S:
            a["state"] = "working" if a["state"] == "working" else "idle"
        else:
            a["state"] = "idle"
        if a["state"] == "idle":
            a["tool"] = ""
            a["task"] = "" if a["state"] == "idle" else a["task"]
        out[sid] = a
    return out


def feed_from_events_only(ev):
    out = []
    for sid, a in ev.items():
        if a["ended"] and time.time() - a["last"] > 3600:
            continue
        out.append({"id": sid, "name": a["name"] or f"{a['platform']} {sid[:4]}", "division": a["platform"], "role": a["role"],
                    "platform": a["platform"], "state": a["state"], "tool": a["tool"], "task": a["task"],
                    "metrics": {"tool_calls": a["tools"]}})
    out.sort(key=lambda x: (x["state"] == "idle", x["division"], x["name"]))
    return {"agents": out[:MAX_AGENTS], "source": "events"}


def get_base_feed():
    mode = source_mode()
    if mode == "api":
        try:
            return feed_from_api()
        except Exception:
            if DB.exists():
                return feed_from_db()
            raise
    if mode == "db":
        return feed_from_db()
    if mode == "agent-office":
        return feed_from_ao()
    return None


def get_feed():
    ev = {}
    try:
        ev = read_events()
    except Exception:
        pass
    try:
        base = get_base_feed()
    except Exception:
        if not ev:
            raise
        base = None
    if base is None:
        if not ev:
            raise RuntimeError("Tidak ada sumber data. Pasang plugin Hermes (python3 install.py) atau atur HERMES_DB / HERMES_API_URL.")
        return feed_from_events_only(ev)
    if not ev or not isinstance(base.get("agents"), list):
        return base
    seen = set()
    for a in base["agents"]:
        e = ev.get(str(a.get("id")))
        if not e:
            continue
        seen.add(str(a["id"]))
        a["state"] = e["state"]
        a["tool"] = e["tool"]
        a["task"] = e["task"] or a.get("task", "")
        if e["tools"]:
            a.setdefault("metrics", {})["tool_calls"] = (a.get("metrics") or {}).get("tool_calls") or e["tools"]
    extra = feed_from_events_only({k: v for k, v in ev.items() if k not in seen})["agents"]
    base["agents"] = (base["agents"] + extra)[:MAX_AGENTS]
    base["source"] = str(base.get("source", "")) + "+events"
    return base


# ---------------------------------------------------------------- chat
def do_chat(body):
    j = json.loads(body)
    msg = str(j.get("message") or "").strip()
    if not msg:
        return 400, {"error": "pesan kosong"}
    if CHAT_URL and "chat/completions" not in CHAT_URL:
        _, out = call(CHAT_URL, data=body, headers={"Content-Type": "application/json"}, timeout=180)
        return 200, json.loads(out)
    url = CHAT_URL or (API + "/v1/chat/completions" if API else "")
    if not url:
        return 501, {"error": "Chat belum diatur. Isi HERMES_API_URL (dan HERMES_API_KEY) atau CHAT_URL."}
    hist = [m for m in (j.get("history") or []) if isinstance(m, dict) and m.get("role") in ("user", "assistant")][-12:]
    who = j.get("agent") or "agent"
    payload = {"model": ENV("HERMES_MODEL", "hermes-agent"), "stream": False,
               "messages": hist + [{"role": "user", "content": msg}]}
    h = {"Content-Type": "application/json", **api_headers()}
    if j.get("agent_id") and API and not CHAT_URL:
        h["X-Hermes-Session-Id"] = str(j["agent_id"])
    _, out = call(url, data=json.dumps(payload).encode(), headers=h, timeout=300)
    r = json.loads(out)
    text = ((r.get("choices") or [{}])[0].get("message") or {}).get("content") or r.get("reply") or ""
    return 200, {"reply": text, "agent": who}


# ---------------------------------------------------------------- HTTP
# ---------------------------------------------------------------- password + sesi
def hash_password(pw, iters=200000):
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), iters).hex()
    return f"pbkdf2_sha256${iters}${salt}${dk}"


def check_password(pw):
    if PASSWORD_HASH:
        try:
            _, iters, salt, dk = PASSWORD_HASH.split("$")
            got = hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), int(iters)).hex()
            return hmac.compare_digest(got, dk)
        except ValueError:
            return False
    return bool(PASSWORD) and hmac.compare_digest(pw.encode(), PASSWORD.encode())


_sessions = {}   # token -> waktu aktivitas terakhir
_fails = {}      # ip -> (jumlah gagal, terkunci sampai)
_slock = threading.Lock()


def new_session():
    tok = secrets.token_urlsafe(32)
    with _slock:
        now = time.time()
        for k in [k for k, v in _sessions.items() if now - v > SESSION_S]:
            del _sessions[k]
        _sessions[tok] = now
    return tok


def session_ok(tok):
    if not tok:
        return False
    with _slock:
        last = _sessions.get(tok)
        if last is None:
            return False
        now = time.time()
        if now - last > SESSION_S:
            del _sessions[tok]
            return False
        _sessions[tok] = now   # perpanjang selama masih dipakai
        return True


def end_session(tok):
    with _slock:
        _sessions.pop(tok, None)


LOGIN_HTML = """<!doctype html><html lang="id"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Masuk - Hermes Pixel Office</title><link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Press+Start+2P&display=swap">
<style>*{box-sizing:border-box;border-radius:0}body{margin:0;min-height:100dvh;display:grid;place-items:center;background:#140f1f;color:#f4e9d8;font:18px/1.3 "Lucida Console","DejaVu Sans Mono",monospace;padding:16px}
form{width:min(380px,100%);background:#241a38;border:3px solid #0b0814;box-shadow:inset 0 0 0 2px #5b4a82,6px 6px 0 #0b0814;padding:22px;display:grid;gap:14px}
h1{margin:0;font:400 14px/1.5 "Press Start 2P",monospace;color:#ffcc33;text-shadow:3px 3px 0 #7a3b00}p{margin:0;color:#a99bc7;font-size:15px}
input{width:100%;background:#140f1f;color:#f4e9d8;border:2px solid #5b4a82;padding:10px;font:inherit}
button{font:400 10px/1.5 "Press Start 2P",monospace;background:#ffcc33;color:#1a1329;border:3px solid #0b0814;padding:12px;cursor:pointer;box-shadow:inset 3px 3px 0 #fff3b8,inset -3px -3px 0 #b88a00}
button:active{transform:translate(2px,2px)}input:focus-visible,button:focus-visible{outline:3px solid #ffcc33;outline-offset:1px}.e{color:#ff7a74;font-size:15px}</style></head>
<body><form method="post" action="/login"><h1>Hermes Pixel Office</h1><p>Masukkan password untuk membuka sesi.</p>__ERR__
<input type="password" name="password" autocomplete="current-password" placeholder="Password" autofocus required><button type="submit">Masuk</button></form></body></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "HermesPixelOffice/" + VERSION

    def log_message(self, *a):
        pass

    def send(self, code, body, ctype="application/json", extra=None):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra or {}).items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def cookie_tok(self):
        for part in self.headers.get("Cookie", "").split(";"):
            k, _, v = part.strip().partition("=")
            if k == "hps":
                return v
        return ""

    def authed(self):
        return (not AUTH_ON) or session_ok(self.cookie_tok())

    def client_ip(self):
        return (self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
                or self.client_address[0])

    def secure_flag(self):
        return "; Secure" if (self.headers.get("X-Forwarded-Proto", "").lower() == "https"
                              or self.headers.get("CF-Visitor", "").find("https") >= 0) else ""

    def login_page(self, err="", code=200):
        body = LOGIN_HTML.replace("__ERR__", f'<p class="e">{html.escape(err)}</p>' if err else "")
        self.send(code, body.encode(), "text/html; charset=utf-8")

    def do_GET(self):
        u = urllib.parse.urlparse(self.path)
        route = u.path
        if route in ("/health", "/healthz"):
            return self.send(200, {"ok": True, "app": "hermes-pixel-office", "version": VERSION,
                                   "source": source_mode(), "chat": bool(CHAT_URL or API) and (AUTH_ON or OPEN_CHAT), "auth": AUTH_ON})
        if AUTH_ON and route == "/login":
            return self.login_page() if not self.authed() else self.send(302, b"", "text/plain", {"Location": "/"})
        if not self.authed():
            if route in ("/", "/index.html"):
                return self.login_page(code=401)
            return self.send(401, {"error": "sesi habis, login lagi"})
        if route in ("/", "/index.html"):
            return self.send(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        if route == "/feed":
            try:
                return self.send(200, get_feed())
            except Exception as exc:
                return self.send(502, {"error": "tidak bisa membaca data Hermes", "detail": f"{type(exc).__name__}: {exc}"[:200]})
        self.send(404, b"not found", "text/plain")

    def do_POST(self):
        route = urllib.parse.urlparse(self.path).path
        if AUTH_ON and route == "/login":
            ip = self.client_ip()
            with _slock:
                n, until = _fails.get(ip, (0, 0))
            if time.time() < until:
                return self.login_page(f"Terlalu banyak percobaan. Coba lagi dalam {int(until - time.time()) + 1} detik.", 429)
            try:
                size = min(int(self.headers.get("Content-Length") or 0), 4096)
                pw = urllib.parse.parse_qs(self.rfile.read(size).decode("utf-8", "replace")).get("password", [""])[0]
            except ValueError:
                pw = ""
            if check_password(pw):
                with _slock:
                    _fails.pop(ip, None)
                cookie = f"hps={new_session()}; Path=/; HttpOnly; SameSite=Strict{self.secure_flag()}"
                return self.send(303, b"", "text/plain", {"Location": "/", "Set-Cookie": cookie})
            with _slock:
                n += 1
                _fails[ip] = (n, time.time() + (min(2 ** (n - 3), 300) if n >= 3 else 0))
            time.sleep(0.6)
            return self.login_page("Password salah.", 401)
        if AUTH_ON and route == "/logout":
            end_session(self.cookie_tok())
            return self.send(200, {"ok": True}, extra={"Set-Cookie": "hps=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"})
        if route != "/chat":
            return self.send(404, b"not found", "text/plain")
        if not AUTH_ON and not OPEN_CHAT:
            return self.send(403, {"error": "Chat dimatikan: atur password (python3 hermes_bridge.py --set-password) agar aman."})
        if not self.authed():
            return self.send(401, {"error": "sesi habis, login lagi"})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if not 0 < n <= 65536:
                raise ValueError
            body = self.rfile.read(n)
        except ValueError:
            return self.send(400, {"error": "body 1-65536 byte"})
        try:
            code, out = do_chat(body)
            self.send(code, out)
        except urllib.error.HTTPError as exc:
            self.send(exc.code, {"error": f"Hermes membalas HTTP {exc.code}", "detail": exc.read()[:200].decode("utf-8", "replace")})
        except Exception as exc:
            self.send(502, {"error": "tidak bisa menghubungi Hermes", "detail": f"{type(exc).__name__}: {exc}"[:200]})


def make_server():
    return ThreadingHTTPServer((HOST, PORT), Handler)


def cli_set_password(write=True):
    import getpass
    pw = getpass.getpass("Password baru: ")
    if len(pw) < 6 or pw != getpass.getpass("Ulangi password: "):
        raise SystemExit("Password minimal 6 karakter dan harus sama.")
    line = "BRIDGE_PASSWORD_HASH=" + hash_password(pw)
    if not write:
        print(line)
        return
    f = hermes_home() / "hermes-pixel-office" / "config.env"
    f.parent.mkdir(parents=True, exist_ok=True)
    keep = [l for l in (f.read_text(encoding="utf-8").splitlines() if f.exists() else [])
            if not l.startswith(("BRIDGE_PASSWORD", "#BRIDGE_PASSWORD"))]
    f.write_text("\n".join(keep + [line]) + "\n", encoding="utf-8")
    os.chmod(f, 0o600)
    print("Password disimpan di", f, "- mulai ulang Hermes (atau layanan) agar berlaku.")


if __name__ == "__main__":
    import sys
    if "--set-password" in sys.argv:
        raise SystemExit(cli_set_password())
    if "--hash" in sys.argv:
        raise SystemExit(cli_set_password(write=False))
    print(f"Hermes Pixel Office {VERSION}  http://{HOST}:{PORT}/")
    print(f"  sumber data : {source_mode()}" + (f" ({API})" if API else f" ({DB})" if source_mode() == "db" else ""))
    print(f"  password    : {'aktif' if AUTH_ON else 'TIDAK ADA (chat dimatikan)'}")
    make_server().serve_forever()
