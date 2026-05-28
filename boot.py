# This file is executed on every boot (including wake-boot from deepsleep)
import gc
import network
import time

gc.collect()
gc.threshold(4096)

def connect_wifi():
    from config import get_config
    cfg = get_config()
    ssid = cfg.get('wifi.ssid', '')
    pw   = cfg.get('wifi.password', '')

    if not ssid:
        print('Kein WLAN konfiguriert.')
        return False

    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    if sta.isconnected():
        print(f'WLAN bereits verbunden: {sta.ifconfig()[0]}')
        return True

    print(f'Verbinde mit WLAN: {ssid} ...')
    sta.connect(ssid, pw)
    for _ in range(20):
        if sta.isconnected():
            ip = sta.ifconfig()[0]
            print(f'WLAN verbunden: {ip}')
            return True
        time.sleep(0.5)

    print('WLAN-Verbindung fehlgeschlagen.')
    return False


def sync_ntp():
    try:
        import ntptime
        from config import get_config
        cfg = get_config()
        ntptime.host = cfg.get('system.ntp_server', 'pool.ntp.org')
        ntptime.settime()
        t = time.localtime()
        print(f'NTP synchronisiert: {t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}')
    except Exception as e:
        print(f'NTP Fehler: {e}')


connected = connect_wifi()

if connected:
    sync_ntp()
else:
    # Kein WLAN → Setup-Portal starten
    try:
        import setup_portal
        setup_portal.start()
    except Exception as e:
        print(f'Setup-Portal Fehler: {e}')

gc.collect()
