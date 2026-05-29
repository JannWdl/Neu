# Ersteinrichtung

## WLAN-Setup

Wenn keine WLAN-Daten gespeichert sind, startet der ESP32 einen Access Point:

```text
SSID: SmartIrrigation-Setup
URL:  http://192.168.4.1/
```

Ablauf:

1. Mit `SmartIrrigation-Setup` verbinden.
2. `http://192.168.4.1/` öffnen.
3. WLAN-Name und Passwort eingeben.
4. Speichern.
5. ESP32 startet neu.

Danach öffnest du:

```text
http://smart-irrigation.local/
```

Wenn das nicht klappt, die IP-Adresse aus dem Serial-Monitor verwenden.

## Setup-Assistent

Der Assistent führt durch:

1. Anzahl der aktiven Kanäle
2. Namen der Kanäle
3. Sensor- und Relais-Pins
4. Relais-Typ
5. Sensor-Kalibrierung
6. Gießmodus
7. optionale Module wie Telegram, MQTT, Wetter und DHT

## Assistent erneut starten

In der Weboberfläche unter:

```text
Einstellungen → System → Setup-Assistent erneut starten
```
