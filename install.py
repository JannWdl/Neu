#!/usr/bin/env python3
"""
install.py - Smart Irrigation Komplett-Installer für ESP32 (WROOM)

Macht alles in einem Durchgang:
  1. Prüft/installiert esptool & mpremote
  2. Lädt MicroPython-Firmware (oder nutzt lokale .bin)
  3. Löscht den ESP32-Flash komplett
  4. Flasht MicroPython
  5. Überträgt alle Projektdateien aus smart-irrigation.zip

Aufruf:
  python install.py                         (interaktiv)
  python install.py COM8                     (Port direkt)
  python install.py COM8 --bin firmware.bin  (lokale Firmware)
  python install.py COM8 --skip-flash        (nur Dateien, kein Flashen)

Voraussetzungen werden automatisch nachinstalliert:
  pip install esptool mpremote
"""

import sys
import os
import subprocess
import zipfile
import tempfile
import time
import json
import urllib.request

# ── Konstanten für ESP32 WROOM ───────────────────────────────────────
CHIP        = "esp32"
FLASH_ADDR  = "0x1000"      # Standard-ESP32 (WROOM): Bootloader-Offset
BAUD        = "460800"
ZIPNAME     = "smart-irrigation.zip"
MP_BOARD    = "ESP32_GENERIC"
MP_DL_BASE  = "https://micropython.org/resources/firmware/"
# Fallback-Firmware falls die Versions-Erkennung scheitert:
MP_FALLBACK = "ESP32_GENERIC-20251209-v1.27.0.bin"


def c(txt, color):
    codes = {"g": "92", "r": "91", "y": "93", "b": "94", "d": "90", "c": "96"}
    return f"\033[{codes.get(color,'0')}m{txt}\033[0m"


def run(cmd, timeout=None, check=False):
    """Führt einen Befehl aus, gibt (rc, stdout, stderr) zurück."""
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if check and r.returncode != 0:
            raise RuntimeError(r.stderr.strip() or r.stdout.strip())
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 1, "", "Timeout"
    except FileNotFoundError:
        return 127, "", "not found"


# ── 1. Tools prüfen / installieren ───────────────────────────────────
def ensure_tools():
    for mod in ("esptool", "mpremote"):
        rc, _, _ = run([sys.executable, "-m", mod, "version"], timeout=15)
        if rc not in (0,):
            # mpremote --version statt version
            rc2, _, _ = run([sys.executable, "-m", mod, "--help"], timeout=15)
            if rc2 != 0:
                print(c(f"  Installiere {mod}...", "y"))
                run([sys.executable, "-m", "pip", "install", "--quiet", mod], timeout=180)


# ── 2. Firmware besorgen ─────────────────────────────────────────────
def latest_firmware_filename():
    """Liest die MicroPython-Download-Seite und findet die neueste stabile .bin."""
    try:
        url = f"https://micropython.org/download/{MP_BOARD}/"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            html = r.read().decode("utf-8", "ignore")
        # Suche nach .bin-Dateien die NICHT preview/unstable sind
        import re
        bins = re.findall(r'(ESP32_GENERIC-\d{8}-v[\d.]+\.bin)', html)
        # Stabile Versionen (kein 'preview')
        stable = [b for b in bins if "preview" not in b.lower()]
        if stable:
            return stable[0]   # erste = neueste
    except Exception as e:
        print(c(f"  Versions-Erkennung fehlgeschlagen: {e}", "d"))
    return MP_FALLBACK


