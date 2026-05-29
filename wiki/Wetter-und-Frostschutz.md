# Wetter und Frostschutz

Das Projekt kann Wetterdaten über OpenWeatherMap abrufen.

## Einrichtung

1. OpenWeatherMap-API-Key erstellen.
2. In der Weboberfläche Wetter aktivieren.
3. API-Key, Stadt und Land eintragen.
4. Regenpause und Frostschutz nach Bedarf aktivieren.

## Funktionen

- Temperatur
- Luftfeuchtigkeit
- Regenmenge
- Wetterbeschreibung
- Regenvorhersage
- Frostschutz

## Regenpause

Wenn Regen erkannt oder vorhergesagt wird, kann automatische Bewässerung pausiert werden.

## Frostschutz

Unterhalb der konfigurierten Temperaturgrenze wird nicht gegossen. Standard ist 4 °C.

Das verhindert zwar keine Eiszeit, aber wenigstens bewässert der ESP32 dann nicht motiviert bei Frost.
