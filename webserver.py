"""
webserver.py – Async HTTP-Server mit REST-API und Web-Interface
Läuft im Heimnetz, bietet vollständige Konfiguration über Browser.
"""
import asyncio
import json
import gc
import os
import time
from config import get_config
from plants_db import all_as_list

# ── Web-UI HTML (minimiert, ohne externe Dependencies) ──────────────
_HTML = """\
<!DOCTYPE html><html lang="de">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Irrigation</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:system-ui,sans-serif;background:#0a0f1e;color:#e2e8f0;font-size:14px}
nav{background:rgba(255,255,255,.04);border-bottom:1px solid rgba(255,255,255,.08);
    display:flex;overflow-x:auto;padding:0 8px}
nav button{background:none;border:none;color:#94a3b8;padding:14px 16px;cursor:pointer;
           white-space:nowrap;font-size:.85rem;border-bottom:2px solid transparent}
nav button.on{color:#22c55e;border-bottom-color:#22c55e}
.page{display:none;padding:12px}.page.on{display:block}
.card{background:rgba(255,255,255,.05);border:1px solid rgba(255,255,255,.1);
      border-radius:12px;padding:14px;margin-bottom:10px}
h2{font-size:.95rem;color:#22c55e;margin-bottom:10px}
h3{font-size:.88rem;color:#94a3b8;margin-bottom:8px}
label{display:block;color:#94a3b8;font-size:.78rem;margin-top:8px;margin-bottom:3px}
input,select,textarea{width:100%;background:#1e293b;border:1px solid #334155;border-radius:7px;
  color:#e2e8f0;padding:8px 10px;font-size:.88rem}
input:focus,select:focus{outline:none;border-color:#22c55e}
.row{display:flex;gap:8px;align-items:flex-end}
.row>*{flex:1}
.btn{padding:8px 14px;border:none;border-radius:7px;cursor:pointer;font-size:.85rem;font-weight:600}
.btn-g{background:#22c55e;color:#0a0f1e}.btn-r{background:#ef4444;color:#fff}
.btn-s{background:rgba(255,255,255,.07);color:#e2e8f0;border:1px solid #334155}
.gauge-wrap{text-align:center;padding:4px 0}
.gauge{display:inline-block;position:relative;width:80px;height:40px;overflow:hidden;margin:0 auto}
.gauge-bg,.gauge-fill{position:absolute;width:80px;height:80px;border-radius:50%;top:0;left:0;
  transform-origin:center center;clip:rect(0,80px,40px,0px)}
.gauge-bg{background:#1e293b}
.gauge-fill{background:#22c55e;transition:.5s}
.pct{font-size:1.1rem;font-weight:700;color:#22c55e;display:block;margin-top:2px}
.badge{display:inline-block;padding:2px 8px;border-radius:99px;font-size:.75rem;font-weight:600}
.badge-g{background:rgba(34,197,94,.15);color:#22c55e}
.badge-r{background:rgba(239,68,68,.15);color:#ef4444}
.badge-y{background:rgba(234,179,8,.15);color:#eab308}
.toggle-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid rgba(255,255,255,.05)}
.toggle{position:relative;width:42px;height:22px;flex-shrink:0}
.toggle input{opacity:0;width:0;height:0}
.slider{position:absolute;inset:0;background:#334155;border-radius:11px;cursor:pointer;transition:.2s}
.slider:before{content:'';position:absolute;width:16px;height:16px;left:3px;top:3px;background:#fff;border-radius:50%;transition:.2s}
input:checked+.slider{background:#22c55e}
input:checked+.slider:before{transform:translateX(20px)}
.toast{position:fixed;bottom:16px;left:50%;transform:translateX(-50%);background:#22c55e;
  color:#0a0f1e;padding:8px 18px;border-radius:8px;font-size:.85rem;font-weight:600;
  opacity:0;transition:.3s;pointer-events:none;z-index:99}
.ch-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:8px}
.ch-card{background:#1e293b;border:1px solid #334155;border-radius:10px;padding:12px;cursor:pointer;transition:.2s}
.ch-card:hover{border-color:#22c55e}
.ch-card.pump{border-color:#22c55e;background:rgba(34,197,94,.07)}
.stat-row{display:flex;justify-content:space-between;padding:5px 0;border-bottom:1px solid rgba(255,255,255,.05);font-size:.85rem}
</style></head>
<body>
<nav id="nav"></nav>
<div id="pages"></div>
<div class="toast" id="toast"></div>

<script>
var state={};var cfg={};var plants=[];var pollTimer=null;

var TABS=[
  {id:'dash',  label:'📊 Dashboard'},
  {id:'ch',    label:'🌿 Kanäle'},
  {id:'stat',  label:'📈 Statistik'},
  {id:'sched', label:'⏰ Zeitplan'},
  {id:'cfg',   label:'⚙️ Einstellungen'},
  {id:'ota',   label:'🔄 Update'}
];

function init(){
  buildNav();buildPages();
  loadState();loadConfig();
  pollTimer=setInterval(loadState,8000);
}

function buildNav(){
  var n=document.getElementById('nav');
  TABS.forEach(function(t,i){
    var b=document.createElement('button');
    b.textContent=t.label;b.onclick=function(){showTab(t.id);};
    b.id='nav-'+t.id;n.appendChild(b);
  });
}

function showTab(id){
  TABS.forEach(function(t){
    document.getElementById('page-'+t.id).className='page'+(t.id===id?' on':'');
    document.getElementById('nav-'+t.id).className=(t.id===id?'on':'');
  });
  if(id==='stat') loadStats();
  if(id==='sched') loadSched();
}

function buildPages(){
  var c=document.getElementById('pages');
  TABS.forEach(function(t){
    var d=document.createElement('div');
    d.id='page-'+t.id;d.className='page';
    if(t.id==='dash')  d.innerHTML=buildDash();
    if(t.id==='ch')    d.innerHTML='<div class="ch-grid" id="ch-grid"></div>';
    if(t.id==='stat')  d.innerHTML=buildStat();
    if(t.id==='sched') d.innerHTML=buildSched();
    if(t.id==='cfg')   d.innerHTML=buildCfg();
    if(t.id==='ota')   d.innerHTML=buildOta();
    c.appendChild(d);
  });
  showTab('dash');
}

function buildDash(){return'<div id="dash-content"><div class="card"><p style="color:#94a3b8;text-align:center">Lade...</p></div></div>';}

function renderDash(){
  var s=state; var h='';
  // System-Info
  h+='<div class="card"><h2>Systemstatus</h2>';
  h+='<div class="stat-row"><span>IP-Adresse</span><span>'+s.ip+'</span></div>';
  h+='<div class="stat-row"><span>WiFi</span><span>'+s.rssi+'dBm</span></div>';
  h+='<div class="stat-row"><span>Freier Heap</span><span>'+(s.heap/1024).toFixed(0)+'kB</span></div>';
  if(s.water_level>=0)h+='<div class="stat-row"><span>Wasserstand</span><span>'+s.water_level+'%</span></div>';
  h+='</div>';
  // Wetter
  if(s.weather&&s.weather.temp!==undefined){
    var w=s.weather;
    h+='<div class="card"><h2>🌡️ Wetter – '+w.city+'</h2>';
    h+='<div class="stat-row"><span>Temperatur</span><span>'+w.temp.toFixed(1)+'°C</span></div>';
    h+='<div class="stat-row"><span>Luftfeuchte</span><span>'+Math.round(w.humidity)+'%</span></div>';
    h+='<div class="stat-row"><span>Niederschlag</span><span>'+w.rain_1h.toFixed(1)+'mm/h</span></div>';
    h+='<div class="stat-row"><span>Vorhersage</span><span>'+(w.rain_forecast?'🌧️ Regen':'☀️ kein Regen')+'</span></div>';
    h+='</div>';
  }
  // Kanäle
  h+='<div class="card"><h2>Kanäle</h2><div class="ch-grid">';
  (s.channels||[]).forEach(function(ch,i){
    var pct=ch.moisture;
    var col=pct>60?'#22c55e':pct>30?'#eab308':'#ef4444';
    var badge=ch.pump?'<span class="badge badge-g">PUMP</span>':
              pct<(ch.thresh||40)?'<span class="badge badge-r">TROCKEN</span>':
              '<span class="badge badge-g">OK</span>';
    h+='<div class="ch-card'+(ch.pump?' pump':'')+ '" onclick="showChDetail('+i+')">';
    h+='<div style="font-weight:600;margin-bottom:6px">'+ch.name+'</div>';
    h+='<div style="font-size:1.8rem;font-weight:700;color:'+col+'">'+pct+'%</div>';
    h+=badge;
    h+='<div style="font-size:.75rem;color:#94a3b8;margin-top:4px">'+(ch.auto_mode?'⚙️ Auto':'✋ Manuell')+'</div>';
    h+='</div>';
  });
  h+='</div></div>';
  document.getElementById('dash-content').innerHTML=h;
}

function renderChannels(){
  var h='';
  (state.channels||[]).forEach(function(ch,i){
    var plant=plants[ch.plant_idx]||{};
    h+='<div class="card">';
    h+='<div class="row" style="margin-bottom:10px">';
    h+='<h2>'+ch.name+'</h2>';
    h+='<div>';
    h+='<button class="btn btn-g" style="margin-right:4px" onclick="pump('+i+',1)">💧 Gießen</button>';
    h+='<button class="btn btn-r" onclick="pump('+i+',0)">■ Stop</button>';
    h+='</div></div>';
    // Feuchte
    var pct=ch.moisture;
    var col=pct>60?'#22c55e':pct>30?'#eab308':'#ef4444';
    h+='<div style="display:flex;align-items:center;gap:16px;margin-bottom:10px">';
    h+='<div style="font-size:2.5rem;font-weight:700;color:'+col+'">'+pct+'%</div>';
    h+='<div style="flex:1"><div style="background:#1e293b;border-radius:4px;height:8px">'
      +'<div style="background:'+col+';width:'+pct+'%;height:8px;border-radius:4px;transition:.5s"></div></div>'
      +'<div style="font-size:.75rem;color:#94a3b8;margin-top:3px">Schwelle: '+ch.thresh+'%  ADC: '+ch.raw_adc+'</div>';
    h+='</div></div>';
    // Status
    if(ch.pump)h+='<div style="color:#22c55e;margin-bottom:8px">💧 Pumpe läuft'+
      (ch.pump_elapsed?' ('+ch.pump_elapsed+'s)':'')+'</div>';
    // Pflanze
    h+='<label>Pflanze</label>';
    h+='<select onchange="setPlant('+i+',this.value)">';
    plants.forEach(function(p,pi){
      h+='<option value="'+pi+'"'+(pi===ch.plant_idx?' selected':'')+'>'+p.emoji+' '+p.name_de+'</option>';
    });
    h+='</select>';
    // Auto-Mode
    h+='<div class="toggle-row" style="margin-top:8px"><span>Automatikmodus</span>';
    h+='<label class="toggle"><input type="checkbox"'+(ch.auto_mode?' checked':'');
    h+=' onchange="setAuto('+i+',this.checked)"><span class="slider"></span></label></div>';
    // Kalibrierung
    h+='<div style="margin-top:10px">';
    h+='<button class="btn btn-s" style="margin-right:6px;margin-top:4px" onclick="calib('+i+',\'dry\')">Trocken kalibrieren</button>';
    h+='<button class="btn btn-s" style="margin-top:4px" onclick="calib('+i+',\'wet\')">Nass kalibrieren</button>';
    h+='<div id="calib-'+i+'" style="font-size:.78rem;color:#94a3b8;margin-top:4px">';
    h+='Dry ADC: '+ch.dry_adc+' | Wet ADC: '+ch.wet_adc+'</div>';
    h+='</div></div>';
  });
  document.getElementById('ch-grid').innerHTML=h;
}

function buildStat(){
  return'<div class="card"><h2>📋 Ereignisse</h2><div id="evts"><div style="color:#94a3b8;text-align:center;padding:20px">Lade...</div></div></div>'+
    '<div class="card"><h2>📊 Feuchtigkeitsverlauf</h2>'+
    '<label>Kanal</label><select id="log-ch" onchange="loadLog()"><option value="0">Kanal 1</option><option value="1">Kanal 2</option></select>'+
    '<div id="log-chart" style="margin-top:10px"></div></div>';
}

function loadStats(){
  fetch('/api/events').then(r=>r.json()).then(d=>{
    var h='';
    (d.events||[]).reverse().forEach(function(e){
      h+='<div class="stat-row"><span style="color:#94a3b8;font-size:.78rem">'+e.ts+'</span><span>'+e.msg+'</span></div>';
    });
    document.getElementById('evts').innerHTML=h||'<p style="color:#94a3b8">Keine Ereignisse.</p>';
  }).catch(function(){});
  loadLog();
}

function loadLog(){
  var ch=document.getElementById('log-ch')?document.getElementById('log-ch').value:0;
  fetch('/api/logs?ch='+ch+'&limit=48').then(r=>r.json()).then(d=>{
    var readings=d.readings||[];
    if(!readings.length){document.getElementById('log-chart').innerHTML='<p style="color:#94a3b8;padding:10px">Keine Daten.</p>';return;}
    var max=Math.max.apply(null,readings.map(r=>r.m));
    var h='<div style="position:relative;height:80px;background:#1e293b;border-radius:8px;overflow:hidden">';
    var w=100/readings.length;
    readings.forEach(function(r,i){
      var pct=r.m/100*100;
      var col=r.m>60?'#22c55e':r.m>30?'#eab308':'#ef4444';
      h+='<div style="position:absolute;bottom:0;left:'+(i*w)+'%;width:'+w+'%;height:'+pct+'%;background:'+col+';opacity:.7"></div>';
    });
    h+='</div>';
    h+='<div style="display:flex;justify-content:space-between;font-size:.72rem;color:#94a3b8;margin-top:4px">';
    h+='<span>'+readings[0].ts+'</span><span>'+readings[readings.length-1].ts+'</span></div>';
    document.getElementById('log-chart').innerHTML=h;
  }).catch(function(){});
}

function buildSched(){
  return'<div class="card"><h2>⏰ Zeitplan</h2>'+
    '<div class="toggle-row"><span>Zeitplan aktivieren</span>'+
    '<label class="toggle"><input type="checkbox" id="sched-en"><span class="slider"></span></label></div>'+
    '<div id="sched-entries" style="margin-top:10px"></div>'+
    '<button class="btn btn-s" onclick="addScheduleEntry()" style="margin-top:8px">+ Eintrag hinzufügen</button>'+
    '<button class="btn btn-g" onclick="saveSched()" style="margin-top:8px;float:right">Speichern</button></div>';
}

function loadSched(){
  fetch('/api/config').then(r=>r.json()).then(d=>{
    var s=d.schedule||{};
    document.getElementById('sched-en').checked=s.enabled||false;
    renderSchedEntries(s.entries||[]);
  });
}

function renderSchedEntries(entries){
  var h='';
  entries.forEach(function(e,i){
    h+='<div class="card" style="margin-bottom:6px">';
    h+='<div class="row">';
    h+='<div><label>Kanal</label><select id="se-ch-'+i+'">';
    (state.channels||[]).forEach(function(ch,ci){
      h+='<option value="'+ci+'"'+(ci===e.channel?' selected':'')+'>'+ch.name+'</option>';
    });
    h+='</select></div>';
    h+='<div><label>Uhrzeit</label><input type="time" id="se-t-'+i+'" value="'+(e.hour||6).toString().padStart(2,'0')+':'+(e.minute||0).toString().padStart(2,'0')+'"></div>';
    h+='<div><label>Dauer (s)</label><input type="number" id="se-d-'+i+'" value="'+(e.duration_s||30)+'" style="width:70px"></div>';
    h+='<div><label>&nbsp;</label><button class="btn btn-r" onclick="removeScheduleEntry('+i+')">✕</button></div>';
    h+='</div></div>';
  });
  document.getElementById('sched-entries').innerHTML=h;
  document.getElementById('sched-entries')._entries=entries;
}

function addScheduleEntry(){
  var entries=document.getElementById('sched-entries')._entries||[];
  entries.push({channel:0,hour:8,minute:0,duration_s:30,days:[0,1,2,3,4,5,6]});
  renderSchedEntries(entries);
}

function removeScheduleEntry(i){
  var entries=document.getElementById('sched-entries')._entries||[];
  entries.splice(i,1);
  renderSchedEntries(entries);
}

function saveSched(){
  var entries=document.getElementById('sched-entries')._entries||[];
  // Lese aktuelle Formularwerte
  entries.forEach(function(e,i){
    var ch=document.getElementById('se-ch-'+i);
    var t=document.getElementById('se-t-'+i);
    var d=document.getElementById('se-d-'+i);
    if(ch) e.channel=parseInt(ch.value);
    if(t){var parts=t.value.split(':');e.hour=parseInt(parts[0]);e.minute=parseInt(parts[1]);}
    if(d) e.duration_s=parseInt(d.value);
  });
  var en=document.getElementById('sched-en').checked;
  postJson('/api/config',{schedule:{enabled:en,entries:entries}}).then(function(){toast('Zeitplan gespeichert','ok');});
}

function buildCfg(){
  return'<div id="cfg-content"><div class="card"><p style="color:#94a3b8;text-align:center">Lade...</p></div></div>';
}

function renderCfg(){
  var d=cfg;var h='';

  // Telegram
  h+='<div class="card"><h2>🤖 Telegram</h2>';
  h+='<div class="toggle-row"><span>Telegram aktivieren</span>'+
    '<label class="toggle"><input type="checkbox" id="tg-en"'+(d.telegram&&d.telegram.enabled?' checked':'')+'><span class="slider"></span></label></div>';
  h+='<label>Bot-Token</label><input id="tg-tok" value="'+(d.telegram&&d.telegram.token||'')+'">';
  h+='<label>Chat-ID</label><input id="tg-chat" value="'+(d.telegram&&d.telegram.chat_id||'')+'">';
  h+='<button class="btn btn-s" onclick="testTelegram()" style="margin-top:8px">Test senden</button>';
  h+='<button class="btn btn-g" onclick="saveTelegram()" style="margin-top:8px;float:right">Speichern</button></div>';

  // MQTT
  h+='<div class="card"><h2>🏠 MQTT / Home Assistant</h2>';
  h+='<div class="toggle-row"><span>MQTT aktivieren</span>'+
    '<label class="toggle"><input type="checkbox" id="mq-en"'+(d.mqtt&&d.mqtt.enabled?' checked':'')+'><span class="slider"></span></label></div>';
  h+='<label>Broker-IP</label><input id="mq-srv" value="'+(d.mqtt&&d.mqtt.server||'')+'">';
  h+='<div class="row"><div><label>Port</label><input id="mq-port" type="number" value="'+(d.mqtt&&d.mqtt.port||1883)+'"></div>'+
    '<div><label>Topic-Basis</label><input id="mq-topic" value="'+(d.mqtt&&d.mqtt.base_topic||'irrigation')+'"></div></div>';
  h+='<div class="row"><div><label>Benutzer</label><input id="mq-user" value="'+(d.mqtt&&d.mqtt.user||'')+'"></div>'+
    '<div><label>Passwort</label><input id="mq-pass" type="password" value=""></div></div>';
  h+='<button class="btn btn-g" onclick="saveMqtt()" style="margin-top:8px;float:right">Speichern</button></div>';

  // OpenWeatherMap
  h+='<div class="card"><h2>🌦️ Wetter (OpenWeatherMap)</h2>';
  h+='<div class="toggle-row"><span>Wetter aktivieren</span>'+
    '<label class="toggle"><input type="checkbox" id="ow-en"'+(d.weather&&d.weather.enabled?' checked':'')+'><span class="slider"></span></label></div>';
  h+='<label>API-Key</label><input id="ow-key" value="'+(d.weather&&d.weather.api_key||'')+'">';
  h+='<div class="row"><div><label>Stadt</label><input id="ow-city" value="'+(d.weather&&d.weather.city||'Berlin')+'"></div>'+
    '<div><label>Land</label><input id="ow-cntry" value="'+(d.weather&&d.weather.country||'DE')+'" style="width:70px"></div></div>';
  h+='<div class="toggle-row"><span>Bei Regen nicht gießen</span>'+
    '<label class="toggle"><input type="checkbox" id="ow-skip"'+(d.weather&&d.weather.skip_on_rain?' checked':'')+'><span class="slider"></span></label></div>';
  h+='<button class="btn btn-g" onclick="saveWeather()" style="margin-top:8px;float:right">Speichern</button></div>';

  // System
  h+='<div class="card"><h2>⚙️ System</h2>';
  h+='<label>Aktive Kanäle</label><select id="sys-ch">';
  for(var i=1;i<=8;i++)h+='<option value="'+i+'"'+(d.system&&d.system.active_channels===i?' selected':'')+'>'+i+'</option>';
  h+='</select>';
  h+='<label>Hostname</label><input id="sys-host" value="'+(d.system&&d.system.hostname||'smart-irrigation')+'">';
  h+='<label>Zeitzone (Stunden-Offset UTC)</label><input id="sys-tz" type="number" value="'+(d.system&&d.system.timezone_offset||1)+'">';
  h+='<div class="toggle-row"><span>Wasserstand-Sensor (HC-SR04)</span>'+
    '<label class="toggle"><input type="checkbox" id="wl-en"'+(d.water_level&&d.water_level.enabled?' checked':'')+'><span class="slider"></span></label></div>';
  h+='<div class="row"><div><label>TRIG-Pin</label><input type="number" id="wl-trig" value="'+(d.water_level&&d.water_level.trig_pin||12)+'"></div>'+
    '<div><label>ECHO-Pin</label><input type="number" id="wl-echo" value="'+(d.water_level&&d.water_level.echo_pin||14)+'"></div>'+
    '<div><label>Tankhöhe cm</label><input type="number" id="wl-h" value="'+(d.water_level&&d.water_level.tank_height_cm||30)+'"></div></div>';
  h+='<button class="btn btn-r" onclick="if(confirm(\'WiFi zurücksetzen und neu einrichten?\'))resetWifi()" style="margin-top:10px">WiFi zurücksetzen</button>';
  h+='<button class="btn btn-g" onclick="saveSys()" style="margin-top:8px;float:right">Speichern</button></div>';

  document.getElementById('cfg-content').innerHTML=h;
}

function buildOta(){
  return'<div class="card"><h2>🔄 Firmware Update</h2>'+
    '<h3>Python-Datei hochladen</h3>'+
    '<input type="file" id="ota-file" accept=".py,.json"><br>'+
    '<button class="btn btn-g" onclick="uploadFile()" style="margin-top:8px">Hochladen</button>'+
    '<div id="ota-status" style="margin-top:10px;color:#94a3b8;font-size:.85rem"></div>'+
    '</div>'+
    '<div class="card"><h2>🐙 GitHub Update</h2>'+
    '<label>Repository (user/repo)</label><input id="gh-repo" placeholder="dein-user/smart-irrigation">'+
    '<label>Branch</label><input id="gh-branch" value="main">'+
    '<button class="btn btn-g" onclick="ghUpdate()" style="margin-top:8px">Von GitHub aktualisieren</button></div>'+
    '<div class="card"><h2>♻️ Neustart</h2>'+
    '<button class="btn btn-r" onclick="if(confirm(\'Wirklich neu starten?\'))reboot()">ESP32 neu starten</button></div>';
}

// ── API-Calls ───────────────────────────────────────────────────────
function loadState(){
  fetch('/api/status').then(r=>r.json()).then(d=>{
    state=d;
    var p0=document.getElementById('page-dash');
    if(p0&&p0.classList.contains('on')) renderDash();
    var p1=document.getElementById('page-ch');
    if(p1&&p1.classList.contains('on')) renderChannels();
  }).catch(function(){});
}

function loadConfig(){
  fetch('/api/config').then(r=>r.json()).then(d=>{
    cfg=d;plants=d.plants||[];
    var p=document.getElementById('page-cfg');
    if(p&&p.classList.contains('on')) renderCfg();
  });
}

function pump(ch,on){
  fetch('/api/'+(on?'water':'stop')+'/'+ch,{method:'POST'})
    .then(()=>{toast(on?'Pumpe gestartet':'Pumpe gestoppt','ok');loadState();});
}

function calib(ch,type){
  fetch('/api/calibrate/'+type+'/'+ch,{method:'POST'}).then(r=>r.json()).then(d=>{
    toast('ADC: '+d.adc,'ok');
    document.getElementById('calib-'+ch).textContent=
      (type==='dry'?'Dry':'Wet')+' ADC: '+d.adc;
  });
}

function setPlant(ch,plant_idx){
  postJson('/api/channel/'+ch,{plant_idx:parseInt(plant_idx)}).then(()=>toast('Pflanze gespeichert','ok'));
}

function setAuto(ch,val){
  postJson('/api/channel/'+ch,{auto_mode:val}).then(()=>toast('Gespeichert','ok'));
}

function saveTelegram(){
  postJson('/api/config',{telegram:{
    enabled:document.getElementById('tg-en').checked,
    token:document.getElementById('tg-tok').value,
    chat_id:document.getElementById('tg-chat').value
  }}).then(()=>toast('Telegram gespeichert','ok'));
}

function testTelegram(){
  fetch('/api/telegram/test',{method:'POST'}).then(()=>toast('Testnachricht gesendet','ok'));
}

function saveMqtt(){
  postJson('/api/config',{mqtt:{
    enabled:document.getElementById('mq-en').checked,
    server:document.getElementById('mq-srv').value,
    port:parseInt(document.getElementById('mq-port').value)||1883,
    user:document.getElementById('mq-user').value,
    password:document.getElementById('mq-pass').value,
    base_topic:document.getElementById('mq-topic').value||'irrigation'
  }}).then(()=>toast('MQTT gespeichert','ok'));
}

function saveWeather(){
  postJson('/api/config',{weather:{
    enabled:document.getElementById('ow-en').checked,
    api_key:document.getElementById('ow-key').value,
    city:document.getElementById('ow-city').value,
    country:document.getElementById('ow-cntry').value.toUpperCase(),
    skip_on_rain:document.getElementById('ow-skip').checked
  }}).then(()=>toast('Wetter gespeichert','ok'));
}

function saveSys(){
  postJson('/api/config',{
    system:{active_channels:parseInt(document.getElementById('sys-ch').value),
            hostname:document.getElementById('sys-host').value,
            timezone_offset:parseInt(document.getElementById('sys-tz').value)||1},
    water_level:{enabled:document.getElementById('wl-en').checked,
                 trig_pin:parseInt(document.getElementById('wl-trig').value),
                 echo_pin:parseInt(document.getElementById('wl-echo').value),
                 tank_height_cm:parseInt(document.getElementById('wl-h').value)}
  }).then(()=>toast('System gespeichert','ok'));
}

function uploadFile(){
  var file=document.getElementById('ota-file').files[0];
  if(!file){toast('Keine Datei ausgewählt','err');return;}
  var fd=new FormData();fd.append('file',file);
  document.getElementById('ota-status').textContent='Uploading '+file.name+'...';
  fetch('/api/ota/upload',{method:'POST',body:fd}).then(r=>r.json()).then(d=>{
    document.getElementById('ota-status').textContent=d.ok?'✅ '+d.msg:'❌ '+d.msg;
  });
}

function ghUpdate(){
  var repo=document.getElementById('gh-repo').value;
  var branch=document.getElementById('gh-branch').value||'main';
  if(!repo){toast('Bitte Repository angeben','err');return;}
  postJson('/api/ota/github',{repo:repo,branch:branch})
    .then(r=>r.json()).then(d=>toast('Aktualisiert: '+d.files.join(', '),'ok'));
}

function reboot(){
  fetch('/api/reboot',{method:'POST'}).then(()=>toast('Neustart...','ok'));
}

function resetWifi(){
  postJson('/api/config',{wifi:{ssid:'',password:''}}).then(()=>{
    fetch('/api/reboot',{method:'POST'});
    toast('WiFi zurückgesetzt – AP-Modus startet...','ok');
  });
}

function postJson(url,data){
  return fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});
}

function showChDetail(i){showTab('ch');}

var _toastTimer;
function toast(msg,type){
  var el=document.getElementById('toast');
  el.textContent=msg;
  el.style.background=type==='err'?'#ef4444':'#22c55e';
  el.style.opacity='1';
  clearTimeout(_toastTimer);
  _toastTimer=setTimeout(function(){el.style.opacity='0';},3000);
}

document.addEventListener('DOMContentLoaded',function(){
  init();
  document.getElementById('page-cfg').addEventListener('click',function(){renderCfg();},{once:false});
  document.getElementById('nav-cfg').addEventListener('click',function(){setTimeout(renderCfg,50);});
});
</script></body></html>"""


