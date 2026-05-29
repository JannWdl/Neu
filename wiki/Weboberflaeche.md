# Weboberfläche

Die Weboberfläche liegt in `index.html` und wird vom ESP32 über `webserver.py` ausgeliefert.

## Bereiche

### Dashboard

Zeigt:

- IP-Adresse
- WLAN-Signal
- freien Speicher
- Kanalstatus
- Feuchtigkeitswerte
- Pumpenstatus
- Wasserstand
- Wetter/DHT-Daten

### Kanäle

Pro Kanal einstellbar:

- Name
- aktiv/inaktiv
- Sensor-Pin
- Relais-Pin
- Relais-Typ
- Automatikmodus
- Feuchtigkeitsschwelle
- Ziel-Feuchte
- Gießdauer
- Mindestpause
- Fördermenge
- Düngerintervall

### Zeitplan

Feste Gießzeiten mit:

- Kanal
- Uhrzeit
- Dauer
- Wochentagen

### Statistik

Zeigt:

- Anzahl der Gießvorgänge
- Gesamtlaufzeit
- geschätzte Liter, wenn Fördermenge hinterlegt ist

### Logs

Zeigt Messwerte und Ereignisse.

### Einstellungen

Für:

- WLAN
- Telegram
- MQTT
- Wetter
- DHT-Sensor
- System
- OTA
