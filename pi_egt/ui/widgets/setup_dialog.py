from __future__ import annotations

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QDialog, QFrame,
    QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget,
)

_DARK = 'background-color:#0d0d1a; color:#ffffff;'
_PANEL = 'background-color:#16213e; border:1px solid #0f3460; border-radius:8px;'

_BTN = '''
    QPushButton {{
        background-color: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 6px;
        font-size: {fs}px;
        font-weight: bold;
    }}
    QPushButton:pressed {{ background-color: {bg_p}; }}
'''


def _style(bg='#1a2a4a', fg='#ffffff', border='#0f3460', bg_p='#0f3460', fs=16) -> str:
    return _BTN.format(bg=bg, fg=fg, border=border, bg_p=bg_p, fs=fs)


class _SettingRow(QWidget):
    """
    Touch-friendly integer setting: large [-] value [+] row.
    Step is applied on each button press; long-press not needed on a touchscreen.
    """

    def __init__(
        self,
        label: str,
        value: int,
        min_val: int,
        max_val: int,
        step: int,
        unit: str = '°C',
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._min = min_val
        self._max = max_val
        self._step = step
        self._value = max(min_val, min(max_val, value))

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        # Row label
        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet('color:#aabbcc; font-size:12px; font-weight:bold;')
        root.addWidget(lbl)

        # Control row: [-] VALUE [+]
        ctrl = QHBoxLayout()
        ctrl.setSpacing(8)

        self._minus = QPushButton('−')
        self._minus.setFixedSize(56, 56)
        self._minus.setStyleSheet(_style(bg='#1a2a4a', fg='#aabbcc', border='#0f3460', bg_p='#0a1020'))
        self._minus.clicked.connect(self._decrement)

        self._val_lbl = QLabel(f'{self._value} {unit}')
        self._val_lbl.setAlignment(Qt.AlignCenter)
        self._val_lbl.setStyleSheet('color:#ffffff; font-size:22px; font-weight:bold; min-width:120px;')

        self._plus = QPushButton('+')
        self._plus.setFixedSize(56, 56)
        self._plus.setStyleSheet(_style(bg='#1a2a4a', fg='#aabbcc', border='#0f3460', bg_p='#0a1020'))
        self._plus.clicked.connect(self._increment)

        ctrl.addStretch()
        ctrl.addWidget(self._minus)
        ctrl.addWidget(self._val_lbl)
        ctrl.addWidget(self._plus)
        ctrl.addStretch()
        root.addLayout(ctrl)

        self._unit = unit
        self._update_buttons()

    # ── Value access ──────────────────────────────────────────────────────────

    @property
    def value(self) -> int:
        return self._value

    @value.setter
    def value(self, v: int) -> None:
        self._value = max(self._min, min(self._max, v))
        self._val_lbl.setText(f'{self._value} {self._unit}')
        self._update_buttons()

    # ── Slots ─────────────────────────────────────────────────────────────────

    def _increment(self) -> None:
        self.value = self._value + self._step

    def _decrement(self) -> None:
        self.value = self._value - self._step

    def _update_buttons(self) -> None:
        self._minus.setEnabled(self._value > self._min)
        self._plus.setEnabled(self._value < self._max)


class _ToggleRow(QWidget):
    """Touch-friendly boolean toggle with label and full-width button."""

    def __init__(self, label: str, value: bool, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._value = value

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 10, 12, 10)
        root.setSpacing(6)

        lbl = QLabel(label)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet('color:#aabbcc; font-size:12px; font-weight:bold;')
        root.addWidget(lbl)

        self._btn = QPushButton()
        self._btn.setFixedHeight(56)
        self._btn.clicked.connect(self._toggle)
        root.addWidget(self._btn)
        self._refresh()

    @property
    def value(self) -> bool:
        return self._value

    def _toggle(self) -> None:
        self._value = not self._value
        self._refresh()

    def _refresh(self) -> None:
        if self._value:
            self._btn.setText('●  ENABLED')
            self._btn.setStyleSheet(_style(bg='#1a3a2a', fg='#7dcca0', border='#2e6b4f', bg_p='#0f2a1a'))
        else:
            self._btn.setText('○  DISABLED')
            self._btn.setStyleSheet(_style(bg='#1a1a2e', fg='#556677', border='#2d2d40', bg_p='#0d0d1a'))


class SetupDialog(QDialog):
    """
    Modal setup dialog for EGT gauge range, alarm threshold and mock mode.
    Access .egt_min / .egt_max / .alarm / .mock_sensors after exec_() == Accepted.
    """

    def __init__(
        self,
        egt_min: int,
        egt_max: int,
        alarm: int,
        mock_sensors: bool,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle('EGT Setup')
        self.setModal(True)
        self.setStyleSheet(f'QDialog {{ {_DARK} }}')
        self._build(egt_min, egt_max, alarm, mock_sensors)

    def _build(self, egt_min: int, egt_max: int, alarm: int, mock_sensors: bool) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        title = QLabel('EGT SETUP')
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('color:#aabbcc; font-size:13px; font-weight:bold; letter-spacing:2px;')
        root.addWidget(title)

        # ── Gauge range section ───────────────────────────────────────────────
        self._min_row = _SettingRow(
            'Gauge Min  (°C)', egt_min,
            min_val=0, max_val=500, step=50,
        )
        self._min_row.setStyleSheet(_PANEL)
        root.addWidget(self._min_row)

        self._max_row = _SettingRow(
            'Gauge Max  (°C)', egt_max,
            min_val=200, max_val=1200, step=50,
        )
        self._max_row.setStyleSheet(_PANEL)
        root.addWidget(self._max_row)

        # ── Alarm section ─────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet('color:#0f3460;')
        root.addWidget(sep)

        self._alarm_row = _SettingRow(
            'Alarm Threshold  (°C)', alarm,
            min_val=100, max_val=1200, step=10,
        )
        self._alarm_row.setStyleSheet(_PANEL)
        root.addWidget(self._alarm_row)

        alarm_note = QLabel('Buzzer activates when EGT exceeds this value.')
        alarm_note.setAlignment(Qt.AlignCenter)
        alarm_note.setStyleSheet('color:#556; font-size:10px;')
        root.addWidget(alarm_note)

        # ── Mock sensor section ───────────────────────────────────────────────
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setStyleSheet('color:#0f3460;')
        root.addWidget(sep2)

        self._mock_row = _ToggleRow('Simulate Sensors (Mock Mode)', mock_sensors)
        self._mock_row.setStyleSheet(_PANEL)
        root.addWidget(self._mock_row)

        mock_note = QLabel('Sawtooth waveform — use when sensors are not connected.')
        mock_note.setAlignment(Qt.AlignCenter)
        mock_note.setStyleSheet('color:#556; font-size:10px;')
        root.addWidget(mock_note)

        # ── Buttons ───────────────────────────────────────────────────────────
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.HLine)
        sep3.setStyleSheet('color:#0f3460;')
        root.addWidget(sep3)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        cancel = QPushButton('Cancel')
        cancel.setFixedHeight(48)
        cancel.setStyleSheet(_style(bg='#1a1a2e', fg='#778', border='#333', bg_p='#0d0d1a'))
        cancel.clicked.connect(self.reject)

        save = QPushButton('Save')
        save.setFixedHeight(48)
        save.setStyleSheet(_style(bg='#1a3a2a', fg='#7dcca0', border='#2e6b4f', bg_p='#0f2a1a', fs=16))
        save.clicked.connect(self._validate_and_accept)

        btn_row.addWidget(cancel)
        btn_row.addWidget(save)
        root.addLayout(btn_row)

    # ── Validation ────────────────────────────────────────────────────────────

    def _validate_and_accept(self) -> None:
        # Ensure min < max with at least 100° gap
        if self._min_row.value >= self._max_row.value - 100:
            self._max_row.value = self._min_row.value + 100
        # Clamp alarm to gauge range
        if self._alarm_row.value > self._max_row.value:
            self._alarm_row.value = self._max_row.value
        if self._alarm_row.value < self._min_row.value:
            self._alarm_row.value = self._min_row.value
        self.accept()

    # ── Result accessors ──────────────────────────────────────────────────────

    @property
    def egt_min(self) -> int:
        return self._min_row.value

    @property
    def egt_max(self) -> int:
        return self._max_row.value

    @property
    def alarm(self) -> int:
        return self._alarm_row.value

    @property
    def mock_sensors(self) -> bool:
        return self._mock_row.value
