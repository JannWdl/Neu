"""
setup_portal.py – AP-Modus Einrichtungsportal
Nur WLAN-Einrichtung für den ESP32.
"""

import socket
import time
import machine
import gc
from config import get_config

SETUP_HTML = """\
<!DOCTYPE html>
<html lang="de">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Smart Irrigation – WLAN-Einrichtung</title>

<style>
*{
    box-sizing:border-box;
    margin:0;
    padding:0
}

body{
    font-family:system-ui,sans-serif;
    background:#0a0f1e;
    color:#e2e8f0;
    min-height:100vh;
    display:flex;
    align-items:center;
    justify-content:center;
    padding:16px
}

.card{
    background:rgba(255,255,255,.06);
    border:1px solid rgba(255,255,255,.12);
    border-radius:16px;
    padding:28px;
    width:100%;
    max-width:420px
}

h1{
    color:#22c55e;
    font-size:1.5rem;
    margin-bottom:4px;
    text-align:center
}

.sub{
    color:#94a3b8;
    font-size:.85rem;
    text-align:center;
    margin-bottom:24px
}

label{
    display:block;
    color:#94a3b8;
    font-size:.82rem;
    margin-bottom:5px;
    margin-top:14px
}

input{
    width:100%;
    background:#1e293b;
    border:1px solid #334155;
    border-radius:8px;
    color:#e2e8f0;
    padding:11px 14px;
    font-size:.95rem
}

input:focus{
    outline:none;
    border-color:#22c55e
}

.btn{
    display:block;
    width:100%;
    padding:13px;
    border:none;
    border-radius:8px;
    font-size:1rem;
    font-weight:600;
    cursor:pointer;
    margin-top:20px;
    background:#22c55e;
    color:#0a0f1e
}

.scan-btn{
    display:block;
    width:100%;
    padding:9px;
    border:1px solid #334155;
    border-radius:8px;
    background:transparent;
    color:#94a3b8;
    font-size:.85rem;
    cursor:pointer;
    margin-bottom:10px
}

.nets{
    margin-top:8px
}

.net{
    background:#1e293b;
    border:1px solid #334155;
    border-radius:8px;
    padding:9px 12px;
    margin-bottom:5px;
    cursor:pointer;
    display:flex;
    justify-content:space-between;
    font-size:.88rem
}

.net:hover{
    border-color:#22c55e
}

.note{
    margin-top:16px;
    padding:12px;
    background:rgba(34,197,94,.08);
    border:1px solid rgba(34,197,94,.2);
    border-radius:8px;
    font-size:.8rem;
    color:#86efac;
    line-height:1.5
}
</style>
</head>

<body>

<div class="card">

<h1>🌱 Smart Irrigation</h1>
<p class="sub">WLAN-Einrichtung</p>

<button class="scan-btn" onclick="scan()">
🔍 Netzwerke scannen
</button>

<div class="nets" id="nets"></div>

<label>WLAN-Name (SSID)</label>
<input id="ssid" type="text" placeholder="Mein WLAN">

<label>Passwort</label>
<input id="pass" type="password" placeholder="Passwort">

<button class="btn" onclick="save()">
Verbinden & Speichern
</button>

<div class="note">
ℹ️ Nach dem Speichern verbindet sich der ESP32 mit deinem WLAN.
</div>

</div>

<script>

function scan(){

    var d=document.getElementById('nets');

    d.innerHTML='Suche...';

    fetch('/scan')
    .then(r=>r.json())
    .then(data=>{

        var h='';

        data.sort((a,b)=>b.rssi-a.rssi);

        data.forEach(n=>{

            h += '<div class="net" onclick="pick(\\''+
                 n.ssid.replace(/'/g,"\\\\'")+
                 '\\')">' +

                 '<span>'+n.ssid+'</span>' +

                 '<span>'+n.rssi+'</span>' +

                 '</div>';
        });

        d.innerHTML=h || 'Keine Netzwerke gefunden';
    })
    .catch(()=>{
        d.innerHTML='Scan fehlgeschlagen';
    });
}

function pick(s){
    document.getElementById('ssid').value=s;
    document.getElementById('pass').focus();
}

function save(){

    var ssid=document.getElementById('ssid').value.trim();
    var pass=document.getElementById('pass').value;

    if(!ssid){
        alert('Bitte SSID eingeben');
        return;
    }

    fetch('/save',{
        method:'POST',
        headers:{
            'Content-Type':'application/x-www-form-urlencoded'
        },
        body:'ssid='+encodeURIComponent(ssid)+
             '&pass='+encodeURIComponent(pass)
    })

    .then(r=>r.text())
