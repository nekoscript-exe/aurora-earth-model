"""AURORA animated welcome experience."""

from .i18n import localized_label, localized_button

import math
import random

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import (
    QPainter, QColor, QPen,
    QRadialGradient, QPainterPath
)
from PySide6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout,
    QHBoxLayout, QPushButton, QSizePolicy
)


class EarthView(QWidget):

    def __init__(self, parent=None):
        super().__init__(parent)

        self.phase = 0.0
        self.setMinimumHeight(250)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding
        )

        rng = random.Random(42)

        self.stars = [
            (rng.random(), rng.random(), rng.uniform(0.4, 1.5))
            for _ in range(180)
        ]

        self.points = []

        for lat in range(-84, 85, 3):
            for lon in range(0, 360, 3):

                n = (
                    math.sin(lon * 0.031 + lat * 0.065)
                    + 0.7 * math.cos(lon * 0.067 - lat * 0.097)
                    + 0.35 * math.sin(lon * 0.13 + lat * 0.17)
                )

                if n > 0.65:
                    self.points.append((
                        math.radians(lat),
                        math.radians(lon),
                        n
                    ))

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)

    def showEvent(self, event):
        super().showEvent(event)
        self.timer.start(33)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def animate(self):
        self.phase += 0.025
        self.update()

    def paintEvent(self, event):

        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )

        painter.fillRect(self.rect(), QColor("#080e17"))

        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2
        radius = min(w * 0.23, h * 0.36)

        center = QPointF(cx, cy)

        painter.setPen(Qt.PenStyle.NoPen)

        for sx, sy, size in self.stars:

            brightness = int(
                65 + 90 * (
                    0.5 + 0.5 *
                    math.sin(self.phase + sx * 40)
                )
            )

            painter.setBrush(
                QColor(160, 195, 220, brightness)
            )

            painter.drawEllipse(
                QPointF(sx * w, sy * h),
                size, size
            )

        glow = QRadialGradient(center, radius * 1.6)

        glow.setColorAt(0.5, QColor("#164d56"))
        glow.setColorAt(0.72, QColor(37, 131, 122, 60))
        glow.setColorAt(1, QColor(8, 14, 23, 0))

        painter.setBrush(glow)

        painter.drawEllipse(
            center, radius * 1.6, radius * 1.6
        )

        painter.save()

        clip = QPainterPath()
        clip.addEllipse(center, radius, radius)
        painter.setClipPath(clip)

        painter.fillRect(
            QRectF(
                cx - radius, cy - radius,
                radius * 2, radius * 2
            ),
            QColor("#102d40")
        )

        painter.setPen(QPen(QColor(65, 145, 150, 75), 0.8))
        painter.setBrush(Qt.BrushStyle.NoBrush)

        for latitude in range(-80, 81, 20):

            lat = math.radians(latitude)
            y = cy - radius * math.sin(lat)
            length = radius * math.cos(lat)

            painter.drawLine(
                QPointF(cx - length, y),
                QPointF(cx + length, y)
            )

        for angle in range(-80, 81, 20):

            path = QPainterPath()
            lon = math.radians(angle)

            for step in range(-90, 91, 3):

                lat = math.radians(step)

                x = cx + radius * math.cos(lat) * math.sin(lon)
                y = cy - radius * math.sin(lat)

                if step == -90:
                    path.moveTo(x, y)
                else:
                    path.lineTo(x, y)

            painter.drawPath(path)

        painter.setPen(Qt.PenStyle.NoPen)

        for lat, lon, density in self.points:

            angle = lon + self.phase * 0.25

            if math.cos(angle) <= 0:
                continue

            x = cx + radius * math.cos(lat) * math.sin(angle)
            y = cy - radius * math.sin(lat)

            color = (
                QColor("#83e5bc")
                if density > 1.1
                else QColor("#3c9d88")
            )

            painter.setBrush(color)

            painter.drawEllipse(
                QPointF(x, y), 1.15, 1.15
            )

        painter.restore()

        painter.setPen(QPen(QColor("#69d9bd"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, radius, radius)

        painter.save()
        painter.translate(cx, cy)
        painter.rotate(-30)

        painter.setPen(QPen(QColor(105, 217, 189, 160), 1.2))

        a, b = radius * 1.55, radius * 0.48

        painter.drawEllipse(QRectF(-a, -b, a * 2, b * 2))

        satellite = QPointF(
            a * math.cos(self.phase),
            b * math.sin(self.phase)
        )

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(105, 217, 189, 40))
        painter.drawEllipse(satellite, 10, 10)

        painter.setBrush(QColor("#b0ffe8"))
        painter.drawEllipse(satellite, 3.5, 3.5)

        painter.restore()
        painter.end()


class WelcomePage(QWidget):

    def __init__(self, launch, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(16)

        layout.addWidget(EarthView(), 1)

        title = localized_label('Discover a changing planet.')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(
            "font-size:30px; font-weight:bold;"
            "color:#e7edf5;"
        )

        subtitle = localized_label(
            'Explore the past. Understand the present. Model what comes next.'
        )

        subtitle.setWordWrap(True)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color:#8da5ba;")

        layout.addWidget(title)
        layout.addWidget(subtitle)

        features = QHBoxLayout()

        for value, label in [
            ("25 years", "Historical NDVI"),
            ("MODIS", "Satellite observations"),
            ("02", "Predictive models")
        ]:

            card = localized_label(
                f'<center><span style="font-size:24px;'
                f'color:#69d9bd;"><b>{value}</b></span>'
                f'<br><span style="color:#8da5ba;">'
                f'{label}</span></center>'
            )

            card.setStyleSheet(
                "background:#14202d;"
                "border-radius:9px;padding:15px;"
            )

            features.addWidget(card, 1)

        layout.addLayout(features)

        button = localized_button('Begin scientific investigation')
        button.clicked.connect(launch)

        layout.addWidget(button)
