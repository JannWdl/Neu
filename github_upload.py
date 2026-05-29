#!/usr/bin/env python3
"""
github_upload.py – Lädt alle Projektdateien zu GitHub (JannWdl/Neu)

Voraussetzung: git ist installiert und du bist eingeloggt
(oder hast einen Personal Access Token bereit).

Aufruf:
  python github_upload.py

Das Skript:
  1. initialisiert ein git-Repo im aktuellen Ordner (falls nötig)
  2. fügt alle Projektdateien hinzu
  3. committed und pusht zu github.com/JannWdl/Neu
"""

import os
import subprocess
import sys

REPO_URL = "https://github.com/JannWdl/Neu.git"
BRANCH   = "main"

FILES = [
    "boot.py", "main.py", "config.py", "irrigation.py", "webserver.py",
    "index.html", "telegram_bot.py", "mqtt_client.py", "weather.py",
    "ota.py", "display.py", "plants_db.py", "setup_portal.py",
    "README.md", "install.py", "local_test_server.py",
]


def run(cmd):
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.stdout.strip():
        print("   ", r.stdout.strip())
    if r.returncode != 0 and r.stderr.strip():
        print("   ", r.stderr.strip())
    return r.returncode == 0


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    os.chdir(here)

    # Prüfen welche Dateien vorhanden sind
    present = [f for f in FILES if os.path.exists(f)]
    missing = [f for f in FILES if not os.path.exists(f)]
    if missing:
        print("⚠️  Fehlend (werden übersprungen):", ", ".join(missing))
    print(f"📦  {len(present)} Dateien werden hochgeladen.\n")

    # Git-Repo initialisieren
    if not os.path.exists(".git"):
        run(["git", "init"])
        run(["git", "branch", "-M", BRANCH])

    # Remote setzen (oder aktualisieren)
    subprocess.run(["git", "remote", "remove", "origin"], capture_output=True)
    run(["git", "remote", "add", "origin", REPO_URL])

    # Dateien hinzufügen
    run(["git", "add"] + present)
    run(["git", "commit", "-m", "Smart Irrigation Update – Telegram Wetter MQTT Installer"])

    # Push
    print("\n⬆   Pushe zu GitHub...")
    ok = run(["git", "push", "-u", "origin", BRANCH])

    if not ok:
        print("\n⚠️  Push fehlgeschlagen. Mögliche Gründe:")
        print("    - Noch nicht bei GitHub eingeloggt → 'gh auth login' oder Token nutzen")
        print("    - Repo 'Neu' existiert noch nicht → auf github.com anlegen")
        print("    - Falls Konflikt: git push -u origin main --force")
    else:
        print("\n✅  Fertig! https://github.com/JannWdl/Neu")


if __name__ == "__main__":
    main()
