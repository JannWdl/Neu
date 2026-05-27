// ╔══════════════════════════════════════════════════════════════════╗
// ║          SMART IRRIGATION v2.0 — smart_irrigation.ino           ║
// ║  ESP32 · Telegram · MQTT / Home Assistant · OTA · SPIFFS-Log    ║
// ╚══════════════════════════════════════════════════════════════════╝
//
//  Benötigte Libraries (Arduino Library Manager):
//    • ESPAsyncWebServer + AsyncTCP  (me-no-dev)
//    • ArduinoJson          v6.x     (Benoit Blanchon)
//    • PubSubClient                  (Nick O'Leary)
//    • UniversalTelegramBot          (Brian Lough)
//    • Preferences                   (integriert in ESP32-Core)
//    • SPIFFS / LittleFS             (integriert in ESP32-Core)
//    • ArduinoOTA                    (integriert in ESP32-Core)
//
//  Optional je nach DISPLAY_TYPE in config.h:
//    • Adafruit SSD1306 + Adafruit GFX  (DISPLAY_TYPE 1)
//    • LiquidCrystal_I2C               (DISPLAY_TYPE 2)
//    • TFT_eSPI                         (DISPLAY_TYPE 3)

#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <AsyncTCP.h>
#include <ESPAsyncWebServer.h>
#include <ArduinoOTA.h>
#include <ArduinoJson.h>
#include <Preferences.h>
#include <SPIFFS.h>
#include <HTTPClient.h>
#include <PubSubClient.h>
#include <UniversalTelegramBot.h>
#include <time.h>

#include <DNSServer.h>
#include "config.h"
#include "plants_db.h"
#include "web_ui.h"
#include "setup_portal.h"

// ─── Display-Includes ──────────────────────────────────────────────
#if DISPLAY_TYPE == 1
  #include <Wire.h>
  #include <Adafruit_GFX.h>
  #include <Adafruit_SSD1306.h>
  Adafruit_SSD1306 display(OLED_WIDTH, OLED_HEIGHT, &Wire, -1);
#elif DISPLAY_TYPE == 2
  #include <Wire.h>
  #include <LiquidCrystal_I2C.h>
  LiquidCrystal_I2C display(LCD_ADDRESS, LCD_COLS, LCD_ROWS);
#elif DISPLAY_TYPE == 3
  #include <TFT_eSPI.h>
  TFT_eSPI tft = TFT_eSPI();
#endif

// ═══════════════════════════════════════════════════════════════════
//  STRUCTS
// ═══════════════════════════════════════════════════════════════════

struct ChannelConfig {
  bool     enabled          = false;
  char     name[24]         = "Kanal 1";
  uint8_t  plant_idx        = 0;          // Index in PLANT_DATABASE
  uint8_t  moisture_thresh  = DEFAULT_MOISTURE_THRESHOLD;
  uint16_t water_duration   = DEFAULT_WATERING_DURATION;
  uint16_t min_interval_h   = DEFAULT_MIN_INTERVAL_H;
  bool     auto_mode        = true;
  int      dry_adc          = DEFAULT_DRY_VALUE;
  int      wet_adc          = DEFAULT_WET_VALUE;
};

struct ChannelState {
  int      raw_adc          = 0;
  uint8_t  moisture_pct     = 0;
  bool     pump_running     = false;
  unsigned long pump_start  = 0;
  unsigned long last_water  = 0;
  uint32_t total_waterings  = 0;
  uint32_t total_seconds    = 0;
};

struct WeatherData {
  bool     valid            = false;
  float    temp             = 0.0f;
  float    humidity         = 0.0f;
  float    rain_1h          = 0.0f;
  bool     rain_forecast    = false;
  char     description[48]  = "";
  char     main[24]         = "";
  unsigned long last_update = 0;
};

struct SystemConfig {
  char  wifi_ssid[64]         = WIFI_SSID;
  char  wifi_pass[64]         = WIFI_PASSWORD;
  char  telegram_token[128]   = DEFAULT_TELEGRAM_TOKEN;
  char  telegram_chat[32]     = DEFAULT_TELEGRAM_CHAT_ID;
  char  mqtt_server[64]       = DEFAULT_MQTT_SERVER;
  int   mqtt_port             = DEFAULT_MQTT_PORT;
  char  mqtt_user[64]         = DEFAULT_MQTT_USER;
  char  mqtt_pass[64]         = DEFAULT_MQTT_PASS;
  bool  mqtt_enabled          = false;
  char  owm_key[64]           = DEFAULT_OWM_API_KEY;
  char  owm_city[64]          = DEFAULT_OWM_CITY;
  char  owm_country[8]        = DEFAULT_OWM_COUNTRY;
  bool  weather_enabled       = false;
  bool  telegram_enabled      = false;
  int   active_channels       = DEFAULT_CHANNELS;
  bool  water_level_enabled   = false;
};

// ═══════════════════════════════════════════════════════════════════
//  GLOBALE VARIABLEN
// ═══════════════════════════════════════════════════════════════════

SystemConfig              sysConfig;
ChannelConfig             chConfig[MAX_CHANNELS];
ChannelState              chState[MAX_CHANNELS];
WeatherData               weather;
Preferences               prefs;
AsyncWebServer            server(80);
WiFiClient                wifiClient;
WiFiClientSecure          secureClient;
PubSubClient              mqttClient(wifiClient);
UniversalTelegramBot*     bot = nullptr;

unsigned long lastSensorRead    = 0;
unsigned long lastTelegramPoll  = 0;
unsigned long lastMqttPublish   = 0;
unsigned long lastWeatherUpdate = 0;
unsigned long lastLogWrite      = 0;
unsigned long lastDisplayUpdate = 0;
unsigned long bootTime          = 0;

int  waterLevel_pct      = -1;   // -1 = nicht gemessen
bool mqttConnected       = false;
bool spiffsOk            = false;

// ═══════════════════════════════════════════════════════════════════
//  FORWARD DECLARATIONS
// ═══════════════════════════════════════════════════════════════════

void loadConfig();
void saveConfig();
void loadChannelConfig(int ch);
void saveChannelConfig(int ch);
void migrateConfig();
void runSetupPortal();
int  readMoisture(int ch);
uint8_t adcToPercent(int raw, int dry, int wet);
void startPump(int ch, int duration = -1);
void stopPump(int ch);
void checkAutoWatering();
void updateWeather();
bool shouldSkipDueToWeather(int ch);
void connectMqtt();
void publishMqtt();
void setupHaDiscovery();
void mqttCallback(char* topic, byte* payload, unsigned int length);
void handleTelegram();
void sendTelegram(const String& msg);
void logReading(int ch, uint8_t moisture);
void logEvent(const char* type, int ch, const char* msg);
String getLogsJson(int ch, const String& range);
void measureWaterLevel();
void updateDisplay();
void setupOTA();
void setupWebServer();
void setupApiEndpoints();
String buildStatusJson();
String buildConfigJson();

// ═══════════════════════════════════════════════════════════════════
//  SETUP
// ═══════════════════════════════════════════════════════════════════

void setup() {
  Serial.begin(115200);
  Serial.println(F("\n=== Smart Irrigation v2.0 ==="));

  // Pins konfigurieren
  for (int i = 0; i < MAX_CHANNELS; i++) {
    pinMode(RELAY_PINS[i], OUTPUT);
    digitalWrite(RELAY_PINS[i], RELAY_ACTIVE_LOW ? HIGH : LOW); // Pumpe AUS
    pinMode(MOISTURE_PINS[i], INPUT);
  }
  analogReadResolution(12);

  // Wasserstand-Pins
  pinMode(WATER_LEVEL_TRIG_PIN, OUTPUT);
  pinMode(WATER_LEVEL_ECHO_PIN, INPUT);

  // SPIFFS
  if (SPIFFS.begin(true)) {
    spiffsOk = true;
    Serial.println(F("SPIFFS OK"));
  } else {
    Serial.println(F("SPIFFS FEHLER – Logging deaktiviert"));
  }

  // Konfiguration laden
  loadConfig();
  for (int i = 0; i < MAX_CHANNELS; i++) loadChannelConfig(i);

  // Display
  #if DISPLAY_TYPE == 1
    Wire.begin();
    if (!display.begin(SSD1306_SWITCHCAPVCC, OLED_ADDRESS)) {
      Serial.println(F("OLED nicht gefunden"));
    } else {
      display.clearDisplay();
      display.setTextSize(1);
      display.setTextColor(SSD1306_WHITE);
      display.setCursor(0, 0);
      display.println(F("Smart Irrigation"));
      display.println(F("Starte..."));
      display.display();
    }
  #elif DISPLAY_TYPE == 2
    Wire.begin();
    display.init();
    display.backlight();
    display.setCursor(0, 0);
    display.print(F("Smart Irrigation"));
    display.setCursor(0, 1);
    display.print(F("Starte..."));
  #elif DISPLAY_TYPE == 3
    tft.init();
    tft.setRotation(1);
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_GREEN);
    tft.setTextSize(2);
    tft.setCursor(10, 10);
    tft.println(F("Smart Irrigation"));
    tft.setTextSize(1);
    tft.println(F("Starte..."));
  #endif

  // ── Konfigurationsmigration ──────────────────────────────────────
  migrateConfig();

  // ── WiFi verbinden ────────────────────────────────────────────────
  // AP-Modus starten wenn: kein SSID gesetzt ODER Verbindung schlägt fehl
  bool needSetup = (strlen(sysConfig.wifi_ssid) == 0 ||
                    strcmp(sysConfig.wifi_ssid, WIFI_SSID) == 0);

  if (!needSetup) {
    WiFi.setHostname(HOSTNAME);
    WiFi.begin(sysConfig.wifi_ssid, sysConfig.wifi_pass);
    Serial.print(F("WiFi verbinden"));
    unsigned long t = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - t < WIFI_TIMEOUT_MS) {
      delay(300); Serial.print('.');
    }
    Serial.println();
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println(F("WiFi fehlgeschlagen → AP-Modus"));
      needSetup = true;
    }
  }

  if (needSetup) {
    runSetupPortal();   // blockiert bis Neustart nach Konfiguration
    return;             // wird nie erreicht (ESP.restart() im Portal)
  }

  Serial.printf("IP: %s\n", WiFi.localIP().toString().c_str());

  // Zeit synchronisieren
  configTzTime(TIMEZONE, NTP_SERVER1, NTP_SERVER2);
  bootTime = millis();

  // OTA
  setupOTA();

  // MQTT
  if (sysConfig.mqtt_enabled) {
    mqttClient.setServer(sysConfig.mqtt_server, sysConfig.mqtt_port);
    mqttClient.setCallback(mqttCallback);
    mqttClient.setBufferSize(1024);
    connectMqtt();
    setupHaDiscovery();
  }

  // Telegram
  if (sysConfig.telegram_enabled && strlen(sysConfig.telegram_token) > 10) {
    secureClient.setInsecure();
    bot = new UniversalTelegramBot(sysConfig.telegram_token, secureClient);
    sendTelegram("🌱 Smart Irrigation gestartet!\nIP: " + WiFi.localIP().toString());
  }

  // Wetter
  if (sysConfig.weather_enabled) updateWeather();

  // Web-Server & API
  setupWebServer();
  setupApiEndpoints();
  server.begin();

  logEvent("system", -1, "Gestartet");
  Serial.println(F("=== Bereit ==="));
}

