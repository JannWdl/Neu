"""
telegram_bot.py – Telegram Bot (Long-Polling + OTA via Datei-Upload)

FIX: _api() nutzt jetzt uasyncio-kompatibles Socket-Handling mit
     asyncio.sleep(0) nach jedem blocking-Call, damit der Webserver
     und andere Tasks nicht einfrieren wenn ein Token hinterlegt ist.
"""
import uasyncio as asyncio
import gc
from config import get_config


class TelegramBot:
    BASE = 'https://api.telegram.org/bot'

    def __init__(self, irrigation, ota=None):
        self.cfg        = get_config()
        self.irrigation = irrigation
        self.ota        = ota
        self.offset     = 0

    @property
    def _token(self): return self.cfg.get('telegram.token', '')
    @property
    def _chat(self):  return str(self.cfg.get('telegram.chat_id', ''))

    def _api_sync(self, method, data=None):
        """Blocking HTTPS-Call – NUR aus dem Telegram-Task aufrufen."""
        import socket, ssl, json as _json
        host = 'api.telegram.org'
        body = _json.dumps(data).encode() if data else b''
        addr = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(15)
        s.connect(addr)
        s = ssl.wrap_socket(s, server_hostname=host)
        path = f'/bot{self._token}/{method}'
        req = (f'POST {path} HTTP/1.0\r\nHost: {host}\r\n'
               f'Content-Type: application/json\r\nContent-Length: {len(body)}\r\n'
               'Connection: close\r\n\r\n').encode() + body
        s.write(req)
        raw = b''
        while True:
            c = s.read(2048)
            if not c:
                break
            raw += c
        s.close()
        body = raw.split(b'\r\n\r\n', 1)[1] if b'\r\n\r\n' in raw else raw
        return _json.loads(body)

    async def _api(self, method, data=None):
        """Async-Wrapper: gibt dem Event-Loop kurz Luft vor dem blocking Call."""
        await asyncio.sleep(0)
        result = self._api_sync(method, data)
        await asyncio.sleep(0)
        return result

    async def send(self, text, chat_id=None):
        if not self.cfg.get('telegram.enabled') or not self._token:
            return
        try:
            await self._api('sendMessage', {
                'chat_id': chat_id or self._chat,
                'text': text, 'parse_mode': 'Markdown'
            })
        except Exception as e:
            print(f'Telegram send error: {e}')

    async def _get_updates(self):
        try:
            r = await self._api('getUpdates', {'offset': self.offset, 'timeout': 5})
            return r.get('result', [])
        except Exception:
            return []

    async def _handle(self, msg):
        chat = str(msg['chat']['id'])
        if chat != self._chat:
            await self.send('⛔ Nicht autorisiert.', chat)
            return

        text = msg.get('text', '')
        doc  = msg.get('document')

        # OTA: .py-Datei empfangen
        if doc and doc.get('file_name', '').endswith('.py'):
            await self._ota_py(doc, chat)
            return

        cmd = text.split()[0] if text else ''

        if cmd in ('/start', '/info'):
            await self.send(
                '*🌱 Smart Irrigation v3.0*\n'
                '/status – Systemüberblick\n'
                '/feuchte – Sensorwerte\n'
                '/wetter – Aktuelles Wetter\n'
                '/giessen N [T] – Kanal N, T Sekunden\n'
                '/stop N – Pumpe stoppen\n'
                '/stopall – Alle stoppen\n'
                '/auto N – Automode umschalten\n'
                '/stats – Verbrauchsstatistik\n'
                '/duengen N – Kanal N als gedüngt markieren\n'
                '/log – Ereignisse\n'
                '_(Sende .py-Datei für OTA-Update)_'
            )

        elif cmd == '/status':
            s = self.irrigation.status_dict()
            txt = f'*📊 Status*\nIP: {s["ip"]}  RSSI: {s["rssi"]}dBm\n'
            txt += f'Heap: {s["heap"]//1024}kB\n'
            if s.get('frost_active'):
                txt += '❄️ Frostschutz aktiv\n'
            if s.get('dht', {}).get('temp') is not None:
                txt += f'🌡 {s["dht"]["temp"]}°C / {s["dht"]["humidity"]}%\n'
            if s['water_level'] >= 0:
                txt += f'Wasserstand: {s["water_level"]}%\n'
            for ch in s['channels']:
                txt += f'\n*{ch["name"]}* – {ch["moisture"]}%'
                txt += ' 💧' if ch['pump'] else ''
                txt += ' ⚙️' if ch['auto_mode'] else ' ✋'
            await self.send(txt)

        elif cmd == '/feuchte':
            txt = '*💧 Feuchtigkeitswerte*\n'
            for ch in self.irrigation.channels:
                warn = ' ⚠️' if ch.moisture_pct < ch.cfg.get('moisture_thresh', 40) else ''
                txt += f'{ch.cfg.get("name")}: {ch.moisture_pct}%{warn}\n'
            await self.send(txt)

        elif cmd == '/wetter':
            w = self.irrigation.weather
            if not w:
                await self.send('❌ Keine Wetterdaten.')
            else:
                await self.send(
                    f'*🌡️ Wetter – {w.get("city")}*\n'
                    f'Temp: {w.get("temp"):.1f}°C\n'
                    f'Feuchte: {w.get("humidity"):.0f}%\n'
                    f'Regen: {w.get("rain_1h"):.1f}mm/h\n'
                    f'Vorhersage: {"🌧️ Regen" if w.get("rain_forecast") else "☀️ kein Regen"}\n'
                    f'Status: {w.get("description")}'
                )

        elif cmd == '/giessen':
            parts = text.split()
            try:
                ch_id = int(parts[1]) - 1
                dur   = int(parts[2]) if len(parts) > 2 else None
                started = self.irrigation.request_pump(ch_id, dur)
                if started:
                    await self.send(f'✅ Kanal {ch_id+1} gießt.')
                else:
                    await self.send(f'⏳ Kanal {ch_id+1} in Warteschlange (andere Pumpe läuft).')
            except Exception:
                await self.send('❌ Nutzung: /giessen N [Sekunden]')

        elif cmd == '/stop':
            try:
                ch_id = int(text.split()[1]) - 1
                self.irrigation.stop_pump(ch_id)
                await self.send(f'✅ Kanal {ch_id+1} gestoppt.')
            except Exception:
                await self.send('❌ Nutzung: /stop N')

        elif cmd == '/stopall':
            for ch in self.irrigation.channels:
                self.irrigation.stop_pump(ch.id)
            await self.send('✅ Alle Pumpen gestoppt.')

        elif cmd == '/auto':
            try:
                ch_id = int(text.split()[1]) - 1
                ch    = self.irrigation.channels[ch_id]
                new   = not ch.cfg.get('auto_mode', True)
                ch.cfg['auto_mode'] = new
                self.irrigation.cfg.set_channel(ch_id, {'auto_mode': new})
                await self.send(f'✅ Kanal {ch_id+1} Auto: {"AN" if new else "AUS"}')
            except Exception:
                await self.send('❌ Nutzung: /auto N')

        elif cmd == '/stats':
            txt = '*📈 Verbrauchsstatistik*\n'
            for ch in self.irrigation.channels:
                secs = ch.cfg.get('total_seconds', 0)
                cnt  = ch.cfg.get('total_waterings', 0)
                flow = ch.cfg.get('flow_ml_min', 0)
                line = f'\n*{ch.cfg.get("name")}*\n'
                line += f'  {cnt}× gegossen, {secs}s gesamt'
                if flow:
                    liters = secs / 60 * flow / 1000
                    line += f'\n  ≈ {liters:.1f} L'
                txt += line
            await self.send(txt)

        elif cmd == '/duengen':
            try:
                ch_id = int(text.split()[1]) - 1
                self.irrigation.mark_fertilized(ch_id)
                await self.send(f'🌿 Kanal {ch_id+1} als gedüngt markiert.')
            except Exception:
                await self.send('❌ Nutzung: /duengen N')

        elif cmd == '/log':
            evts = self.irrigation.get_events(8)
            txt  = '*📋 Letzte Ereignisse*\n'
            for e in evts:
                txt += f'`{e["ts"]}` {e["msg"]}\n'
            await self.send(txt or 'Keine Ereignisse.')

        else:
            await self.send('❓ Unbekannter Befehl. Schreibe /info')

    async def _ota_py(self, doc, chat):
        """Python-Datei direkt via Telegram aktualisieren."""
        if not self.ota:
            await self.send('OTA nicht verfügbar.', chat)
            return
        try:
            await self.send(f'📥 Empfangen: {doc["file_name"]} – wird übertragen...', chat)
            result = self.ota.update_file_from_telegram(doc['file_id'], doc['file_name'])
            if result:
                await self.send(f'✅ {doc["file_name"]} aktualisiert – Neustart...', chat)
                import time, machine
                time.sleep(2)
                machine.reset()
            else:
                await self.send('❌ Übertragung fehlgeschlagen.', chat)
        except Exception as e:
            await self.send(f'❌ Fehler: {e}', chat)

    async def run(self):
        """
        Long-Polling Loop.
        Läuft als asyncio-Task – gibt nach jedem Poll den Event-Loop frei,
        damit Webserver und andere Tasks nicht blockiert werden.
        """
        while True:
            if self.cfg.get('telegram.enabled') and self._token:
                try:
                    updates = await self._get_updates()
                    for u in updates:
                        self.offset = u['update_id'] + 1
                        if 'message' in u:
                            await self._handle(u['message'])
                        await asyncio.sleep(0)  # Event-Loop zwischen Nachrichten freigeben
                except Exception as e:
                    print(f'Telegram poll error: {e}')
                gc.collect()
            # Pause zwischen Polls – Webserver bleibt in dieser Zeit vollständig responsiv
            await asyncio.sleep(3)
