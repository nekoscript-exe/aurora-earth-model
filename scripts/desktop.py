"""Launch AURORA Desktop."""

import sys
import os
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from PySide6.QtWidgets import QApplication
from aurora.desktop.window import AuroraWindow
from aurora.desktop.i18n import install_translation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--device', choices=['auto', 'cpu', 'cuda'], default='auto')
    args, qt_args = parser.parse_known_args()
    os.environ['AURORA_DEVICE'] = args.device
    app = QApplication([sys.argv[0], *qt_args])
    app.setApplicationName("AURORA")
    install_translation(app)
    window = AuroraWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
