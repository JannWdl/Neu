#pragma once

// Web-Oberfläche als PROGMEM — wird aus Flash gestreamt, kein RAM-Verbrauch
const char WEB_HTML[] PROGMEM = R"HTML(
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🌱 Smart Irrigation</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#0a0f1e;--bg2:#0f1a2e;--card:rgba(255,255,255,0.04);
  --border:rgba(255,255,255,0.08);--border2:rgba(255,255,255,0.14);
  --green:#22c55e;--blue:#3b82f6;--amber:#f59e0b;--red:#ef4444;--purple:#a855f7;
  --text:#f1f5f9;--sub:#94a3b8;--muted:#64748b;
}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;min-height:100vh}
/* ─── HEADER ─── */
header{
  background:linear-gradient(135deg,#0d1b2e,#162035);
  border-bottom:1px solid var(--border);
  padding:0 1.5rem;height:62px;
  display:flex;align-items:center;
  position:sticky;top:0;z-index:100;
  backdrop-filter:blur(20px);
}
.logo{
  font-size:1.35rem;font-weight:800;letter-spacing:-.02em;
  background:linear-gradient(135deg,var(--green),var(--blue));
  -webkit-background-clip:text;-webkit-text-fill-color:transparent;
  margin-right:auto;
}
.hstatus{display:flex;gap:.75rem;align-items:center}
.dot{display:flex;align-items:center;gap:.35rem;font-size:.72rem;color:var(--muted)}
.di{width:7px;height:7px;border-radius:50%;background:var(--muted);transition:background .3s}
.di.on{background:var(--green);box-shadow:0 0 7px var(--green)}
.di.off{background:var(--red)}
/* ─── NAV ─── */
nav{background:var(--bg2);border-bottom:1px solid var(--border);display:flex;padding:0 1rem;overflow-x:auto}
nav::-webkit-scrollbar{display:none}
.nb{
  padding:.85rem 1.1rem;background:none;border:none;color:var(--muted);
  cursor:pointer;font-size:.82rem;font-weight:600;letter-spacing:.01em;
  border-bottom:2px solid transparent;transition:all .2s;white-space:nowrap;
}
.nb:hover,.nb.active{color:var(--green);border-bottom-color:var(--green)}
/* ─── MAIN ─── */
main{max-width:1200px;margin:0 auto;padding:1.25rem}
.tab{display:none}.tab.active{display:block}
/* ─── CARDS ─── */
.card{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:1.25rem;
  backdrop-filter:blur(10px);transition:border-color .2s;
}
.card:hover{border-color:var(--border2)}
.ct{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin-bottom:1rem}
/* ─── GRID ─── */
.g2{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:1rem}
.g3{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:1rem}
.gap{margin-bottom:1rem}
/* ─── GAUGE ─── */
.gauge{position:relative;width:120px;height:120px;margin:0 auto .75rem}
.gauge svg{transform:rotate(-90deg)}
.gbg{fill:none;stroke:rgba(255,255,255,0.07);stroke-width:9}
.gfill{fill:none;stroke-width:9;stroke-linecap:round;transition:stroke-dashoffset 1.2s ease}
.gtxt{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}
.gpct{font-size:1.5rem;font-weight:800}
.glbl{font-size:.62rem;color:var(--muted)}
/* ─── CHANNEL CARD ─── */
.ch-card{
  background:var(--card);border:1px solid var(--border);
  border-radius:16px;padding:1.2rem;transition:all .35s;
  animation:fadeUp .4s ease forwards;
}
.ch-card.pumping{border-color:var(--blue);box-shadow:0 0 24px rgba(59,130,246,.18)}
.ch-card.dry{border-color:var(--amber);box-shadow:0 0 20px rgba(245,158,11,.13)}
.ch-hd{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:.9rem}
.ch-name{font-weight:700;font-size:1rem}
.ch-plant{font-size:.72rem;color:var(--muted);margin-top:.1rem}
/* ─── BADGE ─── */
.badge{padding:.22rem .55rem;border-radius:20px;font-size:.68rem;font-weight:700}
.bg{background:rgba(34,197,94,.14);color:var(--green)}
.bb{background:rgba(59,130,246,.14);color:var(--blue)}
.ba{background:rgba(245,158,11,.14);color:var(--amber)}
.br{background:rgba(239,68,68,.14);color:var(--red)}
.bx{background:rgba(100,116,139,.14);color:var(--muted)}
/* ─── BUTTONS ─── */
.btn{
  padding:.5rem 1rem;border-radius:8px;font-size:.83rem;font-weight:700;
  cursor:pointer;border:none;transition:all .18s;
  display:inline-flex;align-items:center;gap:.4rem;
}
.btn:active{transform:scale(.97)}
.btn-g{background:var(--green);color:#000}
.btn-g:hover{background:#16a34a}
.btn-b{background:var(--blue);color:#fff}
.btn-b:hover{background:#2563eb}
.btn-r{background:var(--red);color:#fff}
.btn-r:hover{background:#dc2626}
.btn-a{background:var(--amber);color:#000}
.btn-a:hover{background:#d97706}
.btn-x{background:rgba(255,255,255,.08);color:var(--sub);border:1px solid var(--border)}
.btn-x:hover{background:rgba(255,255,255,.14)}
.btn-x.active{background:rgba(34,197,94,.14);color:var(--green);border-color:rgba(34,197,94,.3)}
.bsm{padding:.3rem .65rem;font-size:.77rem;border-radius:6px}
.bfull{width:100%;justify-content:center}
/* ─── STATS ROW ─── */
.srow{display:flex;gap:.75rem;flex-wrap:wrap;margin:.6rem 0}
.si{display:flex;flex-direction:column;align-items:center;flex:1;min-width:55px}
.sv{font-weight:700;font-size:1rem}
.sl{font-size:.63rem;color:var(--muted);text-align:center;margin-top:.1rem}
/* ─── PROGRESS ─── */
.pbar{height:5px;background:rgba(255,255,255,.07);border-radius:3px;overflow:hidden;margin:.5rem 0}
.pfill{height:100%;border-radius:3px;transition:width 1.2s ease,background .3s}
/* ─── PUMP PULSE ─── */
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.4}}
.pump-dot{display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--blue);animation:pulse 1s infinite;margin-right:4px}
/* ─── WEATHER CARD ─── */
.wcard{background:linear-gradient(135deg,rgba(59,130,246,.08),rgba(139,92,246,.08));border:1px solid rgba(59,130,246,.18)}
.wm{display:flex;align-items:center;gap:1rem;margin-bottom:.6rem}
.wicon{font-size:2.8rem}
.wtemp{font-size:1.9rem;font-weight:800}
.wdesc{color:var(--sub);font-size:.83rem;margin-top:.1rem}
/* ─── FORM ─── */
.fg{margin-bottom:.9rem}
.fl{display:block;font-size:.77rem;color:var(--sub);margin-bottom:.35rem;font-weight:600}
.fi,.fs{
  width:100%;padding:.58rem .75rem;
  background:rgba(255,255,255,.05);border:1px solid var(--border);
  border-radius:8px;color:var(--text);font-size:.85rem;
  transition:border-color .2s;outline:none;
}
.fi:focus,.fs:focus{border-color:var(--green)}
.fs option{background:var(--bg2)}
.frow{display:flex;align-items:center;justify-content:space-between}
/* ─── TOGGLE ─── */
.tgl{position:relative;display:inline-block;width:42px;height:23px}
.tgl input{opacity:0;width:0;height:0}
.tsl{position:absolute;inset:0;background:rgba(255,255,255,.12);border-radius:23px;cursor:pointer;transition:.3s}
.tsl::before{content:'';position:absolute;width:17px;height:17px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.3s}
.tgl input:checked+.tsl{background:var(--green)}
.tgl input:checked+.tsl::before{transform:translateX(19px)}
/* ─── ALERTS ─── */
.alert{padding:.7rem 1rem;border-radius:10px;font-size:.83rem;margin-bottom:.9rem;display:flex;align-items:center;gap:.5rem}
.alert-s{background:rgba(34,197,94,.09);border:1px solid rgba(34,197,94,.25);color:var(--green)}
.alert-e{background:rgba(239,68,68,.09);border:1px solid rgba(239,68,68,.25);color:var(--red)}
.alert-i{background:rgba(59,130,246,.09);border:1px solid rgba(59,130,246,.25);color:var(--blue)}
/* ─── LOG ─── */
.logrow{padding:.55rem 0;border-bottom:1px solid var(--border);display:flex;gap:.75rem;font-size:.79rem;align-items:flex-start}
.ltime{color:var(--muted);min-width:130px;flex-shrink:0}
.lmsg{color:var(--sub);line-height:1.4}
/* ─── WIZARD ─── */
.wstep{display:none}.wstep.active{display:block}
.wdots{display:flex;gap:.5rem;margin-bottom:1.25rem}
.wd{flex:1;height:4px;background:var(--border);border-radius:2px;transition:background .3s}
.wd.done{background:var(--green)}.wd.cur{background:var(--blue)}
/* ─── DROP ZONE ─── */
.dz{
  border:2px dashed var(--border);border-radius:12px;
  padding:2rem;text-align:center;cursor:pointer;transition:all .2s;
}
.dz:hover,.dz.drag{border-color:var(--green);background:rgba(34,197,94,.04)}
.dzicon{font-size:2.8rem;margin-bottom:.5rem}
/* ─── SECTION SEPARATOR ─── */
.sec-title{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);margin:.5rem 0 .75rem}
/* ─── TOAST ─── */
#toast{position:fixed;bottom:1.5rem;right:1.5rem;z-index:9999;max-width:320px;pointer-events:none}
/* ─── SCROLLBAR ─── */
::-webkit-scrollbar{width:5px;height:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.12);border-radius:3px}
/* ─── ANIMATIONS ─── */
@keyframes fadeUp{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes spin{to{transform:rotate(360deg)}}
/* ─── RESPONSIVE ─── */
@media(max-width:600px){main{padding:.9rem}.g2{grid-template-columns:1fr}}
/* ─── CHANNEL DETAIL SECTION ─── */
.ch-sect{background:rgba(255,255,255,.03);border:1px solid var(--border);border-radius:12px;padding:1rem;margin-top:1rem}
</style>
</head>
<body>

<!-- HEADER -->
<header>
  <div class="logo">🌱 Smart Irrigation</div>
  <div class="hstatus">
    <div class="dot"><div class="di" id="d-wifi"></div><span>WiFi</span></div>
    <div class="dot"><div class="di" id="d-mqtt"></div><span>MQTT</span></div>
    <div class="dot"><div class="di" id="d-tg"></div><span>Telegram</span></div>
  </div>
</header>

<!-- NAV -->
<nav>
  <button class="nb active" onclick="showTab('dashboard',this)">📊 Dashboard</button>
  <button class="nb" onclick="showTab('channels',this)">🚿 Kanäle</button>
  <button class="nb" onclick="showTab('stats',this)">📈 Statistik</button>
  <button class="nb" onclick="showTab('settings',this)">⚙️ Einstellungen</button>
  <button class="nb" onclick="showTab('ota',this)">🔄 Update</button>
</nav>

<main>

<!-- ════════════ DASHBOARD ════════════ -->
<div id="tab-dashboard" class="tab active">
  <div class="g2 gap">
    <!-- System Status -->
    <div class="card">
      <div class="ct">System Status</div>
      <div class="srow">
        <div class="si"><span class="sv" id="s-uptime">--</span><span class="sl">Uptime</span></div>
        <div class="si"><span class="sv" id="s-ch">--</span><span class="sl">Kanäle</span></div>
        <div class="si"><span class="sv" id="s-today">0</span><span class="sl">Heute gegossen</span></div>
        <div class="si"><span class="sv" id="s-heap">--</span><span class="sl">RAM frei</span></div>
        <div class="si"><span class="sv" id="s-rssi">--</span><span class="sl">WiFi dBm</span></div>
      </div>
      <div style="font-size:.75rem;color:var(--muted);margin-top:.5rem">
        🌐 <a id="s-ip" href="#" style="color:var(--blue);text-decoration:none">--</a>
        &nbsp;&nbsp;🕐 <span id="s-time">--</span>
      </div>
    </div>
    <!-- Weather -->
    <div class="card wcard">
      <div class="ct">🌤 Wetter</div>
      <div class="wm">
        <div class="wicon" id="w-icon">⏳</div>
        <div>
          <div class="wtemp" id="w-temp">--°C</div>
          <div class="wdesc" id="w-desc">Laden...</div>
        </div>
      </div>
      <div style="display:flex;gap:1rem;font-size:.8rem;color:var(--sub);flex-wrap:wrap">
        <span>💧 <span id="w-hum">--%</span></span>
        <span>🌡 Fühlt <span id="w-feel">--°C</span></span>
        <span>🌬 <span id="w-wind">-- km/h</span></span>
        <span id="w-skip"></span>
      </div>
      <div id="w-info" style="display:none;margin-top:.6rem;font-size:.75rem;color:var(--amber)">
        ⏸ Bewässerung pausiert — Regen erwartet
      </div>
    </div>
  </div>

  <!-- Optionaler Wasserstand -->
  <div id="wl-banner" style="display:none" class="alert alert-i gap">
    🚰 Wasserstand: <strong id="wl-pct">--%</strong>
    <span id="wl-warn" style="display:none;color:var(--amber)"> ⚠️ Niedrig!</span>
  </div>

  <div class="sec-title">Kanäle Übersicht</div>
  <div class="g2" id="ch-overview"></div>
</div>

<!-- ════════════ KANÄLE DETAIL ════════════ -->
<div id="tab-channels" class="tab">
  <div id="ch-sel" style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem"></div>
  <div id="ch-detail"></div>
</div>

<!-- ════════════ STATISTIK ════════════ -->
<div id="tab-stats" class="tab">
  <div class="card gap">
    <div class="ct">📊 Feuchtigkeits-Verlauf</div>
    <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:.75rem">
      <select class="fs" id="stat-ch" style="width:auto" onchange="loadChart()"></select>
      <button class="btn btn-x bsm active" onclick="setRange('24h',this)">24h</button>
      <button class="btn btn-x bsm" onclick="setRange('7d',this)">7 Tage</button>
      <button class="btn btn-x bsm" onclick="setRange('30d',this)">30 Tage</button>
    </div>
    <canvas id="chart" style="max-height:280px"></canvas>
  </div>
  <div class="card">
    <div class="ct">📋 Bewässerungs-Log</div>
    <div id="log-list"><div style="color:var(--muted);text-align:center;padding:2rem">Lade...</div></div>
  </div>
</div>

<!-- ════════════ EINSTELLUNGEN ════════════ -->
<div id="tab-settings" class="tab">
  <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-bottom:1rem">
    <button class="btn btn-x bsm active" id="sb-wifi"     onclick="showSec('wifi',this)">📶 WiFi</button>
    <button class="btn btn-x bsm" id="sb-mqtt"            onclick="showSec('mqtt',this)">🏠 MQTT</button>
    <button class="btn btn-x bsm" id="sb-tg"              onclick="showSec('tg',this)">✈️ Telegram</button>
    <button class="btn btn-x bsm" id="sb-weather"         onclick="showSec('weather',this)">🌤 Wetter</button>
    <button class="btn btn-x bsm" id="sb-channels"        onclick="showSec('channels',this)">🚿 Kanäle</button>
  </div>

  <!-- WiFi -->
  <div id="sec-wifi" class="card">
    <div class="ct">WiFi & Netzwerk</div>
    <div class="fg"><label class="fl">WLAN Name (SSID)</label><input class="fi" id="c-ssid" type="text" placeholder="MeinWLAN"></div>
    <div class="fg"><label class="fl">Passwort</label><input class="fi" id="c-wpass" type="password" placeholder="••••••••"></div>
    <div class="fg"><label class="fl">Hostname</label><input class="fi" id="c-host" type="text" placeholder="smart-irrigation"></div>
    <button class="btn btn-g" onclick="saveSec('wifi')">💾 Speichern &amp; Neustart</button>
  </div>

  <!-- MQTT -->
  <div id="sec-mqtt" class="card" style="display:none">
    <div class="ct">Home Assistant / MQTT</div>
    <div class="fg frow" style="margin-bottom:.9rem"><label class="fl" style="margin:0">MQTT aktivieren</label><label class="tgl"><input type="checkbox" id="c-mqen"><span class="tsl"></span></label></div>
    <div class="fg"><label class="fl">Server / IP</label><input class="fi" id="c-mqsrv" type="text" placeholder="192.168.1.100"></div>
    <div class="fg"><label class="fl">Port</label><input class="fi" id="c-mqport" type="number" placeholder="1883"></div>
    <div class="fg"><label class="fl">Benutzername</label><input class="fi" id="c-mquser" type="text" placeholder="mqtt_user"></div>
    <div class="fg"><label class="fl">Passwort</label><input class="fi" id="c-mqpass" type="password"></div>
    <button class="btn btn-g" onclick="saveSec('mqtt')">💾 Speichern</button>
  </div>

  <!-- Telegram -->
  <div id="sec-tg" class="card" style="display:none">
    <div class="ct">Telegram Bot</div>
    <div class="alert alert-i" style="margin-bottom:1rem">
      ℹ️ Bot erstellen: @BotFather → /newbot. Chat-ID: @userinfobot schreiben.
    </div>
    <div class="fg"><label class="fl">Bot Token</label><input class="fi" id="c-tgtoken" type="text" placeholder="123456789:ABCdef..."></div>
    <div class="fg"><label class="fl">Chat ID</label><input class="fi" id="c-tgchat" type="text" placeholder="123456789"></div>
    <div style="display:flex;gap:.5rem;flex-wrap:wrap;margin-top:.25rem">
      <button class="btn btn-b bsm" onclick="testTg()">📤 Test senden</button>
      <button class="btn btn-g" onclick="saveSec('tg')">💾 Speichern</button>
    </div>
  </div>

  <!-- Wetter -->
  <div id="sec-weather" class="card" style="display:none">
    <div class="ct">OpenWeatherMap</div>
    <div class="fg frow" style="margin-bottom:.9rem"><label class="fl" style="margin:0">Wetter aktivieren</label><label class="tgl"><input type="checkbox" id="c-wen"><span class="tsl"></span></label></div>
    <div class="fg"><label class="fl">API Key (kostenlos auf openweathermap.org)</label><input class="fi" id="c-owmkey" type="text" placeholder="abc123..."></div>
    <div class="fg"><label class="fl">Stadt</label><input class="fi" id="c-owmcity" type="text" placeholder="Berlin"></div>
    <div class="fg"><label class="fl">Land (ISO 2-stellig)</label><input class="fi" id="c-owmcc" type="text" placeholder="DE" style="width:80px"></div>
    <button class="btn btn-g" onclick="saveSec('weather')">💾 Speichern</button>
  </div>

  <!-- Kanal-Einstellungen -->
  <div id="sec-channels" class="card" style="display:none">
    <div class="ct">Kanal-Konfiguration</div>
    <div style="display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem">
      <div class="fg" style="flex:0 0 140px">
        <label class="fl">Aktive Kanäle (1-8)</label>
        <input class="fi" id="c-nch" type="number" min="1" max="8">
      </div>
      <div class="fg frow" style="align-items:flex-end;padding-bottom:.15rem">
        <label class="fl" style="margin:0;margin-right:.75rem">Wasserstand-Sensor</label>
        <label class="tgl"><input type="checkbox" id="c-wlen"><span class="tsl"></span></label>
      </div>
    </div>
    <div id="ch-cfgs"></div>
    <button class="btn btn-g" onclick="saveSec('channels')">💾 Speichern</button>
  </div>
</div>

<!-- ════════════ OTA UPDATE ════════════ -->
<div id="tab-ota" class="tab">
  <div class="card" style="max-width:480px;margin:0 auto">
    <div class="ct">🔄 OTA Firmware Update</div>
    <div class="alert alert-i" style="margin-bottom:1rem">
      ℹ️ Arduino IDE → Sketch → Exportiere binäre Datei → .bin hier hochladen
    </div>
    <div class="dz" id="dz" onclick="document.getElementById('fw').click()">
      <div class="dzicon">📦</div>
      <div style="font-weight:700;margin-bottom:.25rem">Firmware .bin hier ablegen</div>
      <div style="font-size:.8rem;color:var(--muted)">oder klicken zum Auswählen</div>
    </div>
    <input type="file" id="fw" accept=".bin" style="display:none" onchange="pickFw(this.files[0])">
    <div id="fw-info" style="display:none;margin-top:.75rem;padding:.7rem;background:rgba(34,197,94,.09);border-radius:8px;font-size:.85rem;color:var(--green)"></div>
    <div id="fw-prog" style="display:none;margin-top:1rem">
      <div class="pbar"><div class="pfill" id="fw-bar" style="width:0;background:var(--green)"></div></div>
      <div style="text-align:center;font-size:.8rem;color:var(--sub);margin-top:.4rem" id="fw-status">Uploading...</div>
    </div>
    <button class="btn btn-g bfull" style="margin-top:1rem" id="fw-btn" onclick="uploadFw()" disabled>⬆️ Firmware hochladen</button>
  </div>
</div>

</main>

<!-- TOAST -->
<div id="toast"></div>

<script>
'use strict';

// ═══════════════════ STATE ═══════════════════
let STATUS = null, CFG = null, chart = null;
let chartCh = 0, chartRange = '24h';
let selCh = 0, fwFile = null, toastTimer;
let wizStep = 0;

// ═══════════════════ NAV ═══════════════════
function showTab(id, btn) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.nb').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + id).classList.add('active');
  if (btn) btn.classList.add('active');
  if (id === 'stats') { buildStatChSel(); loadChart(); }
  if (id === 'settings') loadCfg();
  if (id === 'channels') renderChDetail();
}

function showSec(id, btn) {
  document.querySelectorAll('[id^="sec-"]').forEach(s => s.style.display = 'none');
  document.querySelectorAll('[id^="sb-"]').forEach(b => b.classList.remove('active'));
  document.getElementById('sec-' + id).style.display = '';
  btn.classList.add('active');
}

// ═══════════════════ API ═══════════════════
async function api(path, opts) {
  try {
    const r = await fetch(path, opts);
    return await r.json();
  } catch(e) { return null; }
}

async function fetchStatus() {
  const d = await api('/api/status');
  if (!d) return;
  STATUS = d;
  updateDash(d);
}

async function loadCfg() {
  const d = await api('/api/config');
  if (!d) return;
  CFG = d;
  fillCfg(d);
}

async function saveSec(sec) {
  const body = {};
  if (sec === 'wifi') {
    body.ssid = g('c-ssid').value;
    body.wifi_password = g('c-wpass').value;
    body.hostname = g('c-host').value;
  } else if (sec === 'mqtt') {
    body.mqtt_enabled = g('c-mqen').checked;
    body.mqtt_server = g('c-mqsrv').value;
    body.mqtt_port = +g('c-mqport').value || 1883;
    body.mqtt_user = g('c-mquser').value;
    body.mqtt_password = g('c-mqpass').value;
  } else if (sec === 'tg') {
    body.telegram_token = g('c-tgtoken').value;
    body.telegram_chat_id = g('c-tgchat').value;
  } else if (sec === 'weather') {
    body.weather_enabled = g('c-wen').checked;
    body.owm_api_key = g('c-owmkey').value;
    body.owm_city = g('c-owmcity').value;
    body.owm_country = g('c-owmcc').value;
  } else if (sec === 'channels') {
    const n = +g('c-nch').value || 1;
    body.num_channels = Math.min(8, Math.max(1, n));
    body.water_level_enabled = g('c-wlen').checked;
    body.channels = [];
    for (let i = 0; i < body.num_channels; i++) {
      body.channels.push({
        name: gv('cc-name-'+i) || ('Kanal '+(i+1)),
        plant_id: +gv('cc-plant-'+i) || 0,
        moisture_threshold: +gv('cc-thr-'+i) || 40,
        watering_duration: +gv('cc-dur-'+i) || 30,
        auto_enabled: !!g('cc-auto-'+i)?.checked,
        dry_value: +gv('cc-dry-'+i) || 3500,
        wet_value: +gv('cc-wet-'+i) || 1500,
      });
    }
  }

  const r = await api('/api/config', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify(body)
  });
  if (r && r.ok) {
    toast('✅ Gespeichert!', 'success');
    if (sec === 'wifi') setTimeout(() => location.reload(), 3000);
  } else {
    toast('❌ Fehler beim Speichern', 'error');
  }
}

async function waterCh(ch, dur) {
  if (!dur) dur = prompt('Dauer in Sekunden:', '30');
  if (!dur) return;
  await api('/api/water/'+ch, {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({duration:+dur})});
  setTimeout(fetchStatus, 600);
}

async function stopCh(ch) {
  await api('/api/stop/'+ch, {method:'POST'});
  setTimeout(fetchStatus, 400);
}

async function testTg() {
  const r = await api('/api/telegram/test', {method:'POST'});
  toast(r && r.ok ? '✅ Testnachricht gesendet!' : '❌ Fehler: ' + (r && r.error || 'unbekannt'), r && r.ok ? 'success' : 'error');
}

async function calDry(ch) {
  const r = await api('/api/calibrate/dry/'+ch, {method:'POST'});
  if (r && r.ok) { toast('✅ Trocken-ADC ' + r.value + ' gespeichert', 'success'); setWiz(2); }
  else toast('❌ Fehler', 'error');
}

async function calWet(ch) {
  const r = await api('/api/calibrate/wet/'+ch, {method:'POST'});
  if (r && r.ok) { toast('✅ Nass-ADC ' + r.value + ' gespeichert', 'success'); setWiz(0); fetchStatus(); }
  else toast('❌ Fehler', 'error');
}

// ═══════════════════ DASHBOARD ═══════════════════
function updateDash(d) {
  sv('s-uptime', fmtUp(d.uptime || 0));
  sv('s-ch', d.num_channels || '--');
  sv('s-heap', ((d.heap || 0)/1024).toFixed(0) + 'KB');
  sv('s-rssi', (d.rssi || '--') + '');
  let tot = 0; if (d.channels) d.channels.forEach(c => tot += c.water_count_today||0);
  sv('s-today', tot);
  const ip = d.ip || '--';
  const el = g('s-ip'); if (el) { el.textContent = ip; el.href = 'http://'+ip; }
  sv('s-time', new Date().toLocaleTimeString('de-DE'));

  dot('d-wifi', d.wifi_connected);
  dot('d-mqtt', d.mqtt_connected);
  dot('d-tg',   d.telegram_ok);

  // Wasserstand
  if (d.water_level_pct !== undefined && d.water_level_pct >= 0) {
    show('wl-banner', true);
    sv('wl-pct', d.water_level_pct + '%');
    show('wl-warn', d.water_level_pct < 15);
  }

  // Wetter
  if (d.weather) {
    const w = d.weather;
    sv('w-temp', w.temp.toFixed(1) + '°C');
    sv('w-desc', w.description || '');
    sv('w-hum',  (w.humidity||0) + '%');
    sv('w-feel', (w.feels_like||w.temp).toFixed(1) + '°C');
    sv('w-wind', ((w.wind_speed||0)*3.6).toFixed(0) + ' km/h');
    sv('w-icon', weatherEmoji(w.main));
    show('w-info', !!w.skip_watering);
    g('w-skip').innerHTML = w.skip_watering ? '<span class="badge bb">⏸ Pause</span>' : '';
  }

  // Kanal-Karten
  if (d.channels) renderChOverview(d.channels);
}

function renderChOverview(chs) {
  const el = g('ch-overview');
  if (!el) return;
  const C = 2 * Math.PI * 52;
  el.innerHTML = chs.map((c, i) => {
    const pct = c.moisture_pct || 0;
    const col = pct < 25 ? 'var(--red)' : pct < 45 ? 'var(--amber)' : 'var(--green)';
    const off = C * (1 - pct/100);
    const bClass = c.pump_active ? 'bb' : pct < 30 ? 'ba' : 'bg';
    const bTxt   = c.pump_active ? '💧 Läuft' : pct < 30 ? '⚠️ Trocken' : '✅ OK';
    return `<div class="ch-card ${c.pump_active?'pumping':pct<30?'dry':''}">
      <div class="ch-hd">
        <div><div class="ch-name">${esc(c.name)}</div><div class="ch-plant">${esc(c.plant_emoji||'')} ${esc(c.plant_name||'')}</div></div>
        <span class="badge ${bClass}">${bTxt}</span>
      </div>
      <div class="gauge">
        <svg viewBox="0 0 120 120" width="120" height="120">
          <circle class="gbg" cx="60" cy="60" r="52"/>
          <circle class="gfill" cx="60" cy="60" r="52" stroke="${col}" stroke-dasharray="${C}" stroke-dashoffset="${off}"/>
        </svg>
        <div class="gtxt">
          <span class="gpct" style="color:${col}">${pct}%</span>
          <span class="glbl">Feuchtigkeit</span>
        </div>
      </div>
      <div class="pbar"><div class="pfill" style="width:${pct}%;background:${col}"></div></div>
      <div class="srow" style="font-size:.73rem">
        <div class="si"><span style="font-weight:700">${c.moisture_threshold||'--'}%</span><span class="sl">Schwelle</span></div>
        <div class="si"><span style="font-weight:700">${c.last_watered ? ago(c.last_watered) : 'Nie'}</span><span class="sl">Zuletzt</span></div>
        <div class="si"><span style="font-weight:700">${c.water_count_today||0}×</span><span class="sl">Heute</span></div>
      </div>
      <div style="display:flex;gap:.5rem;margin-top:.75rem">
        ${c.pump_active
          ? `<button class="btn btn-r bsm" onclick="stopCh(${i})">⏹ Stop</button>`
          : `<button class="btn btn-b bsm" onclick="waterCh(${i})">💧 Gießen</button>`}
        <button class="btn btn-x bsm" onclick="showTab('channels',null);selCh=${i};renderChDetail()">🔧 Details</button>
      </div>
    </div>`;
  }).join('');
}

// ═══════════════════ CHANNEL DETAIL ═══════════════════
function renderChDetail() {
  if (!STATUS || !STATUS.channels) return;
  const chs = STATUS.channels;
  const el = g('ch-detail');
  const sel = g('ch-sel');

  // Kanal-Tabs
  if (sel) sel.innerHTML = chs.map((c,i) =>
    `<button class="btn btn-x bsm ${i===selCh?'active':''}" onclick="selCh=${i};renderChDetail()">${esc(c.name)}</button>`
  ).join('');

  const c = chs[selCh];
  if (!c || !el) return;
  const pct = c.moisture_pct || 0;
  const col = pct < 25 ? 'var(--red)' : pct < 45 ? 'var(--amber)' : 'var(--green)';
  const C   = 2 * Math.PI * 52;

  el.innerHTML = `
  <div class="g2 gap">
    <!-- Sensor Status -->
    <div class="card">
      <div class="ct">Sensor — Kanal ${selCh+1}</div>
      <div class="gauge">
        <svg viewBox="0 0 120 120" width="120" height="120">
          <circle class="gbg" cx="60" cy="60" r="52"/>
          <circle class="gfill" cx="60" cy="60" r="52" stroke="${col}"
            stroke-dasharray="${C}" stroke-dashoffset="${C*(1-pct/100)}"/>
        </svg>
        <div class="gtxt">
          <span class="gpct" style="color:${col}">${pct}%</span>
          <span class="glbl">Feuchtigkeit</span>
        </div>
      </div>
      <div style="text-align:center;font-size:.8rem;color:var(--muted)">
        Rohwert ADC: <strong>${c.moisture_raw||'--'}</strong>
      </div>
      <div style="text-align:center;font-size:.8rem;color:var(--muted);margin-top:.25rem">
        ${esc(c.plant_emoji||'')} ${esc(c.plant_name||'–')} | Auto: ${c.auto_enabled ? '✅' : '❌'}
      </div>
      ${c.pump_active ? `<div style="text-align:center;margin-top:.75rem"><span class="pump-dot"></span><span style="color:var(--blue);font-size:.85rem">Pumpe aktiv — noch ${c.pump_remaining||0}s</span></div>` : ''}
    </div>
    <!-- Steuerung -->
    <div class="card">
      <div class="ct">Manuelle Steuerung</div>
      <div class="fg">
        <label class="fl">Dauer (Sekunden)</label>
        <input class="fi" id="mdur" type="number" value="${c.watering_duration||30}" min="1" max="600" style="max-width:140px">
      </div>
      ${c.pump_active
        ? `<button class="btn btn-r bfull" onclick="stopCh(${selCh})">⏹ Pumpe stoppen</button>`
        : `<button class="btn btn-b bfull" onclick="waterCh(${selCh}, g('mdur').value)">💧 Jetzt bewässern</button>`}
      <div style="margin-top:.9rem;font-size:.78rem;color:var(--muted);line-height:1.7">
        🕐 Zuletzt: ${c.last_watered ? new Date(c.last_watered*1000).toLocaleString('de-DE') : 'Nie'}<br>
        📊 Heute: ${c.water_count_today||0}× bewässert<br>
        🎯 Schwelle: ${c.moisture_threshold||'--'}% | Pumpe: ${c.watering_duration||'--'}s
      </div>
    </div>
  </div>

  <!-- Kalibrierung -->
  <div class="card">
    <div class="ct">🎯 Sensor-Kalibrierung — Kanal ${selCh+1}</div>
    <div class="wdots" id="wdots">
      <div class="wd done" id="wd0"></div>
      <div class="wd" id="wd1"></div>
      <div class="wd" id="wd2"></div>
    </div>

    <div class="wstep active" id="ws0">
      <p style="color:var(--sub);margin-bottom:.9rem;line-height:1.6">
        2-Schritt-Kalibrierung: Sensor zuerst <strong>trocken</strong> halten (Luft), dann in <strong>Wasser</strong> tauchen.
      </p>
      <p style="font-size:.8rem;color:var(--muted);margin-bottom:1rem">
        Aktuell gespeichert — Trocken: <strong>${c.dry_value||3500}</strong> &nbsp;|&nbsp; Nass: <strong>${c.wet_value||1500}</strong>
      </p>
      <button class="btn btn-b" onclick="setWiz(1)">▶ Kalibrierung starten</button>
    </div>

    <div class="wstep" id="ws1">
      <p style="color:var(--sub);margin-bottom:.75rem">Halte den Sensor vollständig <strong>in der Luft</strong> (trocken).</p>
      <div style="font-size:2.2rem;font-weight:800;text-align:center;color:var(--amber);margin-bottom:1rem">${c.moisture_raw||'--'}</div>
      <div style="display:flex;gap:.5rem">
        <button class="btn btn-x" onclick="setWiz(0)">◀ Zurück</button>
        <button class="btn btn-a" onclick="calDry(${selCh})">📍 Trocken-Wert speichern</button>
      </div>
    </div>

    <div class="wstep" id="ws2">
      <p style="color:var(--sub);margin-bottom:.75rem">Tauche den Sensor nun vollständig in <strong>Wasser</strong>.</p>
      <div style="font-size:2.2rem;font-weight:800;text-align:center;color:var(--blue);margin-bottom:1rem">${c.moisture_raw||'--'}</div>
      <div style="display:flex;gap:.5rem">
        <button class="btn btn-x" onclick="setWiz(1)">◀ Zurück</button>
        <button class="btn btn-g" onclick="calWet(${selCh})">💧 Nass-Wert speichern</button>
      </div>
    </div>
  </div>`;
}

function setWiz(step) {
  wizStep = step;
  for (let i = 0; i < 3; i++) {
    const s = g('ws'+i); if (s) { s.classList.toggle('active', i===step); }
    const d = g('wd'+i); if (d) { d.className = 'wd '+(i<step?'done':i===step?'cur':''); }
  }
}

// ═══════════════════ SETTINGS FILL ═══════════════════
function fillCfg(d) {
  sv2('c-ssid',  d.ssid||'');
  sv2('c-host',  d.hostname||'smart-irrigation');
  chk('c-mqen',  d.mqtt_enabled);
  sv2('c-mqsrv', d.mqtt_server||'');
  sv2('c-mqport',d.mqtt_port||1883);
  sv2('c-mquser',d.mqtt_user||'');
  sv2('c-tgtoken',d.telegram_token||'');
  sv2('c-tgchat', d.telegram_chat_id||'');
  chk('c-wen',   d.weather_enabled);
  sv2('c-owmkey', d.owm_api_key||'');
  sv2('c-owmcity',d.owm_city||'');
  sv2('c-owmcc',  d.owm_country||'');
  sv2('c-nch',    d.num_channels||1);
  chk('c-wlen',   d.water_level_enabled);

  // Kanal-Konfigurationen bauen
  const plants = d.plants || [];
  const pOpts = plants.map((p,i) => `<option value="${i}">${esc(p.emoji||'')} ${esc(p.name_de)} (${p.moisture_ideal}% ideal)</option>`).join('');

  let html = '';
  if (d.channels) {
    d.channels.forEach((c, i) => {
      html += `<div class="ch-sect">
        <div style="font-weight:700;color:var(--sub);margin-bottom:.75rem">Kanal ${i+1}</div>
        <div style="display:grid;grid-template-columns:1fr 1fr;gap:0 .75rem">
          <div class="fg"><label class="fl">Name</label><input class="fi" id="cc-name-${i}" value="${esc(c.name||'Kanal '+(i+1))}"></div>
          <div class="fg"><label class="fl">Pflanze</label>
            <select class="fs" id="cc-plant-${i}">${pOpts.replace(`value="${c.plant_id}"`,`value="${c.plant_id}" selected`)}</select></div>
          <div class="fg"><label class="fl">Schwellwert (%)</label><input class="fi" id="cc-thr-${i}" type="number" min="0" max="100" value="${c.moisture_threshold||40}"></div>
          <div class="fg"><label class="fl">Pumpzeit (s)</label><input class="fi" id="cc-dur-${i}" type="number" min="1" max="600" value="${c.watering_duration||30}"></div>
          <div class="fg"><label class="fl">Kalibrierung Trocken (ADC)</label><input class="fi" id="cc-dry-${i}" type="number" value="${c.dry_value||3500}"></div>
          <div class="fg"><label class="fl">Kalibrierung Nass (ADC)</label><input class="fi" id="cc-wet-${i}" type="number" value="${c.wet_value||1500}"></div>
        </div>
        <div class="fg frow"><label class="fl" style="margin:0">Automatische Bewässerung</label><label class="tgl"><input type="checkbox" id="cc-auto-${i}" ${c.auto_enabled?'checked':''}><span class="tsl"></span></label></div>
      </div>`;
    });
  }
  const el = g('ch-cfgs'); if (el) el.innerHTML = html;
}

// ═══════════════════ CHART ═══════════════════
function buildStatChSel() {
  if (!STATUS) return;
  const el = g('stat-ch'); if (!el) return;
  el.innerHTML = (STATUS.channels||[]).map((c,i) =>
    `<option value="${i}">${esc(c.name)}</option>`
  ).join('');
  el.value = chartCh;
}

function setRange(r, btn) {
  chartRange = r;
  document.querySelectorAll('#tab-stats .bsm').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  loadChart();
}

async function loadChart() {
  chartCh = +(g('stat-ch')?.value||0);
  const d = await api(`/api/logs?channel=${chartCh}&range=${chartRange}`);
  if (!d) return;
  renderChart(d);
  renderLog(d.events||[]);
}

function renderChart(d) {
  const ctx = g('chart'); if (!ctx) return;
  if (chart) chart.destroy();
  const labels = (d.readings||[]).map(r =>
    new Date(r.ts*1000).toLocaleString('de-DE',{month:'2-digit',day:'2-digit',hour:'2-digit',minute:'2-digit'})
  );
  const vals = (d.readings||[]).map(r => r.moisture);
  const thr = d.threshold||40;
  chart = new Chart(ctx, {
    type:'line',
    data:{
      labels,
      datasets:[
        {label:'Feuchtigkeit %',data:vals,borderColor:'#22c55e',backgroundColor:'rgba(34,197,94,0.09)',fill:true,tension:.4,pointRadius:2,pointHoverRadius:5},
        {label:'Schwellwert',data:Array(labels.length).fill(thr),borderColor:'#f59e0b',borderDash:[5,5],pointRadius:0,fill:false}
      ]
    },
    options:{
      responsive:true,maintainAspectRatio:true,
      plugins:{legend:{labels:{color:'#94a3b8',font:{size:12}}}},
      scales:{
        x:{ticks:{color:'#64748b',maxTicksLimit:8},grid:{color:'rgba(255,255,255,.04)'}},
        y:{min:0,max:100,ticks:{color:'#64748b'},grid:{color:'rgba(255,255,255,.04)'}}
      }
    }
  });
}

function renderLog(evts) {
  const el = g('log-list'); if (!el) return;
  if (!evts.length) { el.innerHTML = '<div style="color:var(--muted);text-align:center;padding:2rem">Keine Einträge im gewählten Zeitraum</div>'; return; }
  el.innerHTML = [...evts].reverse().map(e => {
    const t = new Date((e.ts||0)*1000).toLocaleString('de-DE');
    const bc = e.type==='water'?'bb':e.type==='alert'?'br':'bx';
    return `<div class="logrow">
      <span class="ltime">${t}</span>
      <span class="badge ${bc}" style="flex-shrink:0">${esc(e.type||'')}</span>
      <span class="lmsg">${esc(e.msg||'')}</span>
    </div>`;
  }).join('');
}

// ═══════════════════ OTA ═══════════════════
function pickFw(file) {
  if (!file) return;
  fwFile = file;
  const el = g('fw-info');
  el.style.display = '';
  el.textContent = '📦 ' + file.name + ' (' + (file.size/1024).toFixed(1) + ' KB)';
  g('fw-btn').disabled = false;
}

function uploadFw() {
  if (!fwFile) return;
  const fd = new FormData();
  fd.append('firmware', fwFile);
  const xhr = new XMLHttpRequest();
  xhr.open('POST', '/api/ota', true);
  g('fw-prog').style.display = '';
  g('fw-btn').disabled = true;
  xhr.upload.onprogress = e => {
    const p = Math.round(e.loaded/e.total*100);
    g('fw-bar').style.width = p+'%';
    sv('fw-status', 'Hochladen... '+p+'%');
  };
  xhr.onload = () => {
    if (xhr.status===200) {
      sv('fw-status', '✅ Update erfolgreich! Neustart in 5s...');
      setTimeout(() => location.reload(), 5500);
    } else {
      sv('fw-status', '❌ Update fehlgeschlagen (HTTP '+xhr.status+')');
      g('fw-btn').disabled = false;
    }
  };
  xhr.onerror = () => { sv('fw-status','❌ Netzwerkfehler'); g('fw-btn').disabled=false; };
  xhr.send(fd);
}

const dz = g('dz');
dz.addEventListener('dragover', e => { e.preventDefault(); dz.classList.add('drag'); });
dz.addEventListener('dragleave', () => dz.classList.remove('drag'));
dz.addEventListener('drop', e => { e.preventDefault(); dz.classList.remove('drag'); pickFw(e.dataTransfer.files[0]); });

// ═══════════════════ HELPERS ═══════════════════
function g(id) { return document.getElementById(id); }
function gv(id) { return g(id)?.value; }
function sv(id, v) { const e=g(id); if(e) e.textContent=v+''; }
function sv2(id,v) { const e=g(id); if(e) e.value=v; }
function chk(id,v) { const e=g(id); if(e) e.checked=!!v; }
function show(id,v) { const e=g(id); if(e) e.style.display=v?'':'none'; }
function dot(id,on) { const e=g(id); if(e) e.className='di '+(on?'on':'off'); }
function esc(s) { return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }

function fmtUp(s) {
  const d=Math.floor(s/86400),h=Math.floor(s%86400/3600),m=Math.floor(s%3600/60);
  if(d>0) return d+'d '+h+'h';
  if(h>0) return h+'h '+m+'m';
  return m+'m '+(s%60)+'s';
}
function ago(ts) {
  const d=Math.floor(Date.now()/1000)-ts;
  if(d<60) return d+'s';
  if(d<3600) return Math.floor(d/60)+'m';
  if(d<86400) return Math.floor(d/3600)+'h';
  return Math.floor(d/86400)+'d';
}
function weatherEmoji(m) {
  return {Clear:'☀️',Clouds:'☁️',Rain:'🌧️',Drizzle:'🌦️',Thunderstorm:'⛈️',Snow:'❄️',Mist:'🌫️',Fog:'🌫️',Haze:'🌫️'}[m]||'🌡️';
}

let toastTmr;
function toast(msg, type) {
  const el = g('toast');
  el.innerHTML = `<div class="alert alert-${type==='success'?'s':type==='error'?'e':'i'}" style="box-shadow:0 10px 30px rgba(0,0,0,.4)">${msg}</div>`;
  clearTimeout(toastTmr);
  toastTmr = setTimeout(() => el.innerHTML='', 4000);
}

// ═══════════════════ INIT ═══════════════════
fetchStatus();
setInterval(fetchStatus, 5000);
</script>
</body>
</html>
)HTML";
