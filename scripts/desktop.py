"""Launch AURORA Desktop."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication
from aurora.desktop.window import AuroraWindow
from aurora.desktop.i18n import install_translation


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AURORA")
    install_translation(app)
    window = AuroraWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
