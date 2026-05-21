"""
XPT2046 resistive touchscreen controller driver.
Shares the SPI bus with the ILI9341; call with_touch_cs() to acquire.
"""
from machine import Pin, SPI
import pins as P
import display

# XPT2046 channel selection bytes (single-ended, 12-bit)
_CMD_X = 0xD0   # channel 1 (X)
_CMD_Y = 0x90   # channel 5 (Y)

# Calibration defaults (adjust after running calibrate())
# Maps raw ADC range to display pixels
CAL_X_MIN = 300
CAL_X_MAX = 3800
CAL_Y_MIN = 300
CAL_Y_MAX = 3800

_cs  = None
_irq = None
_spi = None


def init(spi: SPI):
    global _cs, _irq, _spi
    _spi = spi
    _cs  = Pin(P.TOUCH_CS,  Pin.OUT, value=1)
    _irq = Pin(P.TOUCH_IRQ, Pin.IN,  Pin.PULL_UP)


def is_touched() -> bool:
    return _irq.value() == 0


def _read_raw(cmd: int) -> int:
    _cs.value(0)
    _spi.write(bytes([cmd]))
    hi = _spi.read(1)[0]
    lo = _spi.read(1)[0]
    _cs.value(1)
    return ((hi << 8) | lo) >> 3   # 12-bit result


def _average(cmd: int, samples: int = 4) -> int:
    total = sum(_read_raw(cmd) for _ in range(samples))
    return total // samples


def read() -> tuple:
    """
    Return (x, y) in display pixel coordinates, or None if not touched.
    The SPI bus must be running at <= 2.5 MHz when calling this.
    """
    if not is_touched():
        return None

    # Lower SPI speed for XPT2046 (max 2.5 MHz)
    _spi.init(baudrate=2_000_000)

    raw_x = _average(_CMD_X)
    raw_y = _average(_CMD_Y)

    # Restore display SPI speed
    _spi.init(baudrate=40_000_000)

    if not is_touched():
        return None

    # Map raw ADC → screen pixels (landscape 320x240, MADCTL=0x48)
    x = (raw_x - CAL_X_MIN) * display.WIDTH  // (CAL_X_MAX - CAL_X_MIN)
    y = (raw_y - CAL_Y_MIN) * display.HEIGHT // (CAL_Y_MAX - CAL_Y_MIN)

    x = max(0, min(display.WIDTH  - 1, x))
    y = max(0, min(display.HEIGHT - 1, y))

    return x, y


def calibrate():
    """
    Interactive calibration routine.  Call once and store the printed values
    into CAL_X_MIN/MAX, CAL_Y_MIN/MAX at the top of this file.
    """
    import display as d

    points = [
        (20,  20,  "top-left"),
        (300, 220, "bottom-right"),
    ]
    results = []

    for px, py, label in points:
        d.fill(d.BLACK)
        d.fill_rect(px - 5, py - 1, 11, 3, d.WHITE)
        d.fill_rect(px - 1, py - 5, 3, 11, d.WHITE)
        d.text(f"Touch {label}", 60, 110, d.WHITE)

        # Wait for touch
        while not is_touched():
            pass
        _spi.init(baudrate=2_000_000)
        rx = _average(_CMD_X, 8)
        ry = _average(_CMD_Y, 8)
        _spi.init(baudrate=40_000_000)
        while is_touched():
            pass

        results.append((rx, ry, px, py))

    # Compute calibration from two points
    (rx0, ry0, px0, py0) = results[0]
    (rx1, ry1, px1, py1) = results[1]

    x_min = int(rx0 - (rx1 - rx0) * px0 / (px1 - px0))
    x_max = int(rx1 + (rx1 - rx0) * (display.WIDTH - 1 - px1) / (px1 - px0))
    y_min = int(ry0 - (ry1 - ry0) * py0 / (py1 - py0))
    y_max = int(ry1 + (ry1 - ry0) * (display.HEIGHT - 1 - py1) / (py1 - py0))

    d.fill(d.BLACK)
    d.text(f"CAL_X_MIN={x_min}", 10, 60,  d.WHITE)
    d.text(f"CAL_X_MAX={x_max}", 10, 80,  d.WHITE)
    d.text(f"CAL_Y_MIN={y_min}", 10, 100, d.WHITE)
    d.text(f"CAL_Y_MAX={y_max}", 10, 120, d.WHITE)
    d.text("Update touch.py constants", 10, 150, d.YELLOW)

    return x_min, x_max, y_min, y_max
