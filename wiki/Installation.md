# Installation

## Voraussetzungen

- ESP32, empfohlen ESP32-WROOM
- Python 3 am PC
- USB-Verbindung zum ESP32
- Projektdateien aus dem Repository

Der Installer nutzt bzw. installiert:

```bash
pip install esptool mpremote
```

## Standardinstallation

Windows:

```bash
python install.py COM8
```

Linux/macOS:

```bash
python install.py /dev/ttyUSB0
```

Der Installer führt aus:

1. Tools prüfen/installieren
2. MicroPython-Firmware herunterladen
3. Flash löschen
4. Firmware schreiben
5. Projektdateien übertragen
6. ESP32 neu starten

## Nur Dateien neu übertragen

```bash
python install.py COM8 --skip-flash
```

Das ist sinnvoll nach Änderungen an `.py` oder `index.html`.

## Eigene Firmware verwenden

```bash
python install.py COM8 --bin firmware.bin
```

## Häufige Probleme

### Port unbekannt

Windows: Geräte-Manager öffnen und unter Anschlüsse nachsehen.

Linux/macOS:

```bash
ls /dev/ttyUSB* /dev/ttyACM*
```

### Flashen schlägt fehl

- BOOT-Taste am ESP32 gedrückt halten.
- USB-Kabel tauschen.
- Treiber installieren.
- Anderen USB-Port verwenden.
