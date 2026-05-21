# 🎹 Piano Keyboard LED Visualizer (WIP)

This project is a **custom RP2040-based LED controller** designed to add **reactive RGB lighting** to a piano or MIDI keyboard by reading the incoming **MIDI stream** and driving high-density LED strips.

This is my second iteration of MIDI-driven keyboard LEDs, but the first time going *all in* with a fully custom PCB, power-path management, and an onboard touchscreen UI.

⚠️ **Status:** Work in progress  
Hardware is under active development, firmware and features are evolving, and this README will be updated as the project matures.

---

## ✨ High-Level Overview

- Reads **MIDI input** from a keyboard or computer
- Visualizes notes and velocity using **addressable RGB LEDs**
- Includes a **touchscreen UI** for configuring colors, brightness, and animations
- Designed to safely handle **high LED current** while remaining USB-compliant when connected to a computer

The long-term goal is to make this a flexible platform for experimenting with different LED visualization styles while keeping the hardware robust and reusable.

---

## 🔧 Hardware Overview

### Core Components
- **MCU:** RP2040
- **External Flash:** Winbond **W25Q128JVS** (16 MB)
- **Display:** 2.8″ 320×240 TFT LCD with touch
- **LED Support:**  
  - Designed for ~**1–1.5 m of 144 px/m LED strips**
  - Intended for per-key piano illumination

### USB & Power Architecture
- **USB-C (Data / MIDI / Firmware Flashing)**
- **USB-C (Dedicated LED Power Input)**
- **TPS2121** – automatic power-path switching between USB sources
- **TUSB320** – USB-C CC controller used to determine available current
- **Polyfuses** on both USB inputs for protection

The board is designed to intelligently decide how much LED brightness is safe depending on the power source.

---

## 🎯 Design Goals

- **Dual-mode operation**
  - Plugged into a computer → automatically limit LED current to stay within USB limits (~500 mA)
  - Plugged into a keyboard’s MIDI output + external USB-C PSU → allow much higher LED brightness (~3 A target)
- **Touchscreen UI**
  - Adjust brightness, colors, and animations
  - Switch visualization modes without a computer
- **High LED density support**
  - Enough bandwidth and power to drive dense LED strips cleanly
- **Expandable firmware**
  - External flash provides room for animations, fonts, and UI assets

Exact feature set is still evolving — the focus right now is getting the hardware and power logic correct.

---

## 📌 GPIO Pin Map

Derived from the KiCad schematic (`keyboard-leds.kicad_sch`):

### SPI Bus — ILI9341 Display + XPT2046 Touch (shared)
| GPIO | Net | Function |
|------|-----|----------|
| 16 | LCD_MISO | SPI MISO |
| 18 | LCD_SCK | SPI clock |
| 19 | LCD_MOSI | SPI MOSI |
| 17 | LCD_CS | ILI9341 chip select |
| 20 | LCD_DC | ILI9341 data/command |
| 21 | LCD_RST | ILI9341 reset |
| 22 | LCD_BL_PWM | Backlight PWM |
| 13 | LCD_T_CS | XPT2046 touch chip select |
| 12 | LCD_T_IRQ | XPT2046 touch interrupt |
| 14 | LCD_SD_CS | SD card chip select (LCD module) |

### I2C Bus — Power Management ICs
| GPIO | Net | Function |
|------|-----|----------|
| 4 | SDA | I2C data (TUSB320) |
| 5 | SCL | I2C clock (TUSB320) |

### LEDs & Power Control
| GPIO | Net | Function |
|------|-----|----------|
| 6 | RGB3.3 | SK6812 data → level shifter → 5 V strip |
| 3 | DIM_DATA | TPS2121 dimming/current limit control |
| 8 | POWER_INT | Interrupt from power management IC |

### USB
| Signal | Function |
|--------|----------|
| USB D+ / D− | Data USB-C — MIDI host + firmware flashing |

### QSPI Flash
Managed automatically by MicroPython. Connected to the W25Q128JVS via the RP2040's dedicated QSPI pins (not accessible as general GPIO).

---

## 🧠 Firmware

MicroPython firmware is included in the `firmware/` directory. See [`firmware/README.md`](firmware/README.md) for full setup and flashing instructions.

**Features:**
- USB MIDI host — keyboard plugs directly into the data USB-C port
- SK6812 LED animations: velocity, rainbow, sustain, single color, gradient
- ILI9341 touchscreen UI with scrollable settings menu
- Persistent settings saved to flash (brightness, animation mode, MIDI channel, LED count, etc.)
- Brightness limiting via TPS2121 `DIM_DATA` line based on available power

**Requirements:** MicroPython ≥ 1.24 for RP2040 with `usb.host` support.

---

## 🧩 PCB Review Context

This board uses a few parts that are new to me, particularly for USB-C and power management:

- **TUSB320** – for USB-C current detection
- **TPS2121** – for seamless power-path switching

While I’ve built multiple custom mechanical keyboards, this is my first design combining:
- Dual USB-C inputs
- High LED current
- USB-compliant behavior
- Onboard display + touch

Feedback on **power logic, USB-C usage, and general robustness** is especially appreciated.

---

## 📦 Bill of Materials (BOM)

A complete BOM is included in the repo and reflects the current PCB revision.  
Key highlights:
- RP2040 MCU
- W25Q128JVS external flash
- TPS2121 power mux
- TUSB320 USB-C controller
- SRV05-4 ESD protection
- TFT LCD (ILI9341-based)

⚠️ Component values and footprints may change as the design is reviewed and iterated.

---

## 📸 Media & Updates

I plan to document this project on my **YouTube channel, Modern Hobbyist**, including:
- PCB bring-up
- Power testing
- LED current experiments
- Firmware development

Links will be added as videos are published.

---

## 🤝 Feedback & Contributions

This repo is currently focused on **design review and learning**, but feedback is very welcome.

If you have experience with:
- USB-C power negotiation
- LED power distribution
- RP2040 display pipelines
- MIDI-driven lighting

…I’d love to hear your thoughts.

---

## 📄 License

TBD (will be added once the design stabilizes)

