# 🌱 Smart Irrigation – ESP32 MicroPython

Automatisches Bewässerungssystem für den ESP32. Konfiguration komplett über die Web-Oberfläche, Steuerung zusätzlich per Telegram und MQTT/Home Assistant.

---

## Funktionsumfang

- **Variabel 1–8 Kanäle** – kapazitive Feuchtigkeitssensoren + Relais-gesteuerte Pumpen
- **Zwei Gießmodi pro Kanal** – zeitbasiert (X Sekunden) oder feuchtigkeitsbasiert (gießt bis Zielfeuchte erreicht ist)
- **Pumpen-Warteschlange** – es läuft immer nur **eine** Pumpe gleichzeitig (wichtig bei 5V-Versorgung über den ESP32)
- **Sicherheits-Limit** – keine Pumpe läuft länger als 120 Sekunden am Stück
- **Web-UI** – Dashboard, Kanal-Einstellungen, Sensor-Kalibrierung, Logs, OTA – alles im Browser
- **Telegram-Bot** – Fernsteuerung + OTA-Update per `.py`-Datei
- **MQTT / Home Assistant** – Auto-Discovery für Sensoren und Pumpen
- **Wetter (OpenWeatherMap)** – pausiert die Bewässerung bei Regen(-vorhersage)
- **Setup-Portal** – AP-Modus zur WLAN-Ersteinrichtung

---

## ⚠️ Wichtig: 5V-Pumpen über VIN

Die Pumpen werden über den **VIN-Pin** versorgt (5V direkt von der USB-Buchse, vor dem Spannungsregler):

- Besser als VCC/3V3, da der 3.3V-Regler nicht belastet wird.
- Strom kommt aber weiterhin über USB-Kabel + Buchse + VIN-Diode des Boards (oft ~500 mA–1 A belastbar).
- Mit einem kräftigen **2 A USB-Netzteil** läuft eine Pumpe problemlos.
- Deshalb läuft systemseitig **nur eine Pumpe gleichzeitig** (Warteschlange), Gießdauer hart auf **120 s** begrenzt.
- **Für mehrere Pumpen gleichzeitig:** separates 5V-Netzteil für die Pumpen, ESP32 schaltet nur die Relais (gemeinsame Masse verbinden).

### Relais-Typ

Die meisten günstigen Relais-Module sind **active-LOW** (Pin LOW = Relais an). Das ist der Standard. Falls eine Pumpe direkt beim Einschalten losläuft, ist es vermutlich active-HIGH – das lässt sich pro Kanal in der Konfiguration umstellen (`relay_active_low`).

---

## Installation

### Voraussetzungen
- ESP32 mit MicroPython (v1.20+)
- Am PC: `pip install mpremote`

### Dateien übertragen

1. `install.py` und `smart-irrigation.zip` in denselben Ordner legen
2. Ausführen:
   ```bash
   python install.py COM8        # Windows
   python install.py /dev/ttyUSB0  # Linux/Mac
   ```
3. Der Installer setzt den ESP32 zurück, überträgt alle Dateien und startet neu.

### Ersteinrichtung (WLAN)

Beim ersten Start ohne WLAN-Konfiguration öffnet der ESP32 einen Access Point:

- **SSID:** `SmartIrrigation-Setup`
- Verbinden → Browser → `http://192.168.4.1/`
- WLAN-Daten eingeben → speichern → ESP32 startet neu und verbindet sich

Danach ist die Oberfläche unter `http://smart-irrigation.local/` (oder der IP aus dem Serial-Monitor) erreichbar.

### Setup-Assistent

Beim allerersten Aufruf der Web-Oberfläche startet automatisch ein **Setup-Assistent**, der dich Schritt für Schritt durch die Einrichtung führt:

1. Anzahl der Kanäle festlegen
2. Jeden Kanal einzeln: Name, Sensor-/Relais-Pin, Relais-Typ, **Live-Kalibrierung** (Sensor in Luft → „Trocken", in Wasser → „Nass", der aktuelle Messwert wird in Echtzeit angezeigt), Gießmodus
3. Zusatzmodule auswählen (Telegram, MQTT, Wetter, DHT-Sensor)
4. Fertig – Zugangsdaten der Module danach unter Einstellungen ergänzen

Der Assistent lässt sich jederzeit unter **Einstellungen → System → Setup-Assistent erneut starten** aufrufen.

---

## Bedienung

### Web-UI
- **Dashboard** – alle Kanäle auf einen Blick, anklicken zum Gießen/Stoppen
- **Kanäle** – pro Kanal: Name, Aktiv, Automatik, Gießmodus, Dauer/Zielfeuchte, Schwelle, Pause, Sensor-Kalibrierung
- **Einstellungen** – WLAN, Telegram, MQTT, Wetter, System, OTA-Upload
- **Log** – Ereignisse und Feuchtigkeitsverlauf je Kanal

### Sensor kalibrieren
1. Sensor in die Luft halten → **Trocken** drücken
2. Sensor in Wasser tauchen → **Nass** drücken

Erst danach zeigt der Kanal sinnvolle Prozentwerte.

