"""
webserver.py – STABLE MicroPython HTTP Server (KORRIGIERT für Speichern/POST)
"""

import uasyncio as asyncio
import json
import gc
import os
import machine

from config import get_config
from plants_db import all_as_list


class WebServer:

    def __init__(self, irrigation, telegram=None, ota=None):
        self.irrigation = irrigation
        self.telegram = telegram
        self.ota = ota
        self.cfg = get_config()

    async def run(self, port=80):
        print("Webserver startet...")
        server = await asyncio.start_server(self._handle, "0.0.0.0", port)
        async with server:
            await server.wait_closed()

    def _json_response(self, obj, status="200 OK"):
        """Hilfsfunktion für standardisierte JSON-Antworten"""
        return status, "application/json", json.dumps(obj)

    async def _handle(self, reader, writer):
        try:
            gc.collect()
            header = b""

            # Header einlesen bis zur Leerzeile
            while b"\r\n\r\n" not in header:
                chunk = await reader.read(128)
                if not chunk:
                    return
                header += chunk
                if len(header) > 4096:
                    return

            split_idx = header.find(b"\r\n\r\n")
            raw_header = header[:split_idx]
            body_start = header[split_idx + 4:]

            try:
                header_str = raw_header.decode()
            except:
                return

            lines = header_str.split("\r\n")
            if not lines:
                return

            req = lines[0].split()
            if len(req) < 2:
                return

            method = req[0]
            full_path = req[1]
            path = full_path.split("?")[0]
            query = full_path.split("?")[1] if "?" in full_path else ""

            # Header auswerten (Content-Length & Custom OTA Header)
            content_length = 0
            filename = None
            for line in lines:
                low_line = line.lower()
                if low_line.startswith("content-length:"):
                    try:
                        content_length = int(line.split(":")[1].strip())
                    except:
                        content_length = 0
                elif low_line.startswith("x-filename:"):
                    filename = line.split(":")[1].strip()

            # Routing ausführen
            result = await self._route(
                method, path, query, reader, content_length, body_start, filename
            )

            if isinstance(result, tuple) and len(result) == 3 and result[0] == "FILE":
                _, fpath, ctype = result
                await self._stream_file(writer, fpath, ctype)
                return

            status, ctype, data = result
            if isinstance(data, str):
                data = data.encode()

            # HTTP Antwort senden
            response_header = (
                "HTTP/1.1 {}\r\n"
                "Content-Type: {}\r\n"
                "Content-Length: {}\r\n"
                "Connection: close\r\n\r\n"
            ).format(status, ctype, len(data)).encode()

            writer.write(response_header)
            await writer.drain()
            writer.write(data)
            await writer.drain()

        except Exception as e:
            print("HTTP ERROR:", e)
        finally:
            try:
                writer.close()
                await writer.wait_closed()
            except:
                pass
            gc.collect()

    async def _route(self, method, path, query, reader, content_length=0, body_start=b"", filename=None):
        if path == "/" or path == "/index.html":
            return "FILE", "/index.html", "text/html; charset=utf-8"

        if path == "/api/status":
            return self._json_response(self.irrigation.status_dict())

        if path == "/api/config" and method == "GET":
            d = dict(self.cfg.as_dict())
            d["plants"] = all_as_list()
            return self._json_response(d)

        # FIX: Hier fror der Server beim Speichern der Config ein
        if path == "/api/config" and method == "POST":
            try:
                body = await self._read_small_body(reader, content_length, body_start)
                if not body:
                    return self._json_response({"ok": False, "err": "Leerer Body"}, "400 Bad Request")
                
                parsed_data = json.loads(body)
                self.cfg.update_from_dict(parsed_data)
                return self._json_response({"ok": True})
            except Exception as e:
                print("Config-Save Fehler:", e)
                return self._json_response({"ok": False, "err": str(e)}, "400 Bad Request")

        if path.startswith("/api/water/"):
            ch = int(path.split("/")[-1])
            dur = None
            if "dur=" in query:
                try:
                    dur = int(dict(p.split("=") for p in query.split("&") if "=" in p).get("dur"))
                except:
                    dur = None
            started = self.irrigation.request_pump(ch, dur)
            return self._json_response({"ok": True, "started": started, "queued": not started})

        if path.startswith("/api/stop/"):
            ch = int(path.split("/")[-1])
            self.irrigation.stop_pump(ch)
            return self._json_response({"ok": True})

        if path == "/api/stopall":
            for c in self.irrigation.channels:
                self.irrigation.stop_pump(c.id)
            return self._json_response({"ok": True})

        if path == "/api/logs":
            params = dict(p.split("=") for p in query.split("&") if "=" in p)
            ch = int(params.get("ch", 0))
            limit = int(params.get("limit", 30))
            return self._json_response({"readings": self.irrigation.get_logs(ch, limit)})

        if path == "/api/events":
            return self._json_response({"events": self.irrigation.get_events(30)})

        if path == "/api/reboot":
            async def reboot():
                await asyncio.sleep(1)
                machine.reset()
            asyncio.create_task(reboot())
            return self._json_response({"ok": True, "msg": "rebooting"})

        if path == "/api/schedule" and method == "GET":
            return self._json_response(self.cfg.as_dict().get("schedule", {"enabled": False, "entries": []}))

        # FIX: Hier fror der Server beim Speichern des Zeitplans ein
        if path == "/api/schedule" and method == "POST":
            try:
                body = await self._read_small_body(reader, content_length, body_start)
                if not body:
                    return self._json_response({"ok": False, "err": "Leerer Body"}, "400 Bad Request")
                
                parsed_sched = json.loads(body)
                self.cfg.set("schedule", parsed_sched)
                return self._json_response({"ok": True})
            except Exception as e:
                print("Schedule-Save Fehler:", e)
                return self._json_response({"ok": False, "err": str(e)}, "400 Bad Request")

        if path.startswith("/api/fertilized/"):
            ch = int(path.split("/")[-1])
            self.irrigation.mark_fertilized(ch)
            return self._json_response({"ok": True})

        if path.startswith("/api/raw/"):
            ch = int(path.split("/")[-1])
            if 0 <= ch < len(self.irrigation.channels):
                c2 = self.irrigation.channels[ch]
                raw = c2.read_adc()
                return self._json_response({"raw": raw, "pct": c2.adc_to_pct(raw)})
            return self._json_response({"raw": 0, "pct": 0})

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
            return self._json_response({"stats": stats})

        if path == "/api/ota/upload" and method == "POST":
            if not filename:
                return self._json_response({"ok": False, "err": "Missing X-Filename header"}, "400 Bad Request")
            return await self._ota_stream(reader, content_length, body_start, filename)

        return "404 Not Found", "application/json", json.dumps({"error": "not found"})

    async def _stream_file(self, writer, path, ctype):
        try:
            size = os.stat(path)[6]
        except OSError:
            body = b"Not found"
            writer.write(("HTTP/1.1 404 Not Found\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % len(body)).encode())
            writer.write(body)
            await writer.drain()
            return

        writer.write(("HTTP/1.1 200 OK\r\nContent-Type: %s\r\nContent-Length: %d\r\nConnection: close\r\n\r\n" % (ctype, size)).encode())
        await writer.drain()
        gc.collect()

        with open(path, "rb") as f:
            while True:
                chunk = f.read(512)
                if not chunk:
                    break
                writer.write(chunk)
                await writer.drain()
        gc.collect()

    async def _read_small_body(self, reader, content_length, body_start=b""):
        """Liest den JSON-Body absolut präzise ein ohne hängenzubleiben"""
        gc.collect()
        body = bytearray(body_start)
        
        # Wenn wir schon genug (oder mehr) Daten im body_start haben,
        # schneiden wir exakt bei content_length ab und blockieren den Reader nicht.
        if len(body) >= content_length:
            return bytes(body[:content_length]).decode('utf-8', 'ignore')

        remaining = content_length - len(body)
        while remaining > 0:
            chunk = await reader.read(min(remaining, 128))
            if not chunk:
                break
            body.extend(chunk)
            remaining -= len(chunk)

        try:
            return bytes(body).decode('utf-8', 'ignore')
        except Exception as e:
            print("BODY DECODE ERROR:", e)
            return ""

    async def _ota_stream(self, reader, content_length, body_start, filename):
        try:
            gc.collect()
            dest = f"/{filename}"
            
            written = 0
            with open(dest, "wb") as f_out:
                if body_start:
                    f_out.write(body_start)
                    written += len(body_start)

                remaining = content_length - written
                while remaining > 0:
                    chunk = await reader.read(min(remaining, 512))
                    if not chunk:
                        break
                    f_out.write(chunk)
                    remaining -= len(chunk)
                    gc.collect()

            print("OTA gespeichert:", filename)
            return self._json_response({"ok": True, "file": filename})

        except Exception as e:
            print("OTA ERROR:", e)
            return "500 Internal Server Error", "application/json", json.dumps({"ok": False, "err": str(e)})