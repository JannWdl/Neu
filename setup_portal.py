"""
setup_portal.py – AP-Modus Einrichtungsportal
Zeigt NUR die WiFi-Einrichtung (SSID + Passwort).
Alle anderen Einstellungen erfolgen im Heimnetz.
"""
import socket
import time
import machine
import gc
from config import get_config

SETUP_HTML = """\
<!DOCTYPE html><html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Irrigation – WLAN-Einrichtung</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#0a0f1e;color:#e2e8f0;
     min-height:100vh;display:flex;align-items:center;justify-content:center;padding:16px}
.card{background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12);
      border-radius:16px;padding:28px;width:100%;max-width:420px}
h1{color:#22c55e;font-size:1.5rem;margin-bottom:4px;text-align:center}
.sub{color:#94a3b8;font-size:.85rem;text-align:center;margin-bottom:24px}
label{display:block;color:#94a3b8;font-size:.82rem;margin-bottom:5px;margin-top:14px}
input{width:100%;background:#1e293b;border:1px solid #334155;border-radius:8px;
      color:#e2e8f0;padding:11px 14px;font-size:.95rem}
input:focus{outline:none;border-color:#22c55e}
.btn{display:block;width:100%;padding:13px;border:none;border-radius:8px;
     font-size:1rem;font-weight:600;cursor:pointer;margin-top:20px;
     background:#22c55e;color:#0a0f1e;transition:.2s}
.btn:active{opacity:.8}
.note{margin-top:16px;padding:12px;background:rgba(34,197,94,.08);
      border:1px solid rgba(34,197,94,.2);border-radius:8px;
      font-size:.8rem;color:#86efac;line-height:1.5}
.nets{margin-top:8px}
.net{background:#1e293b;border:1px solid #334155;border-radius:8px;
     padding:9px 12px;margin-bottom:5px;cursor:pointer;display:flex;
     justify-content:space-between;font-size:.88rem;transition:.15s}
.net:hover{border-color:#22c55e}
.scan-btn{display:block;width:100%;padding:9px;border:1px solid #334155;
           border-radius:8px;background:transparent;color:#94a3b8;
           font-size:.85rem;cursor:pointer;margin-bottom:10px}
</style></head>
<body><div class="card">
<h1>&#127807; Smart Irrigation</h1>
<p class="sub">WLAN-Einrichtung</p>
<button class="scan-btn" onclick="scan()">&#128269; Netzwerke scannen</button>
<div class="nets" id="nets"></div>
<label>WLAN-Name (SSID)</label>
<input id="ssid" type="text" placeholder="Mein WLAN" autocomplete="off">
<label>Passwort</label>
<input id="pass" type="password" placeholder="Passwort" autocomplete="new-password">
<button class="btn" onclick="save()">Verbinden &amp; Speichern</button>
<div class="note">
&#9432; Nach dem Speichern verbindet sich der ESP32 mit dem WLAN.<br>
Trenne dann das Ger&auml;t von "<strong>SmartIrrigation-Setup</strong>"
und &ouml;ffne <strong>http://smart-irrigation.local</strong><br>
f&uuml;r alle weiteren Einstellungen.
</div>
</div>
<script>
function scan(){
  var d=document.getElementById('nets');
  d.innerHTML='<div style="color:#94a3b8;font-size:.82rem;padding:6px">Suche...</div>';
  fetch('/scan').then(r=>r.json()).then(data=>{
    var h='';
    data.sort((a,b)=>b.rssi-a.rssi).forEach(n=>{
      var s=n.rssi>-55?'&#9608;&#9608;&#9608;':n.rssi>-70?'&#9608;&#9608;&#9617;':'&#9608;&#9617;&#9617;';
      h+='<div class="net" onclick="pick(\''+n.ssid.replace(/\\/g,'\\\\').replace(/'/g,"\\'")+'\')">'
        +'<span>'+n.ssid+(n.secured?' &#128274;':'')+'</span>'
        +'<span style="color:#94a3b8;font-size:.78rem">'+s+' '+n.rssi+'</span></div>';
    });
    d.innerHTML=h||'<div style="color:#94a3b8;font-size:.82rem;padding:6px">Keine gefunden</div>';
  }).catch(()=>{d.innerHTML='';});
}
function pick(s){document.getElementById('ssid').value=s;document.getElementById('pass').focus();}
function save(){
  var ssid=document.getElementById('ssid').value.trim();
  var pass=document.getElementById('pass').value;
  if(!ssid){alert('Bitte WLAN-Name eingeben.');return;}
  fetch('/save',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},
    body:'ssid='+encodeURIComponent(ssid)+'&pass='+encodeURIComponent(pass)})
  .then(r=>r.text()).then(()=>{
    document.querySelector('.card').innerHTML='<h1 style="color:#22c55e;text-align:center;margin-top:40px">&#10003; Gespeichert!</h1>'
      +'<p style="text-align:center;color:#94a3b8;margin-top:12px">ESP32 verbindet sich...<br>Bitte warten.</p>';
  });
}
</script></body></html>"""


