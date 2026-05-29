# 🌱 Smart Irrigation für ESP32

**Smart Irrigation** ist ein MicroPython-Projekt für den ESP32, mit dem sich bis zu acht Pflanzen- oder Bewässerungskanäle automatisch steuern lassen. Die Einrichtung läuft über eine Weboberfläche, zusätzlich sind Telegram, MQTT/Home Assistant, Wetterdaten, Zeitpläne, OTA-Updates und lokale Tests möglich.

Das Projekt richtet sich an Bastler, Schüler, Azubis und alle, die Pflanzen nicht mehr nach Bauchgefühl ertränken wollen. Technik übernimmt hier also endlich mal eine nützliche Aufgabe.

---

## ✨ Funktionen

- **ESP32 + MicroPython** als kompakte Steuerzentrale
- **1 bis 8 Bewässerungskanäle** mit kapazitiven Feuchtigkeitssensoren und Relais/Pumpen
- **Web-Dashboard** für Status, manuelles Gießen, Einstellungen, Logs, Kalibrierung und OTA
- **Setup-Assistent** für die erste Einrichtung direkt im Browser
- **WLAN-Setup-Portal** über eigenen Access Point `SmartIrrigation-Setup`
- **Sensor-Kalibrierung** pro Kanal mit Live-Rohwerten
- **Zwei Gießmodi**:
  - zeitbasiert: Pumpe läuft X Sekunden
  - feuchtigkeitsbasiert: Pumpe läuft bis zur Ziel-Feuchte
- **Pumpen-Warteschlange**: Es läuft immer nur eine Pumpe gleichzeitig
- **Sicherheitslimit**: Maximale Pumpenlaufzeit pro Vorgang
- **Zeitpläne** für feste Bewässerungszeiten
- **Statistik** für Laufzeit, Gießvorgänge und geschätzte Wassermenge
- **Telegram-Bot** für Status, Steuerung und OTA per `.py`-Datei
- **MQTT/Home Assistant** inklusive Auto-Discovery
- **OpenWeatherMap-Integration** für Regenpause und Frostschutz
- **DHT11/DHT22-Unterstützung** für lokale Temperatur/Luftfeuchte
- **Lokaler Testserver** zum Prüfen der Weboberfläche ohne ESP32

---

## 🧰 Projektdateien

| Datei | Zweck |
|---|---|
| `boot.py` | WLAN-Verbindung, NTP-Sync und Setup-Portal-Fallback |
| `main.py` | Hauptprogramm und Task-Start für Webserver, Bewässerung, MQTT, Telegram usw. |
| `config.py` | Konfiguration, Defaults und Speicherung in `/config.json` |
| `irrigation.py` | Kernlogik für Sensoren, Pumpen, Automatik, Logs und Sicherheitslogik |
| `webserver.py` | Async HTTP-Server mit Weboberfläche und REST-API |
| `index.html` | Web-Dashboard und Setup-Assistent |
| `setup_portal.py` | WLAN-Ersteinrichtung im AP-Modus |
| `plants_db.py` | Pflanzendatenbank und Feuchte-Vorgaben |
| `telegram_bot.py` | Telegram-Steuerung und OTA-Dateiupload |
| `mqtt_client.py` | MQTT und Home-Assistant-Discovery |
| `weather.py` | OpenWeatherMap-Abfrage |
| `ota.py` | OTA-Updatefunktionen |
| `display.py` | Optionale Display-Anbindung |
| `install.py` | PC-Installer zum Flashen und Datei-Upload |
| `local_test_server.py` | Lokaler Mock-Server für Browser-Tests ohne ESP32 |
| `smart-irrigation.zip` | Paket mit den ESP32-Projektdateien für den Installer |

---

## ✅ Voraussetzungen

### Hardware

- ESP32, empfohlen: ESP32-WROOM
- Kapazitive Bodenfeuchtigkeitssensoren
- Relaismodul(e), typischerweise active-low
- 5V-Pumpen oder Ventile
- Geeignete 5V-Stromversorgung
- Optional:
  - DHT11/DHT22
  - Ultraschallsensor für Tankfüllstand
  - OLED/LCD-Display

### Software am PC

- Python 3.10 oder neuer
- Internetzugang für den Firmware-Download
- USB-Treiber für den ESP32, falls Windows wieder Windows-Dinge tut

Der Installer prüft und installiert bei Bedarf:

```bash
pip install esptool mpremote
```

---

## ⚠️ Stromversorgung und Sicherheit

Das Projekt ist für kleine 5V-Pumpen ausgelegt. Der ESP32 ist kein Kraftwerk, auch wenn manche Bastelshops das gern so aussehen lassen.

Wichtig:

- Pumpen nicht über den 3,3V-Pin betreiben.
- Kleine 5V-Pumpen können über VIN/5V versorgt werden, sofern Netzteil, Kabel und Board das schaffen.
- Für mehrere oder stärkere Pumpen ein separates 5V-Netzteil verwenden.
- GND von ESP32 und externem Pumpennetzteil verbinden.
- Relaiskontakte sauber trennen und korrekt anschließen.
- Wasser und Elektronik räumlich trennen.
- Das System ist ein DIY-Projekt und keine zertifizierte Sicherheitssteuerung.