def get_firmware(local_bin):
    """Gibt den Pfad zur Firmware-.bin zurück (lokal oder heruntergeladen)."""
    if local_bin:
        if not os.path.exists(local_bin):
            print(c(f"❌  Firmware nicht gefunden: {local_bin}", "r"))
            sys.exit(1)
        print(c(f"📁  Lokale Firmware: {local_bin}", "g"))
        return local_bin

    fname = latest_firmware_filename()
    url   = MP_DL_BASE + fname
    dest  = os.path.join(tempfile.gettempdir(), fname)

    if os.path.exists(dest) and os.path.getsize(dest) > 100000:
        print(c(f"📁  Firmware im Cache: {fname}", "g"))
        return dest

    print(c(f"⬇   Lade MicroPython: {fname}", "c"))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
            total = int(r.headers.get("Content-Length", 0))
            done = 0
            while True:
                chunk = r.read(16384)
                if not chunk:
                    break
                f.write(chunk)
                done += len(chunk)
                if total:
                    pct = int(done / total * 100)
                    bar = ("█" * (pct // 5)).ljust(20)
                    print(f"\r    [{bar}] {pct:3d}%", end="", flush=True)
        print()
        print(c(f"✓   {done//1024} kB geladen", "g"))
        return dest
    except Exception as e:
        print(c(f"\n❌  Download fehlgeschlagen: {e}", "r"))
        print(c(f"    Tipp: Firmware manuell laden von {url}", "y"))
        print(c(f"    und mit  --bin <datei>  übergeben.", "y"))
        sys.exit(1)


# ── 3+4. Flash löschen & MicroPython schreiben ───────────────────────
def erase_flash(port):
    print(c("\n🧹  Lösche Flash...", "c"))
    rc, out, err = run(
        [sys.executable, "-m", "esptool", "--chip", CHIP, "--port", port, "erase_flash"],
        timeout=120
    )
    if rc != 0:
        print(c(f"❌  Löschen fehlgeschlagen:\n{err or out}", "r"))
        print(c("    BOOT-Taste gedrückt halten beim Verbinden?", "y"))
        sys.exit(1)
    print(c("✓   Flash gelöscht", "g"))


def flash_firmware(port, bin_path):
    print(c("\n⚡  Flashe MicroPython...", "c"))
    rc, out, err = run(
        [sys.executable, "-m", "esptool", "--chip", CHIP, "--port", port,
         "--baud", BAUD, "write_flash", "-z", FLASH_ADDR, bin_path],
        timeout=180
    )
    if rc != 0:
        print(c(f"❌  Flashen fehlgeschlagen:\n{err or out}", "r"))
        sys.exit(1)
    print(c("✓   MicroPython geflasht", "g"))
    print(c("    Warte auf Neustart...", "d"))
    time.sleep(4)


# ── 5. Projektdateien übertragen ─────────────────────────────────────
def _interrupt(port):
    """Schickt Ctrl-C an den ESP um laufenden Code zu stoppen."""
    try:
        import serial
        with serial.Serial(port, 115200, timeout=1) as s:
            s.write(b"\x03\x03")   # 2x Ctrl-C
            time.sleep(0.4)
    except Exception:
        # kein pyserial: mpremote soft-reset versuchen
        run([sys.executable, "-m", "mpremote", "connect", port, "soft-reset"], timeout=8)
        time.sleep(0.5)

def mp_cp(port, local, remote):
    rc, _, err = run(
        [sys.executable, "-m", "mpremote", "connect", port, "cp", local, f":{remote}"],
        timeout=40
    )
    return rc == 0, err


def upload_files(port, zip_path):
    print(c("\n📂  Übertrage Projektdateien...", "c"))
    # ESP anhalten falls schon Code läuft (sonst blockiert die serielle Verbindung)
    _interrupt(port)
    time.sleep(0.5)

    with zipfile.ZipFile(zip_path) as zf:
        entries = sorted([
            n for n in zf.namelist()
            if (n.endswith(".py") or n.endswith(".html") or n.endswith(".md"))
               and "/" not in n.rstrip("/")
        ])
        if not entries:    # GitHub-ZIP mit Unterordner
            prefix = zf.namelist()[0].split("/")[0] + "/"
            entries = sorted([
                n for n in zf.namelist()
                if (n.endswith(".py") or n.endswith(".html") or n.endswith(".md"))
                   and n.count("/") == 1 and n.startswith(prefix)
            ])
          
        # boot.py als ALLERLETZTES übertragen – sobald diese Datei existiert,
        # startet der ESP32 ggf. Code, der die serielle Verbindung blockiert.
        def _order(name):
            base = os.path.basename(name)
            if base == "boot.py": return 2  # Höchster Wert = ganz am Schluss
            if base == "main.py": return 1
            return 0
        entries.sort(key=_order)

        total = len(entries)
        ok, fail = [], []

        with tempfile.TemporaryDirectory() as tmp:
            for i, entry in enumerate(entries):
                fname = os.path.basename(entry)
                pct   = int(i / total * 100)
                bar   = ("█" * (pct // 5)).ljust(20)
                print(f"  [{bar}] {pct:3d}%  {fname:<22}", end="  ", flush=True)

                data  = zf.read(entry)
                local = os.path.join(tmp, fname)
                with open(local, "wb") as f:
                    f.write(data)

                success, err = mp_cp(port, local, fname)
                # Bei TransportError: ESP stoppen und bis zu 2x erneut
                attempts = 0
                while not success and attempts < 2:
                    _interrupt(port)
                    time.sleep(0.8)
                    success, err = mp_cp(port, local, fname)
                    attempts += 1

                if success:
                    print(c(f"✓  {len(data):>6} B", "g"))
                    ok.append(fname)
                else:
                    short = err.strip().splitlines()[-1] if err.strip() else "?"
                    print(c(f"✗  {short}", "r"))
                    fail.append(fname)

                time.sleep(0.15)   # kurze Pause zwischen Dateien

    print(f"  [{'█'*20}] 100%  Fertig")
    return ok, fail


# ── Reset ────────────────────────────────────────────────────────────
def reset(port):
    run([sys.executable, "-m", "mpremote", "connect", port, "reset"], timeout=10)


# ── Hauptablauf ──────────────────────────────────────────────────────
def main():
    args = sys.argv[1:]
    port = None
    local_bin = None
    skip_flash = False

    i = 0
    while i < len(args):
        a = args[i]
        if a == "--bin" and i + 1 < len(args):
            local_bin = args[i+1]; i += 2; continue
        if a == "--skip-flash":
            skip_flash = True; i += 1; continue
        if not a.startswith("--"):
            port = a; i += 1; continue
        i += 1

    print("=" * 54)
    print(c("  🌱 Smart Irrigation - ESP32 Komplett-Installer", "g"))
    print("=" * 54)

    # ZIP finden
    here = os.path.dirname(os.path.abspath(__file__))
    zip_path = None
    for p in (os.path.join(here, ZIPNAME), ZIPNAME):
        if os.path.exists(p):
            zip_path = os.path.abspath(p); break
    if not zip_path:
        print(c(f"\n❌  {ZIPNAME} nicht gefunden (gleicher Ordner wie install.py).", "r"))
        sys.exit(1)
    print(f"\n📦  {os.path.basename(zip_path)}")

    # Tools
    print(c("\n🔧  Prüfe Werkzeuge (esptool, mpremote)...", "c"))
    ensure_tools()
    print(c("✓   Werkzeuge bereit", "g"))

    # Port
    if not port:
        print()
        port = input(c("  COM-Port (z.B. COM8 oder /dev/ttyUSB0): ", "y")).strip()
    if not port:
        print(c("❌  Kein Port angegeben.", "r"))
        sys.exit(1)
    print(f"📡  Port: {port}")

    # Flashen?
    if not skip_flash:
        print(c("\n⚠️   ACHTUNG: Der ESP32 wird KOMPLETT gelöscht und neu geflasht!", "y"))
        confirm = input(c("    Fortfahren? [j/N]: ", "y")).strip().lower()
        if confirm not in ("j", "ja", "y", "yes"):
            print(c("Abgebrochen.", "d"))
            sys.exit(0)

        bin_path = get_firmware(local_bin)
        erase_flash(port)
        flash_firmware(port, bin_path)
    else:
        print(c("\n⏭   Flashen übersprungen (--skip-flash)", "d"))

    # Dateien
    ok, fail = upload_files(port, zip_path)

    # Abschluss
    print()
    print("=" * 54)
    print(c(f"  {len(ok)} ✓ übertragen     {len(fail)} ✗ Fehler", "g" if not fail else "y"))
    if fail:
        print(c(f"\n  Fehlgeschlagen: {', '.join(fail)}", "r"))
        print(c("  Nur Dateien erneut versuchen:  python install.py "
                f"{port} --skip-flash", "y"))
    else:
        print(c("\n  Neustart...", "c"))
        reset(port)
        print(c("  ✅  Installation abgeschlossen!", "g"))
        print()
        print("  📶  Erststart: AP " + c("SmartIrrigation-Setup", "c"))
        print("      → http://192.168.4.1/  (WLAN einrichten)")
        print("  🌐  Danach:  http://smart-irrigation.local/")
    print("=" * 54)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(c("\n\nAbgebrochen.", "d"))
        sys.exit(1)
