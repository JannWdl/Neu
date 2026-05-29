# Hardware und Verdrahtung

## Typische Komponenten

- ESP32-WROOM
- Kapazitive Bodenfeuchtigkeitssensoren
- 1 bis 8 Relaiskanäle
- 5V-Pumpen oder Ventile
- 5V-Netzteil
- Optional: DHT11/DHT22, Ultraschallsensor, Display

## Standard-Pins

| Kanal | Sensor/ADC | Relais |
|---|---:|---:|
| 1 | GPIO 34 | GPIO 16 |
| 2 | GPIO 35 | GPIO 17 |
| 3 | GPIO 32 | GPIO 18 |
| 4 | GPIO 33 | GPIO 19 |
| 5 | GPIO 36 | GPIO 21 |
| 6 | GPIO 39 | GPIO 22 |
| 7 | GPIO 25 | GPIO 23 |
| 8 | GPIO 26 | GPIO 27 |

Die Pins können in der Weboberfläche oder über `config.py` angepasst werden.

## ADC-Hinweis

Für Feuchtigkeitssensoren sollten ADC1-Pins genutzt werden. ADC2-Pins machen bei aktivem WLAN gerne Probleme. Wer sich das ausgedacht hat, hatte offenbar einen schlechten Tag.

## Relais

Viele Relaismodule sind **active-low**:

```text
LOW  = Relais an
HIGH = Relais aus
```

Wenn eine Pumpe sofort beim Start läuft, ist vermutlich der Relais-Typ falsch eingestellt.

## Stromversorgung

- Pumpen nicht über 3,3V betreiben.
- Kleine 5V-Pumpen können über VIN/5V funktionieren.
- Für mehrere Pumpen separates 5V-Netzteil verwenden.
- GND von ESP32 und externem Netzteil verbinden.
- Nur eine Pumpe läuft gleichzeitig, um Stromspitzen zu reduzieren.

## Sicherheit

- Keine offenen Leitungen in Wassernähe.
- Relaiskontakte sauber isolieren.
- Netzteile passend dimensionieren.
- Erst ohne Wasser testen.
