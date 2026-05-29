"""
display.py – Display-Unterstützung (OLED SSD1306, LCD I2C)
"""
from config import get_config
import uasyncio as asyncio
class Display:
    def __init__(self, irrigation):
        self.cfg        = get_config()
        self.irrigation = irrigation
        self._display   = None
        self._page      = 0
        self._init()

    def _init(self):
        dtype = self.cfg.get('display.type', 0)
        if dtype == 0:
            return
        sda = self.cfg.get('display.i2c_sda', 21)
        scl = self.cfg.get('display.i2c_scl', 22)
        try:
            from machine import I2C, Pin
            i2c = I2C(0, sda=Pin(sda), scl=Pin(scl))
            if dtype == 1:
                import ssd1306
                w = self.cfg.get('display.width', 128)
                h = self.cfg.get('display.height', 64)
                self._display = ssd1306.SSD1306_I2C(w, h, i2c)
                print(f'OLED {w}x{h} initialisiert')
            elif dtype == 2:
                from lcd_api import LcdApi
                from i2c_lcd import I2cLcd
                addr = self.cfg.get('display.address', 0x27)
                self._display = I2cLcd(i2c, addr, 2, 16)
                print('LCD 16x2 initialisiert')
        except Exception as e:
            print(f'Display Fehler: {e}')

    def _update_oled(self):
        d = self._display
        d.fill(0)
        n = len(self.irrigation.channels)
        page = self._page % (n + 1)
        if page == 0:
            d.text('Smart Irrigation', 0, 0, 1)
            for i, ch in enumerate(self.irrigation.channels[:3]):
                y = 16 + i * 16
                d.text(f'{ch.cfg.get("name","K"+str(i+1))[:8]}: {ch.moisture_pct}%', 0, y, 1)
                if ch.pump_running:
                    d.text('PUMP', 100, y, 1)
        else:
            ch = self.irrigation.channels[page - 1]
            d.text(ch.cfg.get('name', f'Kanal {page}')[:16], 0, 0, 1)
            big = str(ch.moisture_pct) + '%'
            d.text(big, 40, 20, 1)
            status = 'PUMPE AN' if ch.pump_running else ('TROCKEN!' if ch.moisture_pct < ch.cfg.get('moisture_thresh', 40) else 'OK')
            d.text(status, 0, 48, 1)
        d.show()

    async def run(self):
        while True:
            if self._display:
                try:
                    dtype = self.cfg.get('display.type', 0)
                    if dtype == 1:
                        self._update_oled()
                    self._page += 1
                except Exception as e:
                    print(f'Display update error: {e}')
            await asyncio.sleep(2)
