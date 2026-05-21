"""
Keyboard LED Visualizer — main entry point.

Boot order:
  1. Load settings from flash
  2. Bring up SPI bus → ILI9341 display
  3. Init XPT2046 touch controller
  4. Init SK6812 LED strip
  5. Start USB MIDI host
  6. Show splash screen + LED test
  7. Enter main loop

USB MIDI host requires MicroPython ≥ 1.24 with usb.host compiled in.
If that module is absent the firmware still boots; use midi.inject() in
the REPL to send notes without a keyboard connected.

Quick REPL test:
  import midi
  midi.inject(0x90, 60, 100)   # note-on C4 vel=100
  midi.inject(0x80, 60, 0)     # note-off C4
"""

import time
from machine import Pin, SPI, I2C, PWM
import pins as P
import config
import leds
import display as d
import touch
import midi
import ui


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------

def _init_spi() -> SPI:
    # Display runs at 40 MHz; touch driver drops to 2 MHz while reading.
    spi = SPI(
        P.SPI_ID,
        baudrate=40_000_000,
        polarity=0,
        phase=0,
        sck=Pin(P.SPI_SCK),
        mosi=Pin(P.SPI_MOSI),
        miso=Pin(P.SPI_MISO),
    )
    return spi


def _init_power():
    """
    Configure the TPS2121 dimming line and set up the power-interrupt pin.

    DIM_DATA (GPIO3) drives the TPS2121 VOUT voltage, which controls maximum
    LED current.  Pull it high (3.3 V) to allow full brightness; the main loop
    can lower it based on POWER_INT feedback from the TUSB320.

    For now, assert high unconditionally and let the user tune via the
    brightness setting.  A proper implementation would read I2C registers from
    the TUSB320 and scale accordingly.
    """
    dim = Pin(P.DIM_DATA, Pin.OUT, value=1)
    power_irq = Pin(P.POWER_INT, Pin.IN, Pin.PULL_UP)
    return dim, power_irq


def _splash():
    bg = d.rgb(10, 10, 30)
    d.fill(bg)
    d.text("Keyboard LEDs",     60, 80,  d.WHITE, bg, scale=2)
    d.text("by Modern Hobbyist", 60, 120, d.GRAY,  bg, scale=1)
    d.text("Booting...",        60, 150, d.GRAY,  bg, scale=1)


# ---------------------------------------------------------------------------
# MIDI callbacks
# ---------------------------------------------------------------------------

def _on_note_on(channel: int, note: int, velocity: int):
    leds.note_on(note, velocity)
    ui.mark_note_on(note)


def _on_note_off(channel: int, note: int, velocity: int):
    leds.note_off(note)
    ui.mark_note_off(note)


def _on_cc(channel: int, control: int, value: int):
    # CC 7 = channel volume → map to overall brightness
    if control == 7:
        config.set("brightness", int(value * 255 / 127))


def _on_program_change(channel: int, program: int):
    # Programs 0-4 select animation modes
    modes = ["velocity", "rainbow", "sustain", "single", "gradient"]
    if program < len(modes):
        config.set("animation", modes[program])


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

_LED_UPDATE_INTERVAL_MS  = 16    # ~60 fps LED refresh
_UI_UPDATE_INTERVAL_MS   = 33    # ~30 fps display refresh
_MIDI_POLL_INTERVAL_MS   = 1     # tight MIDI polling


def run():
    # 1. Settings
    settings = config.load()

    # 2. Power management lines
    _dim, _power_irq = _init_power()

    # 3. Display
    spi = _init_spi()
    d.init(spi)
    _splash()

    # 4. Touch
    touch.init(spi)

    # 5. LEDs
    leds.init()

    # 6. MIDI host
    midi.init(
        on_note_on=_on_note_on,
        on_note_off=_on_note_off,
        on_cc=_on_cc,
        on_program_change=_on_program_change,
        channel_filter=config.get("midi_channel"),
    )

    # 7. Startup test
    leds.test_pattern()
    time.sleep_ms(800)
    ui.force_redraw()

    # 8. Main loop
    t_led = time.ticks_ms()
    t_ui  = time.ticks_ms()

    while True:
        now = time.ticks_ms()

        # MIDI: poll as fast as possible
        midi.poll()

        # LEDs: fixed rate
        if time.ticks_diff(now, t_led) >= _LED_UPDATE_INTERVAL_MS:
            leds.update()
            t_led = now

        # UI: display + touch
        if time.ticks_diff(now, t_ui) >= _UI_UPDATE_INTERVAL_MS:
            ui.update()
            t_ui = now


run()
