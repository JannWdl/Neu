# Entwicklung

## Struktur

Das Projekt ist bewusst in mehrere Dateien getrennt:

- `boot.py` für WLAN und Setup-Portal
- `main.py` als Startpunkt
- `irrigation.py` für Bewässerungslogik
- `webserver.py` für API und Frontend-Auslieferung
- `config.py` für Speicherung und Migration
- optionale Module für Telegram, MQTT, Wetter und Display

## Änderungen testen

Nach Änderungen:

```bash
python install.py COM8 --skip-flash
```

Bei Änderungen am Frontend zuerst lokal testen:

```bash
python local_test_server.py
```

## Hinweise für Pull Requests

- Keine echten WLAN-Passwörter oder Tokens committen.
- Änderungen möglichst lokal testen.
- Bei API-Änderungen README/Wiki aktualisieren.
- Speicherverbrauch im Blick behalten. ESP32-RAM ist kein Luxushotel.