Softwareseitig läuft immer nur eine Pumpe gleichzeitig. Dadurch wird die Stromlast reduziert und der ESP32 nicht komplett ins Elend geschickt.

---

## 🚀 Installation auf dem ESP32

### 1. Repository herunterladen

```bash
git clone https://github.com/<user>/<repo>.git
cd <repo>
```

Oder das ZIP von GitHub herunterladen und entpacken.

### 2. ESP32 per USB anschließen

Unter Windows ist der Port meist z. B. `COM8`, unter Linux/macOS meist `/dev/ttyUSB0` oder `/dev/ttyACM0`.

### 3. Installer starten

Windows:

```bash
python install.py COM8
```

Linux/macOS:

```bash
python install.py /dev/ttyUSB0
```

Der Installer erledigt in einem Durchgang:

1. Prüfen/Installieren von `esptool` und `mpremote`
2. Download der passenden MicroPython-Firmware
3. Löschen des ESP32-Flashs
4. Flashen von MicroPython
5. Übertragen der Projektdateien aus `smart-irrigation.zip`

### Nur Dateien neu übertragen

Wenn MicroPython schon installiert ist:

```bash
python install.py COM8 --skip-flash
```

### Lokale Firmware verwenden

```bash
python install.py COM8 --bin firmware.bin
```

---

## 📶 Ersteinrichtung per WLAN-Setup

Wenn noch keine WLAN-Daten gespeichert sind, startet der ESP32 einen eigenen Access Point:

```text
SSID: SmartIrrigation-Setup
Adresse: http://192.168.4.1/
```

Ablauf:

1. Mit dem WLAN `SmartIrrigation-Setup` verbinden.
2. Browser öffnen: `http://192.168.4.1/`
3. WLAN-SSID und Passwort eintragen.
4. Speichern.
5. ESP32 startet neu und verbindet sich mit dem WLAN.

Danach ist die Oberfläche erreichbar über:

```text
http://smart-irrigation.local/
```

Falls mDNS nicht aufgelöst wird, die IP-Adresse aus dem seriellen Monitor verwenden. Weil Namensauflösung natürlich genau dann versagt, wenn man sie zeigen will.

---

## 🖥️ Weboberfläche

Die Weboberfläche läuft direkt auf dem ESP32 und wird aus `index.html` gestreamt.

Bereiche:

- **Dashboard**: Status, Feuchtigkeit, Pumpen, WLAN, Speicher
- **Kanäle**: Pins, Namen, Modi, Auto-Bewässerung und Kalibrierung
- **Zeitplan**: feste Gießzeiten pro Kanal
- **Statistik**: Gießvorgänge, Laufzeiten und geschätzter Verbrauch
- **Logs**: Ereignisse und Messwerte
- **Einstellungen**: WLAN, Telegram, MQTT, Wetter, System und OTA

---

## 🌿 Kanal-Kalibrierung

Jeder Feuchtigkeitssensor muss kalibriert werden.

1. Sensor trocken/in Luft halten.
2. In der Oberfläche **Trocken** übernehmen.
3. Sensor in Wasser oder sehr feuchte Erde halten.
4. **Nass** übernehmen.
5. Kanal speichern.

Ohne Kalibrierung sind Prozentwerte nur dekorative Zahlen mit Selbstbewusstsein.

---

## 🤖 Telegram-Bot

Telegram ist optional.

Einrichtung:

1. Bei Telegram `@BotFather` öffnen.
2. Neuen Bot erstellen.
3. Bot-Token in der Weboberfläche eintragen.
4. Eigene Chat-ID eintragen.
5. Telegram aktivieren und speichern.

Befehle:

| Befehl | Funktion |
|---|---|
| `/start` oder `/info` | Hilfe anzeigen |
| `/status` | Systemstatus anzeigen |
| `/feuchte` | Feuchtigkeitswerte anzeigen |
| `/wetter` | Wetterstatus anzeigen |
| `/giessen N [T]` | Kanal N optional T Sekunden gießen |
| `/stop N` | Kanal N stoppen |
| `/stopall` | Alle Pumpen stoppen |
| `/auto N` | Automatik für Kanal N umschalten |
| `/stats` | Verbrauchsstatistik anzeigen |
| `/duengen N` | Kanal N als gedüngt markieren |
| `/log` | Letzte Ereignisse anzeigen |

OTA per Telegram:

- Eine `.py`-Datei an den Bot senden.
- Datei wird auf den ESP32 übertragen.
- ESP32 startet anschließend neu.

---

## 🏠 MQTT und Home Assistant

Das Projekt kann per MQTT mit Home Assistant verbunden werden.

Standard-Basis-Topic:

```text
irrigation
```

Beispiele:

```text
irrigation/ch0/moisture
irrigation/ch0/pump/state
irrigation/ch0/pump/command
irrigation/water_level
irrigation/weather/temp
```

