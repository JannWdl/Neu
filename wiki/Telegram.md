# Telegram

Telegram ist optional und ermöglicht Steuerung und Statusabfragen aus der Ferne.

## Einrichtung

1. `@BotFather` öffnen.
2. Neuen Bot erstellen.
3. Bot-Token kopieren.
4. Chat-ID ermitteln.
5. In der Weboberfläche Telegram aktivieren.
6. Token und Chat-ID speichern.

## Befehle

| Befehl | Funktion |
|---|---|
| `/start` oder `/info` | Hilfe anzeigen |
| `/status` | Systemstatus |
| `/feuchte` | Feuchtigkeitswerte |
| `/wetter` | Wetterdaten |
| `/giessen N [T]` | Kanal N optional T Sekunden gießen |
| `/stop N` | Kanal N stoppen |
| `/stopall` | alle Pumpen stoppen |
| `/auto N` | Automatik für Kanal N umschalten |
| `/stats` | Statistik anzeigen |
| `/duengen N` | Kanal als gedüngt markieren |
| `/log` | Ereignisse anzeigen |

## OTA per Telegram

Eine `.py`-Datei an den Bot senden. Der ESP32 übernimmt die Datei und startet danach neu.

## Sicherheit

Nur die konfigurierte Chat-ID ist autorisiert. Trotzdem sollte der Bot-Token nicht öffentlich ins Repository. Tokens in GitHub sind eine schlechte Idee, aber offenbar muss man das im Jahr 2026 immer noch sagen.
