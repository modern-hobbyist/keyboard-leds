"""
Minimal ILI9341 SPI display driver for MicroPython.
320x240, 16-bit RGB565 color.
"""
import time
import framebuf
from machine import Pin, SPI, PWM
import pins as P

# ILI9341 command bytes
_NOP      = 0x00
_SWRESET  = 0x01
_SLPOUT   = 0x11
_DISPOFF  = 0x28
_DISPON   = 0x29
_CASET    = 0x2A
_PASET    = 0x2B
_RAMWR    = 0x2C
_MADCTL   = 0x36
_PIXFMT   = 0x3A
_FRMCTR1  = 0xB1
_DFUNCTR  = 0xB6
_PWCTR1   = 0xC0
_PWCTR2   = 0xC1
_VMCTR1   = 0xC5
_VMCTR2   = 0xC7
_GMCTRP1  = 0xE0
_GMCTRN1  = 0xE1

WIDTH  = 320
HEIGHT = 240

# Common RGB565 colors
BLACK   = 0x0000
WHITE   = 0xFFFF
RED     = 0xF800
GREEN   = 0x07E0
BLUE    = 0x001F
CYAN    = 0x07FF
MAGENTA = 0xF81F
YELLOW  = 0xFFE0
GRAY    = 0x7BEF
DKGRAY  = 0x2104
ORANGE  = 0xFD20

_spi: SPI = None
_cs  = None
_dc  = None
_bl: PWM = None

# Row-sized scratch buffer for text blits (avoids per-call allocation)
_TEXT_H = 16
_text_buf = bytearray(WIDTH * _TEXT_H * 2)
_text_fb  = framebuf.FrameBuffer(_text_buf, WIDTH, _TEXT_H, framebuf.RGB565)


def _cmd(c: int):
    _dc.value(0)
    _cs.value(0)
    _spi.write(bytes([c]))
    _cs.value(1)


def _data(d):
    _dc.value(1)
    _cs.value(0)
    _spi.write(d)
    _cs.value(1)


def _cmd_data(c: int, d):
    _dc.value(0)
    _cs.value(0)
    _spi.write(bytes([c]))
    _dc.value(1)
    _spi.write(d if isinstance(d, (bytes, bytearray)) else bytes([d]))
    _cs.value(1)


def _set_window(x0: int, y0: int, x1: int, y1: int):
    _cmd_data(_CASET, bytes([x0 >> 8, x0 & 0xFF, x1 >> 8, x1 & 0xFF]))
    _cmd_data(_PASET, bytes([y0 >> 8, y0 & 0xFF, y1 >> 8, y1 & 0xFF]))
    _cmd(_RAMWR)


def _color16(r: int, g: int, b: int) -> int:
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def rgb(r: int, g: int, b: int) -> int:
    return _color16(r, g, b)


def init(spi: SPI):
    global _spi, _cs, _dc, _bl

    _spi = spi
    _cs  = Pin(P.LCD_CS,  Pin.OUT, value=1)
    _dc  = Pin(P.LCD_DC,  Pin.OUT, value=1)
    rst  = Pin(P.LCD_RST, Pin.OUT, value=1)
    _bl  = PWM(Pin(P.LCD_BL))
    _bl.freq(1000)
    set_backlight(80)

    # Hardware reset
    rst.value(0)
    time.sleep_ms(10)
    rst.value(1)
    time.sleep_ms(120)

    _cmd(_SWRESET)
    time.sleep_ms(150)
    _cmd(_SLPOUT)
    time.sleep_ms(500)

    _cmd_data(_PIXFMT,  b'\x55')            # 16-bit RGB565
    _cmd_data(_MADCTL,  b'\x48')            # row/col swap for landscape 320x240
    _cmd_data(_FRMCTR1, b'\x00\x1B')
    _cmd_data(_DFUNCTR, b'\x0A\x82\x27')
    _cmd_data(_PWCTR1,  b'\x23')
    _cmd_data(_PWCTR2,  b'\x10')
    _cmd_data(_VMCTR1,  b'\x3E\x28')
    _cmd_data(_VMCTR2,  b'\x86')
    _cmd_data(_GMCTRP1, b'\x0F\x31\x2B\x0C\x0E\x08\x4E\xF1\x37\x07\x10\x03\x0E\x09\x00')
    _cmd_data(_GMCTRN1, b'\x00\x0E\x14\x03\x11\x07\x31\xC1\x48\x08\x0F\x0C\x31\x36\x0F')

    _cmd(_DISPON)
    time.sleep_ms(100)

    fill(BLACK)


