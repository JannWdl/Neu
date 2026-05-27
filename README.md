<div align="center">

# 🌱 Smart Irrigation v2.0

**Vollautomatische ESP32-Bewässerungsanlage**  
Telegram · Home Assistant · MQTT · OTA · Web-Interface · Pflanzendatenbank

[![Platform](https://img.shields.io/badge/Platform-ESP32-blue?logo=espressif)](https://www.espressif.com/)
[![Arduino](https://img.shields.io/badge/IDE-Arduino-teal?logo=arduino)](https://www.arduino.cc/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.0-orange)]()
[![Channels](https://img.shields.io/badge/Kanäle-1–8-purple)]()

</div>

---

## 📋 Inhaltsverzeichnis

- [Features](#-features)
- [Hardware](#-hardware)
- [Verkabelung](#-verkabelung)
- [Installation](#-installation)
- [Konfiguration](#-konfiguration)
- [Web-Interface](#-web-interface)
- [OTA-Updates](#-ota-updates)
- [Telegram-Bot](#-telegram-bot)
- [Home Assistant / MQTT](#-home-assistant--mqtt)
- [Pflanzendatenbank](#-pflanzendatenbank)
- [Fehlerbehebung](#-fehlerbehebung)
- [Lizenz](#-lizenz)

---

## ✨ Features

| Feature | Beschreibung |
|---|---|
| 🌡️ **Bodenfeuchte** | Kapazitive Sensoren (1–8 Kanäle), Mehrfach-Mittelung, Kalibrierungs-Wizard |
| 💧 **Automatische Bewässerung** | Schwellwert-basiert, Mindestabstand, Pflanzen-Profil |
| 🌦️ **Wetter-Integration** | OpenWeatherMap: Regen-Skip, Hitze-/Kälteanpassung |
| 🤖 **Telegram-Bot** | Status, manuelle Steuerung, OTA-Update per Datei-Upload |
| 🏠 **Home Assistant** | MQTT Auto-Discovery (Sensoren + Schalter) |
| 🌐 **Web-Interface** | Dark-Theme, Live-Dashboard, Statistik-Charts, OTA |
| 📊 **Daten-Logging** | SPIFFS-Verlauf, 24h/7d/30d-Ansicht, Ereignis-Log |
| 🔄 **OTA-Updates** | Arduino IDE, Web-Upload, Telegram-Bot |
| 💦 **Wasserstand** | Optional: HC-SR04 Ultraschall, Alarm bei Leerstand |
| 🖥️ **Display** | Optional: OLED / LCD I2C / TFT (Compile-Time-Flag) |
| 💾 **NVS-Speicherung** | Alle Einstellungen überstehen Neustarts (Preferences) |

---

## 🔧 Hardware

### Pflichtkomponenten
| Komponente | Menge | Hinweis |
|---|---|---|
| ESP32 Dev Board (38-Pin) | 1× | Empfohlen: AZ-Delivery ESP32 |
| Kapazitiver Bodenfeuchtigkeitssensor v2.0 | 1–8× | Im AEDIKO-Kit enthalten |
| 1-Kanal 5V Relaismodul | 1–8× | Im AEDIKO-Kit enthalten |
| Wasserpumpe 5V | 1–8× | Im AEDIKO-Kit enthalten |
| Vinylschlauch 6mm | 1–8× | Im AEDIKO-Kit enthalten |
| Netzteil 5V / mind. 2A | 1× | Pro Pumpe ~500mA einplanen |

### Optionale Komponenten
| Komponente | Zweck | Flag |
|---|---|---|
| HC-SR04 Ultraschall | Wasserstand-Sensor | `water_level_enabled` |
| OLED SSD1306 128×64 (I2C) | Display | `DISPLAY_TYPE 1` |
| LCD 16×2 (I2C) | Display | `DISPLAY_TYPE 2` |
| TFT ILI9341 / ST7789 | Display | `DISPLAY_TYPE 3` |

---

## 🔌 Verkabelung

### Pinbelegung ESP32

```
╔════════════════════════════════════════════════════════╗
║                     ESP32 Dev Board                    ║
║                                                        ║
║  3.3V ──── Sensor VCC (alle Kanäle)                   ║
║  GND  ──── Sensor GND, Relais GND (gemeinsam!)        ║
║                                                        ║
║  GPIO34 ── Sensor AOUT  Kanal 1  (ADC1_CH6)          ║
║  GPIO35 ── Sensor AOUT  Kanal 2  (ADC1_CH7)          ║
║  GPIO32 ── Sensor AOUT  Kanal 3  (ADC1_CH4)          ║
║  GPIO33 ── Sensor AOUT  Kanal 4  (ADC1_CH5)          ║
║  GPIO36 ── Sensor AOUT  Kanal 5  (ADC1_CH0, nur IN)  ║
║  GPIO39 ── Sensor AOUT  Kanal 6  (ADC1_CH3, nur IN)  ║
║  GPIO25 ── Sensor AOUT  Kanal 7  (ADC1_CH8)          ║
║  GPIO26 ── Sensor AOUT  Kanal 8  (ADC1_CH9)          ║
║                                                        ║
║  GPIO16 ── Relais IN   Kanal 1                        ║
║  GPIO17 ── Relais IN   Kanal 2                        ║
║  GPIO18 ── Relais IN   Kanal 3                        ║
║  GPIO19 ── Relais IN   Kanal 4                        ║
║  GPIO21 ── Relais IN   Kanal 5  (auch SDA!)           ║
║  GPIO22 ── Relais IN   Kanal 6  (auch SCL!)           ║
║  GPIO23 ── Relais IN   Kanal 7                        ║
║  GPIO27 ── Relais IN   Kanal 8                        ║
║                                                        ║
║  GPIO21 ── SDA (OLED / LCD)                           ║
║  GPIO22 ── SCL (OLED / LCD)                           ║
║                                                        ║
║  GPIO12 ── HC-SR04 TRIG (Wasserstand, optional)       ║
║  GPIO14 ── HC-SR04 ECHO (Wasserstand, optional)       ║
╚════════════════════════════════════════════════════════╝
```

> ⚠️ **Wichtig:** Nur ADC1-Pins (34, 35, 32, 33, 36, 39, 25, 26) verwenden!  
> ADC2 ist bei aktivem WiFi **nicht verfügbar**.

> ⚠️ Bei mehr als 4 Kanälen überschneiden sich Relais-Pins mit I2C (GPIO21/22).  
> In diesem Fall Display auf andere I2C-Pins oder SPI wechseln.

### Schaltplan (1 Kanal)

```
5V-Netzteil (+) ──┬──────────────────────── Relais VCC
                  │
                  └── Relais NO-Klemme ─── Pumpe (+) ─── Pumpe (−) ─┐
                                                                       │
5V-Netzteil (−) ──────────────────────────────────────────────────────┘
                  │
                  └──────────────────────── Relais GND
                                            │
ESP32 GND ────────────────────────────── GND (gemeinsam!)

ESP32 GPIO16 ────────────────────────── Relais IN
ESP32 GPIO34 ────────────────────────── Sensor AOUT
ESP32 3.3V  ────────────────────────── Sensor VCC
ESP32 GND   ────────────────────────── Sensor GND
```

### Wasserstand-Sensor (optional)

```
HC-SR04 VCC  → 5V
HC-SR04 GND  → GND
HC-SR04 TRIG → GPIO12
HC-SR04 ECHO → [Spannungsteiler 1kΩ/2kΩ] → GPIO14
```
> ⚠️ ECHO gibt 5V aus — Spannungsteiler oder Pegelwandler auf 3.3V verwenden!

---

## 🛠️ Installation

### 1. Arduino IDE einrichten

```
Datei → Voreinstellungen → Zusätzliche Boardverwalter-URLs:
https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json
```

Board-Einstellungen:
```
Board:            ESP32 Dev Module
Flash Size:       4MB
Partition Scheme: Default 4MB with spiffs
Upload Speed:     921600
```

### 2. Libraries installieren

```
Werkzeuge → Bibliotheken verwalten → suchen:
```

| Library | Autor | Version |
|---|---|---|
| ESPAsyncWebServer | me-no-dev | latest |
| AsyncTCP | me-no-dev | latest |
| ArduinoJson | Benoit Blanchon | **6.x** |
| PubSubClient | Nick O'Leary | latest |
| UniversalTelegramBot | Brian Lough | latest |

Optional (je nach `DISPLAY_TYPE`):
```
Adafruit SSD1306      → DISPLAY_TYPE 1
Adafruit GFX Library  → DISPLAY_TYPE 1
LiquidCrystal_I2C     → DISPLAY_TYPE 2
TFT_eSPI              → DISPLAY_TYPE 3
```

### 3. Repository klonen / herunterladen

```bash
git clone https://github.com/JannWdl/Neu.git
cd smart-irrigation
```

Oder ZIP herunterladen → entpacken → Ordner `smart_irrigation/` in Arduino-Sketchbook.

### 4. Flashen

```
1. config.h anpassen (WLAN, Telegram, OWM)
2. SPIFFS hochladen: Werkzeuge → ESP32 Sketch Data Upload
   (Plugin: https://github.com/me-no-dev/arduino-esp32fs-plugin)
3. Sketch flashen: → (Upload-Pfeil)
4. Serielle Konsole öffnen (115200 Baud) → IP-Adresse ablesen
5. Browser öffnen: http://[IP]/
```

---

## ⚙️ Konfiguration

Alle Einstellungen in `config.h` — einmalig vor dem ersten Flash anpassen:

```cpp
// WiFi
#define WIFI_SSID       "DeinWLAN"
#define WIFI_PASSWORD   "DeinPasswort"

// Telegram (@BotFather → /newbot, Chat-ID: @userinfobot)
#define DEFAULT_TELEGRAM_TOKEN   "1234567890:ABC-xyz..."
#define DEFAULT_TELEGRAM_CHAT_ID "987654321"

// OpenWeatherMap (kostenloser Key: openweathermap.org/api)
#define DEFAULT_OWM_API_KEY  "abc123def456..."
#define DEFAULT_OWM_CITY     "Berlin"
#define DEFAULT_OWM_COUNTRY  "DE"

// Kanäle (Standard 1, max. 8)
#define DEFAULT_CHANNELS  1

// Display (0 = keins, 1 = OLED, 2 = LCD, 3 = TFT)
#define DISPLAY_TYPE  0

// OTA-Passwort (Arduino-IDE OTA)
#define OTA_PASSWORD  "irrigation123"
```

Alle weiteren Einstellungen (MQTT, Schwellwerte, Kalibrierung, Pflanzenzuordnung) sind **im Web-Interface** änderbar und werden im NVS-Speicher gesichert.

---

## 🌐 Web-Interface

Aufruf: `http://[ESP32-IP]/`

| Tab | Inhalt |
|---|---|
| **Dashboard** | Systemstatus, Wetter-Widget, alle Kanäle mit Feuchtigkeits-Gauge |
| **Kanäle** | Kalibrierungs-Wizard (3-Schritt), Manuelle Steuerung, Pflanzenwahl |
| **Statistik** | Chart.js-Verlauf (24h / 7d / 30d), Bewässerungs-Log |
| **Einstellungen** | WiFi, MQTT, Telegram, Wetter, Kanal-Parameter |
| **Update** | OTA per Drag & Drop (`.bin` hochladen) |

---

## 🔄 OTA-Updates

Es gibt **drei Methoden**, alle sind ohne USB möglich:

### Methode 1 — Web-Interface (einfachste)
1. `Sketch → Exportiere kompilierte Binärdatei` → `.bin` erzeugen
2. Browser: `http://[IP]/` → Tab **"Update"**
3. `.bin` per Drag & Drop hochladen
4. ESP32 startet automatisch neu ✅

### Methode 2 — Arduino IDE (direkt aus der IDE)
1. ESP32 muss im gleichen WLAN sein
2. `Werkzeuge → Port` → Netzwerk-Port `smart-irrigation @ 192.168.x.x` wählen
3. Passwort: `irrigation123` (in `config.h` → `OTA_PASSWORD` änderbar)
4. Normal auf **Upload** klicken ✅

> Falls der Port nicht erscheint: IDE neu starten. Windows: Bonjour / Apple-Dienste installieren.

### Methode 3 — Telegram-Bot (remote, ohne Netzwerkzugang)
1. `Sketch → Exportiere kompilierte Binärdatei` → `.bin` erzeugen
2. Im Telegram-Chat mit dem Bot die `.bin`-Datei als **Anhang** schicken
3. Bot bestätigt den Empfang, meldet den Flash-Fortschritt in 10%-Schritten
4. ESP32 startet nach erfolgreichem Flash automatisch neu ✅

```
Du: [Datei: smart_irrigation.ino.esp32.bin]
Bot: 📥 Update empfangen – lade Firmware herunter...
Bot: 🟩⬛⬛⬛⬛⬛⬛⬛⬛⬛ 10%
Bot: 🟩🟩🟩🟩🟩⬛⬛⬛⬛⬛ 50%
Bot: 🟩🟩🟩🟩🟩🟩🟩🟩🟩🟩 100%
Bot: ✅ Update erfolgreich! 487 kB geflasht. Neustart in 3 Sekunden...
```

> ⚠️ Bei allen OTA-Methoden werden **alle Pumpen vor dem Flash automatisch gestoppt**.

---

## 🤖 Telegram-Bot

### Einrichtung
1. Telegram: `@BotFather` → `/newbot` → Token kopieren
2. Eigene Chat-ID: `@userinfobot` schreiben → ID kopieren
3. Beides in `config.h` eintragen oder im Web-Interface unter Einstellungen

### Befehle

| Befehl | Funktion |
|---|---|
| `/start` · `/info` | Hilfe & Befehlsübersicht |
| `/status` | Systemübersicht (Uptime, IP, RSSI, alle Kanäle) |
| `/feuchte` | Alle Sensorwerte mit Warn-Emoji bei Trockenheit |
| `/wetter` | Temperatur, Luftfeuchtigkeit, Niederschlag, Vorhersage |
| `/giessen N` | Kanal N mit Standard-Dauer bewässern |
| `/giessen N T` | Kanal N für T Sekunden bewässern |
| `/stop N` | Pumpe Kanal N sofort stoppen |
| `/stopall` | Alle Pumpen sofort stoppen |
| `/auto N` | Automatikmodus Kanal N umschalten |
| `/log` | Letzte 8 Ereignisse |
| `/ota` | Anleitung für Telegram-OTA |
| *(Datei .bin)* | Firmware-Update direkt per Datei-Upload |

### Automatische Benachrichtigungen
- 💧 Bewässerung gestartet (mit Pflanzenprofil & Feuchtigkeitswert)
- ⚠️ Wasserstand kritisch (unter Mindestwert)
- ⛔ Bewässerung abgebrochen (Wasserstand zu niedrig)
- 🌱 System gestartet (mit IP-Adresse)

---

## 🏠 Home Assistant / MQTT

### Voraussetzungen
- MQTT-Broker (z.B. Mosquitto Add-on in HA)
- MQTT-Integration in Home Assistant aktiviert

### Einrichtung
1. Web-Interface → Einstellungen → MQTT aktivieren
2. Broker-IP, Port, User, Passwort eintragen
3. Speichern → ESP32 verbindet sich → HA erkennt Geräte automatisch

### Auto-Discovery Topics

| Topic | Typ | Wert |
|---|---|---|
| `irrigation/ch0/moisture` | Sensor | `0–100` (%) |
| `irrigation/ch0/pump/state` | Switch-State | `ON` / `OFF` |
| `irrigation/ch0/pump/command` | Switch-Command | `ON` / `OFF` schreiben |
| `irrigation/water_level` | Sensor | `0–100` (%) |
| `irrigation/uptime` | Sensor | Sekunden |
| `irrigation/rssi` | Sensor | dBm |
| `irrigation/weather/temp` | Sensor | °C |
| `irrigation/weather/humidity` | Sensor | % |

> Der Basis-Topic `irrigation` und HA-Discovery-Prefix `homeassistant` sind in `config.h` änderbar.

### Beispiel-Automation (HA YAML)
```yaml
automation:
  - alias: "Bewässerung wenn Feuchte unter 30%"
    trigger:
      - platform: numeric_state
        entity_id: sensor.smart_irrigation_ch1_feuchtigkeit
        below: 30
    action:
      - service: switch.turn_on
        entity_id: switch.smart_irrigation_ch1_pumpe
```

---

## 🌱 Pflanzendatenbank

20 vorkonfigurierte Profile (in `plants_db.h`, im Flash-Speicher):

| # | Pflanze | Min% | Max% | Dauer | Staunässe-sensitiv |
|---|---|---|---|---|---|
| 0 | 🌱 Benutzerdefiniert | — | — | — | — |
| 1 | 🍅 Tomate | 45 | 80 | 45s | — |
| 2 | 🌿 Basilikum | 50 | 80 | 20s | — |
| 3 | 🌵 Kaktus | 5 | 30 | 10s | ✅ |
| 4 | 🪴 Sukkulente | 10 | 35 | 10s | ✅ |
| 5 | 💜 Lavendel | 15 | 45 | 20s | ✅ |
| 6 | 🌹 Rose | 40 | 75 | 40s | — |
| 7 | 🍓 Erdbeere | 50 | 80 | 35s | — |
| 8 | 🫑 Paprika | 45 | 75 | 40s | — |
| 9 | 🌿 Minze | 55 | 85 | 25s | — |
| 10 | 🌸 Orchidee | 30 | 50 | 15s | ✅ |
| 11 | 🌿 Farn | 60 | 90 | 30s | — |
| 12 | 🌿 Efeutute | 30 | 60 | 20s | — |
| 13 | 🌿 Grünlilie | 35 | 65 | 20s | — |
| 14 | 🤍 Einblatt | 45 | 75 | 25s | — |
| 15 | 🌵 Aloe Vera | 10 | 30 | 15s | ✅ |
| 16 | 🥬 Salat | 60 | 90 | 30s | — |
| 17 | 🥒 Gurke | 55 | 85 | 45s | — |
| 18 | 🌻 Sonnenblume | 35 | 65 | 30s | — |
| 19 | 🌶️ Chili | 40 | 70 | 30s | — |

**Wetter-Anpassung je Profil:**
- Bei Temperatur > 28°C → Schwellwert + `temp_hot_adjust` (pflanzspezifisch)
- Bei Temperatur < 8°C → Schwellwert − 5%
- Staunässe-sensitive Pflanzen → Skip bei Luftfeuchtigkeit > 90%
- Bewässerung generell → Skip bei Regen > 2mm/h oder Regen-Vorhersage

---

## ❓ Fehlerbehebung

| Problem | Ursache | Lösung |
|---|---|---|
| Sensor zeigt immer 0% oder 100% | Fehlende Kalibrierung | Kalibrierungs-Wizard im Web-Interface durchführen |
| Sensor zeigt falsche Werte | ADC2-Pin verwendet | Nur ADC1-Pins: 34, 35, 32, 33, 36, 39, 25, 26 |
| Pumpe schaltet nicht | Falsche Relais-Logik | `RELAY_ACTIVE_LOW` in config.h prüfen (Standard: `true`) |
| WiFi verbindet nicht | Falsche Zugangsdaten | AP-Modus: SSID `SmartIrrigation-Setup`, Passwort `setup1234` |
| Telegram antwortet nicht | Falsche Chat-ID | Chat-ID mit `@userinfobot` prüfen |
| OTA-Port fehlt in Arduino IDE | mDNS nicht aktiv | IDE neu starten; Windows: Bonjour installieren |
| Display bleibt leer | Falsche I2C-Adresse | Scanner: 0x3C (SSD1306) oder 0x27 (LCD) versuchen |
| SPIFFS-Fehler beim Upload | Partition falsch | Partition Scheme: `Default 4MB with spiffs` |
| `Update.begin` schlägt fehl | Sketch zu groß | Partition Scheme prüfen; SPIFFS-Plugin neu installieren |
| HC-SR04 misst falsch | 5V→3.3V fehlt | Spannungsteiler am ECHO-Pin einbauen |

---

## 📁 Projektstruktur

```
smart_irrigation/
├── smart_irrigation.ino   # Hauptcode (Logik, API, OTA, Telegram, MQTT)
├── config.h               # Alle Nutzereinstellungen
├── plants_db.h            # Pflanzendatenbank (PROGMEM)
├── web_ui.h               # Komplettes Web-Interface als PROGMEM-String
└── README.md              # Diese Datei
```

---

## 📜 Lizenz

MIT License — frei verwendbar, veränderbar und verteilbar.  
Bitte einen Hinweis auf dieses Projekt lassen, wenn du es öffentlich verwendest. 🌱

---

<div align="center">
Made with ❤️ and too many houseplants.
</div>
