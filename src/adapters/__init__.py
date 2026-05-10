"""Registry aller Adapter — schlanke, getestete Variante.

Stand nach erstem Live-Test:
- Kleinanzeigen ✅ funktioniert (~10 Treffer/Run)
- WG-Gesucht   ✅ funktioniert (~25 Treffer/Run)
- Wagnis       ✅ URL gefixt (öffentliche Neubau-Ausschreibungen)
- Immowelt     ⚠️  HTTP 403 (Cloudflare) — drin gelassen, falls's mal durchkommt
- Wohnungsboerse, SZ Immobilien — drin gelassen, URL-Tuning nötig
- Andere Genossenschaften → meist Mitglieder-only, deaktiviert (siehe sources.py)
- Hausverwaltungen → nur Rohrer drin, Aigner blockt
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

SPECIFIC_ADAPTER_CLASSES: list[type[Adapter]] = [
    ImmoweltAdapter,
    KleinanzeigenAdapter,
    WohnungsboerseAdapter,
    SzImmobilienAdapter,
    WgGesuchtAdapter,
]


def get_all_adapters() -> List[Adapter]:
    adapters: list[Adapter] = []
    for cls in SPECIFIC_ADAPTER_CLASSES:
        adapters.append(cls())
    adapters.extend(all_simple_adapters())
    return adapters
