# Keyboard LED Firmware

MicroPython firmware for the RP2040-based keyboard LED visualizer.

## Requirements

- **MicroPython ≥ 1.24** for RP2040 with `usb.host` compiled in
  ([download](https://micropython.org/download/RPI_PICO/))
- `neopixel` — built-in to MicroPython
- `framebuf`  — built-in to MicroPython

No third-party libraries are required.

## File layout

```
firmware/
  main.py      Entry point (copy all files to the Pico's root filesystem)
  pins.py      GPIO pin assignments (derived from the KiCad schematic)
  config.py    Settings load/save (persisted to settings.json in flash)
  leds.py      SK6812 LED controller + 5 animation modes
  display.py   ILI9341 SPI display driver (320×240, RGB565)
  touch.py     XPT2046 resistive touch driver
  midi.py      USB MIDI host input + REPL injection helper
  ui.py        Main view + settings menu
```

## Flashing

1. Download the MicroPython UF2 with USB host support for RP2040.
2. Hold BOOTSEL, plug in USB, release — Pico appears as a USB drive.
3. Drag the `.uf2` onto the drive.
4. Use `mpremote` (or Thonny) to copy all `firmware/*.py` to `/`:
   ```sh
   mpremote cp firmware/*.py :
   ```
5. The board will reboot and run `main.py` automatically.

## USB MIDI host

The RP2040 USB port acts as a **USB host**.  Plug your MIDI keyboard's USB
cable directly into the board's data USB-C port.  The firmware discovers the
first USB MIDI class interface automatically.

> **Note:** If your keyboard only has a 5-pin DIN MIDI output, you need a
> USB-MIDI adapter (e.g. Roland UM-ONE) between the DIN connector and the
> board, or connect via a computer running a MIDI bridge.

If `usb.host` is not available in your MicroPython build, the firmware still
boots.  Use the REPL to test without a keyboard:

```python
import midi
midi.inject(0x90, 60, 100)   # note-on middle C, velocity 100
midi.inject(0x80, 60, 0)     # note-off middle C
```

## Touch calibration

Run once after first boot if the touch is inaccurate:

```python
import touch, display, machine
from machine import SPI, Pin
import pins as P
spi = SPI(P.SPI_ID, baudrate=2_000_000, sck=Pin(P.SPI_SCK),
          mosi=Pin(P.SPI_MOSI), miso=Pin(P.SPI_MISO))
display.init(spi)
touch.init(spi)
vals = touch.calibrate()
print(vals)
```

Update `CAL_X_MIN/MAX`, `CAL_Y_MIN/MAX` at the top of `touch.py` with the
printed values.

## Settings

Saved to `settings.json` in the Pico's flash.  Editable at runtime via the
touchscreen Settings menu (tap **Settings** in the top-right corner of the
main screen).

| Key           | Default     | Description                              |
|---------------|-------------|------------------------------------------|
| `animation`   | `velocity`  | `velocity`, `rainbow`, `sustain`, `single`, `gradient` |
| `brightness`  | `80`        | LED brightness 0–255                     |
| `sustain_ms`  | `500`       | Note fade-out duration (sustain mode)    |
| `midi_channel`| `0`         | 0 = all channels, 1–16 = specific        |
| `num_leds`    | `144`       | Number of LEDs in the strip              |
| `note_offset` | `0`         | Shift LED mapping ±20 positions          |
| `color_h`     | `200`       | Hue for single-color mode (0–360)        |
| `backlight`   | `80`        | LCD backlight percentage                 |

## Animation modes

| Mode       | Description                                             |
|------------|---------------------------------------------------------|
| `velocity` | Key position → hue, velocity → brightness (default)    |
| `rainbow`  | Static rainbow; active notes flash white                |
| `sustain`  | Notes fade out slowly after release                     |
| `single`   | All active notes use the configured hue                 |
| `gradient` | Dim colour background; active notes show velocity hue   |

MIDI Program Change messages (PC 0–4) also select animation modes in order.
