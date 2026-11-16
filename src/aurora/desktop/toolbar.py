"""Localized Matplotlib controls; action callback IDs remain untouched."""
from matplotlib.backends.backend_qt import NavigationToolbar2QT as QtToolbar
from .i18n import tr, translate_tree


class NavigationToolbar2QT(QtToolbar):
    def __init__(self, canvas, parent, coordinates=True):
        super().__init__(canvas, parent, coordinates)
        translate_tree(self)

    def set_message(self, s):
        super().set_message(tr(s))