// ═══════════════════════════════════════════════════════════════════
//  LOOP
// ═══════════════════════════════════════════════════════════════════

void loop() {
  ArduinoOTA.handle();

  unsigned long now = millis();

  // Sensoren lesen
  if (now - lastSensorRead >= SENSOR_READ_INTERVAL) {
    lastSensorRead = now;
    for (int i = 0; i < sysConfig.active_channels; i++) {
      chState[i].raw_adc      = readMoisture(i);
      chState[i].moisture_pct = adcToPercent(chState[i].raw_adc, chConfig[i].dry_adc, chConfig[i].wet_adc);
    }
    if (sysConfig.water_level_enabled) measureWaterLevel();
    checkAutoWatering();
  }

  // Pumpen-Timeout prüfen
  for (int i = 0; i < sysConfig.active_channels; i++) {
    if (chState[i].pump_running) {
      unsigned long elapsed = (now - chState[i].pump_start) / 1000;
      if (elapsed >= chConfig[i].water_duration) {
        stopPump(i);
      }
    }
  }

  // MQTT
  if (sysConfig.mqtt_enabled) {
    if (!mqttClient.connected()) connectMqtt();
    mqttClient.loop();
    if (now - lastMqttPublish >= MQTT_PUBLISH_INTERVAL) {
      lastMqttPublish = now;
      publishMqtt();
    }
  }

  // Telegram
  if (sysConfig.telegram_enabled && bot && now - lastTelegramPoll >= TELEGRAM_POLL_INTERVAL) {
    lastTelegramPoll = now;
    handleTelegram();
  }

  // Wetter
  if (sysConfig.weather_enabled && now - lastWeatherUpdate >= WEATHER_UPDATE_INTERVAL) {
    lastWeatherUpdate = now;
    updateWeather();
  }

  // Logging
  if (spiffsOk && now - lastLogWrite >= LOG_INTERVAL) {
    lastLogWrite = now;
    for (int i = 0; i < sysConfig.active_channels; i++) {
      logReading(i, chState[i].moisture_pct);
    }
  }

  // Display
  if (now - lastDisplayUpdate >= DISPLAY_UPDATE_INTERVAL) {
    lastDisplayUpdate = now;
    updateDisplay();
  }
}

// ═══════════════════════════════════════════════════════════════════
//  KONFIGURATIONSMIGRATION
//  Läuft beim Start – erhält alle alten Werte, setzt nur neue Defaults
// ═══════════════════════════════════════════════════════════════════

void migrateConfig() {
  prefs.begin("sys", false);
  int stored = prefs.getInt("cfg_ver", 0);

  if (stored < CONFIG_VERSION) {
    Serial.printf("Config-Migration: v%d → v%d\n", stored, CONFIG_VERSION);

    // ── Version 1 → 2 ────────────────────────────────────────────
    // Neue Keys: water_level_enabled, cfg_ver selbst
    if (stored < 2) {
      if (!prefs.isKey("wl_en"))      prefs.putBool("wl_en",  false);
      if (!prefs.isKey("weather_en")) prefs.putBool("weather_en", false);
      if (!prefs.isKey("tg_en"))      prefs.putBool("tg_en",  false);
      if (!prefs.isKey("mqtt_en"))    prefs.putBool("mqtt_en", false);
      if (!prefs.isKey("channels"))   prefs.putInt("channels", DEFAULT_CHANNELS);
    }

    // ── Version 2 → 3 (Beispiel für künftige Updates) ─────────────
    // if (stored < 3) {
    //   if (!prefs.isKey("new_key")) prefs.putInt("new_key", 0);
    // }

    prefs.putInt("cfg_ver", CONFIG_VERSION);
    Serial.println(F("Migration abgeschlossen – alle alten Werte erhalten."));

    // Telegram-Benachrichtigung (falls bereits konfiguriert)
    // Wird nach Bot-Init in setup() gesendet — merken wir uns hier
    prefs.putBool("migrated", true);
  }
  prefs.end();
}

// ═══════════════════════════════════════════════════════════════════
//  AP-MODUS SETUP-PORTAL
//  Blockiert den normalen Start bis der User WiFi konfiguriert hat
// ═══════════════════════════════════════════════════════════════════

