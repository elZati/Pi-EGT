from __future__ import annotations

import os
import sys

_HAS_GPIO = sys.platform == 'linux' and os.path.exists('/dev/gpiomem')

if _HAS_GPIO:
    import RPi.GPIO as GPIO  # type: ignore


class Buzzer:
    """
    Active-buzzer driver via NPN transistor on a BCM GPIO pin.
    No-ops silently when running off-Pi.
    """

    def __init__(self, pin: int) -> None:
        self._pin = pin
        self._mock = not _HAS_GPIO
        self._active = False
        if not self._mock:
            GPIO.setmode(GPIO.BCM)
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)

    @property
    def active(self) -> bool:
        return self._active

    def on(self) -> None:
        if self._active:
            return
        self._active = True
        if not self._mock:
            GPIO.output(self._pin, GPIO.HIGH)

    def off(self) -> None:
        if not self._active:
            return
        self._active = False
        if not self._mock:
            GPIO.output(self._pin, GPIO.LOW)

    def cleanup(self) -> None:
        self.off()
        if not self._mock:
            GPIO.cleanup(self._pin)
