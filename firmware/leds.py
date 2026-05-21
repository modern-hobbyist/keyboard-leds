import neopixel
import time
from machine import Pin
import pins as P
import config


# Note state per MIDI note 0-127
_note_vel  = bytearray(128)   # velocity (0 = off)
_note_time = [0] * 128        # time.ticks_ms() when note turned off (for sustain fade)

_np: neopixel.NeoPixel = None
_num_leds = 144


def init():
    global _np, _num_leds
    _num_leds = config.get("num_leds")
    _np = neopixel.NeoPixel(Pin(P.LED_DATA), _num_leds)
    clear()


def _note_to_led(note: int) -> int:
    """Map a MIDI note number to a LED index. Returns -1 if out of range."""
    offset = config.get("note_offset")
    idx = note - P.MIDI_NOTE_MIN + offset
    if idx < 0 or idx >= _num_leds:
        return -1
    return idx


def _hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    """Convert HSV (h 0-360, s/v 0-1) to (r, g, b) 0-255."""
    if s == 0:
        c = int(v * 255)
        return c, c, c
    h = h % 360
    i = int(h / 60)
    f = h / 60 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    sectors = [
        (v, t, p), (q, v, p), (p, v, t),
        (p, q, v), (t, p, v), (v, p, q),
    ]
    r, g, b = sectors[i]
    return int(r * 255), int(g * 255), int(b * 255)


def _velocity_color(note: int, velocity: int) -> tuple:
    """Map note position to hue, velocity to brightness."""
    bright = config.get("brightness") / 255
    vel_scale = velocity / 127 * bright
    # Hue spans the keyboard: low note = blue (240°), high note = red (0°)
    hue = 240 - (note - P.MIDI_NOTE_MIN) / P.NUM_PIANO_KEYS * 240
    return _hsv_to_rgb(hue, 1.0, vel_scale)


def _rainbow_color(led_idx: int) -> tuple:
    bright = config.get("brightness") / 255
    hue = (led_idx / _num_leds) * 360
    return _hsv_to_rgb(hue, 1.0, bright)


def _single_color(velocity: int) -> tuple:
    bright = config.get("brightness") / 255 * velocity / 127
    h = config.get("color_h")
    s = config.get("color_s") / 255
    return _hsv_to_rgb(h, s, bright)


def note_on(note: int, velocity: int):
    _note_vel[note] = velocity
    _note_time[note] = 0


def note_off(note: int):
    _note_vel[note] = 0
    _note_time[note] = time.ticks_ms()


def all_notes_off():
    for i in range(128):
        _note_vel[i] = 0
        _note_time[i] = time.ticks_ms()


def update():
    """Recompute and write LED colors. Call in main loop."""
    anim = config.get("animation")
    sustain_ms = config.get("sustain_ms")
    now = time.ticks_ms()

    # Start from black
    for i in range(_num_leds):
        _np[i] = (0, 0, 0)

    if anim == "rainbow":
        # Background rainbow regardless of notes
        for i in range(_num_leds):
            _np[i] = _rainbow_color(i)
        # Brighten active notes to white
        for note in range(128):
            if _note_vel[note]:
                idx = _note_to_led(note)
                if idx >= 0:
                    _np[idx] = (255, 255, 255)

    elif anim == "gradient":
        # Static gradient; active notes pulse to white
        bright = config.get("brightness") / 255
        for i in range(_num_leds):
            hue = config.get("color_h")
            _np[i] = _hsv_to_rgb(hue, 1.0, bright * 0.2)
        for note in range(128):
            if _note_vel[note]:
                idx = _note_to_led(note)
                if idx >= 0:
                    _np[idx] = _velocity_color(note, _note_vel[note])

    elif anim == "single":
        for note in range(128):
            if _note_vel[note]:
                idx = _note_to_led(note)
                if idx >= 0:
                    _np[idx] = _single_color(_note_vel[note])

    elif anim == "sustain":
        for note in range(128):
            idx = _note_to_led(note)
            if idx < 0:
                continue
            if _note_vel[note]:
                _np[idx] = _velocity_color(note, _note_vel[note])
            elif _note_time[note]:
                elapsed = time.ticks_diff(now, _note_time[note])
                if elapsed < sustain_ms:
                    fade = 1.0 - elapsed / sustain_ms
                    r, g, b = _velocity_color(note, 64)
                    scale = fade
                    _np[idx] = (int(r * scale), int(g * scale), int(b * scale))

    else:  # velocity (default)
        for note in range(128):
            if _note_vel[note]:
                idx = _note_to_led(note)
                if idx >= 0:
                    _np[idx] = _velocity_color(note, _note_vel[note])

    _np.write()


def clear():
    for i in range(_num_leds):
        _np[i] = (0, 0, 0)
    _np.write()


def test_pattern():
    """Startup LED test: sweep all LEDs."""
    bright = max(20, config.get("brightness") // 4)
    for i in range(_num_leds):
        _np[i] = (bright, bright, bright)
        if i > 0:
            _np[i - 1] = (0, 0, 0)
        _np.write()
        time.sleep_ms(4)
    clear()