void runSetupPortal() {
  Serial.println(F("\n=== AP-MODUS SETUP ==="));
  Serial.printf("SSID: %s\n", AP_SSID);

  WiFi.disconnect(true);
  delay(200);
  WiFi.mode(WIFI_AP);
  WiFi.softAP(AP_SSID, strlen(AP_PASSWORD) > 0 ? AP_PASSWORD : nullptr);
  delay(300);

  IPAddress apIP(192, 168, 4, 1);
  Serial.printf("AP-IP: %s\n", apIP.toString().c_str());

  // DNS-Server: alle Domains → 192.168.4.1 (Captive Portal)
  DNSServer dns;
  dns.setTTL(300);
  dns.start(53, "*", apIP);

  // Eigener Web-Server im AP-Modus
  AsyncWebServer apServer(80);

  // Captive-Portal-Erkennung (Android, iOS, Windows)
  auto portalRedirect = [](AsyncWebServerRequest* req) {
    req->redirect("http://192.168.4.1/");
  };
  apServer.on("/generate_204",        HTTP_GET, portalRedirect);
  apServer.on("/gen_204",             HTTP_GET, portalRedirect);
  apServer.on("/hotspot-detect.html", HTTP_GET, portalRedirect);
  apServer.on("/connecttest.txt",     HTTP_GET, portalRedirect);
  apServer.on("/ncsi.txt",            HTTP_GET, portalRedirect);
  apServer.on("/redirect",            HTTP_GET, portalRedirect);
  apServer.on("/canonical.html",      HTTP_GET, portalRedirect);

  // Setup-Seite
  apServer.on("/", HTTP_GET, [](AsyncWebServerRequest* req) {
    req->send_P(200, "text/html", SETUP_PORTAL_HTML);
  });

  // WiFi-Scan
  apServer.on("/api/scan", HTTP_GET, [](AsyncWebServerRequest* req) {
    int n = WiFi.scanNetworks();
    DynamicJsonDocument doc(2048);
    JsonArray nets = doc.createNestedArray("networks");
    for (int i = 0; i < n; i++) {
      JsonObject o = nets.createNestedObject();
      o["ssid"]    = WiFi.SSID(i);
      o["rssi"]    = WiFi.RSSI(i);
      o["secured"] = (WiFi.encryptionType(i) != WIFI_AUTH_OPEN);
    }
    WiFi.scanDelete();
    String out; serializeJson(doc, out);
    req->send(200, "application/json", out);
  });

  // Setup speichern
  AsyncCallbackJsonWebHandler* setupHandler = new AsyncCallbackJsonWebHandler(
    "/api/setup", [](AsyncWebServerRequest* req, JsonVariant& json) {
      JsonObject cfg = json.as<JsonObject>();

      // ── WiFi ────────────────────────────────────────────────────
      const char* ssid = cfg["wifi_ssid"] | "";
      const char* pass = cfg["wifi_pass"] | "";
      if (strlen(ssid) == 0) {
        req->send(400, "application/json", "{\"ok\":false,\"msg\":\"SSID fehlt\"}");
        return;
      }

      prefs.begin("sys", false);
      prefs.putString("wifi_ssid",  ssid);
      prefs.putString("wifi_pass",  pass);

      // ── Kanäle ──────────────────────────────────────────────────
      int numCh = cfg["channels"] | DEFAULT_CHANNELS;
      numCh = constrain(numCh, 1, MAX_CHANNELS);
      prefs.putInt("channels", numCh);

      // ── GPIO-Pins pro Kanal ────────────────────────────────────
      JsonArray sPins = cfg["sensor_pins"].as<JsonArray>();
      JsonArray rPins = cfg["relay_pins"].as<JsonArray>();
      JsonArray names = cfg["channel_names"].as<JsonArray>();
      prefs.end();

      for (int i = 0; i < numCh; i++) {
        char ns[8]; snprintf(ns, sizeof(ns), "ch%d", i);
        prefs.begin(ns, false);
        if (!sPins.isNull() && i < (int)sPins.size())
          prefs.putInt("sens_pin", sPins[i].as<int>());
        if (!rPins.isNull() && i < (int)rPins.size())
          prefs.putInt("rlay_pin", rPins[i].as<int>());
        if (!names.isNull() && i < (int)names.size()) {
          const char* nm = names[i] | "";
          if (strlen(nm) > 0) prefs.putString("name", nm);
        }
        if (i == 0) prefs.putBool("en", true);
        prefs.end();
      }

      // ── System-Config ──────────────────────────────────────────
      prefs.begin("sys", false);
      prefs.putBool("relay_al",    cfg["relay_active_low"]    | true);
      prefs.putBool("wl_en",       cfg["water_level_enabled"] | false);
      prefs.putInt("wl_trig",      cfg["water_level_trig"]    | WATER_LEVEL_TRIG_PIN);
      prefs.putInt("wl_echo",      cfg["water_level_echo"]    | WATER_LEVEL_ECHO_PIN);
      prefs.putInt("wl_height",    cfg["tank_height"]         | TANK_HEIGHT_CM);
      prefs.putInt("wl_min",       cfg["tank_min_level"]      | TANK_MIN_LEVEL_PCT);
      prefs.putBool("tg_en",       cfg["telegram_enabled"]    | false);
      prefs.putString("tg_token",  cfg["telegram_token"]      | "");
      prefs.putString("tg_chat",   cfg["telegram_chat"]       | "");
      prefs.putBool("mqtt_en",     cfg["mqtt_enabled"]        | false);
      prefs.putString("mqtt_srv",  cfg["mqtt_server"]         | "");
      prefs.putInt("mqtt_port",    cfg["mqtt_port"]           | 1883);
      prefs.putString("mqtt_user", cfg["mqtt_user"]           | "");
      prefs.putString("mqtt_pass", cfg["mqtt_pass"]           | "");
      prefs.putBool("weather_en",  cfg["weather_enabled"]     | false);
      prefs.putString("owm_key",   cfg["owm_key"]             | "");
      prefs.putString("owm_city",  cfg["owm_city"]            | "Berlin");
      prefs.putString("owm_cntry", cfg["owm_country"]         | "DE");
      prefs.putInt("cfg_ver",      CONFIG_VERSION);
      prefs.putBool("migrated",    false);
      prefs.end();

      Serial.println(F("Setup gespeichert – Neustart..."));
      req->send(200, "application/json", "{\"ok\":true}");
      delay(1000);
      ESP.restart();
    }
  );
  apServer.addHandler(setupHandler);

  apServer.onNotFound([](AsyncWebServerRequest* req) {
    req->redirect("http://192.168.4.1/");
  });

  apServer.begin();

  Serial.println(F("Portal bereit. Verbinde mit WLAN 'SmartIrrigation-Setup'"));
  Serial.println(F("Dann Browser öffnen: http://192.168.4.1"));

  // AP-Modus läuft bis zum Neustart nach Konfiguration
  while (true) {
    dns.processNextRequest();
    delay(10);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  KONFIGURATION LADEN / SPEICHERN
// ═══════════════════════════════════════════════════════════════════

void loadConfig() {
  prefs.begin("sys", true);
  prefs.getString("wifi_ssid",  sysConfig.wifi_ssid,  sizeof(sysConfig.wifi_ssid));
  prefs.getString("wifi_pass",  sysConfig.wifi_pass,  sizeof(sysConfig.wifi_pass));
  prefs.getString("tg_token",   sysConfig.telegram_token, sizeof(sysConfig.telegram_token));
  prefs.getString("tg_chat",    sysConfig.telegram_chat,  sizeof(sysConfig.telegram_chat));
  prefs.getString("mqtt_srv",   sysConfig.mqtt_server,    sizeof(sysConfig.mqtt_server));
  sysConfig.mqtt_port    = prefs.getInt("mqtt_port",   DEFAULT_MQTT_PORT);
  prefs.getString("mqtt_user",  sysConfig.mqtt_user,  sizeof(sysConfig.mqtt_user));
  prefs.getString("mqtt_pass",  sysConfig.mqtt_pass,  sizeof(sysConfig.mqtt_pass));
  sysConfig.mqtt_enabled     = prefs.getBool("mqtt_en",   false);
  prefs.getString("owm_key",   sysConfig.owm_key,   sizeof(sysConfig.owm_key));
  prefs.getString("owm_city",  sysConfig.owm_city,  sizeof(sysConfig.owm_city));
  prefs.getString("owm_cntry", sysConfig.owm_country, sizeof(sysConfig.owm_country));
  sysConfig.weather_enabled  = prefs.getBool("weather_en", false);
  sysConfig.telegram_enabled = prefs.getBool("tg_en",     false);
  sysConfig.active_channels  = prefs.getInt("channels",   DEFAULT_CHANNELS);
  sysConfig.water_level_enabled = prefs.getBool("wl_en",  false);
  if (sysConfig.active_channels < 1) sysConfig.active_channels = 1;
  if (sysConfig.active_channels > MAX_CHANNELS) sysConfig.active_channels = MAX_CHANNELS;
  prefs.end();
}

void saveConfig() {
  prefs.begin("sys", false);
  prefs.putString("wifi_ssid", sysConfig.wifi_ssid);
  prefs.putString("wifi_pass", sysConfig.wifi_pass);
  prefs.putString("tg_token",  sysConfig.telegram_token);
  prefs.putString("tg_chat",   sysConfig.telegram_chat);
  prefs.putString("mqtt_srv",  sysConfig.mqtt_server);
  prefs.putInt("mqtt_port",    sysConfig.mqtt_port);
  prefs.putString("mqtt_user", sysConfig.mqtt_user);
  prefs.putString("mqtt_pass", sysConfig.mqtt_pass);
  prefs.putBool("mqtt_en",     sysConfig.mqtt_enabled);
  prefs.putString("owm_key",   sysConfig.owm_key);
  prefs.putString("owm_city",  sysConfig.owm_city);
  prefs.putString("owm_cntry", sysConfig.owm_country);
  prefs.putBool("weather_en",  sysConfig.weather_enabled);
  prefs.putBool("tg_en",       sysConfig.telegram_enabled);
  prefs.putInt("channels",     sysConfig.active_channels);
  prefs.putBool("wl_en",       sysConfig.water_level_enabled);
  prefs.end();
}

void loadChannelConfig(int ch) {
  char ns[8]; snprintf(ns, sizeof(ns), "ch%d", ch);
  prefs.begin(ns, true);
  chConfig[ch].enabled       = prefs.getBool("en",     ch == 0);
  prefs.getString("name",     chConfig[ch].name,  sizeof(chConfig[ch].name));
  if (strlen(chConfig[ch].name) == 0) snprintf(chConfig[ch].name, sizeof(chConfig[ch].name), "Kanal %d", ch+1);
  chConfig[ch].plant_idx     = prefs.getUChar("plant",  0);
  chConfig[ch].moisture_thresh = prefs.getUChar("thresh", DEFAULT_MOISTURE_THRESHOLD);
  chConfig[ch].water_duration  = prefs.getUShort("dur",  DEFAULT_WATERING_DURATION);
  chConfig[ch].min_interval_h  = prefs.getUShort("ivl",  DEFAULT_MIN_INTERVAL_H);
  chConfig[ch].auto_mode     = prefs.getBool("auto",   true);
  chConfig[ch].dry_adc       = prefs.getInt("dry",     DEFAULT_DRY_VALUE);
  chConfig[ch].wet_adc       = prefs.getInt("wet",     DEFAULT_WET_VALUE);
  prefs.end();
}

void saveChannelConfig(int ch) {
  char ns[8]; snprintf(ns, sizeof(ns), "ch%d", ch);
  prefs.begin(ns, false);
  prefs.putBool("en",       chConfig[ch].enabled);
  prefs.putString("name",   chConfig[ch].name);
  prefs.putUChar("plant",   chConfig[ch].plant_idx);
  prefs.putUChar("thresh",  chConfig[ch].moisture_thresh);
  prefs.putUShort("dur",    chConfig[ch].water_duration);
  prefs.putUShort("ivl",    chConfig[ch].min_interval_h);
  prefs.putBool("auto",     chConfig[ch].auto_mode);
  prefs.putInt("dry",       chConfig[ch].dry_adc);
  prefs.putInt("wet",       chConfig[ch].wet_adc);
  prefs.end();
}

// ═══════════════════════════════════════════════════════════════════
//  SENSOREN
// ═══════════════════════════════════════════════════════════════════

int readMoisture(int ch) {
  // Mehrfach messen und mitteln (Rauschen reduzieren)
  long sum = 0;
  const int SAMPLES = 5;
  for (int i = 0; i < SAMPLES; i++) {
    sum += analogRead(MOISTURE_PINS[ch]);
    delay(5);
  }
  return (int)(sum / SAMPLES);
}

uint8_t adcToPercent(int raw, int dry, int wet) {
  if (dry == wet) return 0;
  // Begrenzen
  raw = constrain(raw, min(wet, dry), max(wet, dry));
  // Kapazitiver Sensor: höherer ADC = trockener
  float pct = (float)(dry - raw) / (float)(dry - wet) * 100.0f;
  return (uint8_t)constrain((int)pct, 0, 100);
}

void measureWaterLevel() {
  // HC-SR04 Ultraschall
  digitalWrite(WATER_LEVEL_TRIG_PIN, LOW);
  delayMicroseconds(2);
  digitalWrite(WATER_LEVEL_TRIG_PIN, HIGH);
  delayMicroseconds(10);
  digitalWrite(WATER_LEVEL_TRIG_PIN, LOW);
  long duration = pulseIn(WATER_LEVEL_ECHO_PIN, HIGH, 30000);
  if (duration == 0) { waterLevel_pct = -1; return; }
  float distanceCm = duration * 0.0343f / 2.0f;
  // Abstand von oben → Füllstand in %
  float fill = (float)(TANK_HEIGHT_CM - distanceCm) / (float)TANK_HEIGHT_CM * 100.0f;
  waterLevel_pct = (int)constrain(fill, 0, 100);

  if (waterLevel_pct <= TANK_MIN_LEVEL_PCT) {
    String msg = "⚠️ Wasserstand kritisch: " + String(waterLevel_pct) + "%\nBitte Tank nachfüllen!";
    sendTelegram(msg);
    char buf[64]; snprintf(buf, sizeof(buf), "Wasserstand: %d%%", waterLevel_pct);
    logEvent("water_low", -1, buf);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  PUMPENSTEUERUNG
// ═══════════════════════════════════════════════════════════════════

void startPump(int ch, int duration) {
  if (ch < 0 || ch >= MAX_CHANNELS) return;
  if (chState[ch].pump_running) return;

  // Wasserstand prüfen
  if (sysConfig.water_level_enabled && waterLevel_pct >= 0 && waterLevel_pct <= TANK_MIN_LEVEL_PCT) {
    Serial.printf("CH%d: Pumpe blockiert – Wasserstand zu niedrig (%d%%)\n", ch, waterLevel_pct);
    sendTelegram("⛔ Bewässerung abgebrochen – Wasserstand zu niedrig (" + String(waterLevel_pct) + "%)");
    return;
  }

  int dur = (duration > 0) ? duration : chConfig[ch].water_duration;
  digitalWrite(RELAY_PINS[ch], RELAY_ACTIVE_LOW ? LOW : HIGH);
  chState[ch].pump_running = true;
  chState[ch].pump_start   = millis();
  chState[ch].last_water   = millis();
  chState[ch].total_waterings++;
  chState[ch].total_seconds += dur;
  chConfig[ch].water_duration = dur;

  Serial.printf("CH%d: Pumpe AN (%ds)\n", ch, dur);
  char buf[80];
  snprintf(buf, sizeof(buf), "Bewässert für %d Sekunden (Feuchte: %d%%)", dur, chState[ch].moisture_pct);
  logEvent("water_start", ch, buf);

  if (sysConfig.telegram_enabled) {
    PlantProfile p = getPlantProfile(chConfig[ch].plant_idx);
    String msg = "💧 " + String(chConfig[ch].name) + " wird gegossen\n";
    msg += "Pflanze: " + String(p.emoji) + " " + String(p.name_de) + "\n";
    msg += "Feuchte: " + String(chState[ch].moisture_pct) + "% → Dauer: " + String(dur) + "s";
    sendTelegram(msg);
  }

  if (sysConfig.mqtt_enabled) {
    char topic[80], payload[16];
    snprintf(topic, sizeof(topic), "%s/ch%d/pump/state", MQTT_DEVICE_TOPIC, ch);
    snprintf(payload, sizeof(payload), "ON");
    mqttClient.publish(topic, payload, true);
  }
}

void stopPump(int ch) {
  if (ch < 0 || ch >= MAX_CHANNELS) return;
  if (!chState[ch].pump_running) return;

  digitalWrite(RELAY_PINS[ch], RELAY_ACTIVE_LOW ? HIGH : LOW);
  unsigned long ran = (millis() - chState[ch].pump_start) / 1000;
  chState[ch].pump_running = false;

  Serial.printf("CH%d: Pumpe AUS (gelaufen: %lus)\n", ch, ran);
  logEvent("water_stop", ch, "Bewässerung beendet");

  if (sysConfig.mqtt_enabled) {
    char topic[80];
    snprintf(topic, sizeof(topic), "%s/ch%d/pump/state", MQTT_DEVICE_TOPIC, ch);
    mqttClient.publish(topic, "OFF", true);
  }
}

void checkAutoWatering() {
  unsigned long now = millis();
  for (int i = 0; i < sysConfig.active_channels; i++) {
    if (!chConfig[i].enabled || !chConfig[i].auto_mode) continue;
    if (chState[i].pump_running) continue;

    // Mindestabstand einhalten
    unsigned long elapsed_h = (now - chState[i].last_water) / 3600000UL;
    if (chState[i].last_water > 0 && elapsed_h < chConfig[i].min_interval_h) continue;

    // Wetter-Check
    if (shouldSkipDueToWeather(i)) continue;

    // Schwellwert mit Wetter/Temperatur-Anpassung
    uint8_t thresh = chConfig[i].moisture_thresh;
    if (weather.valid && sysConfig.weather_enabled) {
      PlantProfile p = getPlantProfile(chConfig[i].plant_idx);
      if (weather.temp > WEATHER_HOT_THRESHOLD) thresh = min(100, (int)(thresh + p.temp_hot_adjust));
      if (weather.temp < WEATHER_COLD_THRESHOLD) thresh = max(0, (int)(thresh - 5));
    }

    if (chState[i].moisture_pct < thresh) {
      Serial.printf("CH%d: Auto-Bewässerung (Feuchte %d%% < Schwelle %d%%)\n", i, chState[i].moisture_pct, thresh);
      startPump(i);
    }
  }
}

bool shouldSkipDueToWeather(int ch) {
  if (!weather.valid || !sysConfig.weather_enabled) return false;

  PlantProfile p = getPlantProfile(chConfig[ch].plant_idx);

  // Staunässe-empfindliche Pflanzen bei hoher Luftfeuchtigkeit schützen
  if (p.overwater_sensitive && weather.humidity > 90.0f) {
    Serial.printf("CH%d: Skip – hohe Luftfeuchtigkeit (%.0f%%, Pflanze staunässeempfindlich)\n", ch, weather.humidity);
    return true;
  }

  // Regen-Check
  if (WEATHER_SKIP_ON_RAIN && (weather.rain_1h > 2.0f || weather.rain_forecast)) {
    Serial.printf("CH%d: Skip – Regen erkannt (%.1fmm, Vorhersage: %s)\n", ch, weather.rain_1h, weather.rain_forecast?"ja":"nein");
    return true;
  }

  return false;
}

// ═══════════════════════════════════════════════════════════════════
//  WETTER
// ═══════════════════════════════════════════════════════════════════

void updateWeather() {
  if (!WiFi.isConnected() || strlen(sysConfig.owm_key) < 10) return;

  HTTPClient http;
  String url = "http://api.openweathermap.org/data/2.5/weather?q=";
  url += sysConfig.owm_city;
  url += ",";
  url += sysConfig.owm_country;
  url += "&appid=";
  url += sysConfig.owm_key;
  url += "&units=metric&lang=de";

  http.begin(url);
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    DynamicJsonDocument doc(2048);
    if (deserializeJson(doc, body) == DeserializationError::Ok) {
      weather.temp      = doc["main"]["temp"]     | 0.0f;
      weather.humidity  = doc["main"]["humidity"] | 0.0f;
      weather.rain_1h   = doc["rain"]["1h"]       | 0.0f;
      strlcpy(weather.description, doc["weather"][0]["description"] | "", sizeof(weather.description));
      strlcpy(weather.main,        doc["weather"][0]["main"]        | "", sizeof(weather.main));
      weather.valid       = true;
      weather.last_update = millis();
    }
  }
  http.end();

  // Regenvorhersage (nächste 12h)
  url = "http://api.openweathermap.org/data/2.5/forecast?q=";
  url += sysConfig.owm_city;
  url += ",";
  url += sysConfig.owm_country;
  url += "&appid=";
  url += sysConfig.owm_key;
  url += "&units=metric&cnt=4";

  http.begin(url);
  code = http.GET();
  if (code == 200) {
    String body = http.getString();
    DynamicJsonDocument doc(4096);
    if (deserializeJson(doc, body) == DeserializationError::Ok) {
      weather.rain_forecast = false;
      JsonArray list = doc["list"].as<JsonArray>();
      for (JsonObject item : list) {
        float rain = item["rain"]["3h"] | 0.0f;
        if (rain > 1.0f) { weather.rain_forecast = true; break; }
        const char* cond = item["weather"][0]["main"] | "";
        if (strcmp(cond, "Rain") == 0 || strcmp(cond, "Drizzle") == 0 || strcmp(cond, "Thunderstorm") == 0) {
          weather.rain_forecast = true; break;
        }
      }
    }
  }
  http.end();

  Serial.printf("Wetter: %.1f°C, %.0f%%, Regen: %.1fmm, Vorhersage: %s, %s\n",
    weather.temp, weather.humidity, weather.rain_1h,
    weather.rain_forecast ? "ja" : "nein", weather.description);
}

// ═══════════════════════════════════════════════════════════════════
//  MQTT
// ═══════════════════════════════════════════════════════════════════

void connectMqtt() {
  if (!sysConfig.mqtt_enabled || mqttClient.connected()) return;
  char clientId[32];
  snprintf(clientId, sizeof(clientId), "irrigation-%06X", (uint32_t)(ESP.getEfuseMac() & 0xFFFFFF));
  if (mqttClient.connect(clientId, sysConfig.mqtt_user, sysConfig.mqtt_pass)) {
    mqttConnected = true;
    Serial.println(F("MQTT verbunden"));
    // Pump-Kommandos abonnieren
    for (int i = 0; i < MAX_CHANNELS; i++) {
      char topic[80];
      snprintf(topic, sizeof(topic), "%s/ch%d/pump/command", MQTT_DEVICE_TOPIC, i);
      mqttClient.subscribe(topic);
    }
  } else {
    mqttConnected = false;
  }
}

void mqttCallback(char* topic, byte* payload, unsigned int length) {
  char msg[64] = {0};
  memcpy(msg, payload, min((int)length, 63));

  // "irrigation/ch0/pump/command" → channel auslesen
  int ch = -1;
  for (int i = 0; i < MAX_CHANNELS; i++) {
    char t[80];
    snprintf(t, sizeof(t), "%s/ch%d/pump/command", MQTT_DEVICE_TOPIC, i);
    if (strcmp(topic, t) == 0) { ch = i; break; }
  }
  if (ch < 0) return;

  if (strcasecmp(msg, "ON") == 0)  startPump(ch);
  if (strcasecmp(msg, "OFF") == 0) stopPump(ch);
}

void publishMqtt() {
  if (!sysConfig.mqtt_enabled || !mqttClient.connected()) return;
  char topic[80], payload[64];

  for (int i = 0; i < sysConfig.active_channels; i++) {
    snprintf(topic,   sizeof(topic),   "%s/ch%d/moisture",   MQTT_DEVICE_TOPIC, i);
    snprintf(payload, sizeof(payload), "%d", chState[i].moisture_pct);
    mqttClient.publish(topic, payload, true);

    snprintf(topic,   sizeof(topic),   "%s/ch%d/pump/state", MQTT_DEVICE_TOPIC, i);
    mqttClient.publish(topic, chState[i].pump_running ? "ON" : "OFF", true);
  }

  snprintf(payload, sizeof(payload), "%lu", millis() / 1000);
  snprintf(topic,   sizeof(topic),   "%s/uptime", MQTT_DEVICE_TOPIC);
  mqttClient.publish(topic, payload, true);

  snprintf(payload, sizeof(payload), "%d", WiFi.RSSI());
  snprintf(topic,   sizeof(topic),   "%s/rssi", MQTT_DEVICE_TOPIC);
  mqttClient.publish(topic, payload, true);

  if (sysConfig.water_level_enabled && waterLevel_pct >= 0) {
    snprintf(topic,   sizeof(topic),   "%s/water_level", MQTT_DEVICE_TOPIC);
    snprintf(payload, sizeof(payload), "%d", waterLevel_pct);
    mqttClient.publish(topic, payload, true);
  }

  if (weather.valid) {
    snprintf(topic,   sizeof(topic),   "%s/weather/temp",     MQTT_DEVICE_TOPIC);
    snprintf(payload, sizeof(payload), "%.1f", weather.temp);
    mqttClient.publish(topic, payload, true);

    snprintf(topic,   sizeof(topic),   "%s/weather/humidity", MQTT_DEVICE_TOPIC);
    snprintf(payload, sizeof(payload), "%.0f", weather.humidity);
    mqttClient.publish(topic, payload, true);
  }
}

void setupHaDiscovery() {
  if (!sysConfig.mqtt_enabled || !mqttClient.connected()) return;
  char mac[13];
  snprintf(mac, sizeof(mac), "%012llX", ESP.getEfuseMac());

  for (int i = 0; i < sysConfig.active_channels; i++) {
    DynamicJsonDocument doc(1024);
    char topic[120], uid[40];

    // Feuchtigkeitssensor
    snprintf(uid,   sizeof(uid),   "irrigation_%s_ch%d_moist", mac, i);
    snprintf(topic, sizeof(topic), "%s/sensor/%s/config", MQTT_BASE_TOPIC, uid);
    doc.clear();
    doc["name"]         = String(chConfig[i].name) + " Feuchtigkeit";
    doc["unique_id"]    = uid;
    doc["state_topic"]  = String(MQTT_DEVICE_TOPIC) + "/ch" + i + "/moisture";
    doc["unit_of_measurement"] = "%";
    doc["device_class"] = "moisture";
    doc["icon"]         = "mdi:water-percent";
    JsonObject dev = doc.createNestedObject("device");
    dev["identifiers"][0] = String("irrigation_") + mac;
    dev["name"]           = "Smart Irrigation";
    dev["model"]          = "ESP32 v2.0";
    dev["manufacturer"]   = "DIY";
    String out; serializeJson(doc, out);
    mqttClient.publish(topic, out.c_str(), true);

    // Pumpen-Switch
    snprintf(uid,   sizeof(uid),   "irrigation_%s_ch%d_pump", mac, i);
    snprintf(topic, sizeof(topic), "%s/switch/%s/config", MQTT_BASE_TOPIC, uid);
    doc.clear();
    doc["name"]            = String(chConfig[i].name) + " Pumpe";
    doc["unique_id"]       = uid;
    doc["state_topic"]     = String(MQTT_DEVICE_TOPIC) + "/ch" + i + "/pump/state";
    doc["command_topic"]   = String(MQTT_DEVICE_TOPIC) + "/ch" + i + "/pump/command";
    doc["payload_on"]      = "ON";
    doc["payload_off"]     = "OFF";
    doc["icon"]            = "mdi:water-pump";
    dev = doc.createNestedObject("device");
    dev["identifiers"][0]  = String("irrigation_") + mac;
    dev["name"]            = "Smart Irrigation";
    serializeJson(doc, out);
    mqttClient.publish(topic, out.c_str(), true);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  TELEGRAM
// ═══════════════════════════════════════════════════════════════════

void sendTelegram(const String& msg) {
  if (!sysConfig.telegram_enabled || !bot) return;
  bot->sendMessage(sysConfig.telegram_chat, msg, "");
}

// ─── Telegram OTA – .bin-Datei direkt an den Bot schicken ────────
// Ablauf:
//   1. User schickt .bin-Datei an den Bot
//   2. Bot holt File-Path von der Telegram-API
//   3. Datei wird per HTTPS chunk-weise heruntergeladen
//   4. Chunks werden direkt in den Flash geschrieben (kein RAM-Puffer nötig)
//   5. ESP32 startet neu

void performTelegramOTA(const String& chat, const String& file_id) {
  bot->sendMessage(chat, "📥 Update empfangen – lade Firmware herunter...", "");
  Serial.println(F("Telegram OTA: Starte Download"));

  // Schritt 1: file_path von Telegram holen
  String getFileUrl = "https://api.telegram.org/bot";
  getFileUrl += sysConfig.telegram_token;
  getFileUrl += "/getFile?file_id=";
  getFileUrl += file_id;

  HTTPClient http;
  http.begin(secureClient, getFileUrl);
  int code = http.GET();
  if (code != 200) {
    bot->sendMessage(chat, "❌ Fehler beim Abrufen der Datei-Info (HTTP " + String(code) + ")", "");
    http.end();
    return;
  }

  String body = http.getString();
  http.end();

  DynamicJsonDocument meta(512);
  deserializeJson(meta, body);
  String file_path = meta["result"]["file_path"] | "";
  int file_size    = meta["result"]["file_size"]  | 0;

  if (file_path.isEmpty()) {
    bot->sendMessage(chat, "❌ Kein file_path erhalten.", "");
    return;
  }

  Serial.printf("Telegram OTA: file_path=%s, size=%d\n", file_path.c_str(), file_size);

  // Schritt 2: Datei herunterladen & direkt flashen
  String downloadUrl = "https://api.telegram.org/file/bot";
  downloadUrl += sysConfig.telegram_token;
  downloadUrl += "/";
  downloadUrl += file_path;

  http.begin(secureClient, downloadUrl);
  code = http.GET();
  if (code != HTTP_CODE_OK) {
    bot->sendMessage(chat, "❌ Download-Fehler (HTTP " + String(code) + ")", "");
    http.end();
    return;
  }

  int total = http.getSize();   // -1 bei chunked transfer
  WiFiClient* stream = http.getStreamPtr();

  // Alle Pumpen stoppen
  for (int i = 0; i < MAX_CHANNELS; i++) stopPump(i);

  if (!Update.begin(total > 0 ? total : UPDATE_SIZE_UNKNOWN)) {
    Update.printError(Serial);
    bot->sendMessage(chat, "❌ Update.begin fehlgeschlagen – zu wenig Speicher?", "");
    http.end();
    return;
  }

  uint8_t buf[1024];
  size_t written    = 0;
  unsigned long lastProgress = 0;
  int lastPct = -1;

  while (http.connected() && (total == -1 || written < (size_t)total)) {
    size_t avail = stream->available();
    if (!avail) { delay(1); continue; }

    size_t toRead = min(avail, sizeof(buf));
    size_t got    = stream->readBytes(buf, toRead);
    if (got == 0) break;

    if (Update.write(buf, got) != got) {
      Update.printError(Serial);
      bot->sendMessage(chat, "❌ Flash-Schreibfehler.", "");
      http.end();
      return;
    }
    written += got;

    // Fortschritt alle 10% melden
    if (total > 0) {
      int pct = (int)(written * 100 / total);
      if (pct / 10 != lastPct / 10) {
        lastPct = pct;
        String prog = "⬛";
        for (int p = 0; p < 10; p++) prog = (p < pct/10 ? "🟩" : "⬛") + prog;
        bot->sendMessage(chat, prog + " " + String(pct) + "%", "");
      }
    }

    // Watchdog zurücksetzen
    if (millis() - lastProgress > 5000) {
      lastProgress = millis();
      Serial.printf("OTA: %u / %d Bytes\n", written, total);
    }
  }

  http.end();

  if (Update.end(true)) {
    String ok = "✅ *Update erfolgreich!*\n";
    ok += String(written / 1024) + " kB geflasht.\nNeustart in 3 Sekunden...";
    bot->sendMessage(chat, ok, "Markdown");
    logEvent("ota", -1, "Telegram OTA erfolgreich");
    Serial.println(F("Telegram OTA: Erfolgreich – Neustart"));
    delay(3000);
    ESP.restart();
  } else {
    Update.printError(Serial);
    bot->sendMessage(chat, "❌ Update.end fehlgeschlagen.", "");
  }
}

void handleTelegram() {
  if (!bot) return;
  int n = bot->getUpdates(bot->last_message_received + 1);
  while (n) {
    for (int i = 0; i < n; i++) {
      String chat = bot->messages[i].chat_id;
      // Nur erlaubten Chat beantworten
      if (chat != String(sysConfig.telegram_chat)) {
        bot->sendMessage(chat, "⛔ Nicht autorisiert.", "");
        continue;
      }
      String text = bot->messages[i].text;
      text.trim();
      Serial.println("Telegram: " + text);

      // ── Telegram OTA: .bin-Datei direkt an den Bot schicken ──────
      String file_id = "";
      String file_name = "";
      if (bot->messages[i].type == "document") {
        file_id   = bot->messages[i].file_id;
        file_name = bot->messages[i].file_name;
      }
      if (file_id.length() > 0 && file_name.endsWith(".bin")) {
        performTelegramOTA(chat, file_id);
        n = bot->getUpdates(bot->last_message_received + 1);
        continue;
      }

      if (text == "/start" || text == "/info") {
        String reply = "🌱 *Smart Irrigation v2.0*\n";
        reply += "IP: `" + WiFi.localIP().toString() + "`\n\n";
        reply += "Befehle:\n";
        reply += "/status — Systemübersicht\n";
        reply += "/feuchte — Alle Sensorwerte\n";
        reply += "/wetter — Aktuelles Wetter\n";
        reply += "/giessen N [T] — Kanal N für T Sekunden (Standard-Dauer)\n";
        reply += "/stop N — Pumpe Kanal N stoppen\n";
        reply += "/stopall — Alle Pumpen stoppen\n";
        reply += "/auto N — Automatikmodus Kanal N umschalten\n";
        reply += "/log — Letzte Ereignisse\n";
        reply += "/ota — OTA-Update Anleitung\n";
        bot->sendMessage(chat, reply, "Markdown");
      }
      else if (text == "/status") {
        String r = "📊 *Systemstatus*\n";
        r += "Uptime: " + String(millis() / 3600000UL) + "h\n";
        r += "IP: " + WiFi.localIP().toString() + "\n";
        r += "RSSI: " + String(WiFi.RSSI()) + " dBm\n";
        r += "Kanäle aktiv: " + String(sysConfig.active_channels) + "\n";
        r += "Freier Heap: " + String(ESP.getFreeHeap() / 1024) + " kB\n";
        if (sysConfig.water_level_enabled && waterLevel_pct >= 0)
          r += "Wasserstand: " + String(waterLevel_pct) + "%\n";
        for (int j = 0; j < sysConfig.active_channels; j++) {
          PlantProfile p = getPlantProfile(chConfig[j].plant_idx);
          r += "\n" + String(p.emoji) + " *" + chConfig[j].name + "*\n";
          r += "  Feuchte: " + String(chState[j].moisture_pct) + "%";
          r += chState[j].pump_running ? " 💧 läuft" : "";
          r += chConfig[j].auto_mode  ? " ⚙️ auto" : " ✋ manuell";
          r += "\n";
        }
        bot->sendMessage(chat, r, "Markdown");
      }
      else if (text == "/feuchte") {
        String r = "💧 *Feuchtigkeitswerte*\n";
        for (int j = 0; j < sysConfig.active_channels; j++) {
          PlantProfile p = getPlantProfile(chConfig[j].plant_idx);
          r += p.emoji + " " + chConfig[j].name + ": " + String(chState[j].moisture_pct) + "%";
          if (chState[j].moisture_pct < chConfig[j].moisture_thresh) r += " ⚠️";
          r += "\n";
        }
        bot->sendMessage(chat, r, "Markdown");
      }
      else if (text == "/wetter") {
        if (!weather.valid) {
          bot->sendMessage(chat, "❌ Keine Wetterdaten verfügbar.", "");
        } else {
          String r = "🌡️ *Wetter (" + String(sysConfig.owm_city) + ")*\n";
          r += "Temperatur: " + String(weather.temp, 1) + "°C\n";
          r += "Luftfeuchtigkeit: " + String((int)weather.humidity) + "%\n";
          r += "Niederschlag: " + String(weather.rain_1h, 1) + " mm/h\n";
          r += "Vorhersage: " + String(weather.rain_forecast ? "🌧️ Regen" : "☀️ kein Regen") + "\n";
          r += "Status: " + String(weather.description) + "\n";
          bot->sendMessage(chat, r, "Markdown");
        }
      }
      else if (text.startsWith("/giessen")) {
        // /giessen N [T]
        int ch = -1, dur = -1;
        sscanf(text.c_str(), "/giessen %d %d", &ch, &dur);
        ch--;
        if (ch < 0 || ch >= sysConfig.active_channels) {
          bot->sendMessage(chat, "❌ Ungültiger Kanal.", "");
        } else {
          startPump(ch, dur);
          bot->sendMessage(chat, "✅ Kanal " + String(ch+1) + " gießt.", "");
        }
      }
      else if (text.startsWith("/stop ") || text.startsWith("/stop\n")) {
        int ch = -1;
        sscanf(text.c_str(), "/stop %d", &ch);
        ch--;
        if (ch < 0 || ch >= MAX_CHANNELS) {
          bot->sendMessage(chat, "❌ Ungültiger Kanal.", "");
        } else {
          stopPump(ch);
          bot->sendMessage(chat, "✅ Kanal " + String(ch+1) + " gestoppt.", "");
        }
      }
      else if (text == "/stopall") {
        for (int j = 0; j < MAX_CHANNELS; j++) stopPump(j);
        bot->sendMessage(chat, "✅ Alle Pumpen gestoppt.", "");
      }
      else if (text.startsWith("/auto")) {
        int ch = -1;
        sscanf(text.c_str(), "/auto %d", &ch);
        ch--;
        if (ch < 0 || ch >= sysConfig.active_channels) {
          bot->sendMessage(chat, "❌ Ungültiger Kanal.", "");
        } else {
          chConfig[ch].auto_mode = !chConfig[ch].auto_mode;
          saveChannelConfig(ch);
          bot->sendMessage(chat, "✅ Kanal " + String(ch+1) + " Automatikmodus: " + (chConfig[ch].auto_mode ? "AN" : "AUS"), "");
        }
      }
      else if (text == "/ota") {
        String r = "🔄 *OTA-Update per Telegram*\n\n";
        r += "Schicke einfach eine `.bin`-Datei direkt an diesen Chat.\n\n";
        r += "Datei erzeugen:\n";
        r += "`Sketch → Exportiere kompilierte Binärdatei`\n";
        r += "→ Dann die `.bin` aus dem Sketch-Ordner hier anhängen.\n\n";
        r += "⚠️ Alle Pumpen werden vor dem Flash gestoppt.";
        bot->sendMessage(chat, r, "Markdown");
      }
      else if (text == "/log") {
        if (!spiffsOk) {
          bot->sendMessage(chat, "❌ Kein SPIFFS.", "");
        } else {
          String r = "📋 *Letzte Ereignisse*\n";
          if (SPIFFS.exists("/events.json")) {
            File f = SPIFFS.open("/events.json", "r");
            if (f) {
              DynamicJsonDocument doc(4096);
              deserializeJson(doc, f);
              f.close();
              JsonArray evts = doc["events"].as<JsonArray>();
              int start = max(0, (int)evts.size() - 8);
              for (int j = start; j < (int)evts.size(); j++) {
                r += "`" + String(evts[j]["ts"].as<const char*>()) + "` ";
                r += evts[j]["msg"].as<const char*>();
                r += "\n";
              }
            }
          }
          bot->sendMessage(chat, r, "Markdown");
        }
      }
      else {
        bot->sendMessage(chat, "❓ Unbekannter Befehl. Schreibe /info", "");
      }
    }
    n = bot->getUpdates(bot->last_message_received + 1);
  }
}

// ═══════════════════════════════════════════════════════════════════
//  LOGGING (SPIFFS)
// ═══════════════════════════════════════════════════════════════════

String getTimestamp() {
  struct tm ti;
  if (!getLocalTime(&ti)) return "00:00:00";
  char buf[20];
  strftime(buf, sizeof(buf), "%Y-%m-%d %H:%M", &ti);
  return String(buf);
}

void logReading(int ch, uint8_t moisture) {
  if (!spiffsOk) return;
  char fname[24]; snprintf(fname, sizeof(fname), "/logs_ch%d.json", ch);

  DynamicJsonDocument doc(16384);
  if (SPIFFS.exists(fname)) {
    File f = SPIFFS.open(fname, "r");
    if (f) { deserializeJson(doc, f); f.close(); }
  }
  if (!doc.containsKey("readings")) doc.createNestedArray("readings");

  JsonArray readings = doc["readings"].as<JsonArray>();
  // Älteste Einträge löschen wenn voll
  while ((int)readings.size() >= MAX_LOG_READINGS) readings.remove(0);

  JsonObject entry = readings.createNestedObject();
  entry["ts"]       = getTimestamp();
  entry["moisture"] = moisture;

  File f = SPIFFS.open(fname, "w");
  if (f) { serializeJson(doc, f); f.close(); }
}

void logEvent(const char* type, int ch, const char* msg) {
  Serial.printf("[EVENT] %s ch%d: %s\n", type, ch, msg);
  if (!spiffsOk) return;

  DynamicJsonDocument doc(16384);
  if (SPIFFS.exists("/events.json")) {
    File f = SPIFFS.open("/events.json", "r");
    if (f) { deserializeJson(doc, f); f.close(); }
  }
  if (!doc.containsKey("events")) doc.createNestedArray("events");

  JsonArray events = doc["events"].as<JsonArray>();
  while ((int)events.size() >= MAX_LOG_EVENTS) events.remove(0);

  JsonObject e = events.createNestedObject();
  e["ts"]   = getTimestamp();
  e["type"] = type;
  e["ch"]   = ch;
  e["msg"]  = msg;

  File f = SPIFFS.open("/events.json", "w");
  if (f) { serializeJson(doc, f); f.close(); }
}

String getLogsJson(int ch, const String& range) {
  if (!spiffsOk) return "{}";
  char fname[24]; snprintf(fname, sizeof(fname), "/logs_ch%d.json", ch);
  if (!SPIFFS.exists(fname)) return "{\"readings\":[],\"events\":[]}";

  DynamicJsonDocument doc(16384);
  File f = SPIFFS.open(fname, "r");
  if (!f) return "{}";
  deserializeJson(doc, f);
  f.close();

  // Bei kleinerem Range Daten reduzieren
  int keep = MAX_LOG_READINGS;
  if (range == "24h") keep = 24;
  else if (range == "7d") keep = 24 * 7;

  JsonArray readings = doc["readings"].as<JsonArray>();
  while ((int)readings.size() > keep) readings.remove(0);

  String out;
  serializeJson(doc, out);
  return out;
}

// ═══════════════════════════════════════════════════════════════════
//  DISPLAY
// ═══════════════════════════════════════════════════════════════════

void updateDisplay() {
  #if DISPLAY_TYPE == 1
    // OLED SSD1306 – rotierendes Info-Display
    static uint8_t page = 0;
    display.clearDisplay();
    display.setTextSize(1);
    display.setCursor(0, 0);

    if (page == 0) {
      // Systeminfos
      display.println(F("=Smart Irrigation="));
      display.print(WiFi.localIP().toString());
      display.print(F(" "));
      display.print(WiFi.RSSI());
      display.println(F("dBm"));
      display.print(F("Heap: "));
      display.print(ESP.getFreeHeap() / 1024);
      display.println(F(" kB"));
      if (sysConfig.water_level_enabled && waterLevel_pct >= 0) {
        display.print(F("Wasser: "));
        display.print(waterLevel_pct);
        display.println(F("%"));
      }
    } else {
      // Kanal-Info
      int ch = (page - 1) % sysConfig.active_channels;
      PlantProfile p = getPlantProfile(chConfig[ch].plant_idx);
      display.print(chConfig[ch].name);
      display.println(chState[ch].pump_running ? F(" PUMP") : F(""));
      display.print(p.name_de);
      display.println();
      display.print(F("Feuchte: "));
      display.print(chState[ch].moisture_pct);
      display.println(F("%"));
      display.print(chConfig[ch].auto_mode ? F("Auto") : F("Manuell"));
      if (chState[ch].moisture_pct < chConfig[ch].moisture_thresh)
        display.print(F(" TROCKEN!"));
    }

    display.display();
    page = (page + 1) % (sysConfig.active_channels + 1);

  #elif DISPLAY_TYPE == 2
    // LCD I2C
    static uint8_t page = 0;
    display.clear();
    if (page == 0) {
      display.setCursor(0, 0); display.print(F("Smart Irrigation"));
      display.setCursor(0, 1);
      if (WiFi.isConnected()) {
        display.print(WiFi.localIP().toString());
      } else {
        display.print(F("Kein WiFi"));
      }
    } else {
      int ch = (page - 1) % sysConfig.active_channels;
      display.setCursor(0, 0); display.print(chConfig[ch].name);
      display.setCursor(0, 1);
      display.print(F("Feuchte: "));
      display.print(chState[ch].moisture_pct);
      display.print(F("%"));
      if (chState[ch].pump_running) display.print(F(" P"));
    }
    page = (page + 1) % (sysConfig.active_channels + 1);

  #elif DISPLAY_TYPE == 3
    // TFT ILI9341 / ST7789
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_GREEN);
    tft.setTextSize(2);
    tft.setCursor(5, 5);
    tft.println(F("SmartIrrigation"));
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE);
    tft.setCursor(5, 30);
    tft.print(F("IP: ")); tft.println(WiFi.localIP());
    tft.setCursor(5, 45);
    tft.print(F("RSSI: ")); tft.print(WiFi.RSSI()); tft.println(F(" dBm"));

    int y = 65;
    for (int i = 0; i < min(sysConfig.active_channels, 4); i++) {
      PlantProfile p = getPlantProfile(chConfig[i].plant_idx);
      tft.setCursor(5, y);
      tft.setTextColor(TFT_CYAN);
      tft.print(chConfig[i].name);
      tft.setTextColor(TFT_WHITE);
      tft.print(F(": "));
      // Farbcodierung
      uint16_t col = TFT_GREEN;
      if (chState[i].moisture_pct < chConfig[i].moisture_thresh) col = TFT_RED;
      else if (chState[i].moisture_pct < chConfig[i].moisture_thresh + 10) col = TFT_YELLOW;
      tft.setTextColor(col);
      tft.print(chState[i].moisture_pct); tft.println(F("%"));
      y += 16;
    }

    if (weather.valid) {
      tft.setCursor(5, y + 5);
      tft.setTextColor(TFT_YELLOW);
      tft.print(weather.temp, 1); tft.print(F("°C "));
      tft.print((int)weather.humidity); tft.println(F("% rH"));
    }
  #endif
}

// ═══════════════════════════════════════════════════════════════════
//  OTA
// ═══════════════════════════════════════════════════════════════════

void setupOTA() {
  ArduinoOTA.setHostname(HOSTNAME);
  ArduinoOTA.setPassword(OTA_PASSWORD);

  ArduinoOTA.onStart([]() {
    Serial.println(F("OTA: Start"));
    // Alle Pumpen sicherheitshalber stoppen
    for (int i = 0; i < MAX_CHANNELS; i++) stopPump(i);
  });
  ArduinoOTA.onEnd([]() {
    Serial.println(F("OTA: Ende – Neustart"));
  });
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    Serial.printf("OTA: %u%%\r", progress * 100 / total);
  });
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA Fehler[%u]\n", error);
  });
  ArduinoOTA.begin();
  Serial.println(F("OTA bereit"));
}

