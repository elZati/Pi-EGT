# Pi-EGT Boat Instrument — Hardware Notes

## Overview

Raspberry Pi 3 based boat instrument panel displaying EGT (exhaust gas temperature),
coolant temperature, and ambient temperatures. Includes alarm buzzer for EGT threshold.

---

## Power Supply

### LM2596 Buck Converter
- Input: 10–15V boat battery
- Output: 5V / 3A
- IC: LM2596S-5.0 (TO-263 SMD, fixed 5V)
- Switching frequency: 150kHz
- Input protection diode: SS34 on battery+ input (reverse polarity protection)

### LC Post Filter
- Inductor: 4.7µH (Wurth 7440530047)
- Capacitor: 100µF 10V tantalum D case
- Purpose: reduces LM2596 switching ripple before Pi supply

### Pi Power Connection
- Feed 5V to Pi GPIO header **pin 2** or **pin 4**
- GND to any Pi GND pin
- 100nF decoupling cap + 10µF bulk cap at Pi header pins
- Do NOT use micro USB for power in this installation

---

## GPIO Pin Assignments

| GPIO (BCM) | Physical pin | Function |
|-----------|--------------|---------|
| GPIO4 | pin 7 | 1-Wire bus — DS18B20 temperature sensors |
| GPIO7 | pin 26 | SPI CE1 — MAX31855 #2 chip select |
| GPIO8 | pin 24 | SPI CE0 — MAX31855 #1 chip select |
| GPIO9 | pin 21 | SPI MISO — shared by both MAX31855 |
| GPIO11 | pin 23 | SPI SCLK — shared by both MAX31855 |
| GPIO17 | pin 11 | Buzzer driver output |

---

## Sensors

### DS18B20 — 1-Wire Temperature Sensors
- Two sensors on a single 1-Wire bus
- Protocol: Dallas 1-Wire
- Power: 3.3V from Pi header pin 1 (3-wire mode recommended for marine)
- Data pin: GPIO4 (Pi physical pin 7)
- Pull-up: single 4.7kΩ resistor from DQ to 3.3V (shared by all sensors)
- Connected via 3-position Phoenix Contact screw terminal (VDD / GND / DQ)

**Enable 1-Wire on Pi — add to `/boot/config.txt`:**
```
dtoverlay=w1-gpio
```

**Read temperature:**
```python
# Sensors appear as folders under /sys/bus/w1/devices/
# Named like: 28-xxxxxxxxxxxx
# Temperature in millidegrees C

import glob

sensor_paths = glob.glob('/sys/bus/w1/devices/28-*/temperature')

for path in sensor_paths:
    with open(path) as f:
        temp_mc = int(f.read())
        temp_c = temp_mc / 1000.0
        print(f'{path}: {temp_c:.1f}°C')
```

---

### MAX31855 — Thermocouple Amplifier (EGT + Coolant)
- Two MAX31855 boards (Adafruit breakout)
- Protocol: SPI (read-only, MISO only — no MOSI needed)
- Power: 3.3V
- MAX31855 #1 (EGT): CS on GPIO8 (CE0)
- MAX31855 #2 (Coolant/second EGT): CS on GPIO7 (CE1)
- SCLK: GPIO11 (shared)
- MISO: GPIO9 (shared)
- SPI clock speed: 1MHz recommended (tolerant of long cable run)

**Remote sensor connection:**
- Sensor located at aft of boat
- Connected to Pi hat via Molex 8-pin connector
- Series resistors on Pi hat side: 33Ω on CLK, CS1, CS2, MISO (GPIO protection)
- Common mode chokes on sensor side (already on Adafruit board)
- Cable: twist signal pairs with GND for noise rejection

**Molex 8-pin connector pinout:**

| Pin | Signal | Notes |
|-----|--------|-------|
| 8 | spare | — |
| 7 | 3.3V | Power |
| 6 | 3.3V | Second power pin |
| 5 | TH_3V0 | MAX31855 3V output — leave unconnected on Pi side |
| 4 | GND | Ground |
| 3 | TH_DO / MISO | Data from sensor |
| 2 | TH_CS / CE0 | Chip select — MAX31855 #1 |
| 1 | TH_CLK | SPI clock |

**Read thermocouple with Python:**
```python
import spidev

spi = spidev.SpiDev()
spi.open(0, 0)          # bus 0, CE0 — MAX31855 #1
spi.max_speed_hz = 1000000
spi.mode = 1

def read_max31855(cs):
    spi.open(0, cs)
    raw = spi.readbytes(4)
    spi.close()
    value = (raw[0] << 24) | (raw[1] << 16) | (raw[2] << 8) | raw[3]
    if value & 0x7:
        return None     # fault detected
    temp_raw = (value >> 18) & 0x3FFF
    if temp_raw & 0x2000:
        temp_raw -= 0x4000
    return temp_raw * 0.25

egt_temp   = read_max31855(0)   # CE0 — EGT sensor
cool_temp  = read_max31855(1)   # CE1 — coolant sensor
```

