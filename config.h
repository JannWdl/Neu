#pragma once

// ╔══════════════════════════════════════════════════════════════╗
// ║           SMART IRRIGATION v2.0 — config.h                  ║
// ║  Alle Einstellungen hier anpassen, dann kompilieren.         ║
// ╚══════════════════════════════════════════════════════════════╝


// ========================
//  Konfigurations-Version
//  Bei neuen NVS-Schlüsseln erhöhen -> migrateConfig() in .ino erweitern
// ========================
#define CONFIG_VERSION  2

// ========================
//  AP-Modus Setup
// ========================
#define AP_SSID       "SmartIrrigation-Setup"
#define AP_PASSWORD   ""            // leer = offenes Netz (einfacheres Verbinden)
#define WIFI_TIMEOUT_MS  15000UL   // 15s warten bevor AP-Modus startet

// ========================
//  WiFi
// ========================
#define WIFI_SSID       "DeinWLAN"
#define WIFI_PASSWORD   "DeinPasswort"
#define HOSTNAME        "smart-irrigation"

// ========================
//  Kanäle (modular, 1-8)
// ========================
#define MAX_CHANNELS      8
#define DEFAULT_CHANNELS  1

// ========================
//  GPIO Pins (ESP32)
//  Feuchtigkeitssensoren → ADC1-Pins (kein ADC2, der wird von WiFi belegt)
//  Relais → Standard-GPIOs
// ========================
const int MOISTURE_PINS[MAX_CHANNELS] = { 34, 35, 32, 33, 36, 39, 25, 26 };
const int RELAY_PINS[MAX_CHANNELS]    = { 16, 17, 18, 19, 21, 22, 23, 27 };
#define RELAY_ACTIVE_LOW  true   // true = LOW schaltet Pumpe EIN (Standard für Relaismodule)

// ========================
//  Optionaler Wasserstand-Sensor (HC-SR04 Ultraschall)
//  Aktivieren: sysConfig.water_level_enabled = true im Web-Interface
// ========================
#define WATER_LEVEL_TRIG_PIN   12
#define WATER_LEVEL_ECHO_PIN   14
#define TANK_HEIGHT_CM         30     // Tankhöhe in cm (voll = 0 cm Abstand oben)
#define TANK_MIN_LEVEL_PCT     15     // Warnung unter x%

// ========================
//  Telegram Bot
//  Bot erstellen: @BotFather → /newbot
//  Chat-ID: @userinfobot schreiben
// ========================
#define DEFAULT_TELEGRAM_TOKEN   "YOUR_BOT_TOKEN_HERE"
#define DEFAULT_TELEGRAM_CHAT_ID "YOUR_CHAT_ID_HERE"

// ========================
//  MQTT / Home Assistant
// ========================
#define DEFAULT_MQTT_SERVER  "192.168.1.100"
#define DEFAULT_MQTT_PORT    1883
#define DEFAULT_MQTT_USER    ""
#define DEFAULT_MQTT_PASS    ""
#define MQTT_DEVICE_TOPIC    "irrigation"       // Basis-Topic
#define MQTT_BASE_TOPIC      "homeassistant"    // HA Discovery-Prefix

// ========================
//  Wetter (OpenWeatherMap)
//  Kostenlosen API Key: https://openweathermap.org/api
// ========================
#define DEFAULT_OWM_API_KEY    "YOUR_OWM_KEY_HERE"
#define DEFAULT_OWM_CITY       "Berlin"
#define DEFAULT_OWM_COUNTRY    "DE"
#define WEATHER_SKIP_ON_RAIN   true    // Bewässerung pausieren bei Regen
#define WEATHER_HOT_THRESHOLD  28.0f   // Ab x°C Schwellwert erhöhen
#define WEATHER_COLD_THRESHOLD  8.0f   // Unter x°C Schwellwert senken

// ========================
//  Display (optional, zur Compile-Zeit wählen)
//  0 = Kein Display
//  1 = OLED SSD1306 (I2C, 128×64 oder 128×32)
//  2 = LCD I2C (16×2 oder andere Größe)
//  3 = TFT ILI9341 / ST7789 (via TFT_eSPI)
// ========================
#define DISPLAY_TYPE   0

// OLED Einstellungen
#define OLED_WIDTH     128
#define OLED_HEIGHT    64
#define OLED_ADDRESS   0x3C

// LCD Einstellungen
#define LCD_ADDRESS    0x27
#define LCD_COLS       16
#define LCD_ROWS       2

// ========================
//  NTP & Zeitzone
// ========================
#define NTP_SERVER1  "pool.ntp.org"
#define NTP_SERVER2  "time.nist.gov"
#define TIMEZONE     "CET-1CEST,M3.5.0,M10.5.0/3"   // Deutschland (MEZ/MESZ)

// ========================
//  Timing-Intervalle (Millisekunden)
// ========================
#define SENSOR_READ_INTERVAL    30000UL     // Sensoren alle 30 s lesen
#define TELEGRAM_POLL_INTERVAL   3000UL     // Telegram alle 3 s pollen
#define MQTT_PUBLISH_INTERVAL   30000UL     // MQTT alle 30 s publishen
#define WEATHER_UPDATE_INTERVAL  3600000UL  // Wetter jede Stunde
#define LOG_INTERVAL             3600000UL  // Stündliches Daten-Logging
#define DISPLAY_UPDATE_INTERVAL  5000UL     // Display alle 5 s

// ========================
//  Standard-Bewässerungsparameter
// ========================
#define DEFAULT_MOISTURE_THRESHOLD  40    // Bewässern wenn Feuchtigkeit < 40%
#define DEFAULT_WATERING_DURATION   30    // Pumpe 30 Sekunden an
#define DEFAULT_MIN_INTERVAL_H       6    // Mindestabstand 6 Stunden zwischen Bewässerungen

// Sensor-Kalibrierung (Standard-ADC-Werte, 12-Bit = 0–4095)
#define DEFAULT_DRY_VALUE   3500   // Sensor trocken in der Luft
#define DEFAULT_WET_VALUE   1500   // Sensor vollständig in Wasser

// ========================
//  Logging-Limits (SPIFFS)
// ========================
#define MAX_LOG_READINGS  500    // Max. Messwerte pro Kanal
#define MAX_LOG_EVENTS    200    // Max. Ereignisse

// ========================
//  OTA
// ========================
#define OTA_PASSWORD  "irrigation123"
