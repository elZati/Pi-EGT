# Pi-EGT Software — Description & Architecture

## What it is

Pi-EGT is a marine instrument panel application for Raspberry Pi 3 with a 5-inch DSI
touchscreen.  It displays exhaust gas temperature (EGT) and ambient temperatures in
real time, triggers a buzzer alarm when EGT exceeds a configurable threshold, and
optionally shows today's weather forecast and lightning storm risk when the Pi has a
network connection.

---

## Running the app

```bash
cd ~/pi-egt
DISPLAY=:0 python3 main.py          # real hardware
DISPLAY=:0 python3 main.py --mock   # simulated sensors (development)
```

`--mock` forces all sensors into simulation mode regardless of whether the hardware
interfaces are present.  Useful when the sensors are not yet connected.

Mock mode can also be toggled at runtime from the Setup dialog without restarting.

User settings (EGT range, alarm threshold, mock mode, saved location) are stored in
`~/.pi_egt/config.json` and loaded automatically on startup.

---

## Screen layout  (480 × 800 portrait, Raspberry Pi Touchscreen 2)

```
┌────────────── 480 ───────────────┐
│                                  │
│          EGT analog gauge        │  stretch 8
│       (large circular, full      │
│        width, dominant)          │
│                                  │
├──────────────────────────────────┤
│       15-minute EGT histogram    │  stretch 2
├──────────────────────────────────┤
│   Ambient 1    │    Ambient 2    │  stretch 2 (hidden if no sensors)
├──────────────────────────────────┤
│       Lightning risk panel       │  stretch 2 (hidden by default)
├──────────────────────────────────┤
│       Weather panel              │  stretch 2 (hidden by default)
├──────────────────────────────────┤
│ [⚙ Setup][⚡ Ltng][▼ Wth][⛶ Full]│  fixed 44 px
└──────────────────────────────────┘
```

All sections stack top-to-bottom (portrait orientation).

**Dynamic visibility rules:**
- Ambient temperature row appears only when DS18B20 sensors are detected (or mock
  mode is active).  Hidden entirely when no 1-Wire sensors are found.
- Lightning panel is hidden on startup.  Tap **⚡ Lightning** to reveal it.
- Weather panel is hidden on startup.  Tap **▼ Weather** to reveal it.

---

## Sensors

### MAX31855 — EGT thermocouple (SPI)

| Item | Detail |
|------|--------|
| Interface | SPI bus 0, CE0 (`/dev/spidev0.0`) |
| Clock speed | 1 MHz (tolerant of long cable run to aft sensor) |
| Poll rate | 1 second |
| Mock | Sawtooth 0 → 1000 °C, period ~120 s |

`None` is returned on any fault condition (open circuit, short to VCC/GND).  The
gauge shows **FAULT** and the buzzer stays silent.

### DS18B20 — Ambient temperature (1-Wire)

| Item | Detail |
|------|--------|
| Interface | 1-Wire on GPIO 4 (`/sys/bus/w1/devices/28-*`) |
| Sensors | Up to 2 on one bus |
| Poll rate | 1 second (same timer as EGT) |
| Mock | Sawtooth 0 → 100 °C, period ~60 s; sensor 2 offset by 50 °C |

If the 1-Wire bus is present but no `28-*` sensor files are found, the driver
automatically falls back to mock data rather than showing blank tiles.

The `sensor_count` property exposes how many sensors are active (2 in mock mode,
actual discovered count in hardware mode).  `MainWindow` uses this to show or hide
the ambient temperature tiles dynamically.

### Buzzer — EGT alarm (GPIO 17)

Driven via NPN transistor (BC817-25).  The buzzer activates whenever the EGT reading
exceeds the configured alarm threshold.  It deactivates as soon as the reading drops
back below the threshold.  On Pi OS the driver uses `RPi.GPIO`; off-Pi it is a no-op.

---

## EGT gauge

A custom `QPainter`-drawn circular gauge rendered in a virtual 300 × 300 coordinate
space and scaled to fill the available widget area.

