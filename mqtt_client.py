"""
mqtt_client.py – MQTT + Home Assistant Auto-Discovery
"""
class MQTTClient:
    def __init__(self, irrigation):
        self.cfg        = get_config()
        self.irrigation = irrigation
        self._client    = None
        self._connected = False

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
        # Pump-Kommandos abonnieren
        base = cfg.get('base_topic', 'irrigation')
        for i in range(len(self.irrigation.channels)):
            c.subscribe(f'{base}/ch{i}/pump/command'.encode())
        self._client    = c
        self._connected = True
        self._ha_discovery(base)
        print('MQTT verbunden')

    def _on_message(self, topic, msg):
        topic = topic.decode()
        msg   = msg.decode().upper()
        base  = self.cfg.get('mqtt.base_topic', 'irrigation')
        for i, ch in enumerate(self.irrigation.channels):
            if topic == f'{base}/ch{i}/pump/command':
                if msg == 'ON':  ch.start_pump()
                if msg == 'OFF': ch.stop_pump()

    def _ha_discovery(self, base):
        import network, json as _json
        mac = ''.join(f'{b:02x}' for b in network.WLAN(network.STA_IF).config('mac'))
        dev = {'identifiers': [f'irrigation_{mac}'], 'name': 'Smart Irrigation',
               'model': 'ESP32 MicroPython v3', 'manufacturer': 'DIY'}
        for i, ch in enumerate(self.irrigation.channels):
            name = ch.cfg.get('name', f'Kanal {i+1}')
            uid  = f'irrigation_{mac}_ch{i}'
            # Moisture sensor
            self._pub(f'homeassistant/sensor/{uid}_m/config', _json.dumps({
                'name': f'{name} Feuchtigkeit', 'unique_id': f'{uid}_m',
                'state_topic': f'{base}/ch{i}/moisture',
                'unit_of_measurement': '%', 'device_class': 'moisture',
                'device': dev
            }), retain=True)
            # Pump switch
            self._pub(f'homeassistant/switch/{uid}_p/config', _json.dumps({
                'name': f'{name} Pumpe', 'unique_id': f'{uid}_p',
                'state_topic': f'{base}/ch{i}/pump/state',
                'command_topic': f'{base}/ch{i}/pump/command',
                'payload_on': 'ON', 'payload_off': 'OFF', 'device': dev
            }), retain=True)

    def _pub(self, topic, payload, retain=False):
        if self._client:
            try:
                self._client.publish(topic.encode(),
                    payload.encode() if isinstance(payload, str) else payload,
                    retain=retain)
            except Exception:
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
                    print(f'MQTT error: {e}')
                    self._connected = False
            await asyncio.sleep(30)
