"""
boot.py – Erster Start: WiFi verbinden oder AP-Modus für WLAN-Einrichtung.

AP-Modus zeigt NUR WiFi-SSID/Passwort-Eingabe.
Alle anderen Einstellungen werden im Heimnetz konfiguriert.
"""
import network
import time
import sys
import gc
from config import get_config

WIFI_TIMEOUT = 15   # Sekunden
AP_SSID      = 'SmartIrrigation-Setup'


def connect_wifi(ssid, password, timeout=WIFI_TIMEOUT):
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return wlan.ifconfig()[0]
    wlan.connect(ssid, password)
    print(f'Verbinde mit {ssid}', end='')
    for _ in range(timeout * 2):
        if wlan.isconnected():
            ip = wlan.ifconfig()[0]
            print(f'\nIP: {ip}')
            return ip
        print('.', end='')
        time.sleep(0.5)
    print('\nVerbindung fehlgeschlagen.')
    return None


def start_ap():
    """AP-Modus starten – nur WiFi-Einrichtung, kein weiterer Zugang."""
    wlan_sta = network.WLAN(network.STA_IF)
    wlan_sta.active(False)

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
    time.sleep(0.5)

    print(f'\n=== AP-MODUS ===')
    print(f'SSID: {AP_SSID}')
    print(f'IP:   192.168.4.1')
    print('Öffne http://192.168.4.1 im Browser')

    # Setup-Portal starten (blockiert bis Neustart)
    from setup_portal import run_setup_portal
    run_setup_portal()


# ── Hauptlogik ───────────────────────────────────────────────────
print('\n=== Smart Irrigation MicroPython v3.0 ===')
gc.collect()

cfg  = get_config()
ssid = cfg.get('wifi.ssid', '')

if not ssid:
    print('Kein WLAN konfiguriert → AP-Modus')
    start_ap()
else:
    ip = connect_wifi(ssid, cfg.get('wifi.password', ''))
    if not ip:
        print('WLAN fehlgeschlagen → AP-Modus')
        start_ap()
    else:
        # Hostname setzen
        import machine
        try:
            network.WLAN(network.STA_IF).config(dhcp_hostname=cfg.get('system.hostname', 'smart-irrigation'))
        except Exception:
            pass

        # NTP Zeit synchronisieren
        try:
            import ntptime
            ntptime.host = cfg.get('system.ntp_server', 'pool.ntp.org')
            ntptime.settime()
            print('NTP synchronisiert')
        except Exception as e:
            print(f'NTP Fehler: {e}')

        gc.collect()
        print(f'Boot abgeschlossen. Freier Heap: {gc.mem_free()} Bytes')