**Configurable range** — the gauge min, max, and alarm threshold are all user-settable
via the Setup dialog.  Changes take effect immediately without restarting.

**Zone colours** — derived at runtime from the alarm threshold:

| Zone | Range | Colour |
|------|-------|--------|
| Safe | min → alarm × 0.85 | Green `#27ae60` |
| Caution | alarm × 0.85 → alarm | Amber `#f39c12` |
| Danger | alarm → max | Red `#e74c3c` |

When the alarm threshold changes the colour arc boundaries redraw automatically.

**Tick labels** — font 11 px bold, placed at radius 76 (well inside the colour arc at
radius 110) so they never overlap the arc.  Step size is computed from the display
range (100 °C steps for 0–1000 °C, 50 °C for smaller ranges, etc.).

---

## 15-minute EGT histogram

Keeps a rolling `deque` of `(monotonic_timestamp, temperature)` pairs covering the
last 15 minutes (900 seconds).  Readings older than 15 minutes are pruned on every
new reading.

The histogram spans the full window width below the top row.

The Y-axis scale matches the gauge max setting and redraws correctly when the range
is changed via Setup.  Grid-line and label steps are computed dynamically:

| Max temp | Step |
|----------|------|
| ≤ 200 °C | 50 °C |
| ≤ 500 °C | 100 °C |
| > 500 °C | 200 °C |

---

## Setup dialog

Opened via the **⚙ Setup** button (bottom-left, 44 px tall touch target).

| Setting | Default | Step | Range |
|---------|---------|------|-------|
| Gauge Min | 0 °C | 50 °C | 0 – 500 °C |
| Gauge Max | 1000 °C | 50 °C | 200 – 1200 °C |
| Alarm Threshold | 800 °C | 10 °C | 100 – 1200 °C |
| Mock Sensors | OFF | toggle | — |

On **Save**:
- Alarm is automatically clamped to the display range.
- Gauge Min is clamped so that Max − Min ≥ 100 °C.
- Values are applied immediately to the gauge, histogram, and alarm logic.
- If mock mode changed, sensors are re-initialised in place and tile visibility
  is updated without restarting the app.
- Settings are persisted to `~/.pi_egt/config.json`.

---

## Weather panel

Requires an internet connection (checked before every fetch via a TCP probe to
`8.8.8.8:53`).  When offline, all panels show "No network" and retry on the next
scheduled tick.

**Hidden by default** — tap **▼ Show weather** to reveal it.  The button turns green
when weather is hidden as a reminder that it is available.

