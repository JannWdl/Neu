"""
weather.py – OpenWeatherMap Integration
- Aktuelles Wetter + kleine Übersicht für Dashboard und Telegram
- Status/Fehler werden im Irrigation-Objekt abgelegt
"""
import asyncio
import json
import gc
import time
from config import get_config


def _url_part(v):
    """Mini-URL-Encoding für ESP32: reicht für Städtenamen mit Leerzeichen."""
    return str(v or '').replace(' ', '%20')


class Weather:
    def __init__(self, irrigation):
        self.cfg        = get_config()
        self.irrigation = irrigation
        self.data       = {}

    def _https_get(self, host, path):
        import socket, ssl
        addr = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(12)
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
            self.irrigation.weather_status = {
                'configured': False, 'ok': False,
                'err': 'Wetter ist nicht aktiviert oder es fehlt der API-Key.'
            }
            return None

        key     = cfg.get('api_key', '')
        city    = cfg.get('city', 'Berlin')
        country = cfg.get('country', 'DE')
        try:
            q = _url_part(city) + ',' + _url_part(country)
            path = f'/data/2.5/weather?q={q}&appid={key}&units=metric&lang=de'
            d    = self._https_get('api.openweathermap.org', path)
            if str(d.get('cod')) not in ('200', 'None') and d.get('cod') != 200:
                raise Exception(d.get('message', 'OpenWeatherMap Fehler'))

            data = {
                'temp': d['main']['temp'],
                'feels_like': d.get('main', {}).get('feels_like'),
                'humidity': d['main']['humidity'],
                'pressure': d.get('main', {}).get('pressure'),
                'wind': d.get('wind', {}).get('speed', 0),
                'rain_1h': d.get('rain', {}).get('1h', 0),
                'description': d['weather'][0]['description'],
                'main': d['weather'][0]['main'],
                'city': city,
                'country': country,
                'updated': int(time.time())
            }

            # Kleine Vorhersage für die nächsten Einträge. Bewusst klein halten, RAM ist kein Wunschkonzert.
            path2 = f'/data/2.5/forecast?q={q}&appid={key}&units=metric&cnt=4&lang=de'
            f2    = self._https_get('api.openweathermap.org', path2)
            forecast = []
            rain_forecast = False
            for item in f2.get('list', []):
                rain = item.get('rain', {}).get('3h', 0)
                main = item.get('weather', [{}])[0].get('main', '')
                desc = item.get('weather', [{}])[0].get('description', '')
                if rain > 1 or main in ('Rain', 'Drizzle', 'Thunderstorm'):
                    rain_forecast = True
                forecast.append({
                    'dt_txt': item.get('dt_txt', ''),
                    'temp': item.get('main', {}).get('temp'),
                    'rain_3h': rain,
                    'description': desc,
                    'main': main
                })

            data['rain_forecast'] = rain_forecast
            data['forecast'] = forecast
            frost_thr = cfg.get('frost_threshold', 4.0)
            data['frost'] = data['temp'] <= frost_thr

            self.data = data
            self.irrigation.weather = data
            self.irrigation.weather_status = {
                'configured': True, 'ok': True, 'err': '', 'updated': data['updated']
            }
            print(f'Wetter: {data["temp"]:.1f}°C, {data["description"]}')
            return data
        except Exception as e:
            err = str(e)
            print(f'Wetter Fehler: {err}')
            self.irrigation.weather_status = {
                'configured': True, 'ok': False, 'err': err, 'updated': int(time.time())
            }
            return None
        finally:
            gc.collect()

    async def run(self):
        while True:
            self.update()
            await asyncio.sleep(1800)  # alle 30 Minuten
