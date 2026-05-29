"""
setup_portal.py – AP-Modus Einrichtungsportal
"""
import network
import socket
import time
import gc
from config import get_config

AP_SSID = 'SmartIrrigation-Setup'
AP_IP   = '192.168.4.1'

HTML_FORM = b"""<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Irrigation Setup</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#0a0f1e;color:#e2e8f0;
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}
.card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
      border-radius:16px;padding:28px;width:100%;max-width:400px}
h1{color:#22c55e;font-size:1.4rem;margin-bottom:4px;text-align:center}
.sub{color:#94a3b8;font-size:.85rem;text-align:center;margin-bottom:20px}
label{display:block;color:#94a3b8;font-size:.82rem;margin:12px 0 4px}
input,select{width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;
      color:#e2e8f0;padding:10px 12px;font-size:.95rem;margin:0}
input:focus{outline:none;border-color:#22c55e}
.btn{display:block;width:100%;padding:12px;border:none;border-radius:8px;
     font-size:1rem;font-weight:600;cursor:pointer;margin-top:16px;
     background:#22c55e;color:#0a0f1e}
.note{margin-top:14px;padding:10px;background:rgba(34,197,94,.08);
      border:1px solid rgba(34,197,94,.2);border-radius:8px;
      font-size:.78rem;color:#86efac;line-height:1.5}
</style></head><body>
<div class="card">
<h1>&#127807; Smart Irrigation</h1>
<p class="sub">WLAN-Einrichtung</p>
<form method="POST" action="/save">
<label>WLAN-Name (SSID)</label>
<input name="ssid" type="text" placeholder="Mein WLAN" required autofocus>
<label>Passwort</label>
<input name="pass" type="password" placeholder="Passwort">
<button class="btn" type="submit">Verbinden &amp; Speichern</button>
</form>
<div class="note">&#8505;&#65039; Nach dem Speichern startet der ESP32 neu und verbindet sich mit deinem WLAN.</div>
</div>
</body></html>"""

HTML_OK = b"""<!DOCTYPE html>
<html lang="de"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Gespeichert</title>
<style>
body{font-family:system-ui,sans-serif;background:#0a0f1e;color:#e2e8f0;
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}
.card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
      border-radius:16px;padding:28px;width:100%;max-width:400px;text-align:center}
h1{color:#22c55e;font-size:1.4rem;margin-bottom:12px}
p{color:#94a3b8;font-size:.9rem;line-height:1.6}
</style></head><body>
<div class="card">
<h1>&#10003; Gespeichert</h1>
<p>ESP32 verbindet sich mit dem WLAN<br>und startet in 2 Sekunden neu.</p>
</div>
</body></html>"""


def _parse_form(body):
    params = {}
    for pair in body.split('&'):
        if '=' in pair:
            k, v = pair.split('=', 1)
            out = ''
            i = 0
            while i < len(v):
                if v[i] == '%' and i + 2 < len(v):
                    out += chr(int(v[i+1:i+3], 16))
                    i += 3
                elif v[i] == '+':
                    out += ' '
                    i += 1
                else:
                    out += v[i]
                    i += 1
            params[k] = out
    return params


def _send(conn, status, body, content_type=b'text/html; charset=utf-8'):
    conn.send(b'HTTP/1.0 ' + status + b'\r\n')
    conn.send(b'Content-Type: ' + content_type + b'\r\n')
    conn.send(b'Content-Length: ' + str(len(body)).encode() + b'\r\n')
    conn.send(b'Connection: close\r\n\r\n')
    conn.send(body)


def start():
    cfg = get_config()

    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
    print(f'Setup-AP aktiv | SSID: {AP_SSID} | IP: {AP_IP}')
    print(f'Browser: http://{AP_IP}/')

    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 80))
    srv.listen(3)
    srv.settimeout(0.5)

    saved = False
    while not saved:
        gc.collect()
        try:
            conn, addr = srv.accept()
        except OSError:
            continue

        try:
            # Request lesen
            raw = b''
            conn.settimeout(2)
            while True:
                try:
                    chunk = conn.recv(256)
                    if not chunk:
                        break
                    raw += chunk
                    if b'\r\n\r\n' in raw:
                        # Bei POST: noch den Body lesen
                        header, body_so_far = raw.split(b'\r\n\r\n', 1)
                        # Content-Length ermitteln
                        cl = 0
                        for line in header.split(b'\r\n'):
                            if line.lower().startswith(b'content-length:'):
                                cl = int(line.split(b':')[1].strip())
                        while len(body_so_far) < cl:
                            body_so_far += conn.recv(256)
                        raw = header + b'\r\n\r\n' + body_so_far
                        break
                except OSError:
                    break

            if not raw:
                conn.close()
                continue

            # Methode + Pfad
            first = raw.split(b'\r\n')[0].decode('utf-8', 'ignore')
            parts = first.split()
            if len(parts) < 2:
                conn.close()
                continue
            method = parts[0]
            path   = parts[1].split('?')[0]

            if method == 'GET':
                _send(conn, b'200 OK', HTML_FORM)

            elif method == 'POST' and path == '/save':
                body = raw.split(b'\r\n\r\n', 1)[-1].decode('utf-8', 'ignore')
                params = _parse_form(body)
                ssid = params.get('ssid', '').strip()
                pw   = params.get('pass', '')

                if ssid:
                    _send(conn, b'200 OK', HTML_OK)
                    conn.close()
                    # Kurz warten damit Browser die Antwort noch bekommt
                    time.sleep(0.5)
                    cfg.set('wifi.ssid', ssid, save=False)
                    cfg.set('wifi.password', pw, save=True)
                    print(f'WLAN gespeichert: {ssid}')
                    saved = True
                    continue
                else:
                    _send(conn, b'400 Bad Request', b'SSID fehlt')
            else:
                _send(conn, b'404 Not Found', b'Not found')

        except Exception as e:
            print(f'Portal Fehler: {e}')
        finally:
            try:
                conn.close()
            except:
                pass

    srv.close()
    ap.active(False)
    print('Neustart...')
    time.sleep(1)
    import machine
    machine.reset()
