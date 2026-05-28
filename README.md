# 🌱 Smart Irrigation – ESP32 MicroPython

Automatisches Bewässerungssystem für bis zu 8 Kanäle, läuft auf einem ESP32 mit MicroPython v1.28.

---

## Features

- **8 Kanäle** – Kapazitive Feuchtigkeitssensoren + Relais-gesteuerte Pumpen
- **Web-UI** – Responsive Dashboard (mobil & Desktop) unter `http://<ESP32-IP>/`
- **Telegram Bot** – Fernsteuerung, Status-Abfragen, OTA-Updates per `.py`-Datei
- **MQTT / Home Assistant** – Auto-Discovery, Sensor- & Pump-Entities
- **Wetter (OpenWeatherMap)** – Automatischer Regen-Skip, Temperatur-Anpassung
- **Zeitpläne** – Feste Gießzeiten je Kanal und Wochentag
- **OTA-Updates** – via Webinterface, Telegram oder GitHub (`ota.py`)
- **Display** – OLED SSD1306 oder LCD 16×2 (optional)
- **Wasserstand** – HC-SR04 Ultraschall-Sensor (optional)
- **Pflanzendatenbank** – 20 vorkonfigurierte Pflanzen mit Feuchtigkeits-Profilen

---

## Dateien

| Datei | Funktion |
|---|---|
| `boot.py` | WLAN-Verbindung, NTP, Setup-Portal fallback |
| `main.py` | Haupt-Event-Loop, lädt alle Module |
| `config.py` | Konfigurationsverwaltung (`/config.json`) |
| `irrigation.py` | Sensorlogik, Pumpensteuerung, Automatik |
| `webserver.py` | Async HTTP-Server, REST-API |
| `telegram_bot.py` | Telegram Long-Polling Bot |
| `mqtt_client.py` | MQTT + Home Assistant Auto-Discovery |
| `weather.py` | OpenWeatherMap-Integration |
| `ota.py` | OTA-Updates (Web, Telegram, GitHub) |
| `display.py` | OLED/LCD-Display-Unterstützung |
| `plants_db.py` | Pflanzendatenbank |
| `setup_portal.py` | WLAN-Einrichtungs-AP (falls kein WLAN) |

---

## Schnellstart

### 1. MicroPython flashen

```bash
esptool.py --chip esp32 erase_flash
esptool.py --chip esp32 write_flash -z 0x1000 micropython-esp32-v1.28.bin
```

### 2. Dateien hochladen

```bash
mpremote connect /dev/ttyUSB0 cp *.py :
```

Oder mit [Thonny IDE](https://thonny.org/) alle `.py`-Dateien auf den ESP32 kopieren.

### 3. Ersteinrichtung

Beim ersten Start ohne WLAN-Config öffnet der ESP32 einen **Access Point** namens `SmartIrrigation-Setup`. Damit verbinden → Browser → `http://192.168.4.1/` → WLAN-Daten eingeben.

---

## Pinbelegung (Standard)

| Kanal | Sensor-Pin (ADC) | Relais-Pin |
|---|---|---|
| 1 | GPIO 34 | GPIO 16 |
| 2 | GPIO 35 | GPIO 17 |
| 3 | GPIO 32 | GPIO 18 |
| 4 | GPIO 33 | GPIO 19 |
| 5 | GPIO 36 | GPIO 21 |
| 6 | GPIO 39 | GPIO 22 |
| 7 | GPIO 25 | GPIO 23 |
| 8 | GPIO 26 | GPIO 27 |

Relais: **active-low** (Standard). Einstellbar in der Web-UI.

---

## Telegram Bot einrichten

1. Bot bei [@BotFather](https://t.me/botfather) erstellen → Token kopieren
2. Im Web-UI unter **Einstellungen → Telegram**: Token + Chat-ID eintragen
3. Aktivieren → Speichern → Neustart

**Befehle:**

| Befehl | Funktion |
|---|---|
| `/status` | Systemüberblick (IP, RAM, Kanäle) |
| `/feuchte` | Alle Feuchtigkeitswerte |
| `/giessen N [T]` | Kanal N für T Sekunden gießen |
| `/stop N` | Pumpe Kanal N stoppen |
| `/stopall` | Alle Pumpen stoppen |
| `/auto N` | Automode Kanal N umschalten |
| `/wetter` | Aktuelles Wetter |
| `/log` | Letzte Ereignisse |

OTA: Einfach eine `.py`-Datei an den Bot senden → wird direkt übertragen + ESP32 startet neu.

---

## Bekannte Probleme & Changelog

### v3.1 (aktuell)
- **FIX:** Telegram-Token hinterlegt → Webserver nicht mehr erreichbar  
  _Ursache: Blocking HTTPS-Calls in `telegram_bot._api()` blockierten den asyncio Event-Loop._  
  _Lösung: `_api()` gibt mit `await asyncio.sleep(0)` den Loop zwischen den Socket-Calls frei._
- **FIX:** Pumpen-Automatik: fehlende Methoden `_skip_due_to_weather`, `_adjusted_thresh`, `run` in `irrigation.py` ergänzt
- **FIX:** OTA-Stream (`webserver._ota_stream`) war abgeschnitten – Dateiempfang und Speicherung vervollständigt
- **FIX:** WiFi-Zugangsdaten nicht mehr hart im Code hinterlegt

### v3.0
- Initiale Version mit asyncio-Architektur
