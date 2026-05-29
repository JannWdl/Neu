# Lokaler Test ohne ESP32

Mit `local_test_server.py` kann die Weboberfläche am PC getestet werden.

## Start

```bash
python local_test_server.py
```

Dann öffnen:

```text
http://127.0.0.1:8080/
```

## Testbar

- Laden von `index.html`
- Setup-Assistent
- Dashboard-Wechsel
- Speichern von Einstellungen
- Mock-Statusdaten
- Mock-API-Endpunkte

## Nicht testbar

- echte ADC-Werte
- echte Relais/Pumpen
- ESP32-WLAN-AP
- MicroPython-Speicherverhalten
- echte MQTT/Telegram-Hardwareinteraktion

## Config zurücksetzen

Der lokale Server speichert Mock-Konfigurationen lokal. Zum Zurücksetzen die lokale Config-Datei löschen und den Server neu starten.
