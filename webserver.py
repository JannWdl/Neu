"""
webserver.py – STABLE MicroPython HTTP Server (ESP32 optimized)
- kein RAM Buffering für große Requests
- OTA streaming (kein Memory Overflow)
- reduzierte Fragmentierung
- stabil für 24/7 Betrieb
"""

import uasyncio as asyncio
import json
import gc
import time
import os
import machine

from config import get_config
from plants_db import all_as_list


# ─────────────────────────────────────────────────────────────
# Minimal HTML (nicht dynamisch bauen!)
# ─────────────────────────────────────────────────────────────
_HTML = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Irrigation</title></head>
<body style="font-family:system-ui;background:#0a0f1e;color:#fff">
<h2>Smart Irrigation</h2>
<p>System läuft</p>
</body></html>"""


# ─────────────────────────────────────────────────────────────
# WebServer
# ─────────────────────────────────────────────────────────────
class WebServer:

    def __init__(self, irrigation, telegram=None, ota=None):
        self.irrigation = irrigation
        self.telegram = telegram
        self.ota = ota
        self.cfg = get_config()

    # ─────────────────────────────────────────────
    async def run(self, port=80):
        print("Webserver startet...")
        server = await asyncio.start_server(self._handle, "0.0.0.0", port)
        async with server:
            await server.wait_closed()

    # ─────────────────────────────────────────────
    async def _handle(self, reader, writer):

        try:
            gc.collect()

            # ── 1. Nur Header lesen (KEIN RAW BUFFER!) ──
            header = await reader.read(1024)
            if not header:
                return

            try:
                header_str = header.decode()
            except:
                return

            lines = header_str.split("\r\n")
            req = lines[0].split()

            if len(req) < 2:
                return

            method = req[0]
            full_path = req[1]
            path = full_path.split("?")[0]
            query = full_path.split("?")[1] if "?" in full_path else ""

            # ── 2. Routing ───────────────────────────────
            status, ctype, data = await self._route(method, path, query, reader)

            if isinstance(data, str):
                data = data.encode()

            # ── 3. Response senden ───────────────────────
            header = (
                "HTTP/1.1 {}\r\n"
                "Content-Type: {}\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n\r\n"
            ).format(status, ctype, len(data)).encode()

            writer.write(header)
            writer.write(data)
            await writer.drain()

        except Exception as e:
            print("HTTP ERROR:", e)

        finally:
            try:
                writer.close()
            except:
                pass
            gc.collect()

    # ─────────────────────────────────────────────
    async def _route(self, method, path, query, reader):

        def json_resp(obj, status="200 OK"):
            return status, "application/json", json.dumps(obj)

        # ── HTML ─────────────────────────────────────
        if path == "/" or path == "/index.html":
            return "200 OK", "text/html", _HTML

        # ── Status ───────────────────────────────────
        if path == "/api/status":
            return json_resp(self.irrigation.status_dict())

        # ── Config GET ───────────────────────────────
        if path == "/api/config" and method == "GET":
            d = dict(self.cfg.as_dict())
            d["plants"] = all_as_list()
            return json_resp(d)

        # ── Config POST ──────────────────────────────
        if path == "/api/config" and method == "POST":
            try:
                body = await self._read_small_body(reader)
                self.cfg.update_from_dict(json.loads(body))
                return json_resp({"ok": True})
            except Exception as e:
                return json_resp({"ok": False, "err": str(e)}, "400 Bad Request")

        # ── Pumpen ───────────────────────────────────
        if path.startswith("/api/water/"):
            ch = int(path.split("/")[-1])
            self.irrigation.channels[ch].start_pump()
            return json_resp({"ok": True})

        if path.startswith("/api/stop/"):
            ch = int(path.split("/")[-1])
            self.irrigation.channels[ch].stop_pump()
            return json_resp({"ok": True})

        # ── Logs (leicht gehalten) ───────────────────
        if path == "/api/logs":
            params = dict(p.split("=") for p in query.split("&") if "=" in p)
            ch = int(params.get("ch", 0))
            limit = int(params.get("limit", 30))
            return json_resp({
                "readings": self.irrigation.get_logs(ch, limit)
            })

        # ── Events ───────────────────────────────────
        if path == "/api/events":
            return json_resp({
                "events": self.irrigation.get_events(30)
            })

        # ── Reboot ───────────────────────────────────
        if path == "/api/reboot":
            async def reboot():
                await asyncio.sleep(1)
                machine.reset()
            asyncio.create_task(reboot())
            return json_resp({"ok": True, "msg": "rebooting"})

        # ── OTA STREAM UPLOAD (WICHTIG FIX) ──────────
        if path == "/api/ota/upload" and method == "POST":
            return await self._ota_stream(reader)

        return "404 Not Found", "application/json", json.dumps({"error": "not found"})

    # ─────────────────────────────────────────────
    async def _read_small_body(self, reader):
        """Nur für JSON (klein halten!)"""
        gc.collect()
        data = await reader.read(512)
        try:
            return data.decode()
        except:
            return ""

    # ─────────────────────────────────────────────
    async def _ota_stream(self, reader):
        """
        KRITISCH: KEIN RAM BUFFER!
        Direkt in Datei schreiben.
        """
        try:
            gc.collect()

            header = await reader.read(512)
            if b"filename=" not in header:
                return "400 Bad Request", "application/json", json.dumps({"ok": False})
            # Dateiname aus multipart header extrahieren
            fn_start = header.find(b'filename="') + 10
            fn_end   = header.find(b'"', fn_start)
            filename = header[fn_start:fn_end].decode()

            # Body-Start finden (nach doppeltem CRLF)
            body_start = header.find(b'\r\n\r\n')
            if body_start == -1:
                return "400 Bad Request", "application/json", json.dumps({"ok": False})
            body_start += 4

            # Direkt in Datei streamen (kein RAM-Buffer!)
            dest = f'/{filename}'
            with open(dest, 'wb') as f_out:
                f_out.write(header[body_start:])
                while True:
                    chunk = await reader.read(512)
                    if not chunk:
                        break
                    # Multipart-End-Boundary entfernen
                    if b'--' in chunk:
                        chunk = chunk[:chunk.find(b'--')]
                    if chunk:
                        f_out.write(chunk)
                    gc.collect()

            print(f'OTA: {filename} gespeichert')
            return "200 OK", "application/json", json.dumps({"ok": True, "file": filename})

        except Exception as e:
            print(f'OTA stream error: {e}')
            return "500 Internal Server Error", "application/json", json.dumps({"ok": False, "err": str(e)})
