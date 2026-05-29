# Konfiguration

Die Konfiguration wird auf dem ESP32 als Datei gespeichert:

```text
/config.json
```

Die Defaults stehen in `config.py`.

## Wichtige Bereiche

| Bereich | Zweck |
|---|---|
| `wifi` | WLAN-SSID und Passwort |
| `system` | Hostname, aktive Kanäle, Zeitzone, NTP, Setup-Status |
| `channels` | Kanaleinstellungen |
| `telegram` | Bot-Token und Chat-ID |
| `mqtt` | MQTT-Server, Port, Zugangsdaten, Base-Topic |
| `weather` | OpenWeatherMap, Regenpause, Frostschutz |
| `sensor_dht` | lokaler DHT11/DHT22 |
| `water_level` | Tankfüllstand per Ultraschall |
| `schedule` | Zeitpläne |
| `notify` | Benachrichtigungseinstellungen |

## Konfiguration zurücksetzen

Über seriellen Zugriff oder mpremote kann `/config.json` gelöscht werden. Danach startet das System mit Defaults.

Beispiel:

```bash
mpremote connect COM8 fs rm /config.json
mpremote connect COM8 reset
```

Danach startet wieder die Ersteinrichtung.
