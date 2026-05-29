# REST-API

Der Webserver stellt mehrere JSON-Endpunkte bereit.

## Übersicht

| Methode | Pfad | Beschreibung |
|---|---|---|
| `GET` | `/` | Weboberfläche |
| `GET` | `/index.html` | Weboberfläche |
| `GET` | `/api/status` | Systemstatus |
| `GET` | `/api/config` | Konfiguration lesen |
| `POST` | `/api/config` | Konfiguration speichern |
| `GET/POST` | `/api/water/<id>` | Bewässerung starten |
| `GET/POST` | `/api/stop/<id>` | Bewässerung stoppen |
| `GET/POST` | `/api/stopall` | Alle Pumpen stoppen |
| `GET` | `/api/logs?ch=0&limit=30` | Messwerte lesen |
| `GET` | `/api/events` | Ereignisse lesen |
| `GET` | `/api/stats` | Statistik lesen |
| `GET` | `/api/raw/<id>` | ADC-Rohwert lesen |
| `GET` | `/api/schedule` | Zeitplan lesen |
| `POST` | `/api/schedule` | Zeitplan speichern |
| `POST` | `/api/ota/upload` | Datei per OTA hochladen |
| `GET/POST` | `/api/reboot` | Neustart auslösen |

## Beispiel: Status lesen

```bash
curl http://smart-irrigation.local/api/status
```

## Beispiel: Konfiguration speichern

```bash
curl -X POST http://smart-irrigation.local/api/config \
  -H "Content-Type: application/json" \
  -d '{"system":{"setup_done":true}}'
```

## Hinweis zu POST-Anfragen

Der ESP32 hat wenig RAM. Der Webserver ist deshalb so gebaut, dass kleine JSON-Bodies gezielt gelesen und große Uploads gestreamt werden.
