from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget


class TempTile(QWidget):
    """
    Compact digital temperature readout tile for a DS18B20 sensor.
    Displays sensor label, large temperature value, and °C unit.
    """

    _STYLE_BASE = '''
        TempTile {{
            background-color: #16213e;
            border: 1px solid #0f3460;
            border-radius: 6px;
        }}
    '''

    def __init__(self, label: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(self._STYLE_BASE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(0)

        self._label_w = QLabel(label.upper())
        self._label_w.setAlignment(Qt.AlignCenter)
        self._label_w.setStyleSheet('color:#778; font-size:15px; font-weight:bold;')

        self._value_w = QLabel('---')
        self._value_w.setAlignment(Qt.AlignCenter)
        self._value_w.setStyleSheet('color:#fff; font-size:42px; font-weight:bold;')

        self._unit_w = QLabel('°C')
        self._unit_w.setAlignment(Qt.AlignCenter)
        self._unit_w.setStyleSheet('color:#aaa; font-size:15px;')

        layout.addWidget(self._label_w)
        layout.addWidget(self._value_w)
        layout.addWidget(self._unit_w)

    def set_temperature(self, temp: float | None) -> None:
        if temp is None:
            self._value_w.setText('---')
            self._value_w.setStyleSheet('color:#555; font-size:42px; font-weight:bold;')
        else:
            self._value_w.setText(f'{temp:.1f}')
            self._value_w.setStyleSheet('color:#fff; font-size:42px; font-weight:bold;')