Home Assistant Discovery wird automatisch veröffentlicht, sofern MQTT aktiviert und korrekt konfiguriert ist.

Pumpensteuerung per MQTT:

```text
Topic: irrigation/ch0/pump/command
Payload: ON oder OFF
```

---

## 🌦️ Wetter, Regenpause und Frostschutz

Über OpenWeatherMap kann das System Wetterdaten abrufen.

Funktionen:

- aktuelle Temperatur
- Luftfeuchtigkeit
- Regen der letzten Stunde
- Regenvorhersage
- automatische Bewässerungspause bei Regen
- Frostschutz unter einstellbarer Temperaturgrenze

Benötigt wird ein API-Key von OpenWeatherMap.

---

## 🧪 Lokal ohne ESP32 testen

Die Weboberfläche kann teilweise lokal getestet werden.

```bash
python local_test_server.py
```

Danach im Browser öffnen:

```text
http://127.0.0.1:8080/
```

Damit testbar:

- Laden der Weboberfläche
- Setup-Assistent
- Dashboard-Navigation
- Speichern von Konfigurationen
- API-Aufrufe gegen Mock-Daten

Nicht testbar ohne ESP32:

- echte ADC-Sensorwerte
- Pumpen/Relais
- WLAN-AP-Modus
- MicroPython-spezifische Speichergrenzen

---

## 🔌 REST-API

Auszug der wichtigsten Endpunkte:

| Methode | Pfad | Funktion |
|---|---|---|
| `GET` | `/` oder `/index.html` | Weboberfläche |
| `GET` | `/api/status` | Systemstatus |
| `GET` | `/api/config` | Konfiguration lesen |
| `POST` | `/api/config` | Konfiguration speichern |
| `GET/POST` | `/api/water/<id>` | Kanal starten |
| `GET/POST` | `/api/stop/<id>` | Kanal stoppen |
| `GET/POST` | `/api/stopall` | Alle Pumpen stoppen |
| `GET` | `/api/logs?ch=0&limit=30` | Messwerte eines Kanals |
| `GET` | `/api/events` | Ereignislog |
| `GET` | `/api/stats` | Statistik |
| `GET` | `/api/raw/<id>` | Live-ADC-Wert für Kalibrierung |
| `GET` | `/api/schedule` | Zeitplan lesen |
| `POST` | `/api/schedule` | Zeitplan speichern |
| `POST` | `/api/ota/upload` | OTA-Dateiupload |
| `GET/POST` | `/api/reboot` | ESP32 neu starten |

---

## 🛠️ Troubleshooting

### ESP32 wird nicht gefunden

- Richtigen COM-Port prüfen.
- USB-Kabel tauschen, manche Kabel laden nur und übertragen keine Daten.
- Treiber für CH340/CP210x installieren.
- Beim Flashen ggf. BOOT-Taste gedrückt halten.

### Weboberfläche lädt nicht

- IP-Adresse im Serial-Monitor prüfen.
- `http://smart-irrigation.local/` nur nutzen, wenn mDNS funktioniert.
- Alternativ direkt per IP öffnen.

### Buttons reagieren nicht

- Browser-Konsole öffnen.
- Netzwerk-Tab prüfen.
- Fehler bei `/api/config` deuten meist auf ein API-/JSON-Problem hin.
- Nach Änderungen Dateien neu übertragen:

```bash
python install.py COM8 --skip-flash
```

### `undefined dBm` oder `NaN kB`

Bei lokalem Testserver fehlen dann Mock-Werte für `rssi` oder `heap`. Auf dem ESP32 sollten diese Werte aus `/api/status` kommen.

### Sensorwerte sind falsch herum

Trocken-/Nass-Kalibrierung prüfen. Kapazitive Sensoren liefern je nach Modell unterschiedliche Rohwerte. Willkommen in der Welt billiger Sensoren, wo Standards eher eine grobe Idee sind.

### Pumpe läuft direkt beim Start

Relais-Typ prüfen:

- active-low: LOW = an
- active-high: HIGH = an

In der Kanalkonfiguration `relay_active_low` passend setzen.

---

## 🧱 Roadmap-Ideen

- Import/Export der Konfiguration
- Mehrsprachige Oberfläche
- Diagramme für Feuchtigkeitsverlauf
- Bessere OTA-Versionierung
- Optionale Authentifizierung für die Weboberfläche
- Docker-basierter lokaler Testmodus
- Gehäuse- und Verdrahtungsdokumentation mit Bildern

---

## 📄 Lizenz

Noch keine Lizenz festgelegt. Für GitHub wäre z. B. MIT sinnvoll, wenn das Projekt offen weiterverwendet werden darf.

---

## Haftungsausschluss

Dieses Projekt schaltet Wasser, Strom und Elektronik. Prüfe Verdrahtung, Netzteile und Relais sorgfältig. Der Einsatz erfolgt auf eigenes Risiko. Das System ist nicht für sicherheitskritische Anwendungen geeignet.
