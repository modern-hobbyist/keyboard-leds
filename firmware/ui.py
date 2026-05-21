"""
Touchscreen UI: main view and settings menu for the 320x240 ILI9341 display.

Layout (landscape):
  Main view:
    [0-29]    Title bar
    [30-179]  Note visualiser (piano roll strip)
    [180-239] Status bar + Settings button

  Settings view:
    [0-29]    Title bar + Back/Save buttons
    [30-209]  Scrollable parameter rows (6 visible at a time, 30px each)
    [210-239] Save / Cancel buttons
"""

import display as d
import touch
import config
import time

# ---------------------------------------------------------------------------
# Layout constants
# ---------------------------------------------------------------------------
TITLE_H    = 30
STATUS_H   = 60
BTN_H      = 40
ROW_H      = 30
ROW_INDENT = 10
W          = d.WIDTH    # 320
H          = d.HEIGHT   # 240

# Current screen
_screen = "main"   # "main" | "settings"
_dirty  = True
_last_touch = 0
_DEBOUNCE_MS = 250

# Active notes set (note numbers)
_active_notes: set = set()

# Settings parameter descriptors
# Each entry: (key, label, type, min, max, choices)
_PARAMS = [
    ("animation",    "Animation",   "choice", None, None,
     ["velocity", "rainbow", "sustain", "single", "gradient"]),
    ("brightness",   "Brightness",  "int",    5,    255, None),
    ("sustain_ms",   "Sustain ms",  "int",    50,   2000, None),
    ("midi_channel", "MIDI Ch",     "int",    0,    16, None),
    ("num_leds",     "LED Count",   "int",    1,    180, None),
    ("note_offset",  "Note Offset", "int",    -20,  20, None),
    ("color_h",      "Color Hue",   "int",    0,    360, None),
    ("backlight",    "Backlight %", "int",    10,   100, None),
]

_scroll_offset = 0          # first visible row index in settings
_VISIBLE_ROWS  = (H - TITLE_H - BTN_H) // ROW_H


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def mark_note_on(note: int):
    _active_notes.add(note)
    if _screen == "main":
        _draw_note_bar()


def mark_note_off(note: int):
    _active_notes.discard(note)
    if _screen == "main":
        _draw_note_bar()


def update():
    """Call once per main-loop tick to handle touch and redraw dirty regions."""
    global _dirty, _screen, _last_touch

    if _dirty:
        _full_redraw()
        _dirty = False

    pt = touch.read()
    if pt is None:
        return

    now = time.ticks_ms()
    if time.ticks_diff(now, _last_touch) < _DEBOUNCE_MS:
        return
    _last_touch = now

    if _screen == "main":
        _handle_main_touch(pt)
    else:
        _handle_settings_touch(pt)


def force_redraw():
    global _dirty
    _dirty = True


# ---------------------------------------------------------------------------
# Main view
# ---------------------------------------------------------------------------

def _draw_main_title():
    d.fill_rect(0, 0, W, TITLE_H, d.rgb(20, 20, 80))
    d.text("Keyboard LEDs", 8, 7, d.WHITE)
    # Settings button in title bar (right side)
    d.fill_rect(W - 90, 4, 86, TITLE_H - 8, d.rgb(60, 60, 120))
    d.rect(W - 90, 4, 86, TITLE_H - 8, d.GRAY)
    d.text("Settings", W - 88, 9, d.WHITE)


def _draw_note_bar():
    """Render the piano roll strip showing active notes."""
    bar_y = TITLE_H
    bar_h = H - TITLE_H - STATUS_H
    d.fill_rect(0, bar_y, W, bar_h, d.BLACK)

    import pins as P
    num_leds = config.get("num_leds")
    px_per_led = W / num_leds

    for note in _active_notes:
        led_idx = note - P.MIDI_NOTE_MIN + config.get("note_offset")
        if led_idx < 0 or led_idx >= num_leds:
            continue
        x0 = int(led_idx * px_per_led)
        x1 = max(x0 + 1, int((led_idx + 1) * px_per_led))
        # Color: hue based on note position (same as velocity animation)
        hue = 240 - (note - P.MIDI_NOTE_MIN) / P.NUM_PIANO_KEYS * 240
        r, g, b = _hsv_to_rgb(hue, 1.0, 1.0)
        d.fill_rect(x0, bar_y + 4, x1 - x0, bar_h - 8, d.rgb(r, g, b))

    # Piano key grid lines
    num_white = 52  # 88 keys ≈ 52 white keys
    for i in range(num_white + 1):
        gx = int(i * W / num_white)
        d.vline(gx, bar_y, bar_h, d.DKGRAY)


def _draw_main_status():
    sy = H - STATUS_H
    d.fill_rect(0, sy, W, STATUS_H, d.rgb(15, 15, 15))
    d.hline(0, sy, W, d.DKGRAY)

    anim = config.get("animation")
    bright = config.get("brightness")
    ch = config.get("midi_channel")
    ch_str = "All" if ch == 0 else str(ch)
    n_active = len(_active_notes)

    d.text(f"Mode: {anim}", ROW_INDENT, sy + 8, d.GRAY, d.rgb(15, 15, 15))
    d.text(f"Bright: {bright}  Ch: {ch_str}  Notes: {n_active}",
           ROW_INDENT, sy + 28, d.GRAY, d.rgb(15, 15, 15))


def _full_redraw():
    if _screen == "main":
        _draw_main_title()
        _draw_note_bar()
        _draw_main_status()
    else:
        _draw_settings()


