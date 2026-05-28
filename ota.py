"""
ota.py – OTA Updates: Web-Upload, Telegram .py-Dateien, GitHub-Release
"""
from config import get_config
class OTA:
    def __init__(self, telegram_token=''):
        self.cfg    = get_config()
        self._token = telegram_token

    def update_file_from_telegram(self, file_id, file_name):
        """Lädt eine Datei vom Telegram-Server und speichert sie auf Flash."""
        try:
            import socket, ssl
            token = self.cfg.get('telegram.token', '')
            host  = 'api.telegram.org'

            # 1. file_path holen
            import json
            path = f'/bot{token}/getFile?file_id={file_id}'
            addr = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
            s    = socket.socket(); s.settimeout(10); s.connect(addr)
            s    = ssl.wrap_socket(s, server_hostname=host)
            s.write(f'GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode())
            raw = b''
            while True:
                c = s.read(1024)
                if not c: break
                raw += c
            s.close()
            meta = json.loads(raw.split(b'\r\n\r\n', 1)[1])
            file_path = meta['result']['file_path']

            # 2. Datei herunterladen
            path2 = f'/file/bot{token}/{file_path}'
            addr  = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
            s     = socket.socket(); s.settimeout(30); s.connect(addr)
            s     = ssl.wrap_socket(s, server_hostname=host)
            s.write(f'GET {path2} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode())
            raw2 = b''
            while True:
                c = s.read(2048)
                if not c: break
                raw2 += c
            s.close()
            content = raw2.split(b'\r\n\r\n', 1)[1]

            # 3. Auf Flash speichern
            dest = f'/{file_name}'
            with open(dest, 'wb') as f:
                f.write(content)
            print(f'OTA: {file_name} gespeichert ({len(content)} Bytes)')
            return True
        except Exception as e:
            print(f'OTA Telegram error: {e}')
            return False

    def update_from_github(self, repo, branch='main', files=None):
        """
        Lädt spezifische Dateien von GitHub herunter.
        repo: 'user/repo-name'
        files: Liste von Dateinamen, z.B. ['main.py', 'irrigation.py']
        """
        import socket, ssl, gc
        if not files:
            files = ['boot.py', 'main.py', 'config.py', 'irrigation.py',
                     'weather.py', 'telegram_bot.py', 'mqtt_client.py',
                     'display.py', 'ota.py', 'setup_portal.py',
                     'webserver.py', 'plants_db.py']
        host = 'raw.githubusercontent.com'
        updated = []
        for fname in files:
            try:
                path = f'/{repo}/{branch}/{fname}'
                addr = socket.getaddrinfo(host, 443, 0, socket.SOCK_STREAM)[0][-1]
                s    = socket.socket(); s.settimeout(15); s.connect(addr)
                s    = ssl.wrap_socket(s, server_hostname=host)
                s.write(f'GET {path} HTTP/1.0\r\nHost: {host}\r\nConnection: close\r\n\r\n'.encode())
                raw = b''
                while True:
                    c = s.read(2048)
                    if not c: break
                    raw += c
                s.close()
                if b'404' in raw[:20]:
                    continue
                content = raw.split(b'\r\n\r\n', 1)[1]
                with open(f'/{fname}', 'wb') as f:
                    f.write(content)
                updated.append(fname)
                print(f'OTA GitHub: {fname} aktualisiert')
                gc.collect()
            except Exception as e:
                print(f'OTA GitHub {fname}: {e}')
        return updated

