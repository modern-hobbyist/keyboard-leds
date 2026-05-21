"""
MIDI input via USB MIDI Host mode (MicroPython 1.24+ with usb.host).

The RP2040's USB port acts as a USB host so a MIDI keyboard can plug in
directly.  This module discovers the first MIDI-class interface and reads
raw MIDI bytes from it, dispatching to the provided callbacks.

Fallback: if usb.host is not available in the current build, or no device
is connected, the module silently does nothing so the rest of the firmware
still starts.  Connect via a computer in device mode and forward MIDI there
for development.

Callback signatures:
  on_note_on(channel, note, velocity)
  on_note_off(channel, note, velocity)
  on_cc(channel, control, value)
  on_program_change(channel, program)
"""

_on_note_on = None
_on_note_off = None
_on_cc = None
_on_program_change = None

_midi_iface = None
_running = False
_parse_buf = bytearray(3)
_parse_len = 0
_parse_cmd = 0

# MIDI channel filter: 0 = all channels, 1-16 = specific channel
_channel_filter = 0


def init(on_note_on=None, on_note_off=None, on_cc=None, on_program_change=None,
         channel_filter: int = 0):
    """
    Register callbacks and attempt to start USB MIDI host.

    USB MIDI host requires a MicroPython build with usb.host compiled in
    (e.g. the official RP2040 build from micropython.org 1.24+).
    """
    global _on_note_on, _on_note_off, _on_cc, _on_program_change
    global _channel_filter, _running

    _on_note_on      = on_note_on
    _on_note_off     = on_note_off
    _on_cc           = on_cc
    _on_program_change = on_program_change
    _channel_filter  = channel_filter

    _start_usb_host()


def _start_usb_host():
    """Attempt to acquire the first USB MIDI device seen by the host stack."""
    global _midi_iface, _running
    try:
        import usb.host
        import usb.host.midi as umidi
        _midi_iface = umidi.MIDIHost()
        _running = True
        print("MIDI: USB host started, waiting for device...")
    except ImportError:
        print("MIDI: usb.host not available — no MIDI input will be received.")
        print("      Flash a MicroPython build ≥1.24 with USB host support,")
        print("      or use a computer as a MIDI bridge in USB device mode.")
        _running = False
    except Exception as e:
        print(f"MIDI: USB host init failed: {e}")
        _running = False


def poll():
    """
    Read and dispatch any pending MIDI messages.  Call once per main-loop
    iteration; it is non-blocking.
    """
    if not _running or _midi_iface is None:
        return

    try:
        data = _midi_iface.read(64)
    except Exception:
        return

    if not data:
        return

    # USB MIDI wraps each 3-byte MIDI message in a 4-byte USB MIDI Event Packet:
    #   [cable_number | code_index | byte1 | byte2 | byte3]
    i = 0
    while i + 3 < len(data):
        code = data[i] & 0x0F   # Code Index Number
        b1   = data[i + 1]
        b2   = data[i + 2]
        b3   = data[i + 3]
        i   += 4

        if code < 0x08:
            continue   # sysex, cable events, etc. — skip

        _dispatch(b1, b2, b3)


def _dispatch(b1: int, b2: int, b3: int):
    cmd     = b1 & 0xF0
    channel = (b1 & 0x0F) + 1   # 1-based

    if _channel_filter and channel != _channel_filter:
        return

    if cmd == 0x90 and b3 > 0:
        if _on_note_on:
            _on_note_on(channel, b2, b3)
    elif cmd == 0x80 or (cmd == 0x90 and b3 == 0):
        if _on_note_off:
            _on_note_off(channel, b2, b3)
    elif cmd == 0xB0:
        if _on_cc:
            _on_cc(channel, b2, b3)
        # MIDI CC 123 = all notes off
        if b2 == 123 and _on_note_off:
            for n in range(128):
                _on_note_off(channel, n, 0)
    elif cmd == 0xC0:
        if _on_program_change:
            _on_program_change(channel, b2)


def inject(b1: int, b2: int, b3: int):
    """
    Inject a raw MIDI message directly (useful for testing without hardware).
    Example:  midi.inject(0x90, 60, 100)  →  note-on middle C vel 100
    """
    _dispatch(b1, b2, b3)
