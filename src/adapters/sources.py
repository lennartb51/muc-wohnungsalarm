"""Münchner Wohnbau-Genossenschaften und kleine Vermieter via GenericTextAdapter.

Für Genossenschaften & kleine Hausverwaltungen reicht der GenericTextAdapter:
URL angeben, Name angeben, fertig. Wenn eine Quelle nicht funktioniert, hier
URL anpassen oder einen eigenen Adapter dafür schreiben.

Recherche-Stand: Mai 2026. Wenn eine Site umzieht oder neu strukturiert wird,
einfach die LIST_URL hier korrigieren.
"""
from __future__ import annotations

from typing import List

from .generic import GenericTextAdapter

# ---------- GENOSSENSCHAFTEN (München) ----------
# Reguläre Mietwohnungen (kein WBS nötig). Ausnahme: einzelne Wohnungen können
# trotzdem geförderten Wohnraum sein — Filter dann manuell prüfen.
#
# Format: (Name, URL der "Freie Wohnungen"-Seite)
# Wenn eine URL 404t, die Hauptdomain probieren — der GenericTextAdapter findet
# Listings auf jeder Seite, die die typischen Marker (m²/€/Zimmer) enthält.

GENOSSENSCHAFTEN = [
    # WGMW – Wohnungsgenossenschaft München-West, eine der größten
    ("WGMW", "https://wg-mw.de/wohnen/wohnungsangebote/"),

    # VfV – Verein für Volkswohnungen, ~1.500 Wohnungen, aktive Site
    ("VfV München", "https://www.vfv-muenchen.de/wohnen/aktuelle-wohnungsangebote/"),

    # GIMA – Aggregator mehrerer Genossenschaften, sehr wertvoll
    ("GIMA München", "https://gima-muenchen.de/wohnungsangebote.html"),

    # EBM – Eisenbahner-Baugenossenschaft München-Hauptbahnhof, 2.500 Haushalte
    ("EBM München", "https://ebm-muenchen.de/aktuelle-mietangebote/"),

    # Postbaugenossenschaft München und Oberbayern
    ("Postbaugenossenschaft", "https://www.mietwohnen-eg.de/wohnungsangebote/"),

    # HEIMAG München
    ("HEIMAG", "https://www.heimag-muenchen.de/wohnungsangebote/"),

    # Hartmannshofen eG
    ("BG Hartmannshofen", "https://www.bg-hartmannshofen.de/aktuelle-angebote/"),

    # IWG – Isar Wohnungsbaugenossenschaft
    ("IWG", "https://www.iwg-muenchen.de/wohnen/aktuelle-angebote/"),
]

# ---------- HAUSVERWALTUNGEN (München) ----------
# Inserieren oft erst auf eigener Seite, dann mit Verzögerung auf Portalen.

HAUSVERWALTUNGEN = [
    # Rohrer Immobilien – etablierte Münchner Hausverwaltung
    ("Rohrer Immobilien", "https://www.rohrer-immobilien.de/immobilien/"),

    # Aigner Immobilien
    ("Aigner Immobilien", "https://www.aigner-immobilien.de/immobilien/mietangebote/"),
]

# ---------- Adapter-Instanzen erzeugen ----------

def all_simple_adapters() -> List[GenericTextAdapter]:
    """Liefert alle Genossenschafts- + Hausverwaltungs-Adapter."""
    adapters = []
    for name, url in GENOSSENSCHAFTEN + HAUSVERWALTUNGEN:
        adapters.append(GenericTextAdapter(name=name, list_url=url))
    return adapters