def _handle_main_touch(pt):
    global _screen, _dirty
    x, y = pt
    # Settings button: top-right corner
    if x >= W - 90 and y <= TITLE_H:
        _screen = "settings"
        _dirty  = True


# ---------------------------------------------------------------------------
# Settings view
# ---------------------------------------------------------------------------

def _draw_settings():
    d.fill(d.BLACK)
    # Title bar
    d.fill_rect(0, 0, W, TITLE_H, d.rgb(20, 80, 20))
    d.text("Settings", 8, 7, d.WHITE)
    # Back button
    d.fill_rect(W - 70, 4, 66, TITLE_H - 8, d.rgb(80, 40, 20))
    d.rect(W - 70, 4, 66, TITLE_H - 8, d.ORANGE)
    d.text("Back", W - 65, 9, d.WHITE)

    # Parameter rows
    _draw_param_rows()

    # Save button at bottom
    d.fill_rect(10, H - BTN_H + 5, W // 2 - 20, BTN_H - 10, d.rgb(20, 80, 20))
    d.rect(10, H - BTN_H + 5, W // 2 - 20, BTN_H - 10, d.GREEN)
    d.text("Save", 40, H - BTN_H + 12, d.WHITE)

    # Scroll hints
    if _scroll_offset > 0:
        d.text("^", W - 18, TITLE_H + 4, d.GRAY, d.BLACK)
    if _scroll_offset + _VISIBLE_ROWS < len(_PARAMS):
        d.text("v", W - 18, TITLE_H + ROW_H * _VISIBLE_ROWS - 16, d.GRAY, d.BLACK)


def _draw_param_rows():
    for i in range(_VISIBLE_ROWS):
        idx = i + _scroll_offset
        if idx >= len(_PARAMS):
            break
        _draw_param_row(i, idx)


def _draw_param_row(row_screen: int, param_idx: int):
    key, label, kind, vmin, vmax, choices = _PARAMS[param_idx]
    y = TITLE_H + row_screen * ROW_H
    bg = d.rgb(25, 25, 25) if row_screen % 2 == 0 else d.BLACK

    d.fill_rect(0, y, W, ROW_H, bg)
    d.hline(0, y, W, d.DKGRAY)

    val = config.get(key)
    if kind == "choice":
        val_str = str(val)
    elif key == "midi_channel":
        val_str = "All" if val == 0 else str(val)
    else:
        val_str = str(val)

    d.text(label + ":", ROW_INDENT, y + 8, d.GRAY, bg)
    d.text(val_str, 150, y + 8, d.WHITE, bg)

    # Minus button
    d.fill_rect(250, y + 4, 28, ROW_H - 8, d.rgb(60, 20, 20))
    d.rect(250, y + 4, 28, ROW_H - 8, d.RED)
    d.text("-", 261, y + 8, d.WHITE, d.rgb(60, 20, 20))

    # Plus button
    d.fill_rect(285, y + 4, 28, ROW_H - 8, d.rgb(20, 60, 20))
    d.rect(285, y + 4, 28, ROW_H - 8, d.GREEN)
    d.text("+", 296, y + 8, d.WHITE, d.rgb(20, 60, 20))


def _adjust_param(param_idx: int, direction: int):
    """direction: +1 or -1"""
    key, label, kind, vmin, vmax, choices = _PARAMS[param_idx]
    val = config.get(key)

    if kind == "choice":
        idx = choices.index(val) if val in choices else 0
        idx = (idx + direction) % len(choices)
        config.set(key, choices[idx])
    elif kind == "int":
        step = max(1, (vmax - vmin) // 50)
        if key in ("brightness", "backlight", "midi_channel", "num_leds"):
            step = 1
        if key == "sustain_ms":
            step = 50
        new_val = max(vmin, min(vmax, val + direction * step))
        config.set(key, new_val)

    # Apply immediately
    if key == "backlight":
        d.set_backlight(config.get("backlight"))


def _handle_settings_touch(pt):
    global _screen, _dirty, _scroll_offset
    x, y = pt

    # Back button
    if x >= W - 70 and y <= TITLE_H:
        _screen = "main"
        _dirty  = True
        return

    # Save button
    if y >= H - BTN_H and x < W // 2:
        config.save()
        _screen = "main"
        _dirty  = True
        return

    # Scroll: tap right edge
    if x >= W - 20:
        if y < H // 2 and _scroll_offset > 0:
            _scroll_offset -= 1
            _dirty = True
        elif y >= H // 2 and _scroll_offset + _VISIBLE_ROWS < len(_PARAMS):
            _scroll_offset += 1
            _dirty = True
        return

    # Parameter row touch
    if TITLE_H <= y < H - BTN_H:
        row_screen = (y - TITLE_H) // ROW_H
        param_idx  = row_screen + _scroll_offset
        if param_idx >= len(_PARAMS):
            return

        if 250 <= x <= 278:     # minus button
            _adjust_param(param_idx, -1)
            _draw_param_row(row_screen, param_idx)   # partial refresh
        elif 285 <= x <= 313:   # plus button
            _adjust_param(param_idx, +1)
            _draw_param_row(row_screen, param_idx)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _hsv_to_rgb(h: float, s: float, v: float) -> tuple:
    if s == 0:
        c = int(v * 255)
        return c, c, c
    h = h % 360
    i = int(h / 60)
    f = h / 60 - i
    p = v * (1 - s)
    q = v * (1 - s * f)
    t = v * (1 - s * (1 - f))
    r, g, b = [(v, t, p), (q, v, p), (p, v, t),
                (p, q, v), (t, p, v), (v, p, q)][i]
    return int(r * 255), int(g * 255), int(b * 255)
