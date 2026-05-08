from __future__ import annotations

import math
import os
import sys

from pi_egt import config

# Auto-detect Pi: SPI device node present
_HAS_SPI = sys.platform == 'linux' and os.path.exists('/dev/spidev0.0')

if _HAS_SPI:
    import spidev  # type: ignore


class MAX31855:
    """
    SPI reader for the MAX31855 thermocouple amplifier.
    Falls back to a sine-wave mock when running off-Pi.
    """

    # Sawtooth: 0→1000 °C over 120 s (8.33 °C/s at 1 Hz poll)
    _MOCK_MAX = 1000.0
    _MOCK_STEP = _MOCK_MAX / 120.0

    def __init__(self, bus: int, ce: int, speed_hz: int = 1_000_000) -> None:
        self._bus = bus
        self._ce = ce
        self._speed = speed_hz
        self._mock = config.MOCK_SENSORS or not _HAS_SPI
        self._mock_val = 0.0  # sawtooth accumulator
        if not self._mock:
            self._spi: spidev.SpiDev = spidev.SpiDev()

    # ── Public API ───────────────────────────────────────────────────────────

    def read_celsius(self) -> float | None:
        """Return thermocouple temperature in °C, or None on fault."""
        if self._mock:
            return self._mock_reading()
        return self._hw_reading()

    # ── Hardware path ─────────────────────────────────────────────────────────

    def _hw_reading(self) -> float | None:
        self._spi.open(self._bus, self._ce)
        self._spi.max_speed_hz = self._speed
        self._spi.mode = 1
        raw_bytes = self._spi.readbytes(4)
        self._spi.close()

        raw = (raw_bytes[0] << 24 | raw_bytes[1] << 16
               | raw_bytes[2] << 8 | raw_bytes[3])

        if raw & 0x7:
            return None  # open / short-to-VCC / short-to-GND fault

        temp_raw = (raw >> 18) & 0x3FFF
        if temp_raw & 0x2000:   # sign-extend 14-bit two's complement
            temp_raw -= 0x4000
        return temp_raw * 0.25

    # ── Mock path ─────────────────────────────────────────────────────────────

    def _mock_reading(self) -> float:
        val = self._mock_val
        self._mock_val = (self._mock_val + self._MOCK_STEP) % self._MOCK_MAX
        return val
