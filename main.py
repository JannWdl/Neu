"""
main.py – Hauptprogramm (speicheroptimiert für ESP32)
Module werden erst geladen, wenn sie wirklich benötigt werden.
Inklusive 10 Sekunden Sicherheits-Delay vor der ersten Sensor-Entscheidung.
"""
import gc
import asyncio
import network

# Aggressive Speicherbereinigung direkt beim Start aktivieren
gc.collect()
gc.threshold(4096)

# Prüfen, ob WiFi verbunden ist
_sta = network.WLAN(network.STA_IF)
if not _sta.isconnected():
    print('WLAN nicht verbunden – main.py beendet.')
    raise SystemExit

print(f'=== Smart Irrigation startet | Heap: {gc.mem_free()}B ===')


def load(name, cls=None):
    """Modul laden mit GC-Bereinigung davor/danach."""
    gc.collect()
    mod = __import__(name)
    gc.collect()
    print(f'  geladen: {name} | Heap: {gc.mem_free()}B')
    return getattr(mod, cls) if cls else mod


async def main():
    # ── Bewässerung (immer) ──────────────────────────────────────
    Irrigation = load('irrigation', 'Irrigation')
    irrig = Irrigation()
    gc.collect()

    # ── Config ───────────────────────────────────────────────────
    cfg = load('config').get_config()
    gc.collect()

    tasks = []

    # ── Webserver (immer) ─────────────────────────────────────────
    WebServer = load('webserver', 'WebServer')
    web = WebServer(irrig)
    gc.collect()

    # ── Wetter (optional) ─────────────────────────────────────────
    wth = None
    if cfg.get('weather.enabled') and cfg.get('weather.api_key'):
        try:
            Weather = load('weather', 'Weather')
            wth = Weather(irrig)
            tasks.append(wth.run())
            print(f'  Wetter aktiv | Heap: {gc.mem_free()}B')
        except Exception as e:
            print(f'  Wetter FEHLER: {e}')
        gc.collect()

    # ── OTA ───────────────────────────────────────────────────────
    ota = None
    try:
        OTA = load('ota', 'OTA')
        ota = OTA()
        web.ota = ota
    except Exception as e:
        print(f'  OTA FEHLER: {e}')
    gc.collect()

    # ── Telegram (optional) ───────────────────────────────────────
    tg = None
    tg_cfg = cfg.as_dict().get('telegram', {})
    if tg_cfg.get('enabled') and tg_cfg.get('token'):
        try:
            TelegramBot = load('telegram_bot', 'TelegramBot')
            tg = TelegramBot(irrig, ota)
            web.telegram = tg
            # Benachrichtigungen aus irrigation.py über Telegram leiten
            def _notify_cb(msg, _tg=tg):
                try:
                    asyncio.create_task(_tg.send(msg))
                except Exception:
                    pass
            irrig.notify = _notify_cb
            tasks.append(tg.run())
            print(f'  Telegram aktiv | Heap: {gc.mem_free()}B')
        except Exception as e:
            print(f'  Telegram FEHLER: {e}')
        gc.collect()

    # ── MQTT (optional) ───────────────────────────────────────────
    mq_cfg = cfg.as_dict().get('mqtt', {})
    if mq_cfg.get('enabled') and mq_cfg.get('server'):
        try:
            MQTTClient = load('mqtt_client', 'MQTTClient')
            mqtt = MQTTClient(irrig)
            web.mqtt = mqtt
            tasks.append(mqtt.run())
            print(f'  MQTT aktiv | Heap: {gc.mem_free()}B')
        except Exception as e:
            print(f'  MQTT FEHLER: {e}')
        gc.collect()

    # ── Display (optional) ────────────────────────────────────────
    if cfg.get('display.type', 0) > 0:
        try:
            Display = load('display', 'Display')
            disp = Display(irrig)
            tasks.append(disp.run())
        except Exception as e:
            print(f'  Display FEHLER: {e}')
        gc.collect()

    # ── Boot-Verzögerungs-Task für die Pumpe ──────────────────────
    async def delayed_irrigation_start():
        print("\n[BOOT-DELAY] Webserver läuft. Warte 10s vor der ersten Sensor-Entscheidung...")
        # Die Pumpe bleibt in diesen 10 Sekunden garantiert aus, Webserver läuft aber bereits!
        await asyncio.sleep(10) 
        print("[BOOT-DELAY] 10s um. Sensoren stabilisiert. Starte automatische Bewässerungslogik...")
        # Erst jetzt wird die normale Schleife gestartet, die misst und ggf. die Pumpe einschaltet
        await irrig.run()

    # ── Kern-Tasks zusammenstellen ────────────────────────────────
    tasks += [
        delayed_irrigation_start(), # Verzögerte Bewässerungsteuerung
        web.run(port=80),           # Webserver startet sofort
        _gc_task(),                 # RAM-Manager
        _heartbeat()                # System-Überwachung
    ]

    print(f'\n=== Alle Tasks bereit | Heap: {gc.mem_free()}B ===')
    print(f'Webinterface aktiv unter: http://{_sta.ifconfig()[0]}/')

    # Startnachricht für Telegram (verzögert, um Netzwerklast zu splitten)
    if tg and cfg.get('notify.system', True):
        async def _tg_start():
            await asyncio.sleep(3)
            try:
                await tg.send(f'🌱 Smart Irrigation gestartet\nIP: {_sta.ifconfig()[0]}')
            except Exception:
                pass
        tasks.append(_tg_start())

    # Event-Loop starten
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for i, r in enumerate(results):
        if isinstance(r, Exception):
            print(f'Task #{i} schwerer Fehler: {r}')


async def _gc_task():
    """Hintergrund-Task zur automatischen RAM-Reinigung."""
    while True:
        gc.collect()
        await asyncio.sleep(5)


async def _heartbeat():
    """Gibt alle 60s den aktuellen Speicherzustand auf der Konsole aus."""
    while True:
        await asyncio.sleep(60)
        gc.collect()
        print(f'[HB] Freier RAM: {gc.mem_free()} Bytes')


# Hauptprogramm-Schleife mit automatischem Crash-Schutz
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print('Manuell gestoppt.')
except Exception as e:
    import sys, time, machine
    print('\n💥 SYSTEM-ABSTURZ IN MAIN.PY:')
    sys.print_exception(e)
    print('Starte System in 8 Sekunden neu...\n')
    time.sleep(8)
    machine.reset()
