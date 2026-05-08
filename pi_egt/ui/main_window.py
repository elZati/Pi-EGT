from __future__ import annotations

import os
import sys
import time

from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtWidgets import (
    QDialog, QHBoxLayout, QMainWindow, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from pi_egt import config
from pi_egt.sensors.max31855 import MAX31855
from pi_egt.sensors.ds18b20 import DS18B20
from pi_egt.sensors.buzzer import Buzzer
from pi_egt.network.fetch_thread import FetchThread
from pi_egt.network.weather import WeatherData
from pi_egt.network.lightning import LightningRisk
from pi_egt.ui.widgets.egt_gauge import EGTGauge
from pi_egt.ui.widgets.histogram import EGTHistogram
from pi_egt.ui.widgets.temp_tile import TempTile
from pi_egt.ui.widgets.weather_panel import WeatherPanel
from pi_egt.ui.widgets.lightning_panel import LightningPanel
from pi_egt.ui.widgets.location_dialog import LocationDialog
from pi_egt.ui.widgets.setup_dialog import SetupDialog

# ── Touch-friendly button style ───────────────────────────────────────────────
_BTN_STYLE = '''
    QPushButton {{
        background-color: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 8px;
        font-size: 14px;
        font-weight: bold;
        padding: 0px;
    }}
    QPushButton:pressed {{
        background-color: {bg_press};
    }}
'''


def _btn_style(bg='#1a2a4a', fg='#aabbcc', border='#0f3460', bg_press='#0f3460') -> str:
    return _BTN_STYLE.format(bg=bg, fg=fg, border=border, bg_press=bg_press)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle('Pi-EGT — Boat Instrument')
        # Portrait mode: 480 × 800
        self.resize(480, 800)

        self._user_cfg = config.load_user_config()
        self._location: dict = self._user_cfg.get('location', config.DEFAULT_LOCATION)
        self._weather_visible = False    # hidden by default
        self._lightning_visible = False  # hidden by default

        # Apply saved mock mode (CLI --mock flag always wins)
        if not config.MOCK_SENSORS and self._user_cfg.get('mock_sensors', False):
            config.MOCK_SENSORS = True

        # Sensors
        self._egt = MAX31855(config.SPI_BUS, config.SPI_CE_EGT, config.SPI_SPEED_HZ)
        self._ds18b20 = DS18B20()
        self._buzzer = Buzzer(config.BUZZER_PIN)

        # Per-sensor timestamp of last valid reading (for timeout-based hiding)
        self._amb_last_data: list[float | None] = [None, None]

        self._build_ui()
        self._update_sensor_visibility()

        # Apply saved EGT range to gauge and histogram
        self._gauge.set_range(config.EGT_MIN_DISPLAY, config.EGT_MAX_DISPLAY, config.EGT_ALARM_THRESHOLD)
        self._histogram.set_range(config.EGT_MAX_DISPLAY)

        # Sensor poll — starts at fast rate; throttled dynamically by CPU temp
        self._throttled = False
        self._sensor_timer = QTimer(self)
        self._sensor_timer.timeout.connect(self._poll_sensors)
        self._sensor_timer.start(config.SENSOR_POLL_FAST_MS)

        # CPU temperature check — adjusts sensor poll rate every 10 s
        self._cpu_timer = QTimer(self)
        self._cpu_timer.timeout.connect(self._check_cpu_temp)
        self._cpu_timer.start(10_000)

        # Network fetch — 15 min regular refresh
        self._net_timer = QTimer(self)
        self._net_timer.timeout.connect(self._start_net_fetch)
        self._net_timer.start(config.WEATHER_POLL_MS)

        # Retry every 30 s when offline (up to 20 attempts ≈ 10 min)
        # Stops automatically on first successful fetch.
        self._net_retry_count = 0
        self._net_retry_timer = QTimer(self)
        self._net_retry_timer.timeout.connect(self._start_net_fetch)

        # First attempt after 10 s — gives WiFi time to connect on autostart
        QTimer.singleShot(10_000, self._start_net_fetch)

        self._fetch_thread: FetchThread | None = None

        # Hardware watchdog — keep Pi alive; feeds every 10 s (matches CPU timer)
        # /dev/watchdog times out after ~60 s if not fed → Pi reboots
        try:
            self._hw_watchdog = open('/dev/watchdog', 'wb', buffering=0)
        except OSError:
            self._hw_watchdog = None   # not on Pi, or watchdog not enabled

        # Software watchdog — restarts the process if sensor polling stalls
        self._last_poll_time = time.monotonic()
        self._sw_watchdog_timer = QTimer(self)
        self._sw_watchdog_timer.timeout.connect(self._check_sw_watchdog)
        self._sw_watchdog_timer.start(15_000)   # check every 15 s

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        central.setStyleSheet('background-color: #0d0d1a;')

        root = QVBoxLayout(central)
        root.setContentsMargins(4, 4, 4, 4)
        root.setSpacing(4)

        # EGT gauge — full width, dominant
        self._gauge = EGTGauge()
        self._gauge.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        root.addWidget(self._gauge, stretch=8)

        # EGT histogram — full width
        self._histogram = EGTHistogram(
            history_seconds=config.HISTORY_SECONDS,
            max_temp=float(config.EGT_MAX_DISPLAY),
        )
        self._histogram.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        root.addWidget(self._histogram, stretch=2)

        # Ambient temperature row — two tiles side by side, hidden when no sensors
        self._amb_widget = QWidget()
        self._amb_widget.setStyleSheet('background-color: transparent;')
        amb_row = QHBoxLayout(self._amb_widget)
        amb_row.setContentsMargins(0, 0, 0, 0)
        amb_row.setSpacing(4)
        self._amb_tiles: list[TempTile] = []
        for i in range(2):
            tile = TempTile(f'Ambient {i + 1}')
            tile.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            amb_row.addWidget(tile)
            self._amb_tiles.append(tile)
        root.addWidget(self._amb_widget, stretch=2)

        # Lightning panel — full width, hidden by default
        self._lightning = LightningPanel()
        self._lightning.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._lightning.setVisible(False)
        root.addWidget(self._lightning, stretch=2)

        # Weather panel — full width, hidden by default
        self._weather = WeatherPanel()
        self._weather.location_change_requested.connect(self._open_location_dialog)
        self._weather.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._weather.setVisible(False)
        root.addWidget(self._weather, stretch=2)

        # Button bar — fixed 44 px touch targets
        root.addLayout(self._build_buttons())

    # ── Button bar ────────────────────────────────────────────────────────────

    def _build_buttons(self) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(4)

        self._setup_btn = QPushButton('⚙  Setup')
        self._setup_btn.setFixedHeight(60)
        self._setup_btn.setStyleSheet(
            _btn_style(bg='#1a2a3a', fg='#aabbcc', border='#0f3460', bg_press='#0a1a2a')
        )
        self._setup_btn.clicked.connect(self._open_setup_dialog)

        # Lightning toggle — starts hidden (yellow tint = available to show)
        self._lightning_btn = QPushButton('⚡  Lightning')
        self._lightning_btn.setFixedHeight(60)
        self._lightning_btn.setStyleSheet(
            _btn_style(bg='#2a2a1a', fg='#cccc7d', border='#6b6b2e', bg_press='#1a1a0f')
        )
        self._lightning_btn.clicked.connect(self._toggle_lightning)

        # Weather toggle — starts hidden (green tint = available to show)
        self._toggle_btn = QPushButton('▼  Weather')
        self._toggle_btn.setFixedHeight(60)
        self._toggle_btn.setStyleSheet(
            _btn_style(bg='#1a3a2a', fg='#7dcca0', border='#2e6b4f', bg_press='#0f3460')
        )
        self._toggle_btn.clicked.connect(self._toggle_weather)

        # Fullscreen toggle
        self._fullscreen_btn = QPushButton('⛶  Fullscreen')
        self._fullscreen_btn.setFixedHeight(60)
        self._fullscreen_btn.setStyleSheet(_btn_style())
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)

        row.addWidget(self._setup_btn)
        row.addWidget(self._lightning_btn)
        row.addWidget(self._toggle_btn)
        row.addWidget(self._fullscreen_btn)

        return row

    # ── Sensor visibility ─────────────────────────────────────────────────────

    def _update_sensor_visibility(self) -> None:
        # Reset timestamps so timeout logic restarts cleanly after a sensor reinit.
        self._amb_last_data = [None, None]
        count = self._ds18b20.sensor_count
        # Mock mode: show all tiles immediately — mock data is always available.
        # Real mode: start hidden; _poll_sensors will show tiles when data arrives.
        visible = config.MOCK_SENSORS
        self._amb_widget.setVisible(visible)
        for i, tile in enumerate(self._amb_tiles):
            tile.setVisible(visible and i < count)

    # ── CPU temperature throttling ────────────────────────────────────────────

    @pyqtSlot()
    def _check_cpu_temp(self) -> None:
        self._feed_hw_watchdog()

        try:
            with open('/sys/class/thermal/thermal_zone0/temp') as f:
                cpu_c = int(f.read().strip()) / 1000.0
        except OSError:
            return  # not on Pi — always stay at fast rate

        if not self._throttled and cpu_c >= config.CPU_TEMP_THROTTLE_C:
            self._throttled = True
            self._sensor_timer.stop()
            self._sensor_timer.start(config.SENSOR_POLL_SLOW_MS)
        elif self._throttled and cpu_c <= config.CPU_TEMP_RECOVER_C:
            self._throttled = False
            self._sensor_timer.stop()
            self._sensor_timer.start(config.SENSOR_POLL_FAST_MS)

    def _feed_hw_watchdog(self) -> None:
        if self._hw_watchdog is not None:
            try:
                self._hw_watchdog.write(b'\x01')
            except OSError:
                pass

    # ── Software watchdog ─────────────────────────────────────────────────────

    @pyqtSlot()
    def _check_sw_watchdog(self) -> None:
        elapsed = time.monotonic() - self._last_poll_time
        if elapsed > config.WATCHDOG_POLL_TIMEOUT_S:
            self._restart()

    def _restart(self) -> None:
        """In-process restart — replaces the current process image."""
        self._sw_watchdog_timer.stop()
        self._sensor_timer.stop()
        self._cpu_timer.stop()
        self._net_timer.stop()
        self._net_retry_timer.stop()
        self._buzzer.cleanup()
        # Disarm hardware watchdog so reboot doesn't trigger during execv
        if self._hw_watchdog is not None:
            try:
                self._hw_watchdog.write(b'V')
                self._hw_watchdog.close()
            except OSError:
                pass
            self._hw_watchdog = None
        os.execv(sys.executable, [sys.executable] + sys.argv)

    # ── Sensor polling ────────────────────────────────────────────────────────

    @pyqtSlot()
    def _poll_sensors(self) -> None:
        self._last_poll_time = time.monotonic()

        egt = self._egt.read_celsius()
        self._gauge.set_temperature(egt, fault=(egt is None))
        self._histogram.add_reading(egt)

        if egt is not None and egt > config.EGT_ALARM_THRESHOLD:
            self._buzzer.on()
        else:
            self._buzzer.off()

        now = time.monotonic()
        amb = self._ds18b20.read_all_celsius()
        any_visible = False
        for i, tile in enumerate(self._amb_tiles):
            val = amb[i] if i < len(amb) else None
            if val is not None:
                self._amb_last_data[i] = now
                tile.set_temperature(val)
                tile.setVisible(True)
                any_visible = True
            else:
                tile.set_temperature(None)  # show --- while within timeout window
                last = self._amb_last_data[i]
                still_valid = (
                    last is not None
                    and (now - last) <= config.AMB_SENSOR_TIMEOUT_S
                )
                tile.setVisible(still_valid)
                if still_valid:
                    any_visible = True
        self._amb_widget.setVisible(any_visible)

    # ── Network fetch ─────────────────────────────────────────────────────────

    @pyqtSlot()
    def _start_net_fetch(self) -> None:
        if self._fetch_thread is not None:
            return   # still running — skip this tick
        thread = FetchThread(self._location, parent=self)
        thread.weather_ready.connect(self._on_weather)
        thread.lightning_ready.connect(self._on_lightning)
        thread.offline.connect(self._on_offline)
        thread.finished.connect(self._on_fetch_done)
        self._fetch_thread = thread
        thread.start()

    @pyqtSlot()
    def _on_fetch_done(self) -> None:
        if self._fetch_thread is not None:
            self._fetch_thread.deleteLater()
            self._fetch_thread = None

    @pyqtSlot(object)
    def _on_weather(self, data: WeatherData) -> None:
        self._weather.update_weather(data)
        # Connection succeeded — stop retry timer and reset counter
        self._net_retry_timer.stop()
        self._net_retry_count = 0

    @pyqtSlot(object)
    def _on_lightning(self, risk: LightningRisk) -> None:
        self._lightning.update_risk(risk)

    @pyqtSlot()
    def _on_offline(self) -> None:
        self._weather.set_offline()
        self._lightning.set_offline()
        # Schedule a retry every 30 s, up to 20 attempts (~10 min)
        self._net_retry_count += 1
        if self._net_retry_count <= 20 and not self._net_retry_timer.isActive():
            self._net_retry_timer.start(30_000)

    # ── Histogram / panel mutual visibility ───────────────────────────────────

    def _update_histogram_visibility(self) -> None:
        # Histogram hides when either data panel is open; panels get its space.
        self._histogram.setVisible(
            not self._lightning_visible and not self._weather_visible
        )

    # ── Lightning toggle ──────────────────────────────────────────────────────

    @pyqtSlot()
    def _toggle_lightning(self) -> None:
        self._lightning_visible = not self._lightning_visible
        self._lightning.setVisible(self._lightning_visible)
        if self._lightning_visible:
            self._lightning_btn.setText('⚡  Hide lightning')
            self._lightning_btn.setStyleSheet(_btn_style())
        else:
            self._lightning_btn.setText('⚡  Lightning')
            self._lightning_btn.setStyleSheet(
                _btn_style(bg='#2a2a1a', fg='#cccc7d', border='#6b6b2e', bg_press='#1a1a0f')
            )
        self._update_histogram_visibility()

    # ── Weather toggle ────────────────────────────────────────────────────────

    @pyqtSlot()
    def _toggle_weather(self) -> None:
        self._weather_visible = not self._weather_visible
        self._weather.setVisible(self._weather_visible)
        if self._weather_visible:
            self._toggle_btn.setText('▲  Hide weather')
            self._toggle_btn.setStyleSheet(_btn_style())
        else:
            self._toggle_btn.setText('▼  Show weather')
            self._toggle_btn.setStyleSheet(
                _btn_style(bg='#1a3a2a', fg='#7dcca0', border='#2e6b4f', bg_press='#0f3460')
            )
        self._update_histogram_visibility()

    # ── Fullscreen toggle ─────────────────────────────────────────────────────

    @pyqtSlot()
    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            self._fullscreen_btn.setText('⛶  Fullscreen')
            self._fullscreen_btn.setStyleSheet(_btn_style())
        else:
            self.showFullScreen()
            self._fullscreen_btn.setText('⊞  Windowed')
            self._fullscreen_btn.setStyleSheet(
                _btn_style(bg='#3a1a1a', fg='#cc7d7d', border='#6b2e2e', bg_press='#2a0f0f')
            )

    # ── Setup dialog ──────────────────────────────────────────────────────────

    @pyqtSlot()
    def _open_setup_dialog(self) -> None:
        dlg = SetupDialog(
            egt_min=int(config.EGT_MIN_DISPLAY),
            egt_max=int(config.EGT_MAX_DISPLAY),
            alarm=int(config.EGT_ALARM_THRESHOLD),
            mock_sensors=config.MOCK_SENSORS,
            parent=self,
        )
        if dlg.exec_() != QDialog.Accepted:
            return

        config.EGT_MIN_DISPLAY = dlg.egt_min
        config.EGT_MAX_DISPLAY = dlg.egt_max
        config.EGT_ALARM_THRESHOLD = dlg.alarm

        self._gauge.set_range(config.EGT_MIN_DISPLAY, config.EGT_MAX_DISPLAY, config.EGT_ALARM_THRESHOLD)
        self._histogram.set_range(config.EGT_MAX_DISPLAY)

        self._user_cfg['egt_min'] = config.EGT_MIN_DISPLAY
        self._user_cfg['egt_max'] = config.EGT_MAX_DISPLAY
        self._user_cfg['alarm'] = config.EGT_ALARM_THRESHOLD

        # Reinit sensors if mock mode changed
        if dlg.mock_sensors != config.MOCK_SENSORS:
            config.MOCK_SENSORS = dlg.mock_sensors
            self._egt = MAX31855(config.SPI_BUS, config.SPI_CE_EGT, config.SPI_SPEED_HZ)
            self._ds18b20 = DS18B20()
            self._update_sensor_visibility()

        self._user_cfg['mock_sensors'] = config.MOCK_SENSORS
        config.save_user_config(self._user_cfg)

    # ── Location dialog ───────────────────────────────────────────────────────

    @pyqtSlot()
    def _open_location_dialog(self) -> None:
        dlg = LocationDialog(self)
        if dlg.exec_() == QDialog.Accepted and dlg.selected_location:
            self._location = dlg.selected_location
            self._user_cfg['location'] = self._location
            config.save_user_config(self._user_cfg)
            QTimer.singleShot(200, self._start_net_fetch)

    # ── Cleanup ───────────────────────────────────────────────────────────────

    def closeEvent(self, event) -> None:  # noqa: N802
        self._sw_watchdog_timer.stop()
        self._sensor_timer.stop()
        self._cpu_timer.stop()
        self._net_timer.stop()
        self._net_retry_timer.stop()
        if self._fetch_thread:
            self._fetch_thread.wait(3_000)
        self._buzzer.cleanup()
        # Disarm hardware watchdog — 'V' is the magic disarm byte
        if self._hw_watchdog is not None:
            try:
                self._hw_watchdog.write(b'V')
                self._hw_watchdog.close()
            except OSError:
                pass
        super().closeEvent(event)