def set_backlight(percent: int):
    """Set LCD backlight 0-100."""
    duty = int(percent / 100 * 65535)
    _bl.duty_u16(max(0, min(65535, duty)))


def fill(color: int):
    """Fill entire screen with a 16-bit color."""
    _set_window(0, 0, WIDTH - 1, HEIGHT - 1)
    # Send 320*240 pixels = 153600 bytes in 64-byte chunks
    hi = color >> 8
    lo = color & 0xFF
    chunk = bytes([hi, lo] * 64)
    total = WIDTH * HEIGHT
    _dc.value(1)
    _cs.value(0)
    for _ in range(total // 64):
        _spi.write(chunk)
    rem = total % 64
    if rem:
        _spi.write(bytes([hi, lo] * rem))
    _cs.value(1)


def fill_rect(x: int, y: int, w: int, h: int, color: int):
    if w <= 0 or h <= 0:
        return
    _set_window(x, y, x + w - 1, y + h - 1)
    hi = color >> 8
    lo = color & 0xFF
    total = w * h
    # Pre-build a 64-pixel chunk; send smaller remainder at end
    chunk_px = min(64, total)
    chunk = bytes([hi, lo] * chunk_px)
    _dc.value(1)
    _cs.value(0)
    full_chunks = total // chunk_px
    rem = total % chunk_px
    for _ in range(full_chunks):
        _spi.write(chunk)
    if rem:
        _spi.write(bytes([hi, lo] * rem))
    _cs.value(1)


def text(s: str, x: int, y: int, color: int, bg: int = BLACK, scale: int = 2):
    """Draw a string using the built-in 8x8 framebuf font, optionally scaled."""
    char_w = 8 * scale
    char_h = 8 * scale
    total_w = len(s) * char_w

    # Render into scratch fb at 1x then stretch, or render directly at 1x if scale==1
    src_w = len(s) * 8
    src_h = 8
    src_buf = bytearray(src_w * src_h * 2)
    src_fb  = framebuf.FrameBuffer(src_buf, src_w, src_h, framebuf.RGB565)
    src_fb.fill(bg)
    src_fb.text(s, 0, 0, color)

    if scale == 1:
        _set_window(x, y, x + src_w - 1, y + src_h - 1)
        _dc.value(1)
        _cs.value(0)
        _spi.write(src_buf)
        _cs.value(1)
    else:
        # Scale up by 'scale' factor
        dst_w = src_w * scale
        dst_h = src_h * scale
        dst_buf = bytearray(dst_w * dst_h * 2)
        for row in range(src_h):
            for col in range(src_w):
                px = (src_buf[(row * src_w + col) * 2] << 8) | src_buf[(row * src_w + col) * 2 + 1]
                hi = px >> 8
                lo = px & 0xFF
                for sr in range(scale):
                    for sc in range(scale):
                        dst_idx = ((row * scale + sr) * dst_w + col * scale + sc) * 2
                        dst_buf[dst_idx]     = hi
                        dst_buf[dst_idx + 1] = lo
        _set_window(x, y, x + dst_w - 1, y + dst_h - 1)
        _dc.value(1)
        _cs.value(0)
        _spi.write(dst_buf)
        _cs.value(1)


def hline(x: int, y: int, w: int, color: int):
    fill_rect(x, y, w, 1, color)


def vline(x: int, y: int, h: int, color: int):
    fill_rect(x, y, 1, h, color)


def rect(x: int, y: int, w: int, h: int, color: int):
    hline(x, y, w, color)
    hline(x, y + h - 1, w, color)
    vline(x, y, h, color)
    vline(x + w - 1, y, h, color)
