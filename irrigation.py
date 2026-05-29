"""
irrigation.py – Kernlogik: Sensoren, Pumpen, Automatik, Logging

Angepasst für 5V-Pumpen am ESP32:
  - PUMP_QUEUE: Es läuft IMMER nur EINE Pumpe gleichzeitig (Strombegrenzung!)
  - MAX_PUMP_SECONDS: Hartes Laufzeit-Limit gegen Dauerlauf/Überlauf
  - Zwei Gießmodi pro Kanal: 'time' (X Sekunden) oder 'moisture' (bis Zielwert)
"""
import asyncio
import time
import json
import os
import gc
from machine import ADC, Pin
from config import get_config
from plants_db import get_plant, get_thresh_adjusted

MAX_CHANNELS     = 8
LOG_DIR          = '/logs'
MAX_READINGS     = 288     # 24h bei 5min-Intervall
MAX_EVENTS       = 150
MAX_PUMP_SECONDS = 120     # Sicherheits-Limit: keine Pumpe länger als 2 min am Stück


def _ts():
    t = time.localtime()
    return f'{t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}'


class Channel:
    def __init__(self, ch_id, cfg_data):
        self.id              = ch_id
        self.cfg             = cfg_data
        self.moisture_pct    = 0
        self.raw_adc         = 0
        self.pump_running    = False
        self.pump_start      = 0
        self.pump_duration   = 0
        self.last_watered    = 0
        self.total_waterings = cfg_data.get('total_waterings', 0)

        # ADC-Sensor
        try:
            self._adc = ADC(Pin(cfg_data['sensor_pin']))
            self._adc.atten(ADC.ATTN_11DB)
            self._adc.width(ADC.WIDTH_12BIT)
        except Exception as e:
            print(f'ADC CH{ch_id} Fehler: {e}')
            self._adc = None

        # Relais
        try:
            self._relay = Pin(cfg_data['relay_pin'], Pin.OUT)
            self._pump_off()
        except Exception as e:
            print(f'Relay CH{ch_id} Fehler: {e}')
            self._relay = None

    # ── Sensor ──────────────────────────────────────────────────────
    def read_adc(self):
        if not self._adc:
            return 2048
        total = 0
        for _ in range(8):
            total += self._adc.read()
            time.sleep_ms(2)
        return total // 8

    def adc_to_pct(self, raw):
        dry = self.cfg.get('dry_adc', 3500)
        wet = self.cfg.get('wet_adc', 1500)
        if dry == wet:
            return 0
        pct = (dry - raw) / (dry - wet) * 100
        return max(0, min(100, int(pct)))

    # ── Relais ──────────────────────────────────────────────────────
    def _pump_on(self):
        if self._relay:
            self._relay.value(0 if self.cfg.get('relay_active_low', True) else 1)

    def _pump_off(self):
        if self._relay:
            self._relay.value(1 if self.cfg.get('relay_active_low', True) else 0)

    def start_pump(self, duration=None):
        """Startet die Pumpe. duration=None → Wert aus Config.
        Begrenzt durch MAX_PUMP_SECONDS."""
        if self.pump_running:
            return False
        dur = duration if duration else self.cfg.get('water_duration', 20)
        dur = min(dur, MAX_PUMP_SECONDS)
        self._pump_on()
        self.pump_running    = True
        self.pump_start      = time.time()
        self.pump_duration   = dur
        self.total_waterings += 1
        self.last_watered    = time.time()
        print(f'[CH{self.id}] Pumpe AN ({dur}s | Feuchte {self.moisture_pct}%)')
        return True

    def stop_pump(self):
        if not self.pump_running:
            return
        self._pump_off()
        elapsed = int(time.time() - self.pump_start)
        self.pump_running = False
        # Statistik
        self.cfg['total_seconds'] = self.cfg.get('total_seconds', 0) + elapsed
        self.cfg['total_waterings'] = self.total_waterings
        print(f'[CH{self.id}] Pumpe AUS ({elapsed}s)')

    def check_pump_timeout(self):
        """True wenn Pumpe wegen Zeit-/Feuchtelimit gestoppt wurde."""
        if not self.pump_running:
            return False
        elapsed = time.time() - self.pump_start
        # Zeit-Limit
        if elapsed >= self.pump_duration:
            self.stop_pump()
            return True
        # Feuchte-Modus: stoppen wenn Zielfeuchte erreicht
        if self.cfg.get('water_mode', 'time') == 'moisture':
            target = self.cfg.get('moisture_target', 60)
            if self.moisture_pct >= target:
                self.stop_pump()
                return True
        return False

    def as_dict(self):
        return {
            'id': self.id,
            'name': self.cfg.get('name', f'Kanal {self.id+1}'),
            'enabled': self.cfg.get('enabled', False),
            'plant_idx': self.cfg.get('plant_idx', 0),
            'moisture': self.moisture_pct,
            'raw_adc': self.raw_adc,
            'pump': self.pump_running,
            'auto_mode': self.cfg.get('auto_mode', True),
            'water_mode': self.cfg.get('water_mode', 'time'),
            'thresh': self.cfg.get('moisture_thresh', 40),
            'moisture_target': self.cfg.get('moisture_target', 60),
            'duration': self.cfg.get('water_duration', 20),
            'dry_adc': self.cfg.get('dry_adc', 3500),
            'wet_adc': self.cfg.get('wet_adc', 1500),
            'min_interval_h': self.cfg.get('min_interval_h', 6),
            'total_waterings': self.total_waterings,
            'total_seconds': self.cfg.get('total_seconds', 0),
            'flow_ml_min': self.cfg.get('flow_ml_min', 0),
            'fertilize_days': self.cfg.get('fertilize_days', 0),
            'last_fertilized': self.cfg.get('last_fertilized', 0),
            'last_watered': self.last_watered,
            'pump_elapsed': int(time.time() - self.pump_start) if self.pump_running else 0,
        }


