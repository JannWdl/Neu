"""
mqtt_client.py – MQTT + Home Assistant Auto-Discovery
"""
from config import get_config


class MQTTClient:
    def __init__(self, irrigation):
        self.cfg        = get_config()
        self.irrigation = irrigation
        self._client    = None
        self._connected = False
        self._last_error = ''

    def status_dict(self):
        cfg = self.cfg.as_dict().get('mqtt', {})
        return {
            'enabled': bool(cfg.get('enabled')),
            'server': cfg.get('server', ''),
            'base_topic': cfg.get('base_topic', 'irrigation'),
            'connected': self._connected,
            'last_error': self._last_error
        }

    def _connect(self):
        from umqtt.simple import MQTTClient as _MQTT
        import network
        mac = ':'.join(f'{b:02x}' for b in network.WLAN(network.STA_IF).config('mac'))
        client_id = 'irrigation_' + mac.replace(':', '')[-6:]
        cfg = self.cfg.as_dict().get('mqtt', {})
        c = _MQTT(client_id, cfg['server'], cfg.get('port', 1883),
                  cfg.get('user') or None, cfg.get('password') or None)
        c.set_callback(self._on_message)
        c.connect()
        base = cfg.get('base_topic', 'irrigation')
        for i in range(len(self.irrigation.channels)):
            c.subscribe(f'{base}/ch{i}/pump/command'.encode())
        self._client    = c
        self._connected = True
        self._last_error = ''
        self._ha_discovery(base)
        self._pub(f'{base}/status', 'online', retain=True)
        print('MQTT verbunden')

    def test_connection(self):
        """Manueller Verbindungstest für Web-Dashboard/API."""
        from umqtt.simple import MQTTClient as _MQTT
        import network
        cfg = self.cfg.as_dict().get('mqtt', {})
        if not cfg.get('enabled') or not cfg.get('server'):
            return {'ok': False, 'err': 'MQTT ist nicht aktiviert oder Server fehlt.'}
        try:
            mac = ''.join(f'{b:02x}' for b in network.WLAN(network.STA_IF).config('mac'))
            client_id = 'irrigation_test_' + mac[-6:]
            base = cfg.get('base_topic', 'irrigation')
            c = _MQTT(client_id, cfg['server'], cfg.get('port', 1883),
                      cfg.get('user') or None, cfg.get('password') or None)
            c.connect()
            c.publish(f'{base}/test'.encode(), b'ok', retain=False)
            try:
                c.disconnect()
            except Exception:
                pass
            self._last_error = ''
            return {'ok': True, 'msg': 'MQTT-Verbindung erfolgreich.', 'topic': f'{base}/test'}
        except Exception as e:
            self._last_error = str(e)
            self._connected = False
            return {'ok': False, 'err': str(e)}

    def _on_message(self, topic, msg):
        topic = topic.decode()
        msg   = msg.decode().upper()
        base  = self.cfg.get('mqtt.base_topic', 'irrigation')
        for i, ch in enumerate(self.irrigation.channels):
            if topic == f'{base}/ch{i}/pump/command':
                if msg == 'ON':  self.irrigation.request_pump(i)
                if msg == 'OFF': self.irrigation.stop_pump(i)

    def _ha_discovery(self, base):
        import network, json as _json
        mac = ''.join(f'{b:02x}' for b in network.WLAN(network.STA_IF).config('mac'))
        dev = {'identifiers': [f'irrigation_{mac}'], 'name': 'Smart Irrigation',
               'model': 'ESP32 MicroPython v3', 'manufacturer': 'DIY'}
        for i, ch in enumerate(self.irrigation.channels):
            name = ch.cfg.get('name', f'Kanal {i+1}')
            uid  = f'irrigation_{mac}_ch{i}'
            self._pub(f'homeassistant/sensor/{uid}_m/config', _json.dumps({
                'name': f'{name} Feuchtigkeit', 'unique_id': f'{uid}_m',
                'state_topic': f'{base}/ch{i}/moisture',
                'unit_of_measurement': '%', 'device_class': 'moisture',
                'device': dev
            }), retain=True)
            self._pub(f'homeassistant/switch/{uid}_p/config', _json.dumps({
                'name': f'{name} Pumpe', 'unique_id': f'{uid}_p',
                'state_topic': f'{base}/ch{i}/pump/state',
                'command_topic': f'{base}/ch{i}/pump/command',
                'payload_on': 'ON', 'payload_off': 'OFF', 'device': dev
            }), retain=True)

        # Geräteweite Sensoren
        self._pub(f'homeassistant/sensor/irrigation_{mac}_water/config', _json.dumps({
            'name': 'Smart Irrigation Wasserstand', 'unique_id': f'irrigation_{mac}_water',
            'state_topic': f'{base}/water_level', 'unit_of_measurement': '%',
            'device_class': 'moisture', 'device': dev
        }), retain=True)
        self._pub(f'homeassistant/sensor/irrigation_{mac}_weather_temp/config', _json.dumps({
            'name': 'Smart Irrigation Außentemperatur', 'unique_id': f'irrigation_{mac}_weather_temp',
            'state_topic': f'{base}/weather/temp', 'unit_of_measurement': '°C',
            'device_class': 'temperature', 'device': dev
        }), retain=True)

    def _pub(self, topic, payload, retain=False):
        if self._client:
            try:
                self._client.publish(topic.encode(),
                    payload.encode() if isinstance(payload, str) else payload,
                    retain=retain)
            except Exception as e:
                self._last_error = str(e)
                self._connected = False

    def publish(self):
        cfg  = self.cfg.as_dict().get('mqtt', {})
        base = cfg.get('base_topic', 'irrigation')
        for i, ch in enumerate(self.irrigation.channels):
            self._pub(f'{base}/ch{i}/moisture', str(ch.moisture_pct))
            self._pub(f'{base}/ch{i}/pump/state', 'ON' if ch.pump_running else 'OFF', retain=True)
        if self.irrigation.water_level_pct >= 0:
            self._pub(f'{base}/water_level', str(self.irrigation.water_level_pct))
        w = self.irrigation.weather
        if w:
            self._pub(f'{base}/weather/temp',     f'{w.get("temp", 0):.1f}')
            self._pub(f'{base}/weather/humidity',  str(w.get('humidity', 0)))
            self._pub(f'{base}/weather/rain_1h',   str(w.get('rain_1h', 0)))
        self._pub(f'{base}/heap', str(__import__('gc').mem_free()))

    async def run(self):
        import asyncio
        while True:
            cfg = self.cfg.as_dict().get('mqtt', {})
            if cfg.get('enabled') and cfg.get('server'):
                try:
                    if not self._connected:
                        self._connect()
                    if self._connected:
                        self._client.check_msg()
                        self.publish()
                except Exception as e:
                    self._last_error = str(e)
                    print(f'MQTT error: {e}')
                    self._connected = False
            await asyncio.sleep(30)