// ═══════════════════════════════════════════════════════════════════
//  STATUS JSON
// ═══════════════════════════════════════════════════════════════════

String buildStatusJson() {
  DynamicJsonDocument doc(4096);
  doc["uptime"]       = millis() / 1000;
  doc["heap"]         = ESP.getFreeHeap();
  doc["rssi"]         = WiFi.RSSI();
  doc["ip"]           = WiFi.localIP().toString();
  doc["channels"]     = sysConfig.active_channels;
  doc["water_level"]  = waterLevel_pct;

  JsonArray ch = doc.createNestedArray("ch");
  for (int i = 0; i < sysConfig.active_channels; i++) {
    JsonObject o = ch.createNestedObject();
    o["id"]          = i;
    o["name"]        = chConfig[i].name;
    o["enabled"]     = chConfig[i].enabled;
    o["plant_idx"]   = chConfig[i].plant_idx;
    o["moisture"]    = chState[i].moisture_pct;
    o["pump"]        = chState[i].pump_running;
    o["auto_mode"]   = chConfig[i].auto_mode;
    o["thresh"]      = chConfig[i].moisture_thresh;
    o["duration"]    = chConfig[i].water_duration;
    o["total_w"]     = chState[i].total_waterings;
    o["dry_adc"]     = chConfig[i].dry_adc;
    o["wet_adc"]     = chConfig[i].wet_adc;
    o["raw_adc"]     = chState[i].raw_adc;
  }

  if (weather.valid) {
    JsonObject w = doc.createNestedObject("weather");
    w["temp"]         = weather.temp;
    w["humidity"]     = weather.humidity;
    w["rain_1h"]      = weather.rain_1h;
    w["rain_forecast"]= weather.rain_forecast;
    w["description"]  = weather.description;
    w["main"]         = weather.main;
    w["city"]         = sysConfig.owm_city;
  }

  String out;
  serializeJson(doc, out);
  return out;
}

