"""
config.py – Konfigurationsverwaltung
Speichert alles als /config.json auf dem Flash-Dateisystem.
"""
import json
import os
import gc

CONFIG_FILE   = '/config.json'
CONFIG_VERSION = 7

SENSOR_PINS = [34, 35, 32, 33, 36, 39, 25, 26]
RELAY_PINS  = [16, 17, 18, 19, 21, 22, 23, 27]

def _default_channel(i):
    return {
        'id': i, 'name': f'Kanal {i+1}', 'enabled': i == 0,
        'plant_idx': 0,
        'sensor_pin': SENSOR_PINS[i], 'relay_pin': RELAY_PINS[i],
        'relay_active_low': True,
        # Gießmodus: 'time' = X Sekunden, 'moisture' = bis Zielfeuchte
        'water_mode': 'time',
        'moisture_thresh': 40,    # unter diesem Wert wird gegossen
        'moisture_target': 60,    # Zielfeuchte im moisture-Modus
        'water_duration': 20,     # Sekunden im time-Modus (5V-Pumpe: kurz halten!)
        'min_interval_h': 6,      # Mindestpause zwischen Gießvorgängen
        'auto_mode': True,
        'dry_adc': 3500, 'wet_adc': 1500,
        'total_waterings': 0,
        'total_seconds': 0,       # kumulierte Pumpenlaufzeit (Statistik)
        'flow_ml_min': 0,         # Fördermenge ml/min (0 = unbekannt, nur Sekunden)
        'fertilize_days': 0,      # Dünger-Intervall in Tagen (0 = aus)
        'last_fertilized': 0      # Timestamp letzte Düngung
    }

DEFAULT = {
    '_version': CONFIG_VERSION,
    'wifi': {'ssid': '', 'password': ''},
    'system': {
        'hostname': 'smart-irrigation',
        'active_channels': 1,
        'timezone_offset': 1,
        'ntp_server': 'pool.ntp.org',
        'setup_done': False
    },
    'water_level': {
        'enabled': False, 'trig_pin': 12, 'echo_pin': 14,
        'tank_height_cm': 30, 'min_pct': 15
    },
    'display': {'type': 0, 'i2c_sda': 21, 'i2c_scl': 22,
                'address': 0x3C, 'width': 128, 'height': 64},
    'channels': [_default_channel(i) for i in range(8)],
    'telegram': {'enabled': False, 'token': '', 'chat_id': ''},
    'mqtt': {
        'enabled': False, 'server': '', 'port': 1883,
        'user': '', 'password': '', 'base_topic': 'irrigation'
    },
    'weather': {
        'enabled': False, 'api_key': '', 'city': 'Berlin', 'country': 'DE',
        'skip_on_rain': True, 'hot_threshold': 28.0,
        'frost_protect': True, 'frost_threshold': 4.0
    },
    'sensor_dht': {
        'enabled': False, 'pin': 4, 'type': 22   # 22=DHT22, 11=DHT11
    },
    'notify': {
        'tank_low': True, 'pump_error': True,
        'frost': True, 'fertilize': True, 'daily_report': False,
        'water_start': True, 'water_stop': True, 'system': True
    },
    'schedule': {
        'enabled': False,
        'entries': []
        # entry: {channel, hour, minute, duration_s, days: [0-6]}
    }
}


class Config:
    def __init__(self):
        self._data = {}
        self.load()

    def load(self):
        try:
            with open(CONFIG_FILE, 'r') as f:
                self._data = json.load(f)
            self._migrate()
        except Exception:
            self._data = json.loads(json.dumps(DEFAULT))  # deep copy
            self.save()

    def _migrate(self):
        stored = self._data.get('_version', 0)
        if stored >= CONFIG_VERSION:
            return
        print(f'Config-Migration v{stored} → v{CONFIG_VERSION}')
        # Fehlende Top-Level-Keys aus DEFAULT ergänzen (ohne alte zu überschreiben)
        self._deep_merge(self._data, DEFAULT)
        self._data['_version'] = CONFIG_VERSION
        self.save()

    def _deep_merge(self, target, source):
        """Fügt fehlende Keys aus source in target ein (nicht überschreiben)."""
        for k, v in source.items():
            if k not in target:
                target[k] = json.loads(json.dumps(v))  # deep copy
            elif isinstance(v, dict) and isinstance(target[k], dict):
                self._deep_merge(target[k], v)

    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self._data, f)
            gc.collect()
        except Exception as e:
            print(f'Config save error: {e}')

    # ── Getter / Setter ───────────────────────────────────────────
    def get(self, path, default=None):
        """Zugriff via Punkt-Notation: config.get('mqtt.server')"""
        keys = path.split('.')
        d = self._data
        for k in keys:
            if isinstance(d, dict) and k in d:
                d = d[k]
            else:
                return default
        return d

    def set(self, path, value, save=True):
        """Setzen via Punkt-Notation: config.set('mqtt.enabled', True)"""
        keys = path.split('.')
        d = self._data
        for k in keys[:-1]:
            d = d.setdefault(k, {})
        d[keys[-1]] = value
        if save:
            self.save()

    def get_channel(self, ch_id):
        chs = self._data.get('channels', [])
        if 0 <= ch_id < len(chs):
            return chs[ch_id]
        return _default_channel(ch_id)

    def set_channel(self, ch_id, data, save=True):
        chs = self._data.setdefault('channels', [_default_channel(i) for i in range(8)])
        while len(chs) <= ch_id:
            chs.append(_default_channel(len(chs)))
        chs[ch_id].update(data)
        if save:
            self.save()

    def as_dict(self):
        return self._data

    def update_from_dict(self, d, save=True):
        self._deep_merge_overwrite(self._data, d)
        if save:
            self.save()

    def _deep_merge_overwrite(self, target, source):
        """Wie deep_merge, aber überschreibt vorhandene Werte."""
        for k, v in source.items():
            if isinstance(v, dict) and isinstance(target.get(k), dict):
                self._deep_merge_overwrite(target[k], v)
            else:
                target[k] = v


# Singleton
_instance = None
def get_config():
    global _instance
    if _instance is None:
        _instance = Config()
    return _instance
