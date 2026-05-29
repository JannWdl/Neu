#!/usr/bin/env python3
"""
Lokaler Mock-Server für Smart Irrigation UI.
Start im gleichen Ordner wie index.html:
    python local_test_server.py
Dann öffnen:
    http://127.0.0.1:8080/
"""

from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import json
import os
import mimetypes
import time

HOST = "127.0.0.1"
PORT = 8080
STATE_FILE = "local-test-config.json"

DEFAULT_CONFIG = {
    "setup_done": False,
    "wizard_done": False,
    "first_start": True,
    "wifi_ssid": "Test-WLAN",
    "wifi_password": "",
    "timezone": "Europe/Berlin",
    "plants": [
        {"id": 0, "name": "Tomate"},
        {"id": 1, "name": "Basilikum"},
        {"id": 2, "name": "Paprika"},
        {"id": 3, "name": "Minze"},
    ],
    "channels": [
        {"id": 0, "name": "Kanal 1", "enabled": True, "moisture": 42},
        {"id": 1, "name": "Kanal 2", "enabled": True, "moisture": 55},
        {"id": 2, "name": "Kanal 3", "enabled": False, "moisture": 0},
        {"id": 3, "name": "Kanal 4", "enabled": False, "moisture": 0},
    ],
    "schedule": {"enabled": False, "entries": []},
}


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = dict(DEFAULT_CONFIG)
            merged.update(data)
            return merged
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)


def save_state(data):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


class Handler(BaseHTTPRequestHandler):
    server_version = "SmartIrrigationLocalMock/1.0"

    def log_message(self, fmt, *args):
        print("[%s] %s" % (time.strftime("%H:%M:%S"), fmt % args))

    def send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw = self.rfile.read(length) if length else b"{}"
        print("POST body:", raw.decode("utf-8", "replace"))
        return json.loads(raw.decode("utf-8") or "{}")

    def do_OPTIONS(self):
        self.send_json({"ok": True})

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        qs = parse_qs(parsed.query)
        state = load_state()

        if path in ("/", "/index.html", "/dashboard", "/dashboard.html", "/setup", "/setup.html"):
            return self.serve_file("index.html")

        if path == "/api/config":
            return self.send_json(state)

        if path == "/api/status":
            return self.send_json({
                "ok": True,
                "mode": "local-test",
                "uptime": int(time.time()),
                "wifi": {"connected": True, "ssid": "Local Mock"},
                "channels": state.get("channels", []),
            })

        if path == "/api/events":
            return self.send_json({"events": [
                {"time": "local", "msg": "Mock-Server gestartet"},
                {"time": "local", "msg": "Keine echte Hardware verbunden"},
            ]})

        if path == "/api/schedule":
            return self.send_json(state.get("schedule", {"enabled": False, "entries": []}))

        if path == "/api/stats":
            return self.send_json({"stats": [
                {"name": "Kanal 1", "waterings": 3, "seconds": 120, "liters": 0.24},
                {"name": "Kanal 2", "waterings": 1, "seconds": 45, "liters": 0.09},
            ]})

        if path.startswith("/api/raw/"):
            ch = int(path.rsplit("/", 1)[-1] or 0)
            raw = 1800 + ch * 150
            return self.send_json({"raw": raw, "pct": max(0, min(100, 100 - ch * 12))})

        if path.startswith("/api/logs"):
            return self.send_json({"readings": [
                {"t": "local", "moisture": 42},
                {"t": "local", "moisture": 44},
            ]})

        if path.startswith("/api/water/"):
            return self.send_json({"ok": True, "started": True, "queued": False, "note": "Mock, keine Pumpe aktiv"})

        if path.startswith("/api/stop/") or path == "/api/stopall":
            return self.send_json({"ok": True})

        if path.startswith("/api/fertilized/"):
            return self.send_json({"ok": True})

        if path == "/api/reboot":
            return self.send_json({"ok": True, "msg": "mock reboot"})

        return self.serve_file(path.lstrip("/"))

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        state = load_state()

        if path == "/api/config":
            try:
                data = self.read_json()
                state.update(data)
                # Damit Überspringen lokal sichtbar wird, falls das Frontend nur einzelne Werte setzt.
                if data.get("setup_done") or data.get("wizard_done") or data.get("first_start") is False:
                    state["setup_done"] = True
                    state["wizard_done"] = True
                    state["first_start"] = False
                save_state(state)
                return self.send_json({"ok": True, "saved": state})
            except Exception as e:
                return self.send_json({"ok": False, "err": str(e)}, 400)

        if path == "/api/schedule":
            try:
                data = self.read_json()
                state["schedule"] = data
                save_state(state)
                return self.send_json({"ok": True})
            except Exception as e:
                return self.send_json({"ok": False, "err": str(e)}, 400)

        if path == "/api/ota/upload":
            return self.send_json({"ok": True, "file": "mock-upload"})

        return self.do_GET()

    def serve_file(self, filename):
        filename = filename or "index.html"
        filename = os.path.normpath(filename).replace("\\", "/")
        if filename.startswith("../") or filename == "..":
            return self.send_json({"error": "forbidden"}, 403)
        if not os.path.exists(filename):
            return self.send_json({"error": "not found", "path": filename}, 404)
        ctype = mimetypes.guess_type(filename)[0] or "application/octet-stream"
        with open(filename, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


if __name__ == "__main__":
    if not os.path.exists("index.html"):
        print("Fehler: index.html nicht gefunden. Starte das Script im entpackten Neu-main-Ordner.")
        raise SystemExit(1)
    print(f"Lokaler Testserver läuft: http://{HOST}:{PORT}/")
    print("Abbrechen mit STRG+C. Hardware wird gemockt, weil wir nicht zaubern, sondern nur so tun.")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
