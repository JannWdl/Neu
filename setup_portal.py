"""
setup_portal.py – AP-Modus Einrichtungsportal
Wird gestartet wenn kein WLAN konfiguriert ist.
Öffnet einen Access Point "SmartIrrigation-Setup" und
einen einfachen HTTP-Server zur WLAN-Konfiguration.
"""
import network
import socket
import time
import gc
from config import get_config

AP_SSID     = 'SmartIrrigation-Setup'
AP_PASSWORD = ''           # offen, kein Passwort
AP_IP       = '192.168.4.1'

SETUP_HTML = b"""<!DOCTYPE html>
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
input{width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;
      color:#e2e8f0;padding:10px 12px;font-size:.95rem}
input:focus{outline:none;border-color:#22c55e}
.btn{display:block;width:100%;padding:12px;border:none;border-radius:8px;
     font-size:1rem;font-weight:600;cursor:pointer;margin-top:16px;
     background:#22c55e;color:#0a0f1e}
.scan-btn{display:block;width:100%;padding:9px;border:1px solid #334155;
           border-radius:8px;background:transparent;color:#94a3b8;
           font-size:.85rem;cursor:pointer;margin-bottom:8px}
.net{background:#1e293b;border:1px solid #334155;border-radius:8px;
     padding:9px 12px;margin-bottom:5px;cursor:pointer;
     display:flex;justify-content:space-between;font-size:.85rem}
.net:hover{border-color:#22c55e}
.note{margin-top:14px;padding:10px;background:rgba(34,197,94,.08);
      border:1px solid rgba(34,197,94,.2);border-radius:8px;
      font-size:.78rem;color:#86efac;line-height:1.5}
</style></head><body>
<div class="card">
<h1>&#127807; Smart Irrigation</h1>
<p class="sub">WLAN-Einrichtung</p>
<button class="scan-btn" onclick="scan()">&#128269; Netzwerke scannen</button>
<div id="nets"></div>
<label>WLAN-Name (SSID)</label>
<input id="ssid" type="text" placeholder="Mein WLAN">
<label>Passwort</label>
<input id="pass" type="password" placeholder="Passwort">
<button class="btn" onclick="save()">Verbinden &amp; Speichern</button>
<div class="note">Nach dem Speichern verbindet sich der ESP32 mit dem WLAN und startet neu.</div>
</div>
<script>
function scan(){
  var d=document.getElementById('nets');
  d.innerHTML='Suche...';
  fetch('/scan').then(r=>r.json()).then(data=>{
    data.sort((a,b)=>b.rssi-a.rssi);
    d.innerHTML=data.map(n=>
      '<div class="net" onclick="pick(\''+n.ssid.replace(/\'/g,"\\'")+'\')">'
      +'<span>'+n.ssid+'</span><span>'+n.rssi+'dBm</span></div>'
    ).join('')||'Keine Netzwerke';
  }).catch(()=>{d.innerHTML='Scan fehlgeschlagen';});
}
function pick(s){document.getElementById('ssid').value=s;document.getElementById('pass').focus();}
function save(){
  var ssid=document.getElementById('ssid').value.trim();
  var pass=document.getElementById('pass').value;
  if(!ssid){alert('Bitte SSID eingeben');return;}
  fetch('/save',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:'ssid='+encodeURIComponent(ssid)+'&pass='+encodeURIComponent(pass)})
  .then(r=>r.text()).then(()=>{
    document.querySelector('.card').innerHTML=
      '<h1>&#10003; Gespeichert</h1><p class="sub" style="margin-top:12px">ESP32 verbindet sich und startet neu...</p>';
  }).catch(()=>{alert('Fehler beim Speichern');});
}
</script></body></html>"""


def _parse_form(body):
    """Einfacher URL-encoded Form-Parser."""
    params = {}
    try:
        for pair in body.split('&'):
            if '=' in pair:
                k, v = pair.split('=', 1)
                # Einfaches URL-Decoding
                v = v.replace('+', ' ')
                out = ''
                i = 0
                while i < len(v):
                    if v[i] == '%' and i + 2 < len(v):
                        out += chr(int(v[i+1:i+3], 16))
                        i += 3
                    else:
                        out += v[i]
                        i += 1
                params[k] = out
    except Exception:
        pass
    return params


def start():
    """AP starten und auf WLAN-Konfiguration warten."""
    cfg = get_config()

    # Access Point starten
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=AP_SSID, authmode=network.AUTH_OPEN)
    print(f'Setup-Portal aktiv: SSID={AP_SSID}  IP={AP_IP}')

    # Scan-Interface
    sta = network.WLAN(network.STA_IF)
    sta.active(True)

    # HTTP-Server
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 80))
    srv.listen(3)
    srv.settimeout(1)

    print(f'Webinterface: http://{AP_IP}/')

    saved = False
    while not saved:
        try:
            conn, addr = srv.accept()
        except OSError:
            continue

        try:
            data = conn.recv(1024).decode('utf-8', 'ignore')
            if not data:
                conn.close()
                continue

            first_line = data.split('\r\n')[0]
            method, path = first_line.split()[:2]
            path = path.split('?')[0]

            if path == '/' or path == '/index.html':
                conn.send(b'HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n')
                conn.send(SETUP_HTML)

            elif path == '/scan':
                try:
                    nets = sta.scan()
                    import json
                    result = json.dumps([
                        {'ssid': n[0].decode('utf-8', 'ignore'), 'rssi': n[3]}
                        for n in nets if n[0]
                    ])
                    conn.send(b'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n')
                    conn.send(result.encode())
                except Exception as e:
                    conn.send(b'HTTP/1.0 200 OK\r\nContent-Type: application/json\r\n\r\n[]')

            elif path == '/save' and method == 'POST':
                body = data.split('\r\n\r\n', 1)[-1] if '\r\n\r\n' in data else ''
                params = _parse_form(body)
                ssid = params.get('ssid', '').strip()
                pw   = params.get('pass', '')

                if ssid:
                    cfg.set('wifi.ssid', ssid, save=False)
                    cfg.set('wifi.password', pw, save=True)
                    conn.send(b'HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\nOK')
                    print(f'WLAN gespeichert: {ssid}')
                    saved = True
                else:
                    conn.send(b'HTTP/1.0 400 Bad Request\r\n\r\nFehlt SSID')
            else:
                conn.send(b'HTTP/1.0 404 Not Found\r\n\r\n')

        except Exception as e:
            print(f'Setup-Portal Fehler: {e}')
        finally:
            conn.close()
            gc.collect()

    srv.close()
    ap.active(False)

    print('Starte neu...')
    import time, machine
    time.sleep(2)
    machine.reset()
