from __future__ import annotations

import traceback

from PyQt5.QtCore import QThread, pyqtSignal

from pi_egt.network.connectivity import is_connected
from pi_egt.network.weather import fetch_forecast, WeatherData
from pi_egt.network.lightning import assess_risk, LightningRisk


class FetchThread(QThread):
    """
    One-shot QThread that fetches weather + lightning risk for a location.
    Create a new instance per fetch; connect signals before calling start().
    """

    weather_ready = pyqtSignal(object)    # WeatherData
    lightning_ready = pyqtSignal(object)  # LightningRisk
    offline = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, location: dict, parent=None) -> None:
        super().__init__(parent)
        self._location = location

    def run(self) -> None:
        if not is_connected():
            self.offline.emit()
            return
        try:
            data: WeatherData = fetch_forecast(
                self._location['lat'],
                self._location['lon'],
                self._location['name'],
            )
            self.weather_ready.emit(data)
            risk: LightningRisk = assess_risk(data)
            self.lightning_ready.emit(risk)
        except Exception as exc:
            traceback.print_exc()   # visible in /tmp/pi_egt.log
            self.error.emit(str(exc))