String buildConfigJson() {
  DynamicJsonDocument doc(8192);

  // System
  JsonObject sys = doc.createNestedObject("system");
  sys["active_channels"]    = sysConfig.active_channels;
  sys["mqtt_server"]        = sysConfig.mqtt_server;
  sys["mqtt_port"]          = sysConfig.mqtt_port;
  sys["mqtt_user"]          = sysConfig.mqtt_user;
  sys["mqtt_enabled"]       = sysConfig.mqtt_enabled;
  sys["owm_city"]           = sysConfig.owm_city;
  sys["owm_country"]        = sysConfig.owm_country;
  sys["weather_enabled"]    = sysConfig.weather_enabled;
  sys["telegram_enabled"]   = sysConfig.telegram_enabled;
  sys["telegram_chat"]      = sysConfig.telegram_chat;
  sys["water_level_enabled"]= sysConfig.water_level_enabled;

  // Kanäle
  JsonArray ch = doc.createNestedArray("channels");
  for (int i = 0; i < MAX_CHANNELS; i++) {
    JsonObject o = ch.createNestedObject();
    o["id"]        = i;
    o["name"]      = chConfig[i].name;
    o["enabled"]   = chConfig[i].enabled;
    o["plant_idx"] = chConfig[i].plant_idx;
    o["thresh"]    = chConfig[i].moisture_thresh;
    o["duration"]  = chConfig[i].water_duration;
    o["interval"]  = chConfig[i].min_interval_h;
    o["auto_mode"] = chConfig[i].auto_mode;
    o["dry_adc"]   = chConfig[i].dry_adc;
    o["wet_adc"]   = chConfig[i].wet_adc;
  }

  // Pflanzendatenbank
  JsonArray plants = doc.createNestedArray("plants");
  for (int i = 0; i < PLANT_DB_COUNT; i++) {
    PlantProfile p = getPlantProfile(i);
    JsonObject o = plants.createNestedObject();
    o["idx"]         = i;
    o["name_de"]     = p.name_de;
    o["name_en"]     = p.name_en;
    o["emoji"]       = p.emoji;
    o["moist_min"]   = p.moisture_min;
    o["moist_max"]   = p.moisture_max;
    o["moist_ideal"] = p.moisture_ideal;
    o["dur"]         = p.watering_duration_s;
    o["interval"]    = p.min_interval_h;
    o["ow_sens"]     = p.overwater_sensitive;
    o["notes"]       = p.notes_de;
  }

  String out;
  serializeJson(doc, out);
  return out;
}