---

## Buzzer Alarm

- Buzzer: Same Sky CMI-1295-0585T (5V active, internally driven, through-hole, 5mm pin pitch)
- Driver: BC817-25 NPN transistor (SOT-23)
- GPIO: GPIO17 (Pi physical pin 11)
- Circuit: GPIO17 → 1kΩ R_BASE → transistor base, 10kΩ R_PULL to GND, SS14 flyback diode across buzzer
- Power: 5V rail

**Buzzer control:**
```python
import RPi.GPIO as GPIO

BUZZER_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

def buzzer_on():
    GPIO.output(BUZZER_PIN, GPIO.HIGH)

def buzzer_off():
    GPIO.output(BUZZER_PIN, GPIO.LOW)
```

**EGT alarm example:**
```python
EGT_ALARM_THRESHOLD = 800   # degrees C — adjust to suit engine

def check_egt_alarm(egt_temp):
    if egt_temp is not None and egt_temp > EGT_ALARM_THRESHOLD:
        buzzer_on()
    else:
        buzzer_off()
```

---

## Display

- 5 inch DSI touchscreen connected to Pi DSI port
- Draws 5V from Pi's 5V rail
- DSI interface logic handled internally by Pi
- No extra power wiring needed for display

---

## BOM Summary (DigiKey part numbers)

| Ref | Part number | Qty | Description |
|-----|------------|-----|-------------|
| U1 | LM2596S-5.0/NOPB | 1 | DC-DC regulator IC |
| L1 | SRR1260-330M | 1 | 33µH main inductor |
| L2 | 7440530047 | 1 | 4.7µH post filter inductor |
| D1, D2 | SS34-HF | 2 | Schottky diode 3A/40V |
| D3 | SS14-E3/61T | 1 | Flyback diode buzzer |
| Q1 | BC817-25LT1G | 1 | NPN transistor buzzer driver |
| F1 | 3568-15 | 1 | ATO fuse holder 5A |
| BZ1 | CMI-1295-0585T | 1 | 5V active buzzer |
| C_OUT, C_POST | T491D107K010AT | 2 | 100µF 10V tantalum D case |
| C1-C3, C6 | CC0805KRX7R9BB104 | 4 | 100nF X7R 0805 |
| R4 | RC0805FR-074K7L | 1 | 4.7kΩ 1-Wire pull-up |
| R5,R6,R7,R10 | RC0805FR-0733RL | 4 | 33Ω SPI series resistors |
| R_BASE, R_ONOFF | RC0805FR-071KL | 2 | 1kΩ 0805 |
| R_PULL, R8 | RC0805FR-0710KL | 2 | 10kΩ 0805 |
| J_TEMP | 1751251 | 1 | Phoenix 3-pos 3.5mm terminal |
| J_PWR | 1715022 | 1 | Phoenix 2-pos 5mm terminal |

---

## PCB Design Rules (PCBWay standard 2-layer)

| Parameter | Value |
|-----------|-------|
| Min clearance | 0.127mm |
| Min track width | 0.127mm |
| Min via diameter | 0.6mm |
| Min via drill | 0.3mm |
| Min hole to hole | 0.5mm |
| Hole clearance | 0.25mm |
| Copper to edge | 0.3mm |
| Min text height | 1.0mm |
| Min text stroke | 0.15mm |

### Recommended track widths

| Net | Width |
|-----|-------|
| 5V power | 2.0mm |
| 3.3V power | 1.0mm |
| Signal (SPI, 1-Wire) | 0.25mm |
| LM2596 switch node | 2.5mm (short as possible) |

### Recommended via sizes

| Type | Outer dia | Drill |
|------|----------|-------|
| Signal | 0.8mm | 0.4mm |
| Power / GND stitch | 1.0mm | 0.5mm |
| LM2596 thermal (×6) | 1.0mm | 0.5mm |

---

## Useful Libraries for Pi Development

```bash
pip install RPi.GPIO spidev w1thermsensor adafruit-circuitpython-max31855
```

- `RPi.GPIO` — GPIO control (buzzer)
- `spidev` — raw SPI access (MAX31855)
- `w1thermsensor` — DS18B20 1-Wire (simpler than reading sysfs directly)
- `adafruit-circuitpython-max31855` — Adafruit MAX31855 library

---

## Notes

- Conformal coat all PCBs after assembly — marine salt air environment
- Enable Pi hardware watchdog in software for unattended operation
- Keep SPI clock at 1MHz for long cable run to aft sensor
- LM2596 switch node (pin 2 / inductor / catch diode) — keep traces short and wide
- Keep feedback trace (LM2596 pin 4) away from inductor
- LM2596 TO-263 tab needs copper pour + 6 thermal vias for heat dissipation
- Ground plane on B.Cu flood filled with GND net
- Stitch F.Cu and B.Cu ground planes with vias throughout board
