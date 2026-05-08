from __future__ import annotations

import json
from pathlib import Path

# ── Hardware ────────────────────────────────────────────────────────────────
BUZZER_PIN = 17
SPI_BUS = 0
SPI_CE_EGT = 0          # CE0 → MAX31855 EGT sensor
SPI_SPEED_HZ = 1_000_000

# ── EGT display & alarm (runtime-mutable; also saved in user config) ─────────
EGT_MIN_DISPLAY = 0         # °C — gauge start
EGT_MAX_DISPLAY = 1000      # °C — gauge full-scale
EGT_ALARM_THRESHOLD = 800   # °C — buzzer trigger

# (temp_start, temp_end, hex_color)
EGT_ZONES = [
    (0,   600, '#27ae60'),   # green
    (600, 750, '#f39c12'),   # amber
    (750, 1000, '#e74c3c'),  # red
]

# ── History ──────────────────────────────────────────────────────────────────
HISTORY_SECONDS = 15 * 60   # 15 minutes of EGT data

# ── Poll intervals ───────────────────────────────────────────────────────────
SENSOR_POLL_FAST_MS = 250        # normal rate — 4 Hz
SENSOR_POLL_SLOW_MS = 1_000      # throttled rate when Pi CPU runs hot
WEATHER_POLL_MS = 15 * 60_000    # 15 min
CPU_TEMP_THROTTLE_C = 70.0       # °C — throttle above this
CPU_TEMP_RECOVER_C  = 65.0       # °C — restore fast rate below this (hysteresis)
AMB_SENSOR_TIMEOUT_S = 15.0      # seconds without data before hiding an ambient tile

# ── Lightning risk thresholds (CAPE in J/kg) ─────────────────────────────────
CAPE_MODERATE = 500
CAPE_HIGH = 1_000
LIGHTNING_POTENTIAL_MODERATE = 40   # percent
LIGHTNING_POTENTIAL_HIGH = 70       # percent

# ── Default location (used if no user config saved) ──────────────────────────
DEFAULT_LOCATION: dict = {
    'name': 'Hämeenlinna, Finland',
    'lat': 61.0004,
    'lon': 24.4606,
}

# ── Mock mode (set to True via --mock CLI flag) ──────────────────────────────
MOCK_SENSORS: bool = False

# ── User config file ─────────────────────────────────────────────────────────
_CONFIG_DIR = Path.home() / '.pi_egt'
_CONFIG_FILE = _CONFIG_DIR / 'config.json'


def load_user_config() -> dict:
    global EGT_MIN_DISPLAY, EGT_MAX_DISPLAY, EGT_ALARM_THRESHOLD
    defaults: dict = {
        'location': DEFAULT_LOCATION,
        'egt_min': EGT_MIN_DISPLAY,
        'egt_max': EGT_MAX_DISPLAY,
        'alarm': EGT_ALARM_THRESHOLD,
    }
    if _CONFIG_FILE.exists():
        try:
            with open(_CONFIG_FILE) as f:
                saved = json.load(f)
            defaults.update(saved)
        except Exception:
            pass
    # Apply persisted EGT settings to module-level variables
    EGT_MIN_DISPLAY = int(defaults['egt_min'])
    EGT_MAX_DISPLAY = int(defaults['egt_max'])
    EGT_ALARM_THRESHOLD = int(defaults['alarm'])
    return defaults


def save_user_config(data: dict) -> None:
    _CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    with open(_CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=2)
