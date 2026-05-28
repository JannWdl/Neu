"""
irrigation.py – Kernlogik: Sensoren, Pumpen, Automatik, Logging, Wasserstand
Kombiniert automatische Bewässerung, Zeitpläne und robustes Hardware-Fehlerhandling.
"""
import asyncio
import time
import json
import os
import gc
from machine import ADC, Pin
from config import get_config
from plants_db import get_plant, get_thresh_adjusted

MAX_CHANNELS = 8
LOG_DIR      = '/logs'
MAX_READINGS = 288   # 24h bei 5min-Intervall
MAX_EVENTS   = 200


def _ts():
    t = time.localtime()
    return f'{t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}'


class Channel:
    def __init__(self, ch_id, cfg_data):
        self.id            = ch_id
        self.cfg           = cfg_data
        self.moisture_pct  = 0
        self.raw_adc       = 0
        self.pump_running  = False
        self.pump_start    = 0
        self.last_watered  = 0    # unix timestamp
        self.total_waterings = cfg_data.get('total_waterings', 0)

        # ADC initialisieren
        try:
            self._adc = ADC(Pin(cfg_data['sensor_pin']))
            self._adc.atten(ADC.ATTN_11DB)   # 0–3.9V Bereich
            self._adc.width(ADC.WIDTH_12BIT)  # 12-bit = 0–4095
        except Exception as e:
            print(f'ADC CH{ch_id} Fehler: {e}')
            self._adc = None

        # Relais-Pin
        try:
            self._relay = Pin(cfg_data['relay_pin'], Pin.OUT)
            self._pump_off()
        except Exception as e:
            print(f'Relay CH{ch_id} Fehler: {e}')
            self._relay = None

    # ── ADC ─────────────────────────────────────────────────────────
    def read_adc(self):
        if not self._adc:
            return 2048
        total = 0
        for _ in range(8):    # 8× mitteln
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
        if self.pump_running:
            return False
        dur = duration or self.cfg.get('water_duration', 30)
        self._pump_on()
        self.pump_running = True
        self.pump_start   = time.time()
        self.pump_duration = dur
        self.total_waterings += 1
        self.last_watered  = time.time()
        print(f'[CH{self.id}] Pumpe AN ({dur}s, Feuchte: {self.moisture_pct}%)')
        return True

    def stop_pump(self):
        if not self.pump_running:
            return
        self._pump_off()
        self.pump_running = False
        elapsed = time.time() - self.pump_start
        print(f'[CH{self.id}] Pumpe AUS ({elapsed:.0f}s gelaufen)')

    def check_pump_timeout(self):
        if self.pump_running:
            if time.time() - self.pump_start >= self.pump_duration:
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
            'thresh': self.cfg.get('moisture_thresh', 40),
            'duration': self.cfg.get('water_duration', 30),
            'dry_adc': self.cfg.get('dry_adc', 3500),
            'wet_adc': self.cfg.get('wet_adc', 1500),
            'min_interval_h': self.cfg.get('min_interval_h', 6),
            'total_waterings': self.total_waterings,
            'last_watered': self.last_watered,
            'pump_elapsed': int(time.time() - self.pump_start) if self.pump_running else 0,
        }


