"""Münchner Hausverwaltungen, Genossenschaften und kleine Vermieter.

Quelle: kuratierte Liste 'Hausverwaltungen_Muenchen_FINAL_SORT_2.xlsx' + manuell
ergänzte Quellen vom Nutzer. Alle URLs sind Domains aus der Liste; der
GenericTextAdapter erkennt per Auto-Discovery selbständig die richtige
Listing-Subseite (/mietangebote, /vermietung etc.), falls die Domain direkt
nichts liefert.

Spezifisch behandelte Quellen (eigene Adapter mit Detail-Crawling):
- VfV München → siehe vfv.py
- Wagnis, Südhausbau etc. werden weiterhin generic verarbeitet
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
HAUSVERWALTUNGEN_TOP: list[tuple[str, str]] = [
    # Innenstadt-nah
    ("G&S Hausverwaltung", "https://www.gs-hv.gmbh"),
    ("Omnium Hausverwaltung", "https://www.omnium-hausverwaltung.de"),
    ("Rudolf Schäfer", "https://www.rudolfschaefer.de/vermietung-objektsuche/"),  # UPD: spezifischer Pfad
    ("RB Vermögensverwaltung", "https://rb-muenchen.de"),
    ("Oertle Hausverwaltung", "https://www.oertle-hv.de"),
    ("Apfelbeck", "https://www.apfelbeck-muenchen.de/vermietung/"),
    ("Südhausbau", "https://www.suedhausbau.de/immobilienangebote/mietangebote.html"),

    # Großer Bestand
    ("WSB Bayern", "https://wsb-bayern.de"),
    ("GID München", "https://gid-muenchen.de"),
    ("DIBAG", "https://dibag.de"),
    ("MONACHIA", "https://monachia.de"),

    # Weitere
    ("Born Wohnungsbau", "https://www.born-wohnungsbau.de"),
    ("Constantis", "https://constantis.de"),
    ("Foisinger Miethausverwaltungen", "https://www.miethausverwaltungen.net"),
    ("HV Papa", "https://www.hvpapa.de"),
    ("Häusl", "https://haeusl-hv.de"),
    ("LIKKA Immobilien", "https://www.likka-immobilien.de"),
    ("MARAX", "https://www.marax-hausverwaltung.de"),
    ("HARPUT", "https://harput-immobilien.de"),
    ("Immobilien Mößel", "https://immobilien-moessel.de"),
    ("Schad & Nebauer", "https://hv-schadnebauer.de"),
    ("ERTL.IMMO", "https://www.ertl.immo"),
]

# ---------- HAUSVERWALTUNGEN ★★ HOHE PRIORITÄT ----------
HAUSVERWALTUNGEN_HOCH: list[tuple[str, str]] = [
    # Innenstadt-nah
    ("AWV München", "https://www.awv-muenchen.de"),
    ("Lederer Max", "https://www.hausverwaltung-lederer.de"),

    # Großer Bestand / Gute Signale
    ("Bossert Immobilien", "https://www.bossert-immobilien.de"),

    # Weitere
    ("Hans Sieber", "https://sieber-muenchen.de"),
    ("Riedl Hausverwaltung", "https://www.riedl-hausverwaltung.de"),
    ("HV Durner", "https://hausverwaltung-durner.de"),
    ("Roedel / DerWohnraum", "https://www.derwohnraum.de"),
    ("Horrer Immobilien", "https://horrer-immobilien.de"),
    ("Minga HV", "https://minga-hv.de"),
    ("Peter Wild", "https://peterwild.de"),
    ("Rohrer Immobilien",
     "https://www.rohrer-immobilien.de/immobilien/?action=immosearch"
     "&Aktion=Anbieten&Vermarktungsart=Miete&Objekttyp=Wohnung"),
    ("Alsaol", "https://www.alsaol.de/"),
    ("Schwabinger Immobilien", "https://www.schwabinger-immobilien.de/"),
    ("ELVIRA Immo", "https://www.elvira-immo.de/mieten"),
]

# ---------- BENUTZER-ERGÄNZUNGEN ----------
# Vom Nutzer direkt geschickte Listing-URLs, jeweils auf die konkrete Mieten-Subseite
USER_SOURCES: list[tuple[str, str]] = [
    ("Maier Immobilien", "https://www.maierimmobilien.de/immobilien/miete/"),
    ("Sedlmayr AG", "https://www.sedlmayr-ag.de/angebote/"),
    ("Rohrer Firmengruppe", "https://rohrer-firmengruppe.de/hausverwaltung/immobilien.html"),
    ("Münchner Mietbörse", "https://muenchner-mietboerse.de"),
    ("LPE Immobilien", "https://inserate.lpe-immobilien.com/mietobjekte-lpe-inserate/"),
    ("Riedel Immobilien", "https://www.riedel-immobilien.de/angebote/miete/"),
    ("Friedl Maier Immobilien", "https://friedlmaier-immobilien.de/immobilienangebote-in-muenchen-und-umgebung/"),
    ("FGHM", "https://www.fghm.de/mietangebote/"),
    ("Immobilien Schneider", "https://www.immobilienschneider.com/mietangebote/"),
    ("Citigrund", "https://citigrund.de/immobilienangebote/"),
    ("Immo-Hyp", "https://www.immo-hyp.de/immobilien-ort/muenchen/"),
    ("Kaltenberger HV", "https://kaltenberger-hausverwaltung.de/vermietung/aktuelle-angebote/"),
    ("Chalet Immobilien", "https://www.chalet-immobilien.com/Angebote.htm"),
    ("SIS Immobilien", "https://www.sis.de/immobilienangebote/?sort=rank&ct%5B%5D=30225&ut=living&mt=rent"),
    ("Oellbrunner", "https://www.oellbrunner.eu/pages/unsere-kauf--und-mietangebote.php"),
    ("Aigner Immobilien", "https://aigner-immobilien.de/immobilien/?erwerbsart=miete&objektart_raw=wohnung"),
    ("Franziskanerhof", "https://www.immobilien-im-franziskanerhof.de/aktuelle-angebote.xhtml"),
    ("Von Poll", "https://www.von-poll.com/de/search?search-input=Munich%2C+Bavaria%2C+Germany&latitude=48.136973&longitude=11.575968&property-type=apartment&business-area=2&rent-purchase=2&radius=100&limit=10&page=1"),
    ("Heimhuber Immobilien", "https://heimhuber-immobilien.de/angebote/"),
    ("VS Immobilienservice", "https://www.vs-immobilienservice.com/immobilien/mietimmobilien"),
    ("Pöttinger", "https://www.poettinger.com/de/verwaltung.html"),
    # Immonet-White-Label-Portale (gleiches Backend, gleiche URL-Struktur)
    ("SZ Immobilien", "https://immobilienmarkt.sueddeutsche.de/suche/mieten-wohnung-in-muenchen"),
    ("FAZ Immobilien", "https://immobilienmarkt.faz.net/suche/mieten-wohnung-in-muenchen"),
    ("Idowa", "https://zuhause.idowa.de/suche/mieten-wohnung-in-muenchen"),
    ("Ab ins Zuhause", "https://www.ab-ins-zuhause.de/wohnung-mieten-muenchen"),
    ("Engel & Völkers", "https://www.engelvoelkers.com/de/de/immobilien/res/mieten/immobilien/bayern/muenchen"),
    ("Wohnglück", "https://wohnglueck.de/suche/de/bayern/muenchen/wohnung-mieten"),
    ("Rosenberger Immobilien", "https://rosenbergerimmobilien.de/ff/immobilien/?schema=flat_rent&price=&ffpage=1&sort=date"),
]


def all_simple_adapters() -> List[GenericTextAdapter]:
    """Alle Quellen als GenericTextAdapter-Instanzen."""
    adapters = []
    for name, url in (
        GENOSSENSCHAFTEN
        + HAUSVERWALTUNGEN_TOP
        + HAUSVERWALTUNGEN_HOCH
        + USER_SOURCES
    ):
        adapters.append(GenericTextAdapter(name=name, list_url=url))
    return adapters