def _parse_form(body):
    params = {}
    for part in body.split('&'):
        if '=' in part:
            k, v = part.split('=', 1)
            params[_url_decode(k)] = _url_decode(v)
    return params


def _url_decode(s):
    s = s.replace('+', ' ')
    result = ''
    i = 0
    while i < len(s):
        if s[i] == '%' and i + 2 < len(s):
            result += chr(int(s[i+1:i+3], 16))
            i += 3
        else:
            result += s[i]
            i += 1
    return result


def _wifi_scan():
    import network
    import json
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    try:
        nets = sta.scan()
        result = []
        seen = set()
        for n in nets:
            ssid = n[0].decode('utf-8', 'ignore')
            if ssid and ssid not in seen:
                seen.add(ssid)
                result.append({'ssid': ssid, 'rssi': n[3], 'secured': n[4] != 0})
        return json.dumps(result)
    except Exception as e:
        return '[]'


def _send_response(conn, status, content_type, body):
    if isinstance(body, str):
        body = body.encode()
    header = (
        f'HTTP/1.1 {status}\r\n'
        f'Content-Type: {content_type}\r\n'
        f'Content-Length: {len(body)}\r\n'
        'Connection: close\r\n\r\n'
    ).encode()
    conn.sendall(header + body)


def run_setup_portal():
    """Blockierender Mini-HTTP-Server für WiFi-Einrichtung."""
    import network

    ap = network.WLAN(network.AP_IF)
    srv = socket.socket()
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(('0.0.0.0', 80))
    srv.listen(3)
    srv.settimeout(1)

    cfg = get_config()
    restart_pending = False

    print('Setup-Portal bereit auf 192.168.4.1')

    while True:
        gc.collect()
        try:
            conn, addr = srv.accept()
        except OSError:
            if restart_pending:
                time.sleep(2)
                machine.reset()
            continue

        try:
            conn.settimeout(5)
            raw = b''
            while b'\r\n\r\n' not in raw:
                chunk = conn.recv(512)
                if not chunk:
                    break
                raw += chunk

            lines   = raw.decode('utf-8', 'ignore').split('\r\n')
            req     = lines[0] if lines else ''
            parts   = req.split(' ')
            method  = parts[0] if len(parts) > 0 else 'GET'
            path    = parts[1].split('?')[0] if len(parts) > 1 else '/'

            # Body lesen
            body = ''
            if method == 'POST':
                for line in lines:
                    if line.lower().startswith('content-length:'):
                        clen = int(line.split(':', 1)[1].strip())
                        if b'\r\n\r\n' in raw:
                            existing = raw.split(b'\r\n\r\n', 1)[1]
                            while len(existing) < clen:
                                existing += conn.recv(256)
                            body = existing[:clen].decode('utf-8', 'ignore')
                        break

            # Captive-portal-Weiterleitungen
            if path in ('/generate_204', '/gen_204', '/hotspot-detect.html',
                        '/connecttest.txt', '/ncsi.txt', '/redirect'):
                _send_response(conn, '302 Found', 'text/plain',
                               'Location: http://192.168.4.1/\r\n')
                continue

            if path == '/scan':
                _send_response(conn, '200 OK', 'application/json', _wifi_scan())

            elif path == '/save' and method == 'POST':
                params = _parse_form(body)
                ssid   = params.get('ssid', '').strip()
                pw     = params.get('pass', '')
                if ssid:
                    cfg.set('wifi.ssid',     ssid)
                    cfg.set('wifi.password', pw)
                    cfg.save()
                    _send_response(conn, '200 OK', 'text/plain', 'OK')
                    print(f'WiFi gespeichert: {ssid} – Neustart...')
                    restart_pending = True
                else:
                    _send_response(conn, '400 Bad Request', 'text/plain', 'SSID fehlt')

            else:
                _send_response(conn, '200 OK', 'text/html; charset=utf-8', SETUP_HTML)

        except Exception as e:
            print(f'Portal error: {e}')
        finally:
            try:
                conn.close()
            except Exception:
                pass
