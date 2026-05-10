"""Münchner Quellen via GenericTextAdapter.

REALITY CHECK (Stand: nach erstem Live-Test):

Viele Münchner Wohnbau-Genossenschaften vergeben Wohnungen NUR an Mitglieder
über E-Mail oder ein Intranet. Es gibt schlicht keine öffentliche "freie
Wohnungen"-Seite zum Scrapen. Das wussten wir vorher nicht — jetzt schon.

Beispiele wörtlich von den Sites:
  Wogeno: "Wohnungen werden nur an Mitglieder vergeben und im WOGENO-Intranet
           ausgeschrieben."
  Wagnis: "Diese werden in der Regel nur in der Mitgliedschaft intern
           ausgeschrieben."

Konsequenz: Die meisten Genossenschafts-Adapter werden 0 Treffer liefern,
egal welche URL wir scrapen. Das ist kein Bug, das ist die Realität.

Wo Genossenschaften noch Sinn machen: bei Neubauprojekten und größeren
Vergaben (z.B. Wagnis Augsburg, Wogeno Freiham) wird zur Bewerbung breiter
publiziert — die Adapter fangen das mit ein, wenn die Seite passt.

Daher: Diese Liste ist konservativ gehalten. Lieber wenige Quellen die
funktionieren als viele die 404 liefern. Du kannst jederzeit eigene URLs
ergänzen — Test-Workflow ist im README beschrieben.
"""
from __future__ import annotations

from typing import List

from .generic import GenericTextAdapter

# ---------- VERIFIZIERTE QUELLEN ----------
# Diese URLs liefern HTTP 200 und enthalten Listing-typische Marker.
# Format: (Anzeigename, URL der Listing-Seite)

VERIFIED_SOURCES: list[tuple[str, str]] = [
    # Wagnis publiziert öffentlich Neubau-Ausschreibungen (München-Modell etc.)
    ("Wagnis", "https://www.wagnis.org/aktuelles/freie-wohnungen.html"),
]

# ---------- KANDIDATEN ----------
# URLs die ICH GERATEN HABE und die du selber verifizieren musst, bevor sie
# was bringen. So gehst du vor:
#
# 1. URL im Browser öffnen.
# 2. Wenn 404 oder leer → Site-Navigation prüfen, echten Pfad finden, hier
#    eintragen ODER Quelle aus der Liste rausnehmen.
# 3. Wenn Seite Wohnungen zeigt → in VERIFIED_SOURCES verschieben.
#
# Tipp: Genossenschafts-Sites haben den Listing-Pfad fast immer unter
# "Wohnen" → "Aktuelle Angebote" / "Freie Wohnungen" / "Wohnungsangebote" /
# "Vermietung". Browser-Suche im Hauptmenü hilft.

CANDIDATE_SOURCES: list[tuple[str, str]] = [
    # WGMW – Wohnungsgenossenschaft München-West
    # ("WGMW", "https://wg-mw.de/<TODO>"),

    # VfV – Verein für Volkswohnungen, ~1.500 Wohnungen
    # ("VfV München", "https://www.vfv-muenchen.de/<TODO>"),

    # GIMA – Aggregator mehrerer Genossenschaften, theoretisch sehr wertvoll
    # ("GIMA München", "https://gima-muenchen.de/<TODO>"),

    # EBM – Eisenbahner-Baugenossenschaft München-Hauptbahnhof
    # ("EBM München", "https://ebm-muenchen.de/<TODO>"),

    # Postbaugenossenschaft München und Oberbayern
    # ("Postbaugenossenschaft", "https://www.mietwohnen-eg.de/<TODO>"),

    # Hartmannshofen eG
    # ("BG Hartmannshofen", "https://www.bg-hartmannshofen.de/<TODO>"),

    # IWG – Isar Wohnungsbaugenossenschaft
    # ("IWG", "https://www.iwg-muenchen.de/<TODO>"),
]

# ---------- HAUSVERWALTUNGEN ----------
# Inserieren oft erst auf eigener Seite, dann mit Verzögerung auf Portalen.
# 200 ohne Treffer = aktuell keine Wohnungen frei (kein Bug).
# 403 = Anti-Bot, dann nicht zu retten ohne Playwright.

HAUSVERWALTUNGEN: list[tuple[str, str]] = [
    # Rohrer: Site lädt, Filter auf Mietwohnungen
    ("Rohrer Immobilien", "https://www.rohrer-immobilien.de/immobilien/?action=immosearch"
                          "&Aktion=Anbieten&Vermarktungsart=Miete&Objekttyp=Wohnung"),
]

# ---------- Adapter-Instanzen erzeugen ----------

def all_simple_adapters() -> List[GenericTextAdapter]:
    adapters = []
    for name, url in VERIFIED_SOURCES + CANDIDATE_SOURCES + HAUSVERWALTUNGEN:
        adapters.append(GenericTextAdapter(name=name, list_url=url))
    return adapters
