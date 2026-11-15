"""Monthly calendar/text fields and linked interval timeline."""

from .i18n import tr
import numpy as np
from PySide6.QtCore import Qt, QDate, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QDateEdit, QSlider, QLabel, QPushButton
from aurora.temporal import select_interval, trend_eligibility, quick_period


class TemporalSelector(QWidget):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dates = np.array([], dtype='datetime64[M]')
        layout = QVBoxLayout(self); layout.setContentsMargins(0, 0, 0, 0)
        row = QHBoxLayout()
        self.start, self.end = QDateEdit(), QDateEdit()
        for label, edit in [('Start', self.start), ('End', self.end)]:
            edit.setKeyboardTracking(False); edit.setCalendarPopup(True); edit.setDisplayFormat('yyyy-MM-dd')
            edit.setToolTip('Calendar or manual date; endpoints include their entire observation month')
            col = QVBoxLayout(); col.addWidget(QLabel(label)); col.addWidget(edit); row.addLayout(col)
            edit.dateChanged.connect(self.update_dates)
        layout.addLayout(row)
        self.low, self.high = QSlider(Qt.Orientation.Horizontal), QSlider(Qt.Orientation.Horizontal)
        self.low.setToolTip('Interval start month'); self.high.setToolTip('Interval end month')
        for slider in (self.low, self.high):
            layout.addWidget(slider)
        self.low.valueChanged.connect(self.update_sliders)
        self.high.valueChanged.connect(self.update_sliders)
        quick = QHBoxLayout(); self.quick = {}
        for years in (5, 10, 15, 25):
            button = QPushButton(f'{years}y'); self.quick[years] = button
            button.clicked.connect(lambda _, y=years: self.apply_quick(y)); quick.addWidget(button)
        layout.addLayout(quick)
        self.status = QLabel(tr('Dataset unavailable')); self.status.setWordWrap(True); layout.addWidget(self.status)
        self.setEnabled(False)

    @staticmethod
    def qdate(month):
        year, number = map(int, str(month)[:7].split('-'))
        return QDate(year, number, 1)

    def set_dates(self, dates):
        self.dates = np.asarray(dates).astype('datetime64[M]')
        self.setEnabled(bool(len(self.dates)))
        if not len(self.dates):
            self.status.setText(tr('Dataset unavailable')); return
        for edit in (self.start, self.end):
            edit.blockSignals(True)
            edit.setDateRange(self.qdate(self.dates[0]), self.qdate(self.dates[-1]).addMonths(1).addDays(-1))
            edit.blockSignals(False)
        for slider in (self.low, self.high):
            slider.blockSignals(True); slider.setRange(0, len(self.dates)-1); slider.blockSignals(False)
        self.set_interval(str(self.dates[0]), str(self.dates[-1]))
        for years, button in self.quick.items():
            button.setEnabled(len(self.dates) >= years*12)

    def set_interval(self, start, end):
        selected = select_interval(self.dates, start, end)
        positions = np.flatnonzero(selected)
        for edit, value in ((self.start, start), (self.end, end)):
            edit.blockSignals(True); edit.setDate(self.qdate(value)); edit.blockSignals(False)
        for slider, value in ((self.low, positions[0]), (self.high, positions[-1])):
            slider.blockSignals(True); slider.setValue(int(value)); slider.blockSignals(False)
        self.update_status()

    def interval(self):
        start, end = self.start.date().toString('yyyy-MM'), self.end.date().toString('yyyy-MM')
        select_interval(self.dates, start, end)
        return start, end

    def update_dates(self, *_):
        try:
            start, end = self.interval(); self.set_interval(start, end)
        except ValueError as exc:
            self.status.setText(str(exc)); self.changed.emit()

    def update_sliders(self, *_):
        if not len(self.dates):
            return
        if self.low.value() > self.high.value():
            other = self.high if self.sender() is self.low else self.low
            other.blockSignals(True); other.setValue(self.low.value() if other is self.high else self.high.value()); other.blockSignals(False)
        self.set_interval(str(self.dates[self.low.value()]), str(self.dates[self.high.value()]))

    def update_status(self):
        selected = select_interval(self.dates, *self.interval())
        eligible = trend_eligibility(self.dates[selected])
        self.status.setText(f'{selected.sum()} months · '+eligible['interpretation'])
        self.changed.emit()

    def apply_quick(self, years):
        self.set_interval(*quick_period(self.dates, years))

    def create_toggle(self):
        button = QPushButton(tr('Date interval'))
        button.setCheckable(True)
        self.hide()
        button.toggled.connect(lambda enabled: self.setVisible(enabled))
        def refresh():
            try: start, end = self.interval(); button.setText(f'{start} — {end} · dates')
            except ValueError: button.setText(tr('Date interval'))
        self.changed.connect(refresh)
        return button
