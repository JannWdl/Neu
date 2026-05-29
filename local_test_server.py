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
    "wifi": {"ssid": "Test-WLAN", "password": ""},
    "system": {"setup_done": False, "active_channels": 2, "timezone_offset": 1},
    "plants": [
        {"id": 0, "name": "Tomate"},
        {"id": 1, "name": "Basilikum"},
        {"id": 2, "name": "Paprika"},
        {"id": 3, "name": "Minze"},
    ],
    "channels": [
        {"id": 0, "name": "Kanal 1", "enabled": True, "moisture": 42, "thresh": 40, "pump": False, "auto_mode": True, "raw_adc": 2100},
        {"id": 1, "name": "Kanal 2", "enabled": True, "moisture": 55, "thresh": 40, "pump": False, "auto_mode": True, "raw_adc": 1900},
        {"id": 2, "name": "Kanal 3", "enabled": False, "moisture": 0, "thresh": 40, "pump": False, "auto_mode": False, "raw_adc": 0},
        {"id": 3, "name": "Kanal 4", "enabled": False, "moisture": 0, "thresh": 40, "pump": False, "auto_mode": False, "raw_adc": 0},
    ],
    "telegram": {"enabled": False, "token": "", "chat_id": ""},
    "mqtt": {"enabled": False, "server": "", "port": 1883, "user": "", "password": "", "base_topic": "irrigation"},
    "weather": {"enabled": False, "api_key": "", "city": "Berlin", "country": "DE", "skip_on_rain": True, "frost_protect": True, "frost_threshold": 4},
    "sensor_dht": {"enabled": False, "pin": 4, "type": 22},
    "schedule": {"enabled": False, "entries": []},
}


def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            merged = json.loads(json.dumps(DEFAULT_CONFIG))
            for k, v in data.items():
                if isinstance(v, dict) and isinstance(merged.get(k), dict):
                    merged[k].update(v)
                else:
                    merged[k] = v
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
            wt_cfg = state.get("weather", {})
            weather_enabled = bool(wt_cfg.get("enabled") and wt_cfg.get("api_key"))
            weather = state.get("_weather_data", {}) if weather_enabled else {}
            return self.send_json({
                "ok": True,
                "mode": "local-test",
                "uptime": int(time.time()),
                "ip": "127.0.0.1",
                "rssi": -42,
                "heap": 184320,
                "wifi": {"connected": True, "ssid": "Local Mock"},
                "water_level": 75,
                "active_pump": -1,
                "queue": [],
                "weather": weather,
                "weather_enabled": weather_enabled,
                "weather_status": {"configured": weather_enabled, "ok": bool(weather), "err": "Mock: noch nicht abgerufen" if weather_enabled and not weather else ""},
                "dht": {"temp": 22.3, "humidity": 48} if state.get("sensor_dht", {}).get("enabled") else {},
                "frost_active": bool(weather.get("frost")),
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


        if path in ("/api/weather", "/api/weather/update"):
            wt_cfg = state.get("weather", {})
            if not wt_cfg.get("enabled") or not wt_cfg.get("api_key"):
                return self.send_json({"ok": False, "err": "Wetter ist im Mock nicht aktiviert oder API-Key fehlt."}, 400)
            data = {
                "city": wt_cfg.get("city", "Berlin"),
                "country": wt_cfg.get("country", "DE"),
                "temp": 21.6,
                "feels_like": 21.0,
                "humidity": 54,
                "pressure": 1014,
                "wind": 2.1,
                "rain_1h": 0,
                "rain_forecast": False,
                "description": "leicht bewölkt",
                "frost": False,
                "forecast": [
                    {"temp": 22, "description": "bewölkt"},
                    {"temp": 20, "description": "klar"},
                ],
                "updated": int(time.time()),
            }
            state["_weather_data"] = data
            save_state(state)
            return self.send_json({"ok": True, "weather": data, "status": {"configured": True, "ok": True, "err": ""}})

        if path == "/api/telegram/test":
            tg = state.get("telegram", {})
            if not tg.get("enabled") or not tg.get("token") or not tg.get("chat_id"):
                return self.send_json({"ok": False, "err": "Mock: Telegram aktivieren und Token/Chat-ID eintragen."}, 400)
            return self.send_json({"ok": True, "msg": "Mock-Testnachricht gesendet."})

        if path == "/api/mqtt/test":
            mq = state.get("mqtt", {})
            if not mq.get("enabled") or not mq.get("server"):
                return self.send_json({"ok": False, "err": "Mock: MQTT aktivieren und Server eintragen."}, 400)
            return self.send_json({"ok": True, "msg": "Mock: MQTT-Verbindung erfolgreich.", "topic": (mq.get("base_topic") or "irrigation") + "/test"})

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
                for k, v in data.items():
                    if isinstance(v, dict) and isinstance(state.get(k), dict):
                        state[k].update(v)
                    else:
                        state[k] = v
                if data.get("system", {}).get("setup_done"):
                    state.setdefault("system", {})["setup_done"] = True
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