class Irrigation:
    def __init__(self):
        self.cfg      = get_config()
        self.channels = []
        self.weather  = {}     # gesetzt von weather.py
        self.water_level_pct = -1
        self._init_channels()
        self._ensure_log_dir()

    def _init_channels(self):
        n = self.cfg.get('system.active_channels', 1)
        for i in range(min(n, MAX_CHANNELS)):
            ch_cfg = self.cfg.get_channel(i)
            ch = Channel(i, ch_cfg)
            self.channels.append(ch)
        print(f'Irrigation: {len(self.channels)} Kanäle initialisiert')

    def _ensure_log_dir(self):
        try:
            os.mkdir(LOG_DIR)
        except Exception:
            pass

    # ── Sensoren ─────────────────────────────────────────────────────
    def update_sensors(self):
        for ch in self.channels:
            ch.raw_adc      = ch.read_adc()
            ch.moisture_pct = ch.adc_to_pct(ch.raw_adc)

    def measure_water_level(self):
        cfg = self.cfg.as_dict().get('water_level', {})
        if not cfg.get('enabled', False):
            return
        try:
            from machine import Pin
            import time
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
            t2 = time.ticks_us()
            dist_cm = time.ticks_diff(t2, t1) * 0.0343 / 2
            height  = cfg.get('tank_height_cm', 30)
            pct     = int((height - dist_cm) / height * 100)
            self.water_level_pct = max(0, min(100, pct))
            min_pct = cfg.get('min_pct', 15)
            if self.water_level_pct <= min_pct:
                self._log_event(-1, 'water_low',
                    f'Wasserstand kritisch: {self.water_level_pct}%')
        except OSError:
            # Hier fangen wir den Hardware-EIO Fehler [Errno 5] gezielt ab!
            print('[WARNUNG] Wasserstand-Sensor aktiviert, aber Hardware fehlt oder antwortet nicht.')
            self.water_level_pct = -1  # Signalisiert dem System "Fehler/Nicht verfügbar"
        except Exception as e:
            print(f'Wasserstand unvorhergesehener Fehler: {e}')

    # ── Auto-Bewässerung ──────────────────────────────────────────────
    def check_auto_watering(self):
        for ch in self.channels:
            if not ch.cfg.get('enabled') or not ch.cfg.get('auto_mode'):
                continue
            if ch.pump_running:
                continue
            # Mindestabstand
            ivl_h = ch.cfg.get('min_interval_h', 6)
            if ch.last_watered and (time.time() - ch.last_watered) < ivl_h * 3600:
                continue
            # Wasserstand prüfen
            min_pct = self.cfg.get('water_level.min_pct', 15)
            if self.water_level_pct >= 0 and self.water_level_pct <= min_pct:
                continue
            # Wetter-Check
            if self._skip_due_to_weather(ch):
                continue
            # Schwellwert (wetterbereinigt)
            thresh = self._adjusted_thresh(ch)
            if ch.moisture_pct < thresh:
                ch.start_pump()
                self._log_event(ch.id, 'water_start',
                    f'Auto: {ch.moisture_pct}%<{thresh}% Pflanze:{get_plant(ch.cfg.get("plant_idx",0))["name_de"]}')

    def _skip_due_to_weather(self, ch):
        w = self.weather
        if not w:
            return False
        cfg = self.cfg.as_dict().get('weather', {})
        if not cfg.get('skip_on_rain'):
            return False
        if w.get('rain_forecast') or w.get('rain_1h', 0) > 1.0:
            return True
        return False

    def _adjusted_thresh(self, ch):
        from plants_db import get_thresh_adjusted
        plant_idx = ch.cfg.get('plant_idx', 0)
        base      = ch.cfg.get('moisture_thresh', 40)
        return get_thresh_adjusted(plant_idx, base, self.weather)

    # ── Logging ───────────────────────────────────────────────────────
    def _log_event(self, ch_id, etype, msg):
        entry = {'ts': _ts(), 'type': etype, 'msg': msg, 'ch': ch_id}
        log_file = f'{LOG_DIR}/events.json'
        try:
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)
            except Exception:
                data = {'events': []}
            data['events'].append(entry)
            if len(data['events']) > MAX_EVENTS:
                data['events'] = data['events'][-MAX_EVENTS:]
            with open(log_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Log error: {e}')

    def _log_reading(self, ch_id, moisture):
        log_file = f'{LOG_DIR}/ch{ch_id}.json'
        entry = {'ts': _ts(), 'm': moisture}
        try:
            try:
                with open(log_file, 'r') as f:
                    data = json.load(f)
            except Exception:
                data = {'readings': []}
            data['readings'].append(entry)
            if len(data['readings']) > MAX_READINGS:
                data['readings'] = data['readings'][-MAX_READINGS:]
            with open(log_file, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Reading log error: {e}')

    def get_events(self, limit=30):
        try:
            with open(f'{LOG_DIR}/events.json', 'r') as f:
                return json.load(f).get('events', [])[-limit:]
        except Exception:
            return []

    def get_logs(self, ch_id, limit=30):
        try:
            with open(f'{LOG_DIR}/ch{ch_id}.json', 'r') as f:
                return json.load(f).get('readings', [])[-limit:]
        except Exception:
            return []

    # ── Status ────────────────────────────────────────────────────────
    def status_dict(self):
        import network, gc
        sta = network.WLAN(network.STA_IF)
        return {
            'ip':          sta.ifconfig()[0] if sta.isconnected() else '0.0.0.0',
            'rssi':        sta.status('rssi') if sta.isconnected() else 0,
            'heap':        gc.mem_free(),
            'water_level': self.water_level_pct,
            'channels':    [ch.as_dict() for ch in self.channels],
        }

    # ── Haupt-Loop ────────────────────────────────────────────────────
    async def run(self):
        """Sensor-Lese- und Automatik-Loop."""
        import asyncio
        SENSOR_INTERVAL  = 300   # Sekunden zwischen Sensor-Logs
        AUTO_INTERVAL    = 60    # Sekunden zwischen Automatik-Checks
        last_log  = 0
        last_auto = 0

        while True:
            now = asyncio.ticks_ms() // 1000 if hasattr(asyncio, 'ticks_ms') else 0
            try:
                self.update_sensors()
                self.measure_water_level()

                # Pumpen-Timeout prüfen
                for ch in self.channels:
                    ch.check_pump_timeout()

                # Sensor-Werte loggen (alle 5 min)
                import time
                t = time.time()
                if t - last_log >= SENSOR_INTERVAL:
                    for ch in self.channels:
                        if ch.cfg.get('enabled'):
                            self._log_reading(ch.id, ch.moisture_pct)
                    last_log = t

                # Auto-Bewässerung (jede Minute)
                if t - last_auto >= AUTO_INTERVAL:
                    self.check_auto_watering()
                    last_auto = t

            except Exception as e:
                print(f'Irrigation loop error: {e}')

            gc.collect()
            await asyncio.sleep(10)
