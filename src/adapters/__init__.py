"""Registry aller Adapter.

get_all_adapters() liefert frische Instanzen für jeden Run.
"""
from __future__ import annotations

from typing import List

from .base import Adapter
from .generic import GenericTextAdapter
from .immowelt import ImmoweltAdapter
from .kleinanzeigen import KleinanzeigenAdapter
from .sources import all_simple_adapters
from .sz_immobilien import SzImmobilienAdapter
from .wg_gesucht import WgGesuchtAdapter
from .wohnungsboerse import WohnungsboerseAdapter

# Spezifische Adapter (eigene Parsing-Logik)
SPECIFIC_ADAPTER_CLASSES: list[type[Adapter]] = [
    ImmoweltAdapter,
    KleinanzeigenAdapter,
    WohnungsboerseAdapter,
    SzImmobilienAdapter,
    WgGesuchtAdapter,
]


def get_all_adapters() -> List[Adapter]:
    """Alle Adapter als frische Instanzen."""
    adapters: list[Adapter] = []

    # Wogeno und Wagnis als GenericTextAdapter — gleicher Pattern wie andere
    # Genossenschaften, kein Grund für eigene Implementierung.
    adapters.append(GenericTextAdapter(
        "Wogeno", "https://www.wogeno-muenchen.de/wohnen/freie-wohnungen.html"
    ))
    adapters.append(GenericTextAdapter(
        "Wagnis", "https://www.wagnis.org/wohnen/aktuelle-wohnangebote.html"
    ))

    # Spezifische Adapter (Portale mit eigener Logik)
    for cls in SPECIFIC_ADAPTER_CLASSES:
        adapters.append(cls())

    # Top-10-Erweiterung: 8 Genossenschaften + 2 Hausverwaltungen via Generic
    adapters.extend(all_simple_adapters())

    return adapters
