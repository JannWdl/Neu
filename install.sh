#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════╗
# ║   Smart Irrigation v3.0 MicroPython — install.sh (Linux/macOS) ║
# ╚══════════════════════════════════════════════════════════════════╝
set -euo pipefail
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
ok()   { echo -e "${GREEN}    ✓ $*${NC}"; }
warn() { echo -e "${YELLOW}    ⚠ $*${NC}"; }
err()  { echo -e "${RED}\nFEHLER: $*${NC}"; exit 1; }
step() { echo -e "\n${GREEN}━━━ $* ━━━${NC}"; }

SKIP_FW=false
PORT=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-firmware|--files-only) SKIP_FW=true ;;
        --port) PORT="$2"; shift ;;
        *) PORT="$1" ;;
    esac
    shift
done

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo -e "${GREEN}"
echo " +--------------------------------------------------+"
echo " |   Smart Irrigation v3.0 — MicroPython Installer  |"
echo " |   ESP32 · Telegram · MQTT · OTA · Web-Interface  |"
echo " +--------------------------------------------------+"
echo -e "${NC}"

# ── [1] Python ──────────────────────────────────────────────────────
step "[1] Python"
python3 --version >/dev/null 2>&1 || err "Python3 nicht gefunden. Installieren mit: sudo apt install python3 python3-pip"
ok "$(python3 --version)"

# ── [2] esptool + mpremote ──────────────────────────────────────────
step "[2] esptool + mpremote"
pip3 install --quiet esptool mpremote
ok "esptool + mpremote"

# ── [3] Port ermitteln ──────────────────────────────────────────────
step "[3] Serial-Port"
if [[ -z "$PORT" ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        PORTS=( $(ls /dev/cu.usbserial-* /dev/cu.SLAB_USBtoUART* /dev/cu.usbmodem* 2>/dev/null) )
    else
        PORTS=( $(ls /dev/ttyUSB* /dev/ttyACM* 2>/dev/null) )
    fi

    if [[ ${#PORTS[@]} -eq 0 ]]; then
        warn "Kein Port erkannt. ESP32 einstecken."
        read -rp "    Port manuell eingeben: " PORT
    elif [[ ${#PORTS[@]} -eq 1 ]]; then
        PORT="${PORTS[0]}"
    else
        echo "    Verfügbare Ports:"
        for i in "${!PORTS[@]}"; do echo "      [$i] ${PORTS[$i]}"; done
        read -rp "    Auswahl [0]: " IDX
        PORT="${PORTS[${IDX:-0}]}"
    fi
fi
[[ -z "$PORT" ]] && err "Kein Port angegeben."
ok "Port: $PORT"

# ── [4] Firmware flashen ────────────────────────────────────────────
if [[ "$SKIP_FW" == false ]]; then
    step "[4] MicroPython-Firmware flashen"
    FW_URL="https://micropython.org/download/ESP32_GENERIC/ESP32_GENERIC-latest.bin"
    FW_FILE="/tmp/micropython_esp32.bin"

    echo "    Lade Firmware herunter..."
    curl -fsSL -o "$FW_FILE" "$FW_URL"
    ok "Firmware: $FW_FILE"

    echo "    Flash löschen..."
    python3 -m esptool --chip esp32 --port "$PORT" erase_flash

    echo "    MicroPython flashen..."
    python3 -m esptool --chip esp32 --port "$PORT" --baud 460800 \
        write_flash -z 0x1000 "$FW_FILE"

    ok "MicroPython geflasht"
    echo "    Warte 3 Sekunden..."
    sleep 3
else
    step "[4] Firmware-Flash übersprungen (--skip-firmware)"
fi

# ── [5] Dateien hochladen ───────────────────────────────────────────
step "[5] Projektdateien hochladen"

FILES=(
    boot.py main.py config.py plants_db.py
    irrigation.py weather.py telegram_bot.py
    mqtt_client.py display.py ota.py
    setup_portal.py webserver.py
)

# Verzeichnisse auf ESP32 anlegen
python3 -m mpremote connect "$PORT" exec "
import os
try:
    os.mkdir('/logs')
except:
    pass
" 2>/dev/null || true

# Dateien hochladen
for f in "${FILES[@]}"; do
    local_path="$SCRIPT_DIR/$f"
    if [[ -f "$local_path" ]]; then
        python3 -m mpremote connect "$PORT" cp "$local_path" ":/$f" 2>/dev/null && ok "$f" || warn "Upload fehlgeschlagen: $f"
    else
        warn "Nicht gefunden: $f"
    fi
done

# config.json nur hochladen wenn noch nicht vorhanden
CFG_LOCAL="$SCRIPT_DIR/config.json"
if [[ -f "$CFG_LOCAL" ]]; then
    CFG_EXISTS=$(python3 -m mpremote connect "$PORT" exec "
import os
try: os.stat('/config.json'); print('exists')
except: print('missing')
" 2>/dev/null || echo "missing")
    if [[ "$CFG_EXISTS" != *"exists"* ]]; then
        python3 -m mpremote connect "$PORT" cp "$CFG_LOCAL" ":/config.json" 2>/dev/null && ok "config.json" || warn "config.json Upload fehlgeschlagen"
    else
        warn "config.json bereits vorhanden – wird NICHT überschrieben (Konfiguration erhalten!)"
    fi
fi

ok "Alle Dateien hochgeladen"

# ── [6] Neustart ────────────────────────────────────────────────────
step "[6] Neustart"
python3 -m mpremote connect "$PORT" reset 2>/dev/null || true
ok "ESP32 wird neu gestartet"

# ── Fertig ──────────────────────────────────────────────────────────
echo -e "${GREEN}"
echo " +------------------------------------------------------+"
echo " |  ✅ Installation abgeschlossen!                      |"
echo " |                                                      |"
echo " |  Kein WLAN konfiguriert → AP-Modus:                 |"
echo " |  1. WLAN: SmartIrrigation-Setup (kein Passwort)     |"
echo " |  2. Browser: http://192.168.4.1                     |"
echo " |     → Nur WLAN-Name + Passwort eingeben             |"
echo " |                                                      |"
echo " |  Danach im Heimnetz:                                 |"
echo " |     http://smart-irrigation.local                   |"
echo " |                                                      |"
echo " |  Nur Dateien aktualisieren (kein Firmware-Flash):   |"
echo " |     ./install.sh --skip-firmware                    |"
echo " +------------------------------------------------------+"
echo -e "${NC}"
