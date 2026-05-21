import json
import os

SETTINGS_FILE = "settings.json"

DEFAULTS = {
    "brightness": 80,          # 0-255
    "animation": "velocity",   # velocity | rainbow | sustain | single | gradient
    "color_h": 200,            # hue for single-color mode (0-360)
    "color_s": 255,            # saturation (0-255)
    "midi_channel": 0,         # 0 = omni (all channels)
    "num_leds": 144,
    "note_offset": 0,          # shift LED mapping by N positions
    "backlight": 80,           # LCD backlight 0-100%
    "sustain_ms": 500,         # fade-out duration after note-off (ms)
}

_settings = {}


def load():
    global _settings
    _settings = dict(DEFAULTS)
    try:
        with open(SETTINGS_FILE) as f:
            saved = json.load(f)
        _settings.update({k: saved[k] for k in saved if k in DEFAULTS})
    except (OSError, ValueError):
        pass
    return _settings


def save():
    with open(SETTINGS_FILE, "w") as f:
        json.dump(_settings, f)


def get(key):
    return _settings.get(key, DEFAULTS.get(key))


def set(key, value):
    if key in DEFAULTS:
        _settings[key] = value


def all_settings():
    return dict(_settings)
