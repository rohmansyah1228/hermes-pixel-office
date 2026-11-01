#!/usr/bin/env python3
"""Jembatan Hermes -> Hermes Pixel Office (hanya pustaka standar).

Menyajikan index.html dan /feed pada origin yang sama, lalu meneruskan data dari
server agent-office (/state) ke halaman, sehingga browser tidak terkena
pemblokiran lintas-situs.

Pakai:  python3 hermes_bridge.py   lalu buka http://127.0.0.1:8114/?feed=/feed
Opsional: AGENT_OFFICE_URL (default http://127.0.0.1:8113), BRIDGE_PORT (default 8114),
CHAT_URL (alamat endpoint chat Hermes Anda; dipakai untuk meneruskan POST /chat)
"""
import json, os, urllib.error, urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
SRC = os.environ.get("AGENT_OFFICE_URL", "http://127.0.0.1:8113").rstrip("/")
PORT = int(os.environ.get("BRIDGE_PORT", "8114"))
CHAT_URL = os.environ.get("CHAT_URL", "").strip()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def reply(self, code, body, ctype):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        route = self.path.split("?")[0]
        if route in ("/", "/index.html"):
            self.reply(200, (HERE / "index.html").read_bytes(), "text/html; charset=utf-8")
        elif route == "/feed":
            try:
                with urllib.request.urlopen(SRC + "/state", timeout=5) as r:
                    data = r.read()
                json.loads(data)
                self.reply(200, data, "application/json")
            except Exception as exc:
                msg = json.dumps({"error": "tidak bisa membaca " + SRC + "/state", "detail": type(exc).__name__}).encode()
                self.reply(502, msg, "application/json")
        else:
            self.reply(404, b"not found", "text/plain")

    def do_POST(self):
        if self.path.split("?")[0] != "/chat":
            return self.reply(404, b"not found", "text/plain")
        if not CHAT_URL:
            msg = json.dumps({"error": "CHAT_URL belum diatur. Jalankan: CHAT_URL=<alamat endpoint chat> python3 hermes_bridge.py"}).encode()
            return self.reply(501, msg, "application/json")
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if not 0 < n <= 65536:
                raise ValueError
            body = self.rfile.read(n)
        except ValueError:
            return self.reply(400, b'{"error":"body 1-65536 byte"}', "application/json")
        try:
            req = urllib.request.Request(CHAT_URL, data=body, headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=120) as r:
                self.reply(r.status, r.read(), "application/json")
        except urllib.error.HTTPError as exc:
            self.reply(exc.code, exc.read() or b"{}", "application/json")
        except Exception as exc:
            msg = json.dumps({"error": "tidak bisa menghubungi CHAT_URL", "detail": type(exc).__name__}).encode()
            self.reply(502, msg, "application/json")


if __name__ == "__main__":
    print(f"Hermes Pixel Office: http://127.0.0.1:{PORT}/?feed=/feed  (sumber: {SRC}/state)")
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
