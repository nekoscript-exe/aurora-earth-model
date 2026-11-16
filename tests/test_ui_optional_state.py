"""Invalid optional preferences must not crash widget/plot styling."""
import pytest
from aurora.desktop import appearance


@pytest.mark.parametrize('value', [None, 42, [], 'unrecognized'])
def test_invalid_saved_palette_uses_dark_theme(monkeypatch, value):
    class Settings:
        def value(self, *args):
            return value
    monkeypatch.setattr(appearance, 'QSettings', lambda *args: Settings())
    assert appearance.colors() == appearance.PALETTES['dark']