### Telegram
Bot bei [@BotFather](https://t.me/botfather) anlegen, Token + Chat-ID in den Einstellungen eintragen, aktivieren.

| Befehl | Funktion |
|---|---|
| `/status` | Überblick |
| `/feuchte` | Feuchtigkeitswerte |
| `/giessen N [T]` | Kanal N für T Sekunden gießen |
| `/stop N` · `/stopall` | Pumpe(n) stoppen |
| `/auto N` | Automatik umschalten |
| `/wetter` · `/log` | Wetter / Ereignisse |

OTA: `.py`-Datei an den Bot senden → wird übertragen, ESP32 startet neu.

---

## Standard-Pinbelegung

| Kanal | Sensor (ADC) | Relais |
|---|---|---|
| 1–8 | 34, 35, 32, 33, 36, 39, 25, 26 | 16, 17, 18, 19, 21, 22, 23, 27 |

Anpassbar in `config.py` (`SENSOR_PINS` / `RELAY_PINS`). ADC-Pins müssen ADC1-fähig sein (GPIO 32–39), da ADC2 bei aktivem WLAN nicht nutzbar ist.

---

## Dateien

| Datei | Funktion |
|---|---|
| `boot.py` | WLAN, NTP, Setup-Portal-Fallback |
| `main.py` | Event-Loop, lädt aktive Module |
| `config.py` | Konfiguration (`/config.json`) |
| `irrigation.py` | Sensoren, Pumpen-Queue, Automatik, Logs |
| `webserver.py` | Async HTTP-Server + REST-API |
| `index.html` | Web-Oberfläche (vom Flash gestreamt) |
| `telegram_bot.py` | Telegram-Bot |
| `mqtt_client.py` | MQTT + Home Assistant |
| `weather.py` | OpenWeatherMap |
| `ota.py` | OTA-Updates |
| `display.py` | OLED/LCD (optional) |
| `plants_db.py` | Pflanzendatenbank |
| `setup_portal.py` | WLAN-Einrichtungs-AP |
| `install.py` | PC-Installer (mpremote) |

---

## Erweiterte Funktionen

### Zeitpläne
Reiter **Zeitplan** im Web-UI. Pro Eintrag: Kanal, Uhrzeit, Dauer und Wochentage. Läuft zusätzlich zur Feuchtigkeits-Automatik; Frostschutz greift auch hier.

### Verbrauchs-Statistik
Reiter **Statistik**: Gießvorgänge und Gesamtlaufzeit je Kanal. Wenn du die **Fördermenge** deiner Pumpe (ml/min) im Kanal hinterlegst, wird zusätzlich die Wassermenge in Litern geschätzt.

### Frostschutz
Nutzt die Wetterdaten. Unter der Frost-Schwelle (Standard 4 °C) wird nicht gegossen – egal ob Automatik oder Zeitplan. Aktivierbar unter Einstellungen → Wetter.

### Dünger-Erinnerung
Pro Kanal ein Intervall in Tagen einstellbar. Ist es fällig, kommt eine Telegram-Nachricht. Mit „Jetzt als gedüngt markieren" (UI) oder `/duengen N` (Telegram) zurücksetzen.

### Lokaler Temperatursensor (DHT22/DHT11)
Optionaler DHT-Sensor für lokale Temperatur/Luftfeuchte (ergänzt die Wetter-API). Pin in den Einstellungen festlegen.

### Benachrichtigungen (Telegram)
Automatische Push-Nachrichten bei: leerem Tank, Frostschutz aktiv, Dünger fällig. Einzeln in der `notify`-Konfiguration abschaltbar.

---

## Sprachsteuerung & E-Mail (über Home Assistant)

Der ESP32 kann Alexa/Google und zuverlässiges E-Mailing nicht sinnvoll selbst – das läuft sauberer über Home Assistant, das du via MQTT ohnehin anbinden kannst:

- **MQTT aktivieren** (Einstellungen → MQTT) mit den Daten deines HA-MQTT-Brokers.
- Die Kanäle erscheinen per **Auto-Discovery** automatisch in Home Assistant (Sensoren + Pumpen-Schalter).
- **Alexa/Google:** In HA die Cloud-Integration (Nabu Casa) oder die jeweilige Skill/Action einrichten – die Entities sind dann sprachsteuerbar („Alexa, schalte Kanal 1 ein").
- **E-Mail-Reports:** Eine HA-Automatisierung mit dem `notify.smtp`-Dienst auf Basis der MQTT-Sensoren bauen. Das ist robuster als SMTP direkt auf dem ESP32.

---

## Changelog

### v5.0
- Zeitpläne (feste Gießzeiten je Kanal/Wochentag)
- Verbrauchs-Statistik (Laufzeit, optional Liter)
- Frostschutz auf Basis der Wetterdaten
- Dünger-Erinnerung pro Kanal
- Telegram-Benachrichtigungen (Tank, Frost, Dünger)
- Lokaler DHT22/DHT11-Sensor
- Doku: Alexa/Google & E-Mail über Home Assistant
- Komplett-Installer (Flash + Upload in einem Skript)

### v4.0
- Pumpen-Warteschlange: nur eine Pumpe gleichzeitig
- Hartes Laufzeit-Limit (120 s) pro Gießvorgang
- Zwei Gießmodi pro Kanal (zeit-/feuchtigkeitsbasiert)
- Komplett überarbeitete Web-Oberfläche
- Setup-Portal als echtes HTML-Formular
- Fix: Telegram-Token blockierte Webserver nicht mehr
