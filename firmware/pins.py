# Hardware pin assignments derived from keyboard-leds.kicad_sch
# RP2040 GPIO -> net -> function

# SK6812 LED strip (3.3V data -> level shifter -> 5V -> strip)
LED_DATA = 6          # RGB3.3

# Shared SPI bus (ILI9341 display + XPT2046 touch)
SPI_ID   = 0
SPI_SCK  = 18         # LCD_SCK
SPI_MOSI = 19         # LCD_MOSI
SPI_MISO = 16         # LCD_MISO

# ILI9341 display control
LCD_CS   = 17         # LCD_CS
LCD_DC   = 20         # LCD_DC  (data=1, command=0)
LCD_RST  = 21         # LCD_RST
LCD_BL   = 22         # LCD_BL_PWM  (backlight, PWM on slice 3)

# XPT2046 touch controller (same SPI bus, different CS)
TOUCH_CS  = 13        # LCD_T_CS
TOUCH_IRQ = 12        # LCD_T_IRQ

# SD card on LCD module (reserved, not used)
SD_CS = 14            # LCD_SD_CS

# I2C bus (TUSB320 power negotiation IC)
I2C_ID  = 0
I2C_SDA = 4
I2C_SCL = 5

# Power management
POWER_INT = 8         # Interrupt from power IC
DIM_DATA  = 3         # TPS2121 dimming signal

# MIDI note range for a standard 88-key piano
MIDI_NOTE_MIN = 21    # A0
MIDI_NOTE_MAX = 108   # C8
NUM_PIANO_KEYS = 88
