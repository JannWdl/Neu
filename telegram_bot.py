"""
telegram_bot.py – Telegram Bot (Long-Polling + OTA via Datei-Upload)
"""
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

    def _api(self, method, data=None):
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
            if not c: break
            raw += c
        s.close()
        body = raw.split(b'\r\n\r\n', 1)[1] if b'\r\n\r\n' in raw else raw
        return _json.loads(body)

    def send(self, text, chat_id=None):
        if not self.cfg.get('telegram.enabled') or not self._token:
            return
        try:
            self._api('sendMessage', {
                'chat_id': chat_id or self._chat,
                'text': text, 'parse_mode': 'Markdown'
            })
        except Exception as e:
            print(f'Telegram send error: {e}')

    def _get_updates(self):
        try:
            r = self._api('getUpdates', {'offset': self.offset, 'timeout': 5})
            return r.get('result', [])
        except Exception:
            return []

    def _handle(self, msg):
        chat = str(msg['chat']['id'])
        if chat != self._chat:
            self.send('⛔ Nicht autorisiert.', chat); return

        text     = msg.get('text', '')
        doc      = msg.get('document')

        # OTA: .py-Datei empfangen
        if doc and doc.get('file_name', '').endswith('.py'):
            self._ota_py(doc, chat); return

        cmd = text.split()[0] if text else ''

        if cmd in ('/start', '/info'):
            self.send(
                '*🌱 Smart Irrigation v3.0*\n'
                '/status – Systemüberblick\n'
                '/feuchte – Sensorwerte\n'
                '/wetter – Aktuelles Wetter\n'
                '/giessen N [T] – Kanal N, T Sekunden\n'
                '/stop N – Pumpe stoppen\n'
                '/stopall – Alle stoppen\n'
                '/auto N – Automode umschalten\n'
                '/log – Ereignisse\n'
                '_(Sende .py-Datei für OTA-Update)_'
            )

        elif cmd == '/status':
            s = self.irrigation.status_dict()
            txt = f'*📊 Status*\nIP: {s["ip"]}  RSSI: {s["rssi"]}dBm\n'
            txt += f'Heap: {s["heap"]//1024}kB\n'
            if s['water_level'] >= 0:
                txt += f'Wasserstand: {s["water_level"]}%\n'
            for ch in s['channels']:
                p = ch.get('plant_idx', 0)
                txt += f'\n*{ch["name"]}* – {ch["moisture"]}%'
                txt += ' 💧' if ch['pump'] else ''
                txt += ' ⚙️' if ch['auto_mode'] else ' ✋'
            self.send(txt)

        elif cmd == '/feuchte':
            txt = '*💧 Feuchtigkeitswerte*\n'
            for ch in self.irrigation.channels:
                warn = ' ⚠️' if ch.moisture_pct < ch.cfg.get('moisture_thresh', 40) else ''
                txt += f'{ch.cfg.get("name")}: {ch.moisture_pct}%{warn}\n'
            self.send(txt)

        elif cmd == '/wetter':
            w = self.irrigation.weather
            if not w:
                self.send('❌ Keine Wetterdaten.')
            else:
                self.send(
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
                ch    = self.irrigation.channels[ch_id]
                ch.start_pump(dur)
                self.send(f'✅ Kanal {ch_id+1} gießt.')
            except Exception:
                self.send('❌ Nutzung: /giessen N [Sekunden]')

        elif cmd == '/stop':
            try:
                ch_id = int(text.split()[1]) - 1
                self.irrigation.channels[ch_id].stop_pump()
                self.send(f'✅ Kanal {ch_id+1} gestoppt.')
            except Exception:
                self.send('❌ Nutzung: /stop N')

        elif cmd == '/stopall':
            for ch in self.irrigation.channels:
                ch.stop_pump()
            self.send('✅ Alle Pumpen gestoppt.')

        elif cmd == '/auto':
            try:
                ch_id = int(text.split()[1]) - 1
                ch    = self.irrigation.channels[ch_id]
                new   = not ch.cfg.get('auto_mode', True)
                ch.cfg['auto_mode'] = new
                self.irrigation.cfg.set_channel(ch_id, {'auto_mode': new})
                self.send(f'✅ Kanal {ch_id+1} Auto: {"AN" if new else "AUS"}')
            except Exception:
                self.send('❌ Nutzung: /auto N')

        elif cmd == '/log':
            evts = self.irrigation.get_events(8)
            txt  = '*📋 Letzte Ereignisse*\n'
            for e in evts:
                txt += f'`{e["ts"]}` {e["msg"]}\n'
            self.send(txt or 'Keine Ereignisse.')

        else:
            self.send('❓ Unbekannter Befehl. Schreibe /info')

    def _ota_py(self, doc, chat):
        """Python-Datei direkt via Telegram aktualisieren."""
        if not self.ota:
            self.send('OTA nicht verfügbar.', chat); return
        try:
            self.send(f'📥 Empfangen: {doc["file_name"]} – wird übertragen...', chat)
            result = self.ota.update_file_from_telegram(doc['file_id'], doc['file_name'])
            if result:
                self.send(f'✅ {doc["file_name"]} aktualisiert – Neustart...', chat)
                import time, machine
                time.sleep(2)
                machine.reset()
            else:
                self.send('❌ Übertragung fehlgeschlagen.', chat)
        except Exception as e:
            self.send(f'❌ Fehler: {e}', chat)

    async def run(self):
        import asyncio
        while True:
            if self.cfg.get('telegram.enabled') and self._token:
                try:
                    updates = self._get_updates()
                    for u in updates:
                        self.offset = u['update_id'] + 1
                        if 'message' in u:
                            self._handle(u['message'])
                except Exception as e:
                    print(f'Telegram poll error: {e}')
            await asyncio.sleep(3)
