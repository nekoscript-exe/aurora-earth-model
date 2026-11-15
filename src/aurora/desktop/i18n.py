"""AURORA internationalization system."""

from pathlib import Path
from PySide6.QtCore import QCoreApplication, QSettings, QTranslator

LANGUAGES = {
    "en": "English",
    "es": "Español",
}

DIRECTORY = Path(__file__).resolve().parent / "translations"

_translator = None


def tr(text):
    return QCoreApplication.translate("AURORA", text)


def get_language():
    settings = QSettings("AURORA", "Desktop")
    language = settings.value("language", "en")
    return language if language in LANGUAGES else "en"


def set_language(language):
    if language not in LANGUAGES:
        raise ValueError("Unsupported language")

    QSettings("AURORA", "Desktop").setValue(
        "language", language
    )


def install_translation(app):
    global _translator

    if _translator is not None:
        app.removeTranslator(_translator)

    _translator = QTranslator(app)

    language = get_language()

    if language == "en":
        return True

    if _translator.load(str(DIRECTORY / f"aurora_{language}.qm")):
        app.installTranslator(_translator)
        return True

    return False