# ── HTTP-Server ─────────────────────────────────────────────────────
class WebServer:
    def __init__(self, irrigation, telegram=None, ota=None):
        self.irrigation = irrigation
        self.telegram   = telegram
        self.ota        = ota
        self.cfg        = get_config()

    async def run(self, port=80):
        server = await asyncio.start_server(self._handle, '0.0.0.0', port)
        print(f'Webserver gestartet auf Port {port}')
        async with server:
            await server.wait_closed()

    async def _handle(self, reader, writer):
        try:
            raw = b''
            while b'\r\n\r\n' not in raw:
                chunk = await reader.read(512)
                if not chunk:
                    break
                raw += chunk

            lines  = raw.decode('utf-8', 'ignore').split('\r\n')
            req    = lines[0] if lines else ''
            parts  = req.split(' ')
            method = parts[0] if len(parts) > 0 else 'GET'
            full   = parts[1] if len(parts) > 1 else '/'
            path   = full.split('?')[0]
            query  = full.split('?')[1] if '?' in full else ''

            # Body
            body = b''
            for line in lines:
                if line.lower().startswith('content-length:'):
                    clen = int(line.split(':', 1)[1].strip())
                    if b'\r\n\r\n' in raw:
                        existing = raw.split(b'\r\n\r\n', 1)[1]
                        while len(existing) < clen:
                            existing += await reader.read(256)
                        body = existing[:clen]
                    break

            resp = await self._route(method, path, query, body)
            status, ctype, data = resp

            if isinstance(data, str):
                data = data.encode()
            header = (f'HTTP/1.1 {status}\r\nContent-Type: {ctype}\r\n'
                      f'Content-Length: {len(data)}\r\nConnection: close\r\n\r\n').encode()
            writer.write(header + data)
            await writer.drain()
        except Exception as e:
            print(f'HTTP error: {e}')
        finally:
            writer.close()
            gc.collect()

    async def _route(self, method, path, query, body):
        ok  = '200 OK'
        j   = 'application/json'
        # Helper
        def jresp(d, s=ok):
            return s, j, json.dumps(d)

        # ── Hauptseite ────────────────────────────────────────────────
        if path == '/' or path == '/index.html':
            return ok, 'text/html; charset=utf-8', _HTML

        # ── Status ────────────────────────────────────────────────────
        elif path == '/api/status':
            return jresp(self.irrigation.status_dict())

        # ── Konfiguration ─────────────────────────────────────────────
        elif path == '/api/config' and method == 'GET':
            d = dict(self.cfg.as_dict())
            d['plants'] = all_as_list()
            return jresp(d)

        elif path == '/api/config' and method == 'POST':
            try:
                d = json.loads(body)
                self.cfg.update_from_dict(d)
                return jresp({'ok': True})
            except Exception as e:
                return jresp({'ok': False, 'msg': str(e)}, '400 Bad Request')

        # ── Kanal-spezifisch ──────────────────────────────────────────
        elif path.startswith('/api/channel/') and method == 'POST':
            ch_id = int(path.split('/')[-1])
            try:
                d = json.loads(body)
                self.cfg.set_channel(ch_id, d)
                if ch_id < len(self.irrigation.channels):
                    self.irrigation.channels[ch_id].cfg.update(d)
                return jresp({'ok': True})
            except Exception as e:
                return jresp({'ok': False, 'msg': str(e)})

        # ── Pumpen ────────────────────────────────────────────────────
        elif path.startswith('/api/water/') and method == 'POST':
            ch_id = int(path.split('/')[-1])
            dur   = None
            try:
                d = json.loads(body)
                dur = d.get('duration')
            except Exception:
                pass
            if ch_id < len(self.irrigation.channels):
                self.irrigation.channels[ch_id].start_pump(dur)
            return jresp({'ok': True})

        elif path.startswith('/api/stop/') and method == 'POST':
            ch_id = int(path.split('/')[-1])
            if ch_id < len(self.irrigation.channels):
                self.irrigation.channels[ch_id].stop_pump()
            return jresp({'ok': True})

        # ── Kalibrierung ──────────────────────────────────────────────
        elif path.startswith('/api/calibrate/dry/') and method == 'POST':
            ch_id = int(path.split('/')[-1])
            raw   = self.irrigation.calibrate_dry(ch_id)
            return jresp({'ok': True, 'adc': raw})

        elif path.startswith('/api/calibrate/wet/') and method == 'POST':
            ch_id = int(path.split('/')[-1])
            raw   = self.irrigation.calibrate_wet(ch_id)
            return jresp({'ok': True, 'adc': raw})

        # ── Logs ──────────────────────────────────────────────────────
        elif path == '/api/logs':
            params = dict(p.split('=') for p in query.split('&') if '=' in p)
            ch_id  = int(params.get('ch', 0))
            limit  = int(params.get('limit', 48))
            return jresp({'readings': self.irrigation.get_logs(ch_id, limit)})

        elif path == '/api/events':
            return jresp({'events': self.irrigation.get_events(50)})

        # ── Telegram ─────────────────────────────────────────────────
        elif path == '/api/telegram/test' and method == 'POST':
            if self.telegram:
                self.telegram.send('🔔 Testnachricht von Smart Irrigation MicroPython!')
            return jresp({'ok': True})

        # ── OTA: Datei-Upload ─────────────────────────────────────────
        elif path == '/api/ota/upload' and method == 'POST':
            return await self._handle_file_upload(body)

        elif path == '/api/ota/github' and method == 'POST':
            if self.ota:
                try:
                    d = json.loads(body)
                    files = self.ota.update_from_github(d['repo'], d.get('branch', 'main'))
                    return jresp({'ok': True, 'files': files})
                except Exception as e:
                    return jresp({'ok': False, 'msg': str(e)})
            return jresp({'ok': False, 'msg': 'OTA nicht verfügbar'})

        # ── Neustart ──────────────────────────────────────────────────
        elif path == '/api/reboot' and method == 'POST':
            import machine
            writer_ref = None
            async def do_reboot():
                await asyncio.sleep(1)
                machine.reset()
            asyncio.create_task(do_reboot())
            return jresp({'ok': True, 'msg': 'Neustart...'})

        # ── WiFi-Reset ────────────────────────────────────────────────
        elif path == '/api/wifi/reset' and method == 'POST':
            self.cfg.set('wifi.ssid', '')
            self.cfg.set('wifi.password', '')
            return jresp({'ok': True})

        return '404 Not Found', j, json.dumps({'error': 'Not found'})

    async def _handle_file_upload(self, body):
        """Multipart-Upload einer .py-Datei parsen und speichern."""
        try:
            # Boundary aus Content-Type lesen (vereinfacht)
            boundary_marker = b'Content-Disposition: form-data'
            filename_marker = b'filename="'
            if boundary_marker not in body:
                return '400 Bad Request', 'application/json', '{"ok":false,"msg":"Kein Multipart"}'

            # Dateiname extrahieren
            fi = body.find(filename_marker)
            if fi < 0:
                return '400 Bad Request', 'application/json', '{"ok":false,"msg":"Kein Dateiname"}'
            fi   += len(filename_marker)
            fname = body[fi:body.find(b'"', fi)].decode()

            # Dateiinhalt nach doppeltem CRLF
            sep   = body.find(b'\r\n\r\n', fi)
            if sep < 0:
                return '400 Bad Request', 'application/json', '{"ok":false}"'
            content = body[sep + 4:]
            # Abschließenden Boundary entfernen
            last_nl = content.rfind(b'\r\n--')
            if last_nl >= 0:
                content = content[:last_nl]

            dest = f'/{fname}'
            with open(dest, 'wb') as f:
                f.write(content)
            print(f'OTA Upload: {fname} ({len(content)} Bytes)')
            return '200 OK', 'application/json', json.dumps({
                'ok': True, 'msg': f'{fname} gespeichert ({len(content)} Bytes) – Neustart empfohlen.'
            })
        except Exception as e:
            return '500 Internal Server Error', 'application/json', json.dumps({'ok': False, 'msg': str(e)})