class Irrigation:
    def __init__(self):
        self.cfg             = get_config()
        self.channels        = []
        self.weather         = {}
        self.weather_status  = {'configured': False, 'ok': False, 'err': ''}
        self.water_level_pct = -1
        self._pump_queue     = []   # Kanal-IDs die gießen wollen
        self._active_pump    = None # aktuell laufender Kanal (nur EINER!)
        self.notify          = None # Callback für Telegram-Benachrichtigungen
        self.dht_data        = {}   # lokaler DHT22-Sensor
        self._dht            = None
        self._tank_warned    = False
        self._frost_warned   = False
        self._init_channels()
        self._init_dht()
        self._ensure_log_dir()

    def _init_channels(self):
        n = self.cfg.get('system.active_channels', 1)
        for i in range(min(n, MAX_CHANNELS)):
            self.channels.append(Channel(i, self.cfg.get_channel(i)))
        print(f'Irrigation: {len(self.channels)} Kanäle aktiv')

    def _init_dht(self):
        cfg = self.cfg.as_dict().get('sensor_dht', {})
        if not cfg.get('enabled'):
            return
        try:
            import dht
            from machine import Pin
            pin = Pin(cfg.get('pin', 4))
            self._dht = dht.DHT22(pin) if cfg.get('type', 22) == 22 else dht.DHT11(pin)
            print(f'DHT-Sensor an Pin {cfg.get("pin", 4)}')
        except Exception as e:
            print(f'DHT Init Fehler: {e}')
            self._dht = None

    def read_dht(self):
        if not self._dht:
            return
        try:
            self._dht.measure()
            self.dht_data = {
                'temp': self._dht.temperature(),
                'humidity': self._dht.humidity()
            }
        except Exception as e:
            print(f'DHT Lesefehler: {e}')

    def _notify(self, msg):
        """Sendet Benachrichtigung via Telegram-Callback (falls gesetzt)."""
        if self.notify:
            try:
                self.notify(msg)
            except Exception as e:
                print(f'Notify Fehler: {e}')

    def _ensure_log_dir(self):
        try:
            os.mkdir(LOG_DIR)
        except Exception:
            pass

    # ── Pumpen-Queue (nur EINE Pumpe gleichzeitig!) ──────────────────
    def request_pump(self, ch_id, duration=None):
        """Fordert Gießen an. Läuft sofort wenn frei, sonst Warteschlange."""
        ch = self.channels[ch_id]
        if self._active_pump is None:
            self._active_pump = ch_id
            ch.start_pump(duration)
            self._log_event(ch_id, 'water_start', f'Manuell/Auto: {ch.moisture_pct}%')
            if self.cfg.get('notify.water_start', True):
                self._notify(f'💧 {ch.cfg.get("name", "Kanal")} gestartet ({ch.pump_duration}s, Feuchte {ch.moisture_pct}%).')
            return True
        if ch_id not in [q[0] for q in self._pump_queue] and ch_id != self._active_pump:
            self._pump_queue.append((ch_id, duration))
            print(f'[CH{ch_id}] in Warteschlange')
        return False

    def stop_pump(self, ch_id):
        ch = self.channels[ch_id]
        was_running = ch.pump_running
        before = ch.moisture_pct
        ch.stop_pump()
        if was_running and self.cfg.get('notify.water_stop', True):
            self._notify(f'✅ {ch.cfg.get("name", "Kanal")} gestoppt. Feuchte: {before}%.')
        if self._active_pump == ch_id:
            self._active_pump = None
        # aus Warteschlange entfernen
        self._pump_queue = [q for q in self._pump_queue if q[0] != ch_id]

    def _process_queue(self):
        """Stoppt fertige Pumpe, startet nächste aus der Queue."""
        if self._active_pump is not None:
            ch = self.channels[self._active_pump]
            if ch.check_pump_timeout():
                self._log_event(self._active_pump, 'water_end',
                                f'Fertig: {ch.moisture_pct}%')
                if self.cfg.get('notify.water_stop', True):
                    self._notify(f'✅ {ch.cfg.get("name", "Kanal")} fertig. Feuchte: {ch.moisture_pct}%.')
                self._active_pump = None
        # Nächste Pumpe starten
        if self._active_pump is None and self._pump_queue:
            ch_id, dur = self._pump_queue.pop(0)
            self._active_pump = ch_id
            self.channels[ch_id].start_pump(dur)
            self._log_event(ch_id, 'water_start', 'Aus Warteschlange')
            if self.cfg.get('notify.water_start', True):
                ch = self.channels[ch_id]
                self._notify(f'💧 {ch.cfg.get("name", "Kanal")} aus Warteschlange gestartet ({ch.pump_duration}s).')

    # ── Sensoren ─────────────────────────────────────────────────────
    def update_sensors(self):
        for ch in self.channels:
            ch.raw_adc      = ch.read_adc()
            ch.moisture_pct = ch.adc_to_pct(ch.raw_adc)

    def measure_water_level(self):
        cfg = self.cfg.as_dict().get('water_level', {})
        if not cfg.get('enabled', False):
            self.water_level_pct = -1
            return
        try:
            trig = Pin(cfg.get('trig_pin', 12), Pin.OUT)
            echo = Pin(cfg.get('echo_pin', 14), Pin.IN)
            trig.value(0); time.sleep_us(2)
            trig.value(1); time.sleep_us(10)
            trig.value(0)
            t0 = time.ticks_us()
            while echo.value() == 0:
                if time.ticks_diff(time.ticks_us(), t0) > 30000:
                    return
            t1 = time.ticks_us()
            while echo.value() == 1:
                if time.ticks_diff(time.ticks_us(), t1) > 30000:
                    return
            dist_cm = time.ticks_diff(time.ticks_us(), t1) * 0.0343 / 2
            height  = cfg.get('tank_height_cm', 30)
            pct     = int((height - dist_cm) / height * 100)
            self.water_level_pct = max(0, min(100, pct))
        except Exception:
            self.water_level_pct = -1

    # ── Auto-Bewässerung ─────────────────────────────────────────────
    def check_auto_watering(self):
        for ch in self.channels:
            if not ch.cfg.get('enabled') or not ch.cfg.get('auto_mode'):
                continue
            if ch.pump_running or ch.id == self._active_pump:
                continue
            if ch.id in [q[0] for q in self._pump_queue]:
                continue
            # Mindestabstand zwischen Gießvorgängen
            ivl_h = ch.cfg.get('min_interval_h', 6)
            if ch.last_watered and (time.time() - ch.last_watered) < ivl_h * 3600:
                continue
            # Wasserstand
            if self.water_level_pct >= 0:
                if self.water_level_pct <= self.cfg.get('water_level.min_pct', 15):
                    continue
            # Frostschutz
            if self._frost_active():
                continue
            # Wetter (Regen)
            if self._skip_due_to_weather(ch):
                continue
            # Feuchte-Schwelle (wetterbereinigt)
            thresh = self._adjusted_thresh(ch)
            if ch.moisture_pct < thresh:
                self.request_pump(ch.id)

    def _skip_due_to_weather(self, ch):
        w = self.weather
        if not w:
            return False
        if not self.cfg.get('weather.skip_on_rain'):
            return False
        return bool(w.get('rain_forecast') or w.get('rain_1h', 0) > 1.0)

    def _frost_active(self):
        if not self.cfg.get('weather.frost_protect', True):
            return False
        return bool(self.weather.get('frost'))

    def _adjusted_thresh(self, ch):
        base = ch.cfg.get('moisture_thresh', 40)
        try:
            return get_thresh_adjusted(ch.cfg.get('plant_idx', 0), base, self.weather)
        except Exception as e:
            print(f"[Anpassungs-Fehler] Nutze Standard-Schwelle: {e}")
            return base

    def _check_alerts(self):
        """Tank-, Frost- und Düngerwarnungen prüfen und ggf. melden."""
        # Tank leer
        if self.water_level_pct >= 0:
            min_pct = self.cfg.get('water_level.min_pct', 15)
            if self.water_level_pct <= min_pct:
                if not self._tank_warned and self.cfg.get('notify.tank_low', True):
                    self._notify(f'⚠️ Wasserstand niedrig: {self.water_level_pct}%')
                    self._log_event(-1, 'tank_low', f'Tank: {self.water_level_pct}%')
                    self._tank_warned = True
            else:
                self._tank_warned = False
        # Frost
        if self._frost_active():
            if not self._frost_warned and self.cfg.get('notify.frost', True):
                t = self.weather.get('temp', '?')
                self._notify(f'❄️ Frostschutz aktiv ({t}°C) – Bewässerung pausiert.')
                self._frost_warned = True
        else:
            self._frost_warned = False
        # Dünger fällig
        if self.cfg.get('notify.fertilize', True):
            for ch in self.channels:
                days = ch.cfg.get('fertilize_days', 0)
                if not days or not ch.cfg.get('enabled'):
                    continue
                last = ch.cfg.get('last_fertilized', 0)
                if last and (time.time() - last) >= days * 86400:
                    self._notify(f'🌿 {ch.cfg.get("name")}: Düngen fällig (alle {days} Tage).')
                    ch.cfg['last_fertilized'] = time.time()
                    self.cfg.save()
                elif not last:
                    ch.cfg['last_fertilized'] = time.time()

    def mark_fertilized(self, ch_id):
        """Manuell als gedüngt markieren (vom UI/Telegram)."""
        if 0 <= ch_id < len(self.channels):
            self.channels[ch_id].cfg['last_fertilized'] = time.time()
            self.cfg.save()

    # ── Logging ──────────────────────────────────────────────────────
    def _log_event(self, ch_id, etype, msg):
        try:
            path = f'{LOG_DIR}/events.json'
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                data = {'events': []}
            data['events'].append({'ts': _ts(), 'type': etype, 'msg': msg, 'ch': ch_id})
            if len(data['events']) > MAX_EVENTS:
                data['events'] = data['events'][-MAX_EVENTS:]
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Log error: {e}')

    def _log_reading(self, ch_id, moisture):
        try:
            path = f'{LOG_DIR}/ch{ch_id}.json'
            try:
                with open(path) as f:
                    data = json.load(f)
            except Exception:
                data = {'readings': []}
            data['readings'].append({'ts': _ts(), 'm': moisture})
            if len(data['readings']) > MAX_READINGS:
                data['readings'] = data['readings'][-MAX_READINGS:]
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Reading log error: {e}')

    def get_events(self, limit=30):
        try:
            with open(f'{LOG_DIR}/events.json') as f:
                return json.load(f).get('events', [])[-limit:]
        except Exception:
            return []

    def get_logs(self, ch_id, limit=30):
        try:
            with open(f'{LOG_DIR}/ch{ch_id}.json') as f:
                return json.load(f).get('readings', [])[-limit:]
        except Exception:
            return []

    # ── Status ───────────────────────────────────────────────────────
    def status_dict(self):
        import network
        sta = network.WLAN(network.STA_IF)
        return {
            'ip':          sta.ifconfig()[0] if sta.isconnected() else '0.0.0.0',
            'rssi':        sta.status('rssi') if sta.isconnected() else 0,
            'heap':        gc.mem_free(),
            'water_level': self.water_level_pct,
            'active_pump': self._active_pump if self._active_pump is not None else -1,
            'queue':       [q[0] for q in self._pump_queue],
            'weather':     self.weather,
            'weather_status': self.weather_status,
            'weather_enabled': bool(self.cfg.get('weather.enabled') and self.cfg.get('weather.api_key')),
            'dht':         self.dht_data,
            'frost_active': self._frost_active(),
            'channels':    [ch.as_dict() for ch in self.channels],
        }

    # ── Zeitpläne ─────────────────────────────────────────────────────
    def check_schedule(self):
        """Prüft feste Gießzeiten. entry: {channel, hour, minute, duration_s, days}"""
        sched = self.cfg.as_dict().get('schedule', {})
        if not sched.get('enabled'):
            return
        lt  = time.localtime()
        now_h, now_m, wday = lt[3], lt[4], lt[6]   # wday: 0=Mo
        for e in sched.get('entries', []):
            if e.get('hour') == now_h and e.get('minute') == now_m:
                if wday in e.get('days', [0,1,2,3,4,5,6]):
                    ch_id = e.get('channel', 0)
                    if self._frost_active():
                        continue
                    if 0 <= ch_id < len(self.channels):
                        self.request_pump(ch_id, e.get('duration_s'))
                        self._log_event(ch_id, 'schedule', f'Zeitplan {now_h:02d}:{now_m:02d}')

    # ── Haupt-Loop ────────────────────────────────────────────────────
    async def run(self):
        SENSOR_INTERVAL = 300   # Sensorwerte alle 5 min loggen
        AUTO_INTERVAL   = 60    # Automatik-Check jede Minute
        ALERT_INTERVAL  = 300   # Warnungen alle 5 min prüfen
        last_log   = 0
        last_auto  = 0
        last_alert = 0
        last_sched_min = -1

        while True:
            try:
                self.update_sensors()
                self.measure_water_level()
                self.read_dht()

                # Pumpen-Queue verarbeiten (Timeout/nächste Pumpe)
                self._process_queue()

                t = time.time()

                # Zeitplan: einmal pro Minute prüfen
                cur_min = time.localtime()[4]
                if cur_min != last_sched_min:
                    self.check_schedule()
                    last_sched_min = cur_min

                if t - last_log >= SENSOR_INTERVAL:
                    for ch in self.channels:
                        if ch.cfg.get('enabled'):
                            self._log_reading(ch.id, ch.moisture_pct)
                    last_log = t

                if t - last_auto >= AUTO_INTERVAL:
                    self.check_auto_watering()
                    last_auto = t

                if t - last_alert >= ALERT_INTERVAL:
                    self._check_alerts()
                    last_alert = t

            except Exception as e:
                import sys
                print("\n🚨 [LOOP-CRASH] Genaue Fehlerstelle:")
                sys.print_exception(e)
                print("🚨 ----------------------------------\n")

            gc.collect()
            # Wenn Pumpe läuft: häufiger prüfen (für genaues Timing)
            await asyncio.sleep(2 if self._active_pump is not None else 10)
