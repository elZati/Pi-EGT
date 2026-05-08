from __future__ import annotations

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QVBoxLayout, QWidget,
)

from pi_egt.network.weather import WeatherData, WMO_DESCRIPTIONS, WMO_ICONS

_STYLE = '''
    WeatherPanel {
        background-color: #16213e;
        border: 1px solid #0f3460;
        border-radius: 6px;
    }
'''


class WeatherPanel(QWidget):
    """
    Compact today-only weather panel: icon, description, min/max temperature.
    Emits location_change_requested when the settings button is tapped.
    """

    location_change_requested = pyqtSignal()

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_STYLE)
        self._build()

    def _build(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # ── Header row ────────────────────────────────────────────────────────
        hdr = QHBoxLayout()
        self._loc_lbl = QLabel('WEATHER')
        self._loc_lbl.setStyleSheet('color:#778; font-size:15px; font-weight:bold;')
        self._loc_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        btn = QPushButton('⚙')
        btn.setFixedSize(36, 36)
        btn.setToolTip('Change location')
        btn.setStyleSheet(
            'QPushButton{color:#778;border:none;font-size:18px;background:transparent;}'
            'QPushButton:pressed{color:#aaa;}'
        )
        btn.clicked.connect(self.location_change_requested)
        hdr.addWidget(self._loc_lbl)
        hdr.addWidget(btn)
        root.addLayout(hdr)

        # ── Weather icon + description ────────────────────────────────────────
        self._icon_lbl = QLabel('—')
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet('font-size:40px;')
        root.addWidget(self._icon_lbl)

        self._desc_lbl = QLabel('No data')
        self._desc_lbl.setAlignment(Qt.AlignCenter)
        self._desc_lbl.setStyleSheet('color:#ccc; font-size:16px;')
        self._desc_lbl.setWordWrap(True)
        root.addWidget(self._desc_lbl)

        # ── Min / Max ─────────────────────────────────────────────────────────
        mm = QHBoxLayout()
        self._min_lbl = QLabel('—')
        self._min_lbl.setAlignment(Qt.AlignCenter)
        self._min_lbl.setStyleSheet('color:#6af; font-size:22px; font-weight:bold;')

        sep = QLabel('/')
        sep.setAlignment(Qt.AlignCenter)
        sep.setStyleSheet('color:#555; font-size:22px;')

        self._max_lbl = QLabel('—')
        self._max_lbl.setAlignment(Qt.AlignCenter)
        self._max_lbl.setStyleSheet('color:#fa8; font-size:22px; font-weight:bold;')

        mm.addWidget(self._min_lbl)
        mm.addWidget(sep)
        mm.addWidget(self._max_lbl)
        root.addLayout(mm)

    # ── Public API ────────────────────────────────────────────────────────────

    def update_weather(self, data: WeatherData) -> None:
        city = data.location_name.split(',')[0]
        self._loc_lbl.setText(city.upper())

        code = data.today.weather_code if data.today else data.current_code
        self._icon_lbl.setText(WMO_ICONS.get(code, '?'))
        self._desc_lbl.setText(WMO_DESCRIPTIONS.get(code, ''))

        if data.today:
            self._min_lbl.setText(f'{data.today.temp_min:.0f}°C')
            self._max_lbl.setText(f'{data.today.temp_max:.0f}°C')
        else:
            self._min_lbl.setText(f'{data.current_temp:.0f}°C')
            self._max_lbl.setText('—')

    def set_offline(self) -> None:
        self._loc_lbl.setText('WEATHER')
        self._icon_lbl.setText('—')
        self._desc_lbl.setText('No network')
        self._min_lbl.setText('—')
        self._max_lbl.setText('—')
