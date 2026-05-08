from __future__ import annotations

import glob
import os

from pi_egt import config

_HAS_1WIRE = os.path.exists('/sys/bus/w1/devices')


class DS18B20:
    """
    Reader for DS18B20 sensors on the 1-Wire bus (GPIO4 / sysfs).
    Falls back to gentle sine-wave mocks when running off-Pi.
    """

    # Sawtooth: 0→100 °C over 60 s (~1.67 °C/s at 1 Hz poll), offset per sensor
    _MOCK_MAX = 100.0
    _MOCK_STEP = _MOCK_MAX / 60.0
    _MOCK_OFFSETS = [0.0, _MOCK_MAX / 2]   # sensor 2 starts mid-ramp

    def __init__(self) -> None:
        self._mock = config.MOCK_SENSORS or not _HAS_1WIRE
        self._paths: list[str] = []
        self._mock_vals = list(self._MOCK_OFFSETS)
        if not self._mock:
            self._discover()

    # ── Public API ───────────────────────────────────────────────────────────

    @property
    def sensor_count(self) -> int:
        """Number of sensors currently providing data (2 in mock, discovered count in hardware)."""
        if self._mock:
            return 2
        return len(self._paths)

    def read_all_celsius(self) -> list[float | None]:
        """Return temperature list, one entry per discovered sensor (None = read error)."""
        if self._mock:
            return self._mock_readings()
        if not self._paths:
            self._discover()  # retry on every poll until sensors appear (supports hot-plug)
        return self._hw_readings()

    # ── Hardware path ─────────────────────────────────────────────────────────

    def _discover(self) -> None:
        self._paths = sorted(glob.glob('/sys/bus/w1/devices/28-*/temperature'))

    def _hw_readings(self) -> list[float | None]:
        results: list[float | None] = []
        for path in self._paths:
            try:
                with open(path) as f:
                    results.append(int(f.read().strip()) / 1000.0)
            except OSError:
                results.append(None)
        return results

    # ── Mock path ─────────────────────────────────────────────────────────────

    def _mock_readings(self) -> list[float | None]:
        readings: list[float | None] = []
        for i in range(len(self._mock_vals)):
            readings.append(self._mock_vals[i])
            self._mock_vals[i] = (self._mock_vals[i] + self._MOCK_STEP) % self._MOCK_MAX
        return readings
