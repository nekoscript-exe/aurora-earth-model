"""AURORA visual identity and design system."""

COLORS = {
    "background": "#080e17",
    "surface": "#101b29",
    "border": "#243548",
    "primary": "#69d9bd",
    "text": "#e7edf5",
    "muted": "#8da5ba",
    "warning": "#efbd76",
}

STYLE = """
QWidget {
    background: #080e17;
    color: #e7edf5;
    font-family: "Inter", "Ubuntu", sans-serif;
    font-size: 14px;
}

QFrame#sidebar {
    background: #101b29;
    border: 1px solid #243548;
    border-radius: 12px;
}

QFrame#sidebar QLabel {
    background: transparent;
}

QLabel#brand {
    font-size: 34px;
    font-weight: bold;
    color: #69d9bd;
}

QLabel#subtitle {
    font-size: 12px;
    color: #8da5ba;
}

QComboBox, QSpinBox, QPlainTextEdit {
    background: #101b29;
    border: 1px solid #243548;
    border-radius: 8px;
    padding: 10px;
    selection-background-color: #267c70;
}

QComboBox:hover, QSpinBox:hover {
    border-color: #69d9bd;
}

QComboBox QAbstractItemView {
    background: #101b29;
    selection-background-color: #267c70;
    border: 1px solid #243548;
    padding: 5px;
}

QPushButton {
    background: #24796c;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background: #329d89;
}

QPushButton:disabled {
    background: #1b2938;
    color: #64788b;
}

QTabWidget::pane {
    border: 1px solid #243548;
    border-radius: 8px;
    background: #101b29;
}

QTabBar::tab {
    background: #101b29;
    color: #8da5ba;
    padding: 14px 18px;
    margin-right: 3px;
}

QTabBar::tab:selected {
    color: #69d9bd;
    border-bottom: 2px solid #69d9bd;
}

QProgressBar {
    background: #1b2938;
    border: none;
    border-radius: 3px;
    min-height: 6px;
    max-height: 6px;
}

QProgressBar::chunk {
    background: #69d9bd;
    border-radius: 3px;
}

QToolTip {
    background: #162536;
    color: #e7edf5;
    border: 1px solid #345064;
    padding: 6px;
}
"""
