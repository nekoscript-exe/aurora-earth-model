"""AURORA Mission Control visual identity."""

STYLE = """
QWidget {
    background-color: #090f1b;
    color: #e4ebf6;
    font-size: 13px;
}

QMainWindow {
    background-color: #070c15;
}

QFrame#sidebar {
    background-color: #111c2d;
    border: 1px solid #263950;
    border-radius: 16px;
}

QLabel {
    background: transparent;
}

QLabel#brand {
    color: #d9edff;
    font-size: 26px;
    font-weight: 700;
}

QLabel#subtitle {
    color: #7e97b2;
    font-size: 11px;
}

QPushButton {
    background-color: #192b40;
    color: #d9e8f7;
    border: 1px solid #2d465f;
    border-radius: 10px;
    padding: 9px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #22435a;
    border-color: #65c4dd;
}

QPushButton:pressed {
    background-color: #173447;
}

QPushButton:disabled {
    background-color: #111a26;
    color: #526476;
    border-color: #202c3b;
}

QComboBox, QSpinBox, QDateEdit, QLineEdit {
    background-color: #101e30;
    border: 1px solid #2a4058;
    border-radius: 8px;
    padding: 8px;
    min-height: 18px;
    selection-background-color: #27566e;
}

QComboBox:hover, QSpinBox:hover {
    border-color: #65c4dd;
}

QComboBox QAbstractItemView {
    background-color: #142236;
    selection-background-color: #27566e;
    border: 1px solid #385369;
    outline: none;
}

QTabWidget::pane {
    border: 1px solid #23344a;
    border-radius: 14px;
    background-color: #0b1422;
}

QTabBar::tab {
    background-color: transparent;
    color: #879cb4;
    padding: 10px 14px;
    margin: 3px;
    border-radius: 10px;
}

QTabBar::tab:selected {
    background-color: #183448;
    color: #a6e8ff;
    border: 1px solid #3c758e;
}

QTabBar::tab:hover:!selected {
    background-color: #152338;
    color: #e1efff;
}

QTextBrowser, QPlainTextEdit {
    background-color: #0b1422;
    border: 1px solid #23344a;
    border-radius: 12px;
    padding: 10px;
}

QScrollArea {
    border: none;
    background: transparent;
}

QScrollBar:vertical {
    background: #0a1320;
    width: 7px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #344c65;
    border-radius: 3px;
    min-height: 24px;
}

QScrollBar::add-line, QScrollBar::sub-line {
    height: 0;
    width: 0;
}

QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #192a3c;
    color: #e4ebf6;
    min-height: 8px;
    text-align: center;
}

QProgressBar::chunk {
    border-radius: 4px;
    background-color: #68cce5;
}

QToolTip {
    background-color: #18283c;
    color: #e2efff;
    border: 1px solid #38536c;
    padding: 6px;
}
"""

STYLE += """
QPushButton#missionNavigation {
    background: transparent;
    border: 1px solid transparent;
    color: #8fa4bd;
    border-radius: 16px;
    padding: 10px 14px;
}

QPushButton#missionNavigation:hover {
    background: #14263b;
    color: #d3eaff;
}

QPushButton#missionNavigation:checked {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #143343,
        stop:1 #17273a
    );
    border: 1px solid #68cce5;
    color: #dbf6ff;
}

QFrame#scientificNavigation {
    background: #101c2c;
    border: 1px solid #243a51;
    border-radius: 12px;
}

QFrame#missionCard {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1a2b40,
        stop:1 #0d1727
    );
    border: 1px solid #2b4058;
    border-radius: 18px;
}

QLabel#missionMetric {
    font-size: 28px;
    font-weight: 700;
    color: #a5e5fa;
}
"""

STYLE += """
QPushButton#missionPrimary {
    background: #133748;
    color: #d9f5ff;
    border: 1px solid #70cde8;
    border-radius: 18px;
    padding: 13px;
    font-size: 15px;
}

QPushButton#missionPrimary:hover {
    background: #20546b;
}

QPushButton#missionShortcut {
    background: qlineargradient(
        x1:0, y1:0, x2:1, y2:1,
        stop:0 #1a2c42,
        stop:1 #111b2a
    );
    border: 1px solid #2a435d;
    border-radius: 14px;
    padding: 18px 10px;
}

QPushButton#missionShortcut:hover {
    border-color: #70cde8;
    background: #20364d;
}
"""

DARK_STYLE = STYLE

LIGHT_STYLE = """
QWidget {
    background: #edf2f8;
    color: #23374a;
    font-size: 13px;
}

QMainWindow {
    background: #e6edf5;
}

QLabel {
    background: transparent;
    color: #23374a;
}

QLabel#brand {
    color: #17698b;
    font-size: 26px;
    font-weight: 700;
}

QLabel#subtitle {
    color: #607589;
    font-size: 11px;
}

QFrame#sidebar, QFrame#missionCard,
QFrame#scientificNavigation {
    background: #ffffff;
    border: 1px solid #d7e1ec;
    border-radius: 14px;
}

QPushButton {
    background: #ffffff;
    color: #29465c;
    border: 1px solid #c6d5e3;
    border-radius: 9px;
    padding: 9px 14px;
    font-weight: 600;
}

QPushButton:hover {
    background: #dceef7;
    border-color: #409cc0;
}

QPushButton:checked {
    background: #d5eaf5;
    color: #12688b;
    border-color: #409cc0;
}

QPushButton:disabled {
    background: #e3e9ef;
    color: #94a3b1;
    border-color: #d4dde6;
}

QPushButton#missionNavigation {
    border-radius: 16px;
}

QPushButton#missionPrimary {
    background: #187da3;
    color: white;
    border-radius: 16px;
    padding: 12px;
}

QComboBox, QSpinBox, QDateEdit, QLineEdit {
    background: #ffffff;
    color: #23374a;
    border: 1px solid #c6d5e3;
    border-radius: 8px;
    padding: 8px;
}

QComboBox QAbstractItemView {
    background: #ffffff;
    color: #23374a;
    selection-background-color: #d5eaf5;
    selection-color: #12688b;
}

QTextBrowser, QPlainTextEdit {
    background: #ffffff;
    color: #23374a;
    border: 1px solid #d7e1ec;
    border-radius: 10px;
    padding: 10px;
}

QTabWidget::pane {
    background: #edf2f8;
    border: none;
}

QScrollArea {
    border: none;
}

QProgressBar {
    background: #dce5ef;
    border: none;
    border-radius: 3px;
}

QProgressBar::chunk {
    background: #187da3;
    border-radius: 3px;
}

QToolTip {
    background: #ffffff;
    color: #23374a;
    border: 1px solid #c6d5e3;
    padding: 6px;
}
"""


DARK_STYLE += """
QLabel#missionTitle {
    color: #d9edff;
    font-size: 23px;
    font-weight: 700;
}
QLabel#missionHeading {
    color: #8ea7c1;
    font-size: 12px;
}
QLabel#missionMetric {
    color: #ccefff;
    font-size: 23px;
    font-weight: 700;
}
QLabel#missionDetail {
    color: #8197ae;
    font-size: 11px;
}
"""

LIGHT_STYLE += """
QLabel#missionTitle {
    color: #23374a;
    font-size: 23px;
    font-weight: 700;
}
QLabel#missionHeading {
    color: #52697f;
    font-size: 12px;
}
QLabel#missionMetric {
    color: #17698b;
    font-size: 23px;
    font-weight: 700;
}
QLabel#missionDetail {
    color: #52697f;
    font-size: 11px;
}
"""
