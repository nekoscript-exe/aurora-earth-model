"""AURORA Mission Control — interactive home workspace."""

from PySide6.QtWidgets import (
    QWidget, QFrame, QVBoxLayout, QHBoxLayout,
    QGridLayout
)

from .i18n import localized_label, localized_button, tr
from .globe import Planet
from aurora.catalog import DatasetRegistry


class MissionHome(QWidget):

    def __init__(self, root, navigate, parent=None):
        super().__init__(parent)

        self.root = root
        self.navigate = navigate
        self.registry = DatasetRegistry(root)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        workspace = QHBoxLayout()
        workspace.setSpacing(14)

        # Observation system
        left = QVBoxLayout()
        left.setSpacing(12)

        left.addWidget(self.card(
            "Satellite observations",
            "Terra / MODIS · GPM",
            "NDVI / LST / PRECIP"
        ))

        for variable in ("ndvi", "lst", "precip"):
            try:
                record = self.registry.find("global", variable)
                summary = record.summary()
                coverage = summary["mean_declared_coverage"]

                value = (
                    f"{coverage:.2%}"
                    if coverage is not None else "—"
                )

                source = summary["source"]

            except FileNotFoundError:
                value = "—"
                source = "Not available"

            left.addWidget(self.card(
                variable.upper(),
                value,
                "Satellite coverage"
            ))

            left.addWidget(self.card(
                "Source",
                source,
                variable.upper()
            ))

        left.addStretch()

        left_panel = QWidget()
        left_panel.setLayout(left)
        left_panel.setMaximumWidth(245)

        workspace.addWidget(left_panel)

        # Real interactive Earth
        center = QVBoxLayout()
        center.setSpacing(8)

        title = localized_label("Discover a changing planet.")
        title.setObjectName("missionTitle")
        center.addWidget(title)

        self.planet = Planet(root, self)
        self.planet.lon = -25.0
        self.planet.lat = 18.0
        self.planet.zoom = 1.10
        self.planet.markers = False
        self.planet.borders = False
        self.planet.grid = True

        center.addWidget(self.planet, 1)

        explore = localized_button("Planetary Explorer")
        explore.setObjectName("missionPrimary")
        explore.clicked.connect(lambda: navigate(1))
        center.addWidget(explore)

        workspace.addLayout(center, 1)

        # Real catalog metrics
        right = QVBoxLayout()
        right.setSpacing(12)

        records = []

        for variable in ("ndvi", "lst", "precip"):
            try:
                records.append(
                    self.registry.find("global", variable)
                )
            except FileNotFoundError:
                pass

        months = sum(len(record.dates) for record in records)

        period = "—"

        if records:
            first = min(str(r.dates[0]) for r in records)
            last = max(str(r.dates[-1]) for r in records)
            period = f"{first[:4]} – {last[:4]}"

        resolution = (
            f"{records[0].resolution[0]/1000:g} km"
            if records else "—"
        )

        right.addWidget(self.card(
            "Historical dataset", str(months),
            "Monthly maps"
        ))

        right.addWidget(self.card(
            "Historical period", period,
            "Satellite observations"
        ))

        right.addWidget(self.card(
            "Spatial resolution", resolution,
            "Global"
        ))

        right.addWidget(self.card(
            "Region of interest",
            str(len(self.registry.regions())),
            "Available regions"
        ))

        right.addStretch()

        right_panel = QWidget()
        right_panel.setLayout(right)
        right_panel.setMaximumWidth(245)

        workspace.addWidget(right_panel)

        layout.addLayout(workspace, 1)

    def card(self, title, value, description):
        frame = QFrame()
        frame.setObjectName("missionCard")

        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(5)

        heading = localized_label(title)
        heading.setWordWrap(True)
        heading.setObjectName("missionHeading")

        metric = localized_label(value)
        metric.setWordWrap(True)
        metric.setObjectName("missionMetric")

        detail = localized_label(description)
        detail.setWordWrap(True)
        detail.setObjectName("missionDetail")

        layout.addWidget(heading)
        layout.addWidget(metric)
        layout.addWidget(detail)

        return frame