// ═══════════════════════════════════════════════════════════════════
//  WEB SERVER & REST API
// ═══════════════════════════════════════════════════════════════════

void setupWebServer() {
  // Statische HTML-Seite
  server.on("/", HTTP_GET, [](AsyncWebServerRequest* req) {
    req->send_P(200, "text/html", WEB_UI_HTML);
  });

  // OTA-Upload per Webbrowser
  server.on("/api/ota", HTTP_POST,
    [](AsyncWebServerRequest* req) {
      bool ok = !Update.hasError();
      AsyncWebServerResponse* r = req->beginResponse(200, "application/json",
        ok ? "{\"ok\":true,\"msg\":\"Update OK – Neustart...\"}"
           : "{\"ok\":false,\"msg\":\"Update fehlgeschlagen\"}");
      r->addHeader("Connection", "close");
      req->send(r);
      if (ok) {
        delay(500);
        for (int i = 0; i < MAX_CHANNELS; i++) stopPump(i);
        ESP.restart();
      }
    },
    [](AsyncWebServerRequest* req, String filename, size_t index, uint8_t* data, size_t len, bool final) {
      if (!index) {
        Serial.printf("OTA Web-Upload: %s\n", filename.c_str());
        if (!Update.begin(UPDATE_SIZE_UNKNOWN)) {
          Update.printError(Serial);
        }
      }
      if (Update.write(data, len) != len) Update.printError(Serial);
      if (final) {
        if (Update.end(true)) {
          Serial.printf("OTA fertig: %u Bytes\n", index + len);
        } else {
          Update.printError(Serial);
        }
      }
    }
  );
}

