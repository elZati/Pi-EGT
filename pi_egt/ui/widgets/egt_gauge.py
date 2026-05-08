from __future__ import annotations

import math

from PyQt5.QtCore import Qt, QPointF, QRectF
from PyQt5.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QBrush
from PyQt5.QtWidgets import QWidget

# ── Gauge geometry (virtual 300×300 space, centred at 0,0) ───────────────────
_ARC_RADIUS = 110
_ARC_WIDTH = 16
_TICK_OUTER = 124
_TICK_MAJOR_INNER = 112
_TICK_MINOR_INNER = 119
_LABEL_RADIUS = 76
_NEEDLE_LEN = 100
_HUB_R = 7

# Angular convention: "degrees CCW from 3-o'clock" (standard Qt drawArc).
# 0 °C (gauge min) → 7-o'clock (225°), max → 5-o'clock (−45°).
_START_DEG = 225.0
_SWEEP_DEG = 270.0

class EGTGauge(QWidget):
    """
    Circular analog EGT gauge with coloured zone arc, tick marks, needle
    and a large digital readout.  Call set_range() to reconfigure scale.

    Zone colours are derived from the alarm threshold:
      green  → [min, alarm × 0.85)
      amber  → [alarm × 0.85, alarm)
      red    → [alarm, max]
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._temp: float | None = None
        self._fault = False
        self._min_temp = 0.0
        self._max_temp = 1000.0
        self._alarm = 800.0
        self._zones: list[tuple[float, float, QColor]] = []
        self._rebuild_zones()
        self.setMinimumSize(260, 260)

    # ── Public API ────────────────────────────────────────────────────────────

    def set_temperature(self, temp: float | None, fault: bool = False) -> None:
        self._temp = temp
        self._fault = fault
        self.update()

    def set_range(self, min_temp: float, max_temp: float, alarm: float) -> None:
        self._min_temp = float(min_temp)
        self._max_temp = float(max_temp)
        self._alarm = float(alarm)
        self._rebuild_zones()
        self.update()

    def _rebuild_zones(self) -> None:
        caution = self._alarm * 0.85
        self._zones = [
            (self._min_temp, caution,          QColor('#27ae60')),   # green
            (caution,        self._alarm,      QColor('#f39c12')),   # amber
            (self._alarm,    self._max_temp,   QColor('#e74c3c')),   # red
        ]

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _angle(self, temp: float) -> float:
        """CCW-from-3-o'clock angle for a temperature within the display range."""
        span = self._max_temp - self._min_temp
        if span == 0:
            return _START_DEG
        frac = max(0.0, min(1.0, (temp - self._min_temp) / span))
        return _START_DEG - frac * _SWEEP_DEG

    def _tick_step(self) -> tuple[float, float]:
        """Return (major_step, minor_step) appropriate for the current range."""
        span = self._max_temp - self._min_temp
        if span <= 200:
            return 20.0, 10.0
        if span <= 500:
            return 50.0, 25.0
        return 100.0, 50.0

    # ── Paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)

        side = min(self.width(), self.height())
        p.translate(self.width() / 2, self.height() / 2)
        p.scale(side / 300.0, side / 300.0)

        self._draw_background(p)
        self._draw_arc_background(p)
        self._draw_zones(p)
        self._draw_ticks(p)
        self._draw_needle(p)
        self._draw_hub(p)
        self._draw_readout(p)

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_background(self, p: QPainter) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#1a1a2e'))
        p.drawEllipse(QRectF(-148, -148, 296, 296))

    def _draw_arc_background(self, p: QPainter) -> None:
        pen = QPen(QColor('#2d2d40'), _ARC_WIDTH)
        pen.setCapStyle(Qt.FlatCap)
        p.setPen(pen)
        r = _ARC_RADIUS
        p.drawArc(QRectF(-r, -r, r * 2, r * 2),
                  int(_START_DEG * 16), int(-_SWEEP_DEG * 16))

    def _draw_zones(self, p: QPainter) -> None:
        pen = QPen()
        pen.setWidth(_ARC_WIDTH)
        pen.setCapStyle(Qt.FlatCap)
        r = _ARC_RADIUS
        rect = QRectF(-r, -r, r * 2, r * 2)

        for z_start, z_end, color in self._zones:
            # Clip zone boundaries to display range
            draw_start = max(z_start, self._min_temp)
            draw_end = min(z_end, self._max_temp)
            if draw_start >= draw_end:
                continue
            pen.setColor(color)
            p.setPen(pen)
            a_s = self._angle(draw_start)
            a_e = self._angle(draw_end)
            p.drawArc(rect, int(a_s * 16), int((a_e - a_s) * 16))

    def _draw_ticks(self, p: QPainter) -> None:
        major_step, minor_step = self._tick_step()

        # Determine tick positions
        span = self._max_temp - self._min_temp
        n_minor = int(round(span / minor_step))
        ticks = [self._min_temp + i * minor_step for i in range(n_minor + 1)]

        for t in ticks:
            if t > self._max_temp + 0.01:
                break
            a_rad = math.radians(self._angle(t))
            is_major = (round((t - self._min_temp) / major_step) * major_step
                        == round(t - self._min_temp))
            inner = _TICK_MAJOR_INNER if is_major else _TICK_MINOR_INNER
            x1 = _TICK_OUTER * math.cos(a_rad)
            y1 = -_TICK_OUTER * math.sin(a_rad)
            x2 = inner * math.cos(a_rad)
            y2 = -inner * math.sin(a_rad)
            p.setPen(QPen(QColor('#cccccc' if is_major else '#777777'),
                          2 if is_major else 1))
            p.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Labels at major ticks — bigger font for 5" readability
        p.setFont(QFont('Helvetica', 11, QFont.Bold))
        p.setPen(QColor('#bbbbbb'))
        n_major = int(round(span / major_step))
        for i in range(n_major + 1):
            t = self._min_temp + i * major_step
            if t > self._max_temp + 0.01:
                break
            a_rad = math.radians(self._angle(t))
            x = _LABEL_RADIUS * math.cos(a_rad)
            y = -_LABEL_RADIUS * math.sin(a_rad)
            text = str(int(round(t)))
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(text)
            th = fm.ascent()
            p.drawText(QPointF(x - tw / 2, y + th / 2), text)

    def _draw_needle(self, p: QPainter) -> None:
        if self._temp is None or self._fault:
            return
        a_rad = math.radians(self._angle(self._temp))
        tip_x = _NEEDLE_LEN * math.cos(a_rad)
        tip_y = -_NEEDLE_LEN * math.sin(a_rad)

        perp_x = -math.sin(a_rad) * 6
        perp_y = -math.cos(a_rad) * 6
        path = QPainterPath()
        path.moveTo(QPointF(tip_x, tip_y))
        path.lineTo(QPointF(perp_x, perp_y))
        path.lineTo(QPointF(-perp_x, -perp_y))
        path.closeSubpath()

        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#e74c3c'))
        p.drawPath(path)

        tail_x = -18 * math.cos(a_rad)
        tail_y = 18 * math.sin(a_rad)
        pen = QPen(QColor('#e74c3c'), 6)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(0, 0), QPointF(tail_x, tail_y))

    def _draw_hub(self, p: QPainter) -> None:
        p.setPen(Qt.NoPen)
        p.setBrush(QColor('#cccccc'))
        p.drawEllipse(QRectF(-_HUB_R, -_HUB_R, _HUB_R * 2, _HUB_R * 2))

    def _draw_readout(self, p: QPainter) -> None:
        # Small EGT label directly above the temperature value
        p.setFont(QFont('Helvetica', 10))
        p.setPen(QColor('#666666'))
        p.drawText(QRectF(-35, 56, 70, 16), Qt.AlignCenter, 'EGT')

        # Large value in the bottom gap of the arc (below needle travel, y > 71)
        if self._fault:
            text, color = 'FAULT', QColor('#e74c3c')
        elif self._temp is None:
            text, color = '---', QColor('#555555')
        else:
            text, color = f'{self._temp:.0f}', QColor('#ffffff')

        p.setFont(QFont('Helvetica', 36, QFont.Bold))
        p.setPen(color)
        p.drawText(QRectF(-75, 74, 150, 52), Qt.AlignCenter, text)

        # Unit just below the value
        p.setFont(QFont('Helvetica', 13))
        p.setPen(QColor('#aaaaaa'))
        p.drawText(QRectF(-22, 126, 44, 18), Qt.AlignCenter, '°C')
