"""Münchner Hausverwaltungen, Genossenschaften und kleine Vermieter.

Quelle: kuratierte Liste 'Hausverwaltungen_Muenchen_FINAL_SORT_2.xlsx' mit
Top + Hoch Priorität. Alle URLs sind Domains aus der Liste; der
GenericTextAdapter erkennt per Auto-Discovery selbständig die richtige
Listing-Subseite (/mietangebote, /vermietung etc.), falls die Domain direkt
nichts liefert.

Schon vorhandene/eingebaute Quellen (Wagnis, Südhausbau, Apfelbeck, EBM,
KSWM, Bossert, Rohrer, GWG-Gruppe, Alsaol, Schwabinger Immo, ELVIRA) sind
bereits weiter unten in HAUSVERWALTUNGEN/GENOSSENSCHAFTEN gelistet.

Stand: Mai 2026. Erfahrungswerte zu erwartender Trefferquote:
- ~30–40% liefern beim ersten Run direkt Inserate
- ~30% liefern HTTP 200 + 0 Inserate (= aktuell keine freien Wohnungen)
- ~20% brauchen URL-Anpassung (Auto-Discovery findet nichts)
- ~10% blocken per Cloudflare / reCAPTCHA

Bei 0-Treffer-Quellen: in 1-2 Wochen erneut prüfen — Hausverwaltungs-Listings
sind volatil, manchmal kommt nach Wochen plötzlich eine Wohnung rein.
"""
from __future__ import annotations

from typing import List

from .generic import GenericTextAdapter

# ---------- GENOSSENSCHAFTEN ----------
GENOSSENSCHAFTEN: list[tuple[str, str]] = [
    ("Wagnis", "https://www.wagnis.org/aktuelles/freie-wohnungen.html"),
    ("EBM München", "https://ebm-muenchen.de/mietangebote"),
    ("KSWM", "https://www.kswm.de/vermietung.html"),
]

# ---------- HAUSVERWALTUNGEN ★★★ TOP-PRIORITÄT ----------
# Aus Excel-Liste, alle mit verifizierter Mietverwaltung + Website.
HAUSVERWALTUNGEN_TOP: list[tuple[str, str]] = [
    # Innenstadt-nah (Glockenbach, Isarvorstadt, Maxvorstadt, Ludwigsvorstadt, Schwabing)
    ("G&S Hausverwaltung", "https://www.gs-hv.gmbh"),                       # Isarvorstadt / Glockenbach
    ("Omnium Hausverwaltung", "https://www.omnium-hausverwaltung.de"),      # Maxvorstadt
    ("Rudolf Schäfer", "https://www.rudolfschaefer.de"),                    # Maxvorstadt
    ("RB Vermögensverwaltung", "https://rb-muenchen.de"),                   # Ludwigsvorstadt
    ("Oertle Hausverwaltung", "https://www.oertle-hv.de"),                  # Schwabing
    ("Apfelbeck", "https://www.apfelbeck-muenchen.de/vermietung/"),
    ("Südhausbau", "https://www.suedhausbau.de/immobilienangebote/mietangebote.html"),

    # Großer Bestand (eigene Wohnungen, hohe Trefferchance über Zeit)
    ("WSB Bayern", "https://wsb-bayern.de"),                                # 19.500 Wohnungen!
    ("Bayerische Immobilien Management", "https://www.bi-m.de"),            # 18.000 Einheiten
    ("GID München", "https://gid-muenchen.de"),                             # 300 eigene Wohnungen
    ("DIBAG", "https://dibag.de"),                                          # Doblinger-Gruppe
    ("MONACHIA", "https://monachia.de"),                                    # Doblinger-Gruppe

    # Weitere Top-Priorität in München / Umland
    ("Born Wohnungsbau", "https://www.born-wohnungsbau.de"),                # Berg am Laim
    ("Constantis", "https://constantis.de"),                                # Ramersdorf
    ("Foisinger Miethausverwaltungen", "https://www.miethausverwaltungen.net"),  # Bogenhausen
    ("HV Papa", "https://www.hvpapa.de"),                                   # Pasing
    ("Häusl", "https://haeusl-hv.de"),                                      # Laim
    ("LIKKA Immobilien", "https://www.likka-immobilien.de"),                # Sendling
    ("MARAX", "https://www.marax-hausverwaltung.de"),                       # Bogenhausen
    ("HARPUT", "https://harput-immobilien.de"),                             # Oberschleißheim
    ("Immobilien Mößel", "https://immobilien-moessel.de"),                  # München Süd/Ost
    ("Schad & Nebauer", "https://hv-schadnebauer.de"),                      # Grasbrunn
    ("Sterr", "https://www.sterrgmbh.de"),                                  # Unterhaching
    ("ERTL.IMMO", "https://www.ertl.immo"),                                 # Aschheim
]

# ---------- HAUSVERWALTUNGEN ★★ HOHE PRIORITÄT ----------
HAUSVERWALTUNGEN_HOCH: list[tuple[str, str]] = [
    # Innenstadt-nah
    ("AWV München", "https://www.awv-muenchen.de"),                         # Isarvorstadt
    ("Lederer Max", "https://www.hausverwaltung-lederer.de"),               # Isarvorstadt
    ("PARTNER Immobilienverwaltung", "https://www.partner-immobilienverwaltung.de"),  # Schwabing-West
    ("Arno Dietzel", "https://dietzelgbr.de"),                              # Schwabing-West

    # Großer Bestand / Gute Signale
    ("Bayerische Hausbau", "https://www.bayerische-hausverwaltung.de"),     # Bogenhausen
    ("Münchner Grund", "https://www.muenchner-grund.de"),                   # Bogenhausen
    ("Gruber Günther", "https://wohnungsangebote-muenchen.de"),             # eigener Listing-Host!
    ("Bossert Immobilien", "https://www.bossert-immobilien.de"),            # Untergiesing

    # Weitere
    ("Hans Sieber", "https://sieber-muenchen.de"),
    ("Riedl Hausverwaltung", "https://www.riedl-hausverwaltung.de"),        # Aubing
    ("HV Durner", "https://hausverwaltung-durner.de"),                      # Eichenau
    ("Roedel / DerWohnraum", "https://www.derwohnraum.de"),                 # Nymphenburg
    ("Horrer Immobilien", "https://horrer-immobilien.de"),
    ("Minga HV", "https://minga-hv.de"),                                    # Moosach
    ("Peter Wild", "https://peterwild.de"),
    ("Rohrer Immobilien",
     "https://www.rohrer-immobilien.de/immobilien/?action=immosearch"
     "&Aktion=Anbieten&Vermarktungsart=Miete&Objekttyp=Wohnung"),
    ("GWG-Gruppe", "https://gwg-gruppe.de/standorte/muenchen"),
    ("Alsaol", "https://www.alsaol.de/"),
    ("Schwabinger Immobilien", "https://www.schwabinger-immobilien.de/"),
    ("ELVIRA Immo", "https://www.elvira-immo.de/mieten"),
]


def all_simple_adapters() -> List[GenericTextAdapter]:
    """Alle Quellen als GenericTextAdapter-Instanzen."""
    adapters = []
    for name, url in (
        GENOSSENSCHAFTEN + HAUSVERWALTUNGEN_TOP + HAUSVERWALTUNGEN_HOCH
    ):
        adapters.append(GenericTextAdapter(name=name, list_url=url))
    return adapters
