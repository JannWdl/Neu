# ╔══════════════════════════════════════════════════════════════════╗
# ║   Smart Irrigation v3.0 MicroPython — install.ps1               ║
# ║   Flasht MicroPython-Firmware und lädt alle Dateien hoch        ║
# ║                                                                  ║
# ║   Ausführen: .\install.ps1                                       ║
# ║   Bei Fehler "nicht geladen":                                    ║
# ║     Set-ExecutionPolicy RemoteSigned -Scope CurrentUser          ║
# ╚══════════════════════════════════════════════════════════════════╝
param(
    [string]$Port    = '',      # COM-Port, z.B. COM3 (auto-detect wenn leer)
    [switch]$SkipFirmware,      # Nur Dateien hochladen, Firmware überspringen
    [switch]$FilesOnly          # Alias für SkipFirmware
)
$ErrorActionPreference = 'Stop'
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path

function Step($n,$msg)  { Write-Host "`n━━━ [$n] $msg ━━━" -ForegroundColor Cyan }
function Ok($msg)       { Write-Host "    ✓ $msg" -ForegroundColor Green }
function Warn($msg)     { Write-Host "    ⚠ $msg" -ForegroundColor Yellow }
function Fail($msg)     {
    Write-Host "`nFEHLER: $msg" -ForegroundColor Red
    Read-Host 'Enter drücken zum Beenden' | Out-Null
    exit 1
}

Write-Host @'

 +--------------------------------------------------+
 |   Smart Irrigation v3.0 — MicroPython Installer  |
 |   ESP32 · Telegram · MQTT · OTA · Web-Interface  |
 +--------------------------------------------------+
'@ -ForegroundColor Green

# ══ [1] Python + pip prüfen ════════════════════════════════════════
Step 1 'Python'
try {
    $pyVer = python --version 2>&1
    Ok $pyVer
} catch {
    Fail 'Python nicht gefunden. Bitte von https://python.org herunterladen (Python 3.8+).'
}

# ══ [2] esptool + mpremote installieren ════════════════════════════
Step 2 'esptool + mpremote'

$pip = { python -m pip install --quiet @args }

& $pip esptool
Ok 'esptool'
& $pip mpremote
Ok 'mpremote'

# ══ [3] COM-Port ermitteln ══════════════════════════════════════════
Step 3 'Serial-Port'
Write-Host ''

if (-not $Port) {
    # Verfügbare Ports anzeigen
    $ports = python -c "
import serial.tools.list_ports
for p in serial.tools.list_ports.comports():
    print(p.device, '-', p.description)
" 2>$null
    if (-not $ports) {
        # Fallback: WMI
        $wmi = Get-WmiObject Win32_SerialPort -ErrorAction SilentlyContinue
        if ($wmi) {
            $ports = $wmi | ForEach-Object { "$($_.DeviceID) - $($_.Description)" }
        }
    }

    if ($ports) {
        Write-Host '    Verfügbare Ports:'
        $ports | ForEach-Object { Write-Host "      $_" }
    } else {
        Warn 'Keine Ports erkannt. ESP32 einstecken und Enter drücken.'
        Read-Host | Out-Null
    }
    $Port = (Read-Host '    COM-Port eingeben (z.B. COM3)').Trim()
}

if (-not $Port) { Fail 'Kein Port angegeben.' }
Ok "Port: $Port"

# ══ [4] MicroPython-Firmware flashen ═══════════════════════════════
if (-not $SkipFirmware -and -not $FilesOnly) {
    Step 4 'MicroPython-Firmware flashen'

    # Neueste Firmware-URL
    $FW_URL  = 'https://micropython.org/download/ESP32_GENERIC/ESP32_GENERIC-latest.bin'
    $FW_FILE = Join-Path $env:TEMP 'micropython_esp32.bin'

    Write-Host '    Lade MicroPython-Firmware herunter...'
    Invoke-WebRequest -Uri $FW_URL -OutFile $FW_FILE -UseBasicParsing
    Ok "Firmware: $FW_FILE"

    Write-Host '    Flash löschen...'
    python -m esptool --chip esp32 --port $Port erase_flash

    Write-Host '    MicroPython flashen...'
    python -m esptool --chip esp32 --port $Port --baud 460800 `
        write_flash -z 0x1000 $FW_FILE

    Ok 'MicroPython geflasht'
    Write-Host '    Warte 3 Sekunden...'
    Start-Sleep 3
} else {
    Step 4 'Firmware-Flash übersprungen (--SkipFirmware)'
}

# ══ [5] Projektdateien hochladen ═══════════════════════════════════
Step 5 'Projektdateien hochladen'

# Dateien die hochgeladen werden sollen
$FILES = @(
    'boot.py', 'main.py', 'config.py', 'plants_db.py',
    'irrigation.py', 'weather.py', 'telegram_bot.py',
    'mqtt_client.py', 'display.py', 'ota.py',
    'setup_portal.py', 'webserver.py'
)

function Upload-File($localPath, $remotePath) {
    python -m mpremote connect $Port cp $localPath ":$remotePath" 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Warn "Upload fehlgeschlagen: $localPath"
    } else {
        Ok $remotePath
    }
}

# Verzeichnisse anlegen
Write-Host '    Erstelle Verzeichnisse...'
python -m mpremote connect $Port exec "
import os
try:
    os.mkdir('/logs')
except:
    pass
" 2>$null | Out-Null

# Python-Dateien hochladen
foreach ($f in $FILES) {
    $local = Join-Path $ScriptDir $f
    if (Test-Path $local) {
        Upload-File $local $f
    } else {
        Warn "Datei nicht gefunden: $f"
    }
}

# config.json (falls vorhanden, nicht überschreiben wenn schon da)
$cfgLocal = Join-Path $ScriptDir 'config.json'
if (Test-Path $cfgLocal) {
    $cfgExists = python -m mpremote connect $Port exec "
import os
try:
    os.stat('/config.json')
    print('exists')
except:
    print('missing')
" 2>$null
    if ($cfgExists -notmatch 'exists') {
        Upload-File $cfgLocal 'config.json'
    } else {
        Warn 'config.json bereits vorhanden – wird NICHT überschrieben (Konfiguration erhalten!)'
    }
}

Ok 'Alle Dateien hochgeladen'

# ══ [6] Neustart ═══════════════════════════════════════════════════
Step 6 'Neustart'
python -m mpremote connect $Port reset 2>$null | Out-Null
Ok 'ESP32 wird neu gestartet...'

# ══ Fertig ═══════════════════════════════════════════════════════
Write-Host @'

 +------------------------------------------------------+
 |  ✅ Installation abgeschlossen!                      |
 |                                                      |
 |  Der ESP32 startet jetzt.                            |
 |                                                      |
 |  Kein WLAN konfiguriert → AP-Modus:                 |
 |  1. WLAN suchen: SmartIrrigation-Setup               |
 |  2. Verbinden (kein Passwort)                        |
 |  3. Browser: http://192.168.4.1                      |
 |     → Nur WLAN-Name und Passwort eingeben            |
 |                                                      |
 |  Danach im Heimnetz (Telegram, MQTT usw.):           |
 |     http://smart-irrigation.local                    |
 |                                                      |
 |  Nur Dateien aktualisieren (ohne Firmware):          |
 |     .\install.ps1 -SkipFirmware                      |
 +------------------------------------------------------+
'@ -ForegroundColor Green
