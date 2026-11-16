"""Predictive laboratory availability regression tests."""

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication
from aurora.desktop.ai_lab import AILaboratory


def test_missing_models_disable_predictive_actions(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])

    monkeypatch.setattr(
        AILaboratory,
        "refresh_catalog",
        lambda self: None
    )

    lab = AILaboratory(tmp_path)

    try:
        def forbidden_read(*args, **kwargs):
            raise AssertionError("Unexpected predictive file access")

        monkeypatch.setattr(lab, "read_json", forbidden_read)
        monkeypatch.setattr(lab, "draw_benchmark", forbidden_read)
        monkeypatch.setattr(lab, "draw_prediction", forbidden_read)

        lab.render_results()

        assert lab.directory is None
        assert not lab.view.isEnabled()
        assert not lab.export_button.isEnabled()
        assert lab.details.text()

    finally:
        lab.close()
        app.processEvents()
