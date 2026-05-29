# Troubleshooting

## ESP32 wird nicht erkannt

- USB-Kabel prüfen.
- Anderen USB-Port nutzen.
- Treiber installieren.
- COM-Port prüfen.
- BOOT-Taste beim Flashen gedrückt halten.

## Installation bricht ab

- Terminal als normaler Benutzer neu öffnen.
- Python prüfen:

```bash
python --version
```

- Tools manuell installieren:

```bash
pip install esptool mpremote
```

## Weboberfläche nicht erreichbar

- IP im seriellen Monitor prüfen.
- Direkt per IP öffnen.
- Nicht blind auf `.local` verlassen.
- Sicherstellen, dass ESP32 im WLAN ist.

## Assistent/Dashboard reagiert nicht

- Browser-Konsole öffnen.
- Netzwerk-Tab prüfen.
- `/api/config` testen.
- Dateien neu übertragen:

```bash
python install.py COM8 --skip-flash
```

## `undefined dBm` oder `NaN kB`

Bei lokalem Testserver fehlen oder passen Mock-Werte nicht. Erwartet werden u. a. `rssi` und `heap` im Status-JSON.

## Sensor zeigt 0% oder 100%

- Trocken/Nass-Kalibrierung prüfen.
- Sensor-Pin prüfen.
- ADC1-Pin verwenden.
- Sensorversorgung prüfen.

## Pumpe startet verkehrt herum

Relais-Typ ändern:

- active-low
- active-high

## MQTT taucht nicht in Home Assistant auf

- MQTT-Broker erreichbar?
- Zugangsdaten korrekt?
- Base-Topic korrekt?
- Home Assistant Discovery aktiviert?
- ESP32 neu starten.

## Telegram antwortet nicht

- Bot-Token prüfen.
- Chat-ID prüfen.
- Telegram aktiviert?
- Internetverbindung des ESP32 prüfen.
