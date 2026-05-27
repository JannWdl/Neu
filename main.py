"""
main.py – Hauptprogramm: Startet alle Dienste als asyncio-Tasks
Wird von MicroPython nach boot.py ausgeführt.
"""
import asyncio
import gc
import network

# Prüfen ob WiFi verbunden (boot.py könnte im AP-Modus enden)
_sta = network.WLAN(network.STA_IF)
if not _sta.isconnected():
    print('WLAN nicht verbunden – main.py beendet.')
    raise SystemExit

# ── Module laden ──────────────────────────────────────────────────
from config import get_config
from irrigation import Irrigation

cfg = get_config()
gc.collect()

async def main():
    print('=== Starte alle Dienste ===')
    gc.collect()

    # Kern-Bewässerungslogik
    irrig = Irrigation()
    gc.collect()

    # Wetter
    weather_task = None
    if cfg.get('weather.enabled') and cfg.get('weather.api_key'):
        from weather import Weather
        wth  = Weather(irrig)
        wth.update()           # Sofort einmal aktualisieren
        weather_task = asyncio.create_task(wth.run())
        gc.collect()

    # OTA
    from ota import OTA
    ota = OTA()
    gc.collect()

    # Telegram
    tg_task = None
    tg = None
    if cfg.get('telegram.enabled') and cfg.get('telegram.token'):
        from telegram_bot import TelegramBot
        tg      = TelegramBot(irrig, ota)
        tg_task = asyncio.create_task(tg.run())
        tg.send(f'🌱 Smart Irrigation gestartet!\nIP: {_sta.ifconfig()[0]}')
        gc.collect()

    # MQTT
    mqtt_task = None
    if cfg.get('mqtt.enabled') and cfg.get('mqtt.server'):
        from mqtt_client import MQTTClient
        mqtt      = MQTTClient(irrig)
        mqtt_task = asyncio.create_task(mqtt.run())
        gc.collect()

    # Display
    from display import Display
    disp = Display(irrig)
    display_task = asyncio.create_task(disp.run())
    gc.collect()

    # Web-Server
    from webserver import WebServer
    web  = WebServer(irrig, telegram=tg, ota=ota)
    gc.collect()

    print(f'Freier Heap vor Webserver: {gc.mem_free()} Bytes')
    print(f'Webinterface: http://{_sta.ifconfig()[0]}/')
    print(f'Lokal:        http://{cfg.get("system.hostname","smart-irrigation")}.local/')

    # Alle Tasks parallel starten
    tasks = [
        asyncio.create_task(irrig.run()),
        asyncio.create_task(web.run(port=80)),
        asyncio.create_task(_gc_task()),
        asyncio.create_task(_heartbeat()),
    ]
    if weather_task: tasks.append(weather_task)
    if tg_task:      tasks.append(tg_task)
    if mqtt_task:    tasks.append(mqtt_task)
    tasks.append(display_task)

    await asyncio.gather(*tasks)


async def _gc_task():
    """Garbage Collector regelmäßig aufrufen."""
    while True:
        gc.collect()
        await asyncio.sleep(10)


async def _heartbeat():
    """Watchdog / Status alle 60s auf Serial ausgeben."""
    import time
    while True:
        await asyncio.sleep(60)
        sta = network.WLAN(network.STA_IF)
        print(f'[HB] Heap: {gc.mem_free()}B  RSSI: {sta.status("rssi") if sta.isconnected() else "NC"}dBm')
        gc.collect()


try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('Gestoppt.')
except Exception as e:
    import sys
    print(f'FATAL: {e}')
    sys.print_exception(e)
    import time, machine
    time.sleep(5)
    machine.reset()
