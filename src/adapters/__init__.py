"""Registry aller Adapter."""
from __future__ import annotations

from typing import List

from .base import Adapter
from .email_inbox import EmailInboxAdapter
from .generic import GenericTextAdapter
from .immowelt import ImmoweltAdapter
from .kleinanzeigen import KleinanzeigenAdapter
from .sources import all_simple_adapters
from .vfv import VfvAdapter
from .wg_gesucht import WgGesuchtAdapter
from .wohnungsboerse import WohnungsboerseAdapter

SPECIFIC_ADAPTER_CLASSES: list[type[Adapter]] = [
    ImmoweltAdapter,
    KleinanzeigenAdapter,
    WohnungsboerseAdapter,
    WgGesuchtAdapter,
    VfvAdapter,
    EmailInboxAdapter,
]


def get_all_adapters() -> List[Adapter]:
    adapters: list[Adapter] = []
    for cls in SPECIFIC_ADAPTER_CLASSES:
        adapters.append(cls())
    adapters.extend(all_simple_adapters())
    return adapters