void setupApiEndpoints() {
  // Status
  server.on("/api/status", HTTP_GET, [](AsyncWebServerRequest* req) {
    req->send(200, "application/json", buildStatusJson());
  });

  // Konfiguration lesen
  server.on("/api/config", HTTP_GET, [](AsyncWebServerRequest* req) {
    req->send(200, "application/json", buildConfigJson());
  });

  // Konfiguration speichern
  AsyncCallbackJsonWebHandler* cfgHandler = new AsyncCallbackJsonWebHandler(
    "/api/config", [](AsyncWebServerRequest* req, JsonVariant& json) {
      JsonObject obj = json.as<JsonObject>();
      JsonObject sys = obj["system"];
      if (!sys.isNull()) {
        if (sys.containsKey("active_channels"))     sysConfig.active_channels     = sys["active_channels"];
        if (sys.containsKey("mqtt_server"))         strlcpy(sysConfig.mqtt_server,  sys["mqtt_server"],  sizeof(sysConfig.mqtt_server));
        if (sys.containsKey("mqtt_port"))           sysConfig.mqtt_port           = sys["mqtt_port"];
        if (sys.containsKey("mqtt_user"))           strlcpy(sysConfig.mqtt_user,    sys["mqtt_user"],    sizeof(sysConfig.mqtt_user));
        if (sys.containsKey("mqtt_pass"))           strlcpy(sysConfig.mqtt_pass,    sys["mqtt_pass"],    sizeof(sysConfig.mqtt_pass));
        if (sys.containsKey("mqtt_enabled"))        sysConfig.mqtt_enabled        = sys["mqtt_enabled"];
        if (sys.containsKey("owm_key"))             strlcpy(sysConfig.owm_key,      sys["owm_key"],      sizeof(sysConfig.owm_key));
        if (sys.containsKey("owm_city"))            strlcpy(sysConfig.owm_city,     sys["owm_city"],     sizeof(sysConfig.owm_city));
        if (sys.containsKey("owm_country"))         strlcpy(sysConfig.owm_country,  sys["owm_country"],  sizeof(sysConfig.owm_country));
        if (sys.containsKey("weather_enabled"))     sysConfig.weather_enabled     = sys["weather_enabled"];
        if (sys.containsKey("telegram_token"))      strlcpy(sysConfig.telegram_token, sys["telegram_token"], sizeof(sysConfig.telegram_token));
        if (sys.containsKey("telegram_chat"))       strlcpy(sysConfig.telegram_chat,  sys["telegram_chat"],  sizeof(sysConfig.telegram_chat));
        if (sys.containsKey("telegram_enabled"))    sysConfig.telegram_enabled    = sys["telegram_enabled"];
        if (sys.containsKey("water_level_enabled")) sysConfig.water_level_enabled = sys["water_level_enabled"];
        saveConfig();
      }

      JsonArray channels = obj["channels"].as<JsonArray>();
      for (JsonObject c : channels) {
        int id = c["id"] | -1;
        if (id < 0 || id >= MAX_CHANNELS) continue;
        if (c.containsKey("name"))      strlcpy(chConfig[id].name, c["name"], sizeof(chConfig[id].name));
        if (c.containsKey("enabled"))   chConfig[id].enabled   = c["enabled"];
        if (c.containsKey("plant_idx")) chConfig[id].plant_idx = c["plant_idx"];
        if (c.containsKey("thresh"))    chConfig[id].moisture_thresh = c["thresh"];
        if (c.containsKey("duration"))  chConfig[id].water_duration  = c["duration"];
        if (c.containsKey("interval"))  chConfig[id].min_interval_h  = c["interval"];
        if (c.containsKey("auto_mode")) chConfig[id].auto_mode  = c["auto_mode"];
        saveChannelConfig(id);
      }

      req->send(200, "application/json", "{\"ok\":true}");
      logEvent("config", -1, "Konfiguration gespeichert");
    }
  );
  server.addHandler(cfgHandler);

  // Pumpe starten
  server.on("^\\/api\\/water\\/([0-9]+)$", HTTP_POST, [](AsyncWebServerRequest* req) {
    int ch = req->pathArg(0).toInt();
    if (ch < 0 || ch >= MAX_CHANNELS) {
      req->send(400, "application/json", "{\"ok\":false,\"msg\":\"Ungültiger Kanal\"}");
      return;
    }
    startPump(ch);
    req->send(200, "application/json", "{\"ok\":true}");
  });

  // Pumpe stoppen
  server.on("^\\/api\\/stop\\/([0-9]+)$", HTTP_POST, [](AsyncWebServerRequest* req) {
    int ch = req->pathArg(0).toInt();
    if (ch < 0 || ch >= MAX_CHANNELS) {
      req->send(400, "application/json", "{\"ok\":false,\"msg\":\"Ungültiger Kanal\"}");
      return;
    }
    stopPump(ch);
    req->send(200, "application/json", "{\"ok\":true}");
  });

  // Kalibrierung – Trockenwert
  server.on("^\\/api\\/calibrate\\/dry\\/([0-9]+)$", HTTP_POST, [](AsyncWebServerRequest* req) {
    int ch = req->pathArg(0).toInt();
    if (ch < 0 || ch >= MAX_CHANNELS) {
      req->send(400, "application/json", "{\"ok\":false}");
      return;
    }
    int raw = readMoisture(ch);
    chConfig[ch].dry_adc = raw;
    saveChannelConfig(ch);
    char buf[64]; snprintf(buf, sizeof(buf), "{\"ok\":true,\"adc\":%d}", raw);
    req->send(200, "application/json", buf);
    logEvent("calib_dry", ch, "Trockenwert gesetzt");
  });

  // Kalibrierung – Nasswert
  server.on("^\\/api\\/calibrate\\/wet\\/([0-9]+)$", HTTP_POST, [](AsyncWebServerRequest* req) {
    int ch = req->pathArg(0).toInt();
    if (ch < 0 || ch >= MAX_CHANNELS) {
      req->send(400, "application/json", "{\"ok\":false}");
      return;
    }
    int raw = readMoisture(ch);
    chConfig[ch].wet_adc = raw;
    saveChannelConfig(ch);
    char buf[64]; snprintf(buf, sizeof(buf), "{\"ok\":true,\"adc\":%d}", raw);
    req->send(200, "application/json", buf);
    logEvent("calib_wet", ch, "Nasswert gesetzt");
  });

  // Logs
  server.on("/api/logs", HTTP_GET, [](AsyncWebServerRequest* req) {
    int ch = 0;
    String range = "24h";
    if (req->hasParam("channel")) ch    = req->getParam("channel")->value().toInt();
    if (req->hasParam("range"))   range = req->getParam("range")->value();
    req->send(200, "application/json", getLogsJson(ch, range));
  });

  // Telegram Test
  server.on("/api/telegram/test", HTTP_POST, [](AsyncWebServerRequest* req) {
    sendTelegram("🔔 Testnachricht von Smart Irrigation!");
    req->send(200, "application/json", "{\"ok\":true}");
  });

  // Wetter manuell aktualisieren
  server.on("/api/weather/update", HTTP_POST, [](AsyncWebServerRequest* req) {
    updateWeather();
    req->send(200, "application/json", "{\"ok\":true}");
  });

  // SPIFFS-Info
  server.on("/api/fs", HTTP_GET, [](AsyncWebServerRequest* req) {
    char buf[128];
    size_t total = SPIFFS.totalBytes();
    size_t used  = SPIFFS.usedBytes();
    snprintf(buf, sizeof(buf), "{\"total\":%u,\"used\":%u,\"free\":%u}", total, used, total-used);
    req->send(200, "application/json", buf);
  });

  // 404
  server.onNotFound([](AsyncWebServerRequest* req) {
    req->send(404, "application/json", "{\"error\":\"Not found\"}");
  });
}
