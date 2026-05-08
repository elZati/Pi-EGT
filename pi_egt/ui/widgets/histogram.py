from __future__ import annotations

import time
from collections import deque

from PyQt5.QtCore import Qt, QRectF, QPointF
from PyQt5.QtGui import (
    QColor, QFont, QPainter, QPainterPath, QPen, QBrush,
)
from PyQt5.QtWidgets import QWidget


class EGTHistogram(QWidget):
    """
    Scrolling line chart showing the last N seconds of EGT temperature.
    X-axis = time (oldest left, 'now' right).
    Y-axis = temperature, fixed 0–max_temp.
    """

    def __init__(
        self,
        history_seconds: int = 900,
        max_temp: float = 1000.0,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._max_s = history_seconds
        self._max_temp = max_temp
        # deque of (monotonic_timestamp, temp_celsius)
        self._data: deque[tuple[float, float]] = deque()
        self.setMinimumHeight(130)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_range(self, max_temp: float) -> None:
        self._max_temp = max_temp
        self.update()

    def add_reading(self, temp: float | None) -> None:
        if temp is None:
            return
        now = time.monotonic()
        self._data.append((now, temp))
        cutoff = now - self._max_s
        while self._data and self._data[0][0] < cutoff:
            self._data.popleft()
        self.update()

    # ── Paint ─────────────────────────────────────────────────────────────────

    # Margins in pixels
    _ML, _MR, _MT, _MB = 54, 8, 8, 28

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        ml, mr, mt, mb = self._ML, self._MR, self._MT, self._MB
        plot_w = w - ml - mr
        plot_h = h - mt - mb
        plot = QRectF(ml, mt, plot_w, plot_h)

        p.fillRect(self.rect(), QColor('#0d0d1a'))
        p.fillRect(plot, QColor('#111122'))

        self._draw_grid(p, plot)
        self._draw_series(p, plot)
        self._draw_axes(p, plot)

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _y(self, temp: float, plot: QRectF) -> float:
        frac = max(0.0, min(1.0, temp / self._max_temp))
        return plot.bottom() - frac * plot.height()

    def _x(self, ts: float, now: float, plot: QRectF) -> float:
        frac = max(0.0, min(1.0, (ts - (now - self._max_s)) / self._max_s))
        return plot.left() + frac * plot.width()

    def _y_step(self) -> int:
        if self._max_temp <= 200: return 50
        if self._max_temp <= 500: return 100
        return 200

    def _draw_grid(self, p: QPainter, plot: QRectF) -> None:
        pen = QPen(QColor('#222233'), 1, Qt.DotLine)
        p.setPen(pen)
        step = self._y_step()
        t = step
        while t <= self._max_temp:
            y = self._y(t, plot)
            p.drawLine(QPointF(plot.left(), y), QPointF(plot.right(), y))
            t += step

    def _draw_series(self, p: QPainter, plot: QRectF) -> None:
        if len(self._data) < 2:
            return
        now = time.monotonic()

        line = QPainterPath()
        fill = QPainterPath()
        first = True
        for ts, temp in self._data:
            x = self._x(ts, now, plot)
            y = self._y(temp, plot)
            if first:
                line.moveTo(x, y)
                fill.moveTo(x, plot.bottom())
                fill.lineTo(x, y)
                first = False
            else:
                line.lineTo(x, y)
                fill.lineTo(x, y)

        last_ts, _ = self._data[-1]
        fill.lineTo(self._x(last_ts, now, plot), plot.bottom())
        fill.closeSubpath()

        fill_color = QColor('#e74c3c')
        fill_color.setAlpha(35)
        p.fillPath(fill, QBrush(fill_color))

        p.setPen(QPen(QColor('#e74c3c'), 1.5))
        p.drawPath(line)

    def _draw_axes(self, p: QPainter, plot: QRectF) -> None:
        p.setFont(QFont('Helvetica', 13))
        p.setPen(QColor('#666677'))

        # Y labels — scaled to current max_temp
        step = self._y_step()
        t = 0
        while t <= self._max_temp:
            y = self._y(t, plot)
            p.drawText(
                QRectF(0, y - 9, self._ML - 4, 18),
                Qt.AlignRight | Qt.AlignVCenter,
                str(int(t)),
            )
            t += step

        # X labels
        p.drawText(
            QRectF(plot.left() - 14, plot.bottom() + 4, 36, 18),
            Qt.AlignCenter, '−15m',
        )
        p.drawText(
            QRectF(plot.right() - 18, plot.bottom() + 4, 36, 18),
            Qt.AlignCenter, 'now',
        )

        # Border
        p.setPen(QPen(QColor('#333344'), 1))
        p.drawRect(plot)
