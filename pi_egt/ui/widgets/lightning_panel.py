from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QLabel, QVBoxLayout, QWidget

from pi_egt.network.lightning import LightningRisk

_LEVEL_COLOR = {
    'low':      '#27ae60',
    'moderate': '#f39c12',
    'high':     '#e67e22',
    'active':   '#e74c3c',
}
_LEVEL_ICON = {
    'low':      '⚡',
    'moderate': '⚡',
    'high':     '⚡⚡',
    'active':   '⚡⚡⚡',
}
_NORMAL_STYLE = '''
    LightningPanel {
        background-color: #16213e;
        border: 1px solid #0f3460;
        border-radius: 6px;
    }
'''
_ALARM_STYLE = '''
    LightningPanel {
        background-color: #2a0a0a;
        border: 1px solid #e74c3c;
        border-radius: 6px;
    }
'''


class LightningPanel(QWidget):
    """Displays lightning storm risk level derived from Open-Meteo CAPE / weather codes."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(_NORMAL_STYLE)
        self._build()

    def _build(self) -> None:
        v = QVBoxLayout(self)
        v.setContentsMargins(10, 8, 10, 8)
        v.setSpacing(4)

        hdr = QLabel('LIGHTNING RISK')
        hdr.setAlignment(Qt.AlignCenter)
        hdr.setStyleSheet('color:#778; font-size:14px; font-weight:bold;')
        v.addWidget(hdr)

        self._icon_lbl = QLabel('⚡')
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        self._icon_lbl.setStyleSheet('font-size:34px;')
        v.addWidget(self._icon_lbl)

        self._level_lbl = QLabel('—')
        self._level_lbl.setAlignment(Qt.AlignCenter)
        self._level_lbl.setStyleSheet('color:#555; font-size:22px; font-weight:bold;')
        v.addWidget(self._level_lbl)

        self._desc_lbl = QLabel('')
        self._desc_lbl.setAlignment(Qt.AlignCenter)
        self._desc_lbl.setStyleSheet('color:#778; font-size:14px;')
        self._desc_lbl.setWordWrap(True)
        v.addWidget(self._desc_lbl)

    # ── Public API ────────────────────────────────────────────────────────────

    def update_risk(self, risk: LightningRisk) -> None:
        color = _LEVEL_COLOR.get(risk.level, '#555')
        icon = _LEVEL_ICON.get(risk.level, '⚡')

        self._icon_lbl.setText(icon)
        self._level_lbl.setText(risk.level.upper())
        self._level_lbl.setStyleSheet(
            f'color:{color}; font-size:22px; font-weight:bold;'
        )
        self._desc_lbl.setText(risk.description)

        self.setStyleSheet(_ALARM_STYLE if risk.level == 'active' else _NORMAL_STYLE)

    def set_offline(self) -> None:
        self._level_lbl.setText('OFFLINE')
        self._level_lbl.setStyleSheet('color:#555; font-size:22px; font-weight:bold;')
        self._desc_lbl.setText('No network')
        self.setStyleSheet(_NORMAL_STYLE)
