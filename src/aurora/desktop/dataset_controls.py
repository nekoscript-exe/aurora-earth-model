"""Localize registry captions at the UI boundary; IDs/registry logic are unchanged."""
from aurora.catalog import populate_regions as _regions, populate_variables as _variables
from .i18n import tr


def _captions(combo):
    blocked = combo.blockSignals(True)
    for index in range(combo.count()):
        source = combo.itemText(index)
        combo.setItemData(index, source, 257)
        combo.setItemText(index, tr(source))
    combo.blockSignals(blocked)


def populate_regions(combo, root, paired=False):
    registry = _regions(combo, root, paired=paired)
    _captions(combo)
    return registry


def populate_variables(combo, registry, region, preserve=True):
    _variables(combo, registry, region, preserve=preserve)
    _captions(combo)
