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


# Index-HTML wird von /index.html auf dem Flash gestreamt


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
            result = await self._route(method, path, query, reader)

            # Datei-Streaming (kein RAM-Buffer): ("FILE", pfad, ctype)
            if isinstance(result, tuple) and len(result) == 3 and result[0] == "FILE":
                _, fpath, ctype = result
                await self._stream_file(writer, fpath, ctype)
                return

            status, ctype, data = result
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

        # ── HTML (gestreamt von Flash, kein RAM-Buffer) ──
        if path == "/" or path == "/index.html":
            return ("FILE", "/index.html", "text/html; charset=utf-8")

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

        # ── Pumpen (über Queue – nur EINE gleichzeitig) ──
        if path.startswith("/api/water/"):
            ch = int(path.split("/")[-1])
            # optionale Dauer: /api/water/0?dur=15
            dur = None
            if "dur=" in query:
                try:
                    dur = int(dict(p.split("=") for p in query.split("&") if "=" in p).get("dur"))
                except Exception:
                    dur = None
            started = self.irrigation.request_pump(ch, dur)
            return json_resp({"ok": True, "started": started,
                              "queued": not started})

        if path.startswith("/api/stop/"):
            ch = int(path.split("/")[-1])
            self.irrigation.stop_pump(ch)
            return json_resp({"ok": True})

        if path == "/api/stopall":
            for c in self.irrigation.channels:
                self.irrigation.stop_pump(c.id)
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

        # ── Zeitpläne ────────────────────────────────
        if path == "/api/schedule" and method == "GET":
            return json_resp(self.cfg.as_dict().get("schedule", {"enabled": False, "entries": []}))

        if path == "/api/schedule" and method == "POST":
            try:
                body = await self._read_small_body(reader)
                self.cfg.set("schedule", json.loads(body))
                return json_resp({"ok": True})
            except Exception as e:
                return json_resp({"ok": False, "err": str(e)}, "400 Bad Request")

        # ── Dünger markieren ─────────────────────────
        if path.startswith("/api/fertilized/"):
            ch = int(path.split("/")[-1])
            self.irrigation.mark_fertilized(ch)
            return json_resp({"ok": True})

        # ── Live-ADC (für Kalibrierung im Assistenten) ──
        if path.startswith("/api/raw/"):
            ch = int(path.split("/")[-1])
            if 0 <= ch < len(self.irrigation.channels):
                c2 = self.irrigation.channels[ch]
                raw = c2.read_adc()
                return json_resp({"raw": raw, "pct": c2.adc_to_pct(raw)})
            return json_resp({"raw": 0, "pct": 0})

        # ── Statistik ────────────────────────────────
        if path == "/api/stats":
            stats = []
            for c2 in self.irrigation.channels:
                secs = c2.cfg.get("total_seconds", 0)
                flow = c2.cfg.get("flow_ml_min", 0)
                stats.append({
                    "name": c2.cfg.get("name"),
                    "waterings": c2.cfg.get("total_waterings", 0),
                    "seconds": secs,
                    "liters": round(secs / 60 * flow / 1000, 2) if flow else None
                })
            return json_resp({"stats": stats})

        # ── OTA STREAM UPLOAD ────────────────────────
        if path == "/api/ota/upload" and method == "POST":
            return await self._ota_stream(reader)

        return "404 Not Found", "application/json", json.dumps({"error": "not found"})

    # ─────────────────────────────────────────────
    async def _stream_file(self, writer, path, ctype):
        """Datei in 512-Byte-Chunks senden – nie mehr als 1 Chunk im RAM."""
        try:
            size = os.stat(path)[6]
        except OSError:
            body = b"Not found: " + path.encode()
            writer.write(("HTTP/1.1 404 Not Found\r\nContent-Length: %d\r\n"
                          "Connection: close\r\n\r\n" % len(body)).encode())
            writer.write(body)
            await writer.drain()
            return
        # Header mit bekannter Größe
        writer.write((
            "HTTP/1.1 200 OK\r\n"
            "Content-Type: %s\r\n"
            "Content-Length: %d\r\n"
            "Connection: close\r\n\r\n" % (ctype, size)
        ).encode())
        await writer.drain()
        # Datei häppchenweise senden
        gc.collect()
        with open(path, "rb") as f:
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        gc.collect()

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
