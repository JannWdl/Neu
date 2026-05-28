"""
weather.py – OpenWeatherMap Integration
"""
import asyncio
import json
import gc
from config import get_config

class Weather:
    def __init__(self, irrigation):
        self.cfg        = get_config()
        self.irrigation = irrigation
        self.data       = {}

    def _https_get(self, host, path):
        import socket, ssl
        addr = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect(addr)
        s = ssl.wrap_socket(s, server_hostname=host)
        req = f'GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n'
        s.write(req.encode())
        raw = b''
        while True:
            chunk = s.read(1024)
            if not chunk:
                break
            raw += chunk
        s.close()
        body = raw.split(b'\r\n\r\n', 1)[1] if b'\r\n\r\n' in raw else raw
        return json.loads(body)

    def update(self):
        cfg = self.cfg.as_dict().get('weather', {})
        if not cfg.get('enabled') or not cfg.get('api_key'):
            return
        key  = cfg['api_key']
        city = cfg.get('city', 'Berlin')
        country = cfg.get('country', 'DE')
        try:
            path = f'/data/2.5/weather?q={city},{country}&appid={key}&units=metric&lang=de'
            d    = self._https_get('api.openweathermap.org', path)
            self.data = {
                'temp': d['main']['temp'],
                'humidity': d['main']['humidity'],
                'rain_1h': d.get('rain', {}).get('1h', 0),
                'description': d['weather'][0]['description'],
                'main': d['weather'][0]['main'],
                'city': city,
            }
            # Regenvorhersage
            path2 = f'/data/2.5/forecast?q={city},{country}&appid={key}&units=metric&cnt=4'
            f2    = self._https_get('api.openweathermap.org', path2)
            rain_forecast = any(
                item.get('rain', {}).get('3h', 0) > 1 or
                item['weather'][0]['main'] in ('Rain', 'Drizzle', 'Thunderstorm')
                for item in f2.get('list', [])
            )
            self.data['rain_forecast'] = rain_forecast
            self.irrigation.weather    = self.data
            print(f'Wetter: {self.data["temp"]:.1f}°C, {self.data["description"]}')
        except Exception as e:
            print(f'Wetter Fehler: {e}')
        gc.collect()

    async def run(self):
        while True:
            self.update()
            await asyncio.sleep(1800)  # alle 30 Minuten
�
