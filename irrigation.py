"""
irrigation.py – Kernlogik: Sensoren, Pumpen, Automatik, Logging, Wasserstand
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
        except Exception as e:
            print(f'Wasserstand Fehler: {e}')

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
                started = ch.start_pump()
                if started:
                    plant = get_plant(ch.cfg.get('plant_idx', 0))
                    self._log_event(ch.id, 'water_start',
                        f'Auto: {ch.moisture_pct}%<{thresh}% Pflanze:{plant[1]}')

    def _skip_due_to_weather(self, ch):
        if not self.weather:
            return False
        plant = get_plant(ch.cfg.get('plant_idx', 0))
        # Staunässe-sensitive Pflanzen + hohe Luftfeuchte
        if plant[9] and self.weather.get('humidity', 0) > 90:
            return True
        # Regen-Skip
        if (self.cfg.get('weather.skip_on_rain') and
                (self.weather.get('rain_1h', 0) > 2.0 or self.weather.get('rain_forecast'))):
            return True
        return False

    def _adjusted_thresh(self, ch):
        plant  = get_plant(ch.cfg.get('plant_idx', 0))
        temp   = self.weather.get('temp') if self.weather else None
        hum    = self.weather.get('humidity') if self.weather else None
        base   = ch.cfg.get('moisture_thresh', 40)
        # Nutze plant-basierten Threshold wenn > channel-thresh
        plant_thresh = get_thresh_adjusted(plant, temp, hum)
        return max(base, plant_thresh)

    # ── Zeitplan-Bewässerung ──────────────────────────────────────────
    def check_schedule(self):
        if not self.cfg.get('schedule.enabled', False):
            return
        t = time.localtime()
        now_h, now_m, now_dow = t[3], t[4], t[6]
        for entry in self.cfg.get('schedule.entries') or []:
            ch_id = entry.get('channel', 0)
            if ch_id >= len(self.channels):
                continue
            ch = self.channels[ch_id]
            if ch.pump_running:
                continue
            days = entry.get('days', list(range(7)))
            if now_dow not in days:
                continue
            if entry.get('hour') == now_h and entry.get('minute') == now_m:
                dur = entry.get('duration_s', ch.cfg.get('water_duration', 30))
                if ch.start_pump(dur):
                    self._log_event(ch_id, 'water_schedule',
                        f'Zeitplan: {now_h:02d}:{now_m:02d}')

    # ── Kalibrierung ──────────────────────────────────────────────────
    def calibrate_dry(self, ch_id):
        if ch_id >= len(self.channels):
            return None
        raw = self.channels[ch_id].read_adc()
        self.cfg.set_channel(ch_id, {'dry_adc': raw})
        self.channels[ch_id].cfg['dry_adc'] = raw
        self._log_event(ch_id, 'calib_dry', f'Trockenwert: {raw}')
        return raw

    def calibrate_wet(self, ch_id):
        if ch_id >= len(self.channels):
            return None
        raw = self.channels[ch_id].read_adc()
        self.cfg.set_channel(ch_id, {'wet_adc': raw})
        self.channels[ch_id].cfg['wet_adc'] = raw
        self._log_event(ch_id, 'calib_wet', f'Nasswert: {raw}')
        return raw

    # ── Logging ───────────────────────────────────────────────────────
    def log_readings(self):
        for ch in self.channels:
            if not ch.cfg.get('enabled'):
                continue
            path = f'{LOG_DIR}/ch{ch.id}.json'
            try:
                try:
                    with open(path, 'r') as f:
                        data = json.load(f)
                except Exception:
                    data = {'readings': []}
                readings = data.get('readings', [])
                readings.append({'ts': _ts(), 'm': ch.moisture_pct})
                if len(readings) > MAX_READINGS:
                    readings = readings[-MAX_READINGS:]
                data['readings'] = readings
                with open(path, 'w') as f:
                    json.dump(data, f)
            except Exception as e:
                print(f'Log error CH{ch.id}: {e}')
            gc.collect()

    def _log_event(self, ch_id, event_type, msg):
        print(f'[EVENT] {event_type} ch{ch_id}: {msg}')
        path = f'{LOG_DIR}/events.json'
        try:
            try:
                with open(path, 'r') as f:
                    data = json.load(f)
            except Exception:
                data = {'events': []}
            evts = data.get('events', [])
            evts.append({'ts': _ts(), 'type': event_type, 'ch': ch_id, 'msg': msg})
            if len(evts) > MAX_EVENTS:
                evts = evts[-MAX_EVENTS:]
            data['events'] = evts
            with open(path, 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f'Event log error: {e}')

    def get_logs(self, ch_id, limit=48):
        path = f'{LOG_DIR}/ch{ch_id}.json'
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return data.get('readings', [])[-limit:]
        except Exception:
            return []

    def get_events(self, limit=50):
        try:
            with open(f'{LOG_DIR}/events.json', 'r') as f:
                data = json.load(f)
            return data.get('events', [])[-limit:]
        except Exception:
            return []

    # ── Haupt-Task ────────────────────────────────────────────────────
    async def run(self):
        log_timer    = 0
        sensor_timer = 0
        sched_timer  = 0

        while True:
            now = time.time()

            # Sensoren alle 10s
            if now - sensor_timer >= 10:
                sensor_timer = now
                self.update_sensors()
                self.measure_water_level()
                self.check_auto_watering()

            # Zeitplan jede Minute prüfen
            if now - sched_timer >= 60:
                sched_timer = now
                self.check_schedule()

            # Pump-Timeouts ständig prüfen
            for ch in self.channels:
                ch.check_pump_timeout()

            # Logging alle 5 Minuten
            if now - log_timer >= 300:
                log_timer = now
                self.log_readings()

            gc.collect()
            await asyncio.sleep(1)

    def status_dict(self):
        import gc
        import network
        import os
        sta = network.WLAN(network.STA_IF)
        statvfs = os.statvfs('/')
        free_flash = statvfs[0] * statvfs[3]
        return {
            'uptime': time.time(),
            'heap': gc.mem_free(),
            'rssi': sta.status('rssi') if sta.isconnected() else 0,
            'ip': sta.ifconfig()[0] if sta.isconnected() else '',
            'flash_free': free_flash,
            'water_level': self.water_level_pct,
            'channels': [ch.as_dict() for ch in self.channels],
            'weather': self.weather,
        }