**Data source:** [Open-Meteo](https://open-meteo.com/) — free, no API key required.

**What is shown:**
- Location name (city)
- Today's dominant weather icon and description (WMO weather code)
- Today's min / max temperature (°C)

**Location selection:** tap the **⚙** button inside the weather panel to open a city
search dialog.  The geocoding API is also Open-Meteo.  Selected location is saved to
`~/.pi_egt/config.json`.

**Sensor poll rate:** adaptive — 250 ms (4 Hz) normally; drops to 1000 ms when the
Pi CPU temperature exceeds 70 °C, and restores once it falls back below 65 °C.
The CPU temperature is sampled every 10 seconds from
`/sys/class/thermal/thermal_zone0/temp`.  On non-Pi hardware the fast rate is
always used.

**Fetch interval:** every 15 minutes.  Each fetch runs in a one-shot `QThread`
(`FetchThread`) so the UI is never blocked.  After the thread finishes it is deleted
and the reference cleared; only one fetch runs at a time.

**Connectivity retry:** the first fetch fires 10 seconds after startup (to give WiFi
time to connect on autostart).  If the network is unreachable, the app retries every
30 seconds for up to 10 minutes (20 attempts).  The retry stops automatically on the
first successful fetch; the regular 15-minute timer continues independently.

---

## Lightning risk panel

Derived from the same Open-Meteo fetch as the weather data (no separate API call).
Full width, hidden by default — tap **⚡ Lightning** to show it.

| Level | Trigger |
|-------|---------|
| Low | Default — no elevated CAPE or thunderstorm code |
| Moderate | CAPE ≥ 500 J/kg  or  lightning potential ≥ 40 % |
| High | CAPE ≥ 1000 J/kg  or  lightning potential ≥ 70 % |
| Active | Current-hour WMO weather code is 95, 96, or 99 (thunderstorm) |

When **Active**, the panel background turns dark red as a visual alarm.

---

## Panel toggles

Four buttons in the 44 px bar at the bottom control what is visible:

| Button | Hidden state | Shown state |
|--------|-------------|-------------|
| ⚡ Lightning | Yellow tint | Normal, "Hide lightning" |
| ▼ Weather | Green tint | Normal, "▲ Hide weather" |

When a panel is hidden its stretch is removed from the layout, giving more vertical
space to the gauge and histogram.  Both panels are hidden on startup.

---

## Fullscreen toggle

The **⛶ Fullscreen** button (44 px, bottom-right) switches between windowed and
fullscreen mode.  In fullscreen mode the OS taskbar and window decorations are
hidden, giving the instrument the full 800 × 480 display.  Pressing **⊞ Windowed**
restores the normal windowed view.

---

## Desktop shortcut

`pi-egt.desktop` in the project root is a standard `.desktop` launcher for the Pi OS
desktop environment.  To install it on the Pi:

```bash
cp ~/pi-egt/pi-egt.desktop ~/Desktop/
chmod +x ~/Desktop/pi-egt.desktop
```

The shortcut launches the app from the desktop without opening a terminal.

---

## Auto-start on boot

`~/.config/autostart/pi-egt.desktop` is installed on the Pi.  The XDG autostart
mechanism starts the app automatically whenever the desktop session loads (Pi OS
auto-logs in as `pi` by default, so this fires on every boot).

A `sleep 8` delay is built into the launch command to give the display server time
to finish initialising before the app starts.

To disable auto-start:
```bash
rm ~/.config/autostart/pi-egt.desktop
```

---

## Project structure

```
Pi-EGT/
├── main.py                        Entry point; --mock flag; dark Qt palette
├── pi-egt.desktop                 Desktop shortcut (copy to ~/Desktop/ on Pi)
├── requirements.txt
├── docs/
│   ├── notes.md                   Hardware design notes, PCB, BOM
│   └── software.md                This file
└── pi_egt/
    ├── config.py                  All constants + user config load/save
    ├── sensors/
    │   ├── max31855.py            SPI reader / sawtooth mock
    │   ├── ds18b20.py             1-Wire reader / sawtooth mock; sensor_count property
    │   └── buzzer.py              GPIO buzzer / no-op mock
    ├── network/
    │   ├── connectivity.py        TCP reachability check
    │   ├── weather.py             Open-Meteo API client (weather + geocoding)
    │   ├── lightning.py           Lightning risk assessment from weather data
    │   └── fetch_thread.py        One-shot QThread for non-blocking fetch
    └── ui/
        ├── main_window.py         QMainWindow — vertical layout, timers, signal wiring
        └── widgets/
            ├── egt_gauge.py       Circular analog gauge (QPainter)
            ├── histogram.py       15-minute scrolling EGT chart (QPainter)
            ├── temp_tile.py       Digital ambient temperature tile
            ├── weather_panel.py   Compact today-only weather display
            ├── lightning_panel.py Lightning risk level display
            ├── setup_dialog.py    EGT range + alarm + mock mode configuration
            └── location_dialog.py City search + selection dialog
```

---

## Pi configuration requirements

The following must be enabled in `/boot/firmware/config.txt` before the hardware
sensors will work:

```ini
dtparam=spi=on        # MAX31855 thermocouple
dtoverlay=w1-gpio     # DS18B20 1-Wire sensors
```

A reboot is required after enabling these overlays.

---

## Dependencies

| Package | Purpose | Pi only? |
|---------|---------|----------|
| `PyQt5 ≥ 5.15` | UI framework | No |
| `requests ≥ 2.28` | Weather API HTTP | No |
| `spidev ≥ 3.5` | MAX31855 SPI | Yes |
| `RPi.GPIO ≥ 0.7` | Buzzer GPIO | Yes |
