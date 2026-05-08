# Pi-EGT

Marine boat instrument panel for Raspberry Pi 3 with a 5" DSI touchscreen (portrait mode, 480 × 800).

Displays exhaust gas temperature (EGT) in real time via a large circular analog gauge, logs a 15-minute rolling history, monitors ambient temperatures, and — when connected to WiFi — shows today's weather forecast and lightning storm risk.

---

## Hardware

| Component | Detail |
|-----------|--------|
| Raspberry Pi 3 | Any variant |
| Raspberry Pi Touchscreen 2 (5") | DSI, 480 × 800 portrait |
| MAX31855 thermocouple amplifier | EGT sensor via SPI (CE0, 1 MHz) |
| DS18B20 temperature sensor(s) | Up to 2 on 1-Wire bus (GPIO 4) |
| Buzzer | EGT alarm via GPIO 17 (NPN transistor) |
| Custom HAT PCB | LM2596 buck converter from boat battery |

## Features

- **EGT gauge** — circular analog gauge with coloured zone arc (green / amber / red), digital readout and 15-minute scrolling histogram
- **Ambient temperature tiles** — shown automatically when DS18B20 sensors are detected; hidden if sensors disconnect (with 15-second timeout)
- **Buzzer alarm** — activates when EGT exceeds a configurable threshold
- **Weather panel** — today's forecast (icon, description, min/max °C) via [Open-Meteo](https://open-meteo.com/), selectable location
- **Lightning risk panel** — Low / Moderate / High / Active derived from CAPE and WMO weather codes
- **Adaptive poll rate** — 4 Hz normally, drops to 1 Hz if the Pi CPU exceeds 70 °C
- **Portrait layout** — all panels stack vertically; weather and lightning panels are hidden by default and revealed on demand (histogram hides to make room)
- **Setup dialog** — configure EGT gauge min/max, alarm threshold, and mock sensor mode without restarting
- **Fullscreen toggle** — hides the OS taskbar for a clean instrument view
- **Auto-start on boot** via XDG autostart (`~/.config/autostart/pi-egt.desktop`)

## Requirements

```
PyQt5 >= 5.15
requests >= 2.28
spidev >= 3.5      # Pi only
RPi.GPIO >= 0.7    # Pi only
```

Install on the Pi:

```bash
pip3 install -r requirements.txt
```

## Pi OS configuration

Add to `/boot/firmware/config.txt` and reboot:

```ini
dtparam=spi=on        # MAX31855
dtoverlay=w1-gpio     # DS18B20
```

## Running

```bash
cd ~/pi-egt
DISPLAY=:0 python3 main.py            # normal mode
DISPLAY=:0 python3 main.py --mock     # simulated sawtooth sensors
```

Mock mode can also be toggled at runtime from the **Setup** dialog.

## Deployment to Pi

```bash
# Copy project
scp -r . pi@<pi-ip>:~/pi-egt/

# Install desktop shortcut
ssh pi@<pi-ip> "cp ~/pi-egt/pi-egt.desktop ~/Desktop/ && chmod +x ~/Desktop/pi-egt.desktop"

# Install autostart (runs on every boot)
ssh pi@<pi-ip> "mkdir -p ~/.config/autostart && cp ~/pi-egt/pi-egt.desktop ~/.config/autostart/"
```

## Project structure

```
Pi-EGT/
├── main.py                   Entry point; --mock flag; dark Qt palette
├── pi-egt.desktop            Desktop / autostart launcher
├── requirements.txt
├── docs/
│   ├── notes.md              Hardware design notes, PCB, BOM
│   └── software.md           Full software description & architecture
└── pi_egt/
    ├── config.py             Constants and user config (load/save JSON)
    ├── sensors/
    │   ├── max31855.py       SPI thermocouple reader
    │   ├── ds18b20.py        1-Wire temperature reader
    │   └── buzzer.py         GPIO buzzer
    ├── network/
    │   ├── connectivity.py   TCP reachability check
    │   ├── weather.py        Open-Meteo API client
    │   ├── lightning.py      Lightning risk assessment
    │   └── fetch_thread.py   Non-blocking QThread fetch
    └── ui/
        ├── main_window.py    Main window, layout, timers
        └── widgets/
            ├── egt_gauge.py
            ├── histogram.py
            ├── temp_tile.py
            ├── weather_panel.py
            ├── lightning_panel.py
            ├── setup_dialog.py
            └── location_dialog.py
```

## License

MIT
