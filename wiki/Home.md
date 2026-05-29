# Smart Irrigation Wiki

Willkommen im Wiki zu **Smart Irrigation für ESP32**.

Dieses Projekt ist ein MicroPython-basiertes Bewässerungssystem mit Weboberfläche, Setup-Assistent, MQTT/Home Assistant, Telegram, Wetterdaten und OTA-Updates.

## Schnellnavigation

- [Installation](Installation)
- [Hardware und Verdrahtung](Hardware-und-Verdrahtung)
- [Ersteinrichtung](Ersteinrichtung)
- [Weboberfläche](Weboberflaeche)
- [Konfiguration](Konfiguration)
- [REST-API](REST-API)
- [Telegram](Telegram)
- [MQTT und Home Assistant](MQTT-und-Home-Assistant)
- [Wetter und Frostschutz](Wetter-und-Frostschutz)
- [Lokaler Test ohne ESP32](Lokaler-Test-ohne-ESP32)
- [Troubleshooting](Troubleshooting)

## Grundidee

Der ESP32 liest Feuchtigkeitswerte aus, entscheidet anhand der Konfiguration, ob gegossen werden soll, und schaltet über Relais kleine Pumpen oder Ventile. Die Bedienung läuft über eine lokale Weboberfläche. Externe Dienste wie Telegram, MQTT und Wetterdaten sind optional.

## Wichtig

Das Projekt ist ein DIY-System. Wasser und Elektronik sind gemeinsam ungefähr so entspannt wie Drucker und Updates. Verdrahtung und Stromversorgung müssen sauber geprüft werden.
