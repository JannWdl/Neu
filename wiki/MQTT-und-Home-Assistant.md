# MQTT und Home Assistant

MQTT ist optional und dient zur Integration in Home Assistant oder andere Automatisierungssysteme.

## Einstellungen

In der Weboberfläche konfigurieren:

- MQTT aktivieren
- Server/IP
- Port, Standard `1883`
- Benutzername
- Passwort
- Base-Topic, Standard `irrigation`

## Topics

| Topic | Zweck |
|---|---|
| `irrigation/ch0/moisture` | Feuchtigkeit Kanal 1 |
| `irrigation/ch0/pump/state` | Pumpenstatus Kanal 1 |
| `irrigation/ch0/pump/command` | Pumpenbefehl Kanal 1 |
| `irrigation/water_level` | Tankfüllstand |
| `irrigation/weather/temp` | Wettertemperatur |
| `irrigation/weather/humidity` | Wetter-Luftfeuchte |

## Pumpen schalten

```text
Topic: irrigation/ch0/pump/command
Payload: ON
```

Stoppen:

```text
Topic: irrigation/ch0/pump/command
Payload: OFF
```

## Home Assistant Discovery

Bei erfolgreicher MQTT-Verbindung werden Sensoren und Schalter automatisch per Home-Assistant-Discovery veröffentlicht.
