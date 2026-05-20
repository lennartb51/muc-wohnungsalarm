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
    ("KSWM", "https://www.kswm.de/leistungsspektrum/mietwohnungen.html"),
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
    # Südhausbau hat eigenen Adapter (TYPO3-h3+table-Layout, nicht generic parseable)

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
    # Immonet-White-Label-Portale (gleiches Backend, gleiche URL-Struktur)
    ("SZ Immobilien", "https://immobilienmarkt.sueddeutsche.de/suche/mieten-wohnung-in-muenchen"),
    ("FAZ Immobilien", "https://immobilienmarkt.faz.net/suche/mieten-wohnung-in-muenchen"),
    ("Idowa", "https://zuhause.idowa.de/suche/mieten-wohnung-in-muenchen"),
    ("Ab ins Zuhause", "https://www.ab-ins-zuhause.de/wohnung-mieten-muenchen"),
    ("Engel & Völkers", "https://www.engelvoelkers.com/de/de/immobilien/res/mieten/immobilien/bayern/muenchen"),
    ("Wohnglück", "https://wohnglueck.de/suche/de/bayern/muenchen/wohnung-mieten"),
    ("Rosenberger Immobilien", "https://rosenbergerimmobilien.de/ff/immobilien/?schema=flat_rent&price=&ffpage=1&sort=date"),
    ("Pandion Service", "https://pandion-service.de/immobilien/?post_type=immomakler_object&paged=1&lang=de&vermarktungsart=miete&nutzungsart=&typ=&ort=muenchen"),
    ("Immobilie1", "https://www.immobilie1.de/immobilien/bayern/muenchen/wohnung/mieten?sort=-created_at&page=1"),
    ("Munich Property", "https://www.munich-property.de/properties/?sort=date_desc"),
    ("Idowa Altstadt-Lehel", "https://zuhause.idowa.de/suche/mieten-wohnung-in-muenchen-altstadt-lehel-bez-mit-balkon"),
    ("Immobilo", "https://www.immobilo.de/mieten/wohnung/muenchen-kreis?s=most_recently_updated_first"),
    ("Nuroa", "https://www.nuroa.de/mieten/munchen-wohnung?order=1&way=2"),
    ("LEG Wohnen", "https://www.leg-wohnen.de/immobilien/mietwohnungen#/geo/48.13329869584388,11.576734033343515,12"),
    ("GVG Net", "https://www.gvgnet.de/mietobjekte-category/wohnobjekte/#objekte"),
    ("Walser Immobiliengruppe", "https://www.walser-immobiliengruppe.de/miete/"),
    ("KLN Immobilien", "https://kln-immobilien.de/vermietung-2/wohnungen/"),
    ("TUM Living", "https://living.tum.de/listings?viewMode=list&tumLocation=MUNICH&type=APARTMENT&rentTo=1550"),
    # --- Tageszeitungs- & Privat-Vermieter-Portale ---
    ("ohne-makler.net", "https://www.ohne-makler.net/immobilien/wohnung-mieten/bayern/munchen/", False),
    ("Münchner Wochenanzeiger", "https://www.wochenanzeiger.de/immobilien", False),
    # Entfernt (alle permanent tot seit Wochen):
    # - Wohnungsbörse München (DNS NXDOMAIN)
    # - meinestadt.de München: drin gelassen (HTTP 403, könnte zurückkommen)
    # - Abendzeitung München (HTTP 404)
    # - Münchner Merkur Immo (SSL Cert Mismatch)
    ("meinestadt.de München", "https://www.meinestadt.de/muenchen/immobilien/wohnungen"),
    ("Drescher Immobilien", "https://drescher-immobilien.de/mietangebote"),
    ("EP Immobilien", "https://www.ep-immobilien.com/?post_type=immomakler_object&vermarktungsart=miete&nutzungsart=wohnen"),
    ("Fleckenstein Immobilien", "https://fleckenstein-immobilien.com/mieten/"),
    ("Mutzhas Immobilien", "https://mutzhas-immobilien.de/immobilien/"),
    ("Harinali", "https://www.harinali.de/immobilienangebote/"),
    ("Hegerich Immobilien", "https://www.hegerich-immobilien.de/Mietangebote.htm"),
    ("Immobilien Lederer", "https://immobilien-lederer.de/angebote/angebote.html", False),
    ("Dawonia", "https://www.dawonia.de/de/mieten?city=M%C3%BCnchen&items-per-page=100"),
    ("Vonovia", "https://www.vonovia.de/zuhause-finden/immobilien?rentType=miete&city=M%C3%BCnchen&immoType=wohnung"),
    ("Immobilien Schlamp", "https://www.immobilien-schlamp.de/index.php/mietangebote/"),
    ("Hausverwaltung-SG", "https://www.hausverwaltung-sg.de/"),
    ("RE/MAX Prime München", "https://prime-muenchen.remax.de/de/wohnung-mieten-in-muenchen/"),
    ("Wegener Immobilien", "https://www.wegenerimmobilien.de/Muenchen/Mietwohnungen-Muenchen.html"),
    ("Rogers Immobilien", "https://www.rogers-immobilien.de/immobilienangebote/"),
    # auto_discover=False für Sources mit spezifischen URLs/Query-Params
    # die sonst von Auto-Discovery überschrieben würden:
    ("KIP Immobilien", "https://www.kip.net/bayern/muenchen/mieten/wohnungen/1", False),
    ("Wohnreferat München", "https://www.wohnref-muenchen.de/immobilien/"),
    ("Garant Immo", "https://www.garant-immo.de/result.html?search=rent&t=rental-apartment&q=M%C3%BCnchen&qt=county", False),
    ("VR-Bank München Land", "https://www.vr-bank-muenchen-land.de/privatkunden/immobilie-und-wohnen/produkte/immobilien/immobiliensuche.html"),
    ("Lehmann Hueber", "https://lehmannhueber.de/immobilien/?post_type=immomakler_object&vermarktungsart=miete&nutzungsart=wohnen", False),
    ("Egger Immobilien", "https://egger-immo.de/immobilien/immobilien-muenchen/"),
    ("Immobilien PS", "https://www.immobilien-ps.de/aktuelle-mietangebote?slg=immomakler_object&mdf_cat=40&page_mdf=9134&order_by=mverfuegbarkeit&order=DESC", False),
    ("Roethig Immobilien", "https://www.roethig-immobilien.de/angebote/vermietung/", False),
    ("Pöttinger", "https://www.poettinger.com/de/miet-immobilien.html", False),
    ("ImmoSmart", "https://immosmart.de/mieten/"),
]

# ---------- HAUSVERWALTUNGEN ★ MITTEL (Auto-Discovery) ----------
# Aus der Excel "Hausverwaltungen_Muenchen_FINAL_SORT_2", gefiltert nach
# Lennarts Kern-Bezirken. Auto-Discovery findet Listing-Subpfade selbständig;
# EXCLUDE_PATH_KEYWORDS filtert Service-Pfade (Mieterwechsel, Vermieterservice
# etc.) raus. Die mit echten Listings liefern automatisch beim nächsten Run.
HAUSVERWALTUNGEN_MITTEL: list[tuple[str, str]] = [
    # --- Bogenhausen / Pienzenauer ---
    ("Pienzenauer Immobilien", "https://pienzenauer-immobilien.de/immobilien/?inx-search-property-type=wohnungen&inx-search-marketing-type=zu-vermieten", False),

    # --- Altstadt-Lehel ---
    ("DOMINO Haus- und Grundbesitz", "https://www.domino-muc.de"),
    ("Fries & Co Grundstücksverwaltung", "https://www.friesundco.de/immobilienangebote", False),
    ("Hausverwaltung Heinz Zimmermann", "https://www.hausverwaltung-zimmermann.de"),
    ("Isaria Hausverwaltung", "https://www.isaria-hv.de"),
    ("Leuchtenberger Immobilien", "https://www.leuchtenberger-immobilien.de"),
    ("Stockmayr-Kielleuthner", "https://www.stockmayr.de"),
    ("Kribitzneck Anton Hausverwaltung", "https://www.hausverwaltung-kribitzneck.de"),
    # --- Maxvorstadt ---
    ("Arnold Ingeborg Immobilien", "https://www.arnold-immobilien-gmbh.de"),
    ("Concept-Real Hausverwaltungs", "https://concept-real.de"),
    ("Maneum Hausverwaltung", "https://www.maneum.de"),
    ("Ries Immobilien KG", "https://www.riesimmobilienkg.de"),
    ("Stoll Hausverwaltungen", "https://www.stoll-hv.de"),
    # --- Schwabing(-West) ---
    ("Dietzel GbR Vermietung", "https://www.hv-dietzel.de/objekte/401/", False),
    ("PARTNER Immobilien-Verwaltung", "https://www.partner-immobilienverwaltung.de"),
    ("DHG-Hausverwaltung Fischbaum", "https://www.ipg-gmbh.de"),
    ("EIGENSCHINK Grundstücksverwaltung", "https://www.eigenschink-gv.de"),
    ("Franke & Leal Hausverwaltung", "https://www.frankeundpartner.com"),
    ("Fritz Kuschel u Söhne", "https://www.hv-kuschel.de"),
    ("Günthert & Gollmann", "https://www.hausverwaltung-gollmann.de"),
    ("Hausverwaltung Potzler", "https://www.hv-potzler.de"),
    ("M-Haus Hausverwaltung", "https://www.m-haus.info"),
    ("MuM Real Estates / Winkler", "https://www.hv-winkler.de"),
    ("Schaefer Christian Hausverwaltung", "https://www.hausverwaltung-schaefer.de"),
    ("Interco Grundbesitz / Suedboden", "https://www.suedboden.com"),
    # --- Isarvorstadt / Ludwigsvorstadt ---
    ("B.I.G. Hausverwaltung", "https://www.big-hausverwaltung.de"),
    ("BC Hausverwaltung & Immobilien", "https://www.bc-verwaltung.de"),
    ("Enzenhöfer Hausverwaltung", "https://www.enzenhoefer-immobilien.de/content/vermietung", False),
    ("GATT Hausverwaltung", "https://www.gatt-immobilienverwaltung.de"),
    ("Hahn & Schmid Immobilien", "https://www.hahn-schmid.de"),
    ("HVK Grundbesitz", "https://www.hvk-grundbesitz.de"),
    ("Landlord Immobilien Verwaltung", "https://www.landlord-iv.de"),
    ("Dr. Hanns Maier / Hamabau", "https://www.hamabau.de"),
    ("MSH Immobilien", "https://www.msh-immobilien.de"),
    ("Schenk Mariele Hausverwaltung", "https://www.ra-schenk.de"),
    ("Schmid Stefan Hausverwaltung", "https://hv-schmid.de/leistungen/mietangebote/", False),
    # --- Au-Haidhausen ---
    ("Brauner Fred Hausverwaltung", "https://www.hv-brauner.de"),
    ("Hausverwaltung Geisinger", "https://www.geisinger-hausverwaltung.de"),
    ("Gegenfurtner Helmut Hausverwaltung", "https://hv-gegenfurtner.de/news-feed/", False),
    ("HAVAU Immobilien", "https://havau.everreal.co/candidates/public/listings", False),
    ("Prospera Immobilien", "https://www.prospera-immo.de"),
    # --- Sendling ---
    ("Grassl Gertraud Hausverwaltung", "https://www.grassl-hausverwaltung.de"),
    ("Hinterseer Peter Hausverwaltung", "https://www.hv-hinterseer.de"),
    ("Homewise GmbH", "https://www.homewise.de"),
    ("Küffel Werner Hausverwaltung", "https://www.kueffel-online.de"),
    ("J. Rüprich Hausverwaltungen", "https://www.rueprich.net"),
    # --- Schwanthalerhöhe / Westend ---
    ("Solitär Immobilienverwaltung", "https://immo.mbc1.de"),
    ("Teichmann Hausverwaltungen", "https://www.teichmanngmbh-online.de"),
    # --- Neuhausen / Nymphenburg ---
    ("Drost & Reidler / Voelkner", "https://www.voelkner-immo.de"),
    ("Hauskonzept Hausverwaltungs", "https://www.hauskonzept-gmbh.de"),
    ("Hausverwaltung Nymphenburg HVN", "https://www.hvny.de"),
    ("Merkl Haus- und Grundstücksverwaltung", "https://www.merkl-immob.com"),
    ("Nymphenburger Grund Verwaltung", "https://www.nygr.de"),
    ("Urbanski Hausverwaltung", "https://www.hv-urbanski.com"),
    # --- Bogenhausen ---
    ("Bayerische Hausbau Management", "https://www.bayerische-hausverwaltung.de"),
    ("Krautbauer Ernst Immobilien", "https://www.krautbauer.de"),
    ("Hausverwaltung Pharao", "https://www.pharaohaus.de"),
    ("VITA-Hausverwaltung", "https://www.vita-hausverwaltung.com"),
]

# ---------- HAUSVERWALTUNGEN AUDIT-POOL ----------
# Großzügig hinzugefügt nach Lennarts "so viele wie möglich"-Strategie.
# Auto-Discovery prüft selbst ob Listing-Seite existiert; EXCLUDE_PATH_KEYWORDS
# blockt Service-Pfade. Nach 3-4 Runs werden nicht-funktionierende rausgenommen.
HAUSVERWALTUNGEN_AUDIT: list[tuple[str, str]] = [
    # --- Chris-Quellen (vom User vorgemerkt) ---
    ("A&C Immobilien", "https://www.ac-immobilien-gmbh.de"),
    ("AV Immobilien", "https://www.av-immo.de"),
    ("Boos & Co Verwaltung", "https://www.boos-verwaltung.com"),
    ("CM CASA Hausverwaltung", "https://www.cm-casa-hausverwaltung.de"),
    ("conta Immobilien-Gruppe", "https://www.conta.eu"),
    ("DAHLER München", "https://www.dahlercompany.com"),
    ("Eichler Immobilien", "https://www.eichler.de"),
    ("Finestep Immobilien", "https://www.finestep.de"),
    ("Fritz N. Osterried Immobilien", "https://www.immobilien-osterried.de"),
    ("Hartlaub / Cocon Immobilienstiftung", "https://www.cocon.de"),
    ("HOMEFacilities Seelbach", "https://www.homefacilities.de"),
    ("IMCON Immobilien Consulting", "https://www.imcon.info"),
    ("Immobilien Zippold", "https://www.immobilien-zippold.de"),
    ("IntigrA Immobilien Management", "https://www.intigra-immobilien.de"),
    ("KITHAN GmbH", "https://www.kithan.de"),
    ("Norbert Marte Immobilien", "https://www.immobilienmarte.de/immobilienangebote.xhtml", False),
    ("Park Avenue Immobilien", "https://www.parkavenue.immobilien"),
    ("Projekt M Immobilien", "https://www.projektmimmobilien.de"),
    ("Schön Immobilien", "https://www.schoenimmobilien.de"),
    ("Westfalia Immobilienverwaltung", "https://www.westfalia-gmbh.de"),
    ("Andreas Hage Immobilien", "https://www.hage-immobilien.net"),
    ("Immobilien Boos", "https://www.immobilien-boos.de"),
    ("Immovision München", "https://www.immovision.de"),
    ("KLATTE Immobilien", "https://www.klatte-immobilien.de"),
    ("Tectareal Property Management", "https://www.tectareal.de"),

    # --- Weitere München-HVs (alle URLs aus Excel) ---
    ("Bayerische Immobilien Management", "https://www.bi-m.de"),
    ("Gruber Günther Hausverwaltung", "https://www.wohnungsangebote-muenchen.de"),
    ("ACM Immobilien Hausverwaltung", "https://www.acmgmbh.de"),
    ("anima Immobilien Verwaltung", "https://www.animare-immobilien.de"),
    ("ARCO / Zinkl Hausverwaltung", "https://www.hvzinkl.de"),
    ("Arendt Hausverwaltung", "https://www.arendt-hausverwaltung.de"),
    ("ASI Immobilienverwaltungen", "https://www.asi-iv.de"),
    ("Bettinger Norbert Hausverwaltung", "https://www.beno-immobilien.de"),
    ("BPV Hausverwaltung", "https://www.bpv-muenchen.de"),
    ("Cohaus München", "https://www.cohaus-muenchen.de"),
    ("Dall'Armi Immobilienverwaltung", "https://www.lunovalinner.de"),
    ("Dimperl & Sohn Hausverwaltung", "https://www.dimperl-muenchen.de"),
    ("Etcos Immobilien Management", "https://www.etcos-gmbh.de"),
    ("F. Schlagenhaufer Hausverwaltung", "https://www.immobilien-schlagenhaufer.de"),
    ("Fischer / Keilich Hausverwaltung", "https://www.hausverwaltung-keilich-muenchen.de"),
    ("Frommhold Maximilian Hausverwaltung", "https://www.maximilian-frommhold.de"),
    ("GFF Hausverwaltung", "https://www.gff-hv.de"),
    ("Hausgrund München", "https://www.hausgrund-muenchen.de"),
    ("Hausverwaltung Moosach / Meinhart", "https://www.hv-meinhart.de"),
    ("Hausverwaltung Schmidt", "https://www.schmidt-hausverwaltung.net"),
    ("Hausverwaltung WEMA", "https://www.wema-hausverwaltung.de"),
    ("E. Schmaus Hausverwaltung", "https://www.schmaus-immob-int.de"),
    ("HS-Immoteam", "https://hs-immoteam.jimdo.com"),
    ("Immler Martin Hausverwaltung", "https://www.immler.com"),
    ("Klaus Hausverwaltung", "https://www.klaus-immo.de"),
    ("Margot Ludl Immobilienbetreuung", "https://www.ludl-immobilien.de"),
    ("MHM Hausverwaltungs", "https://www.m-h-m.de"),
    ("mvh Immobilienverwaltung München", "https://www.mrh-immobilienverwaltung.de"),
    ("OBM Hausverwaltung München", "https://www.obm-hausverwaltung.de"),
    ("PARTNER Immobilien Vermittlung", "https://www.partnerimmobilienverwaltung.de"),
    ("Roth Immobilienverwaltung", "https://www.roth-immobilienverwaltung.de"),
    ("S2H Immobilienmanagement", "https://www.s2h-muenchen.de"),
    ("Schwerdt Tobias Immobilien", "https://www.schwerdt-immobilien.de"),
    ("SEHAG Hausverwaltung", "https://www.sehag.de"),
    ("Sollner Grundbesitzverwaltung", "https://www.sollner-grund.de"),
    ("Sonntag Horst Hausverwaltung", "https://www.hausverwaltung-sonntag.de"),
    ("Walger Grundstücksverwaltung", "https://www.verwaltung123.de"),
    ("ADM GmbH Hausverwaltung", "https://www.adm-gmbh.net"),
    ("admincasa Hausverwaltung", "https://www.admincasa.de"),
    ("ADVISUM Hausverwaltung", "https://www.advisum.de"),
    ("AIMAG Immobilien-Management", "https://www.aimag.de"),
    ("Arivon Service", "https://www.arivon.de"),
    ("Aufbau West Innovationspark HV", "https://www.aufbau-west.org"),
    ("Castle Eigentum", "https://www.castle-hausverwaltung.de"),
    ("D. Baumann Immobilien", "https://www.dbi-germany.de"),
    ("Diez Grundstücks", "https://www.diez-verwaltung.de"),
    ("EFIMA AG", "https://www.efima-ag.eu"),
    ("Empetus Hausverwaltung", "https://www.empetus.de"),
    ("Erl Wilhelm Verwaltung", "https://www.wilhelm-erl.de"),
    ("GEMA Gebäudemanagement", "https://www.gema-gebaeudemanagement.de"),
    ("GLOBAL Institut Immobilien", "https://www.global-immobilien.de"),
    ("Graphigrund Hausverwaltung", "https://www.graphigrund.de"),
    ("Gruber Herbert Hausverwaltung", "https://www.hv-gruber.de"),
    ("HADIEFA Hausverwaltung", "https://www.hadiefa.de"),
    ("Hammerla Hausverwaltung", "https://www.hausverwaltung-hammerla.de"),
    ("Hartmann Immoinvest", "https://www.hartmann-immoinvest.de"),
    ("Haus-Treu-Süd", "https://www.haus-treu-sued.de"),
    ("Danhuber Haus- und Vermögensverwaltung", "https://www.hausverwaltung-danhuber.de"),
    ("HGSK Hausverwaltung", "https://www.hgsk.eu"),
    ("HI Wohnbau", "https://www.hi-wohnbau.de"),
    ("HIS Real Estate", "https://www.hisrealestate.de"),
    ("Häusl Peter Hausverwaltung", "https://www.haeusl-hausverwaltung.de"),
    ("ifena Hausverwaltung", "https://www.ifena.de"),
    ("ihr-WEGVerwalter", "https://www.ihr-wegverwalter.de"),
    ("Jugan Investmentverwaltung", "https://www.jugan.de"),
    ("Scheel Immobilien", "https://www.scheel-immobilien.de"),
    ("Herbst Immobilienverwaltung", "https://www.daniel-immo.eu"),
    ("Immobilienbüro 24", "https://www.immobilienbuero24.de"),
    ("Impro Hausverwaltung", "https://www.impro-hausverwaltung.de"),
    ("IMV Immobilien Management", "https://www.imv.eu"),
    ("Johann Landstorfer Immobilien", "https://www.landstorfer-immobilien.de"),
    ("Krinninger Immobilien", "https://www.krinninger-immobilien.de"),
    ("Ljubicic Hausverwaltung", "https://www.ljubicic-gmbh.com"),
    ("MG Haus- und Vermögensverwaltung", "https://www.ww-hausverwaltung.de"),
    ("München Inter Hausverwaltung", "https://www.muenchen-inter.de"),
    ("P. Traut Hausverwaltung", "https://www.hausverwaltung-traut.de"),
    ("Prager Liegenschaftsverwaltung", "https://www.liegenschaften-prager.de"),
    ("Schuhmann Verwaltung", "https://www.schuhmann-muenchen.de"),
    ("Strondl Hausverwaltung", "https://www.strondl.com"),
    ("VOGT Gebäudeverwaltung", "https://www.vogt-management.de"),
    ("VOGT Holger Immobilien", "https://www.vogt-immobilien.de"),
    ("Wottschal Marina / Immowot", "https://www.immowot.de"),
    ("Zenveo Hausverwaltung", "https://www.zenveo.de"),
]


# ---------- DISABLED DOMAINS ----------
# Hosts die konsistent kaputt sind und niemals listings liefern.
# Adapter mit diesen Hosts werden in all_simple_adapters() übersprungen.
# Begründungen:
# - DNS NXDOMAIN: Domain existiert nicht (mehr)
# - Network unreachable: Server seit Wochen offline
# - HTTP 403 trotz UA-Spoofing: aktiver Anti-Bot (Cloudflare etc.)
# - HTTP 500: Server-Side broken
# - 404: Listing-Page gibt's nicht mehr
# Wenn eine Domain hier rein soll, einfach den Hostnamen anhängen.
DISABLED_DOMAINS: set[str] = {
    # DNS NXDOMAIN — domain existiert nicht
    "dietzelgbr.de",
    "partner-immobilienverwaltung.de",
    "frankeundpartner.com",
    "hausverwaltung-gollmann.de",
    "hahn-schmid.de",
    "teichmanngmbh-online.de",
    "nygr.de",
    "bayerische-hausverwaltung.de",
    "lunovalinner.de",
    "etcos-gmbh.de",
    "hausverwaltung-keilich-muenchen.de",
    "castle-hausverwaltung.de",
    "aufbau-west.org",
    "schmaus-immob-int.de",
    "mrh-immobilienverwaltung.de",
    "schuhmann-muenchen.de",
    "hausverwaltung-traut.de",
    # Network unreachable
    "leuchtenberger-immobilien.de",
    "efima-ag.eu",
    "adm-gmbh.net",
    "munich-property.de",   # gelegentlich
    "drescher-immobilien.de",  # gelegentlich
    # HTTP 403 — Cloudflare / Anti-Bot, mit UA-Spoofing nicht zu umgehen
    "big-hausverwaltung.de",
    "empetus.de",
    "global-immobilien.de",
    "animare-immobilien.de",
    "ihr-wegverwalter.de",
    "aigner-immobilien.de",
    "von-poll.com",
    "meinestadt.de",
    "mutzhas-immobilien.de",
    "harinali.de",
    # HTTP 500 — server side broken
    "bc-verwaltung.de",
    "gatt-immobilienverwaltung.de",
    # HTTP 404 — page gone
    "landstorfer-immobilien.de",
}


def all_simple_adapters() -> List[GenericTextAdapter]:
    """Alle Quellen als GenericTextAdapter-Instanzen.

    Source-Tuple kann sein:
      (name, url)                       → auto_discover=True (Standard)
      (name, url, auto_discover_bool)   → explizit gesetzt

    Quellen deren Host in DISABLED_DOMAINS steht werden übersprungen.
    """
    from urllib.parse import urlparse

    def _is_disabled(url: str) -> bool:
        host = urlparse(url).netloc.lower()
        host_no_www = host[4:] if host.startswith("www.") else host
        return host_no_www in DISABLED_DOMAINS or host in DISABLED_DOMAINS

    adapters = []
    skipped = 0
    for entry in (
        GENOSSENSCHAFTEN
        + HAUSVERWALTUNGEN_TOP
        + HAUSVERWALTUNGEN_HOCH
        + HAUSVERWALTUNGEN_MITTEL
        + HAUSVERWALTUNGEN_AUDIT
        + USER_SOURCES
    ):
        if len(entry) == 3:
            name, url, auto_discover = entry
        else:
            name, url = entry
            auto_discover = True
        if _is_disabled(url):
            skipped += 1
            continue
        adapters.append(
            GenericTextAdapter(name=name, list_url=url, auto_discover=auto_discover)
        )
    if skipped:
        import logging
        logging.getLogger(__name__).info(
            f"{skipped} Adapter via DISABLED_DOMAINS übersprungen"
        )
    return adapters
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
    # Immonet-White-Label-Portale (gleiches Backend, gleiche URL-Struktur)
    ("SZ Immobilien", "https://immobilienmarkt.sueddeutsche.de/suche/mieten-wohnung-in-muenchen"),
    ("FAZ Immobilien", "https://immobilienmarkt.faz.net/suche/mieten-wohnung-in-muenchen"),
    ("Idowa", "https://zuhause.idowa.de/suche/mieten-wohnung-in-muenchen"),
    ("Ab ins Zuhause", "https://www.ab-ins-zuhause.de/wohnung-mieten-muenchen"),
    ("Engel & Völkers", "https://www.engelvoelkers.com/de/de/immobilien/res/mieten/immobilien/bayern/muenchen"),
    ("Wohnglück", "https://wohnglueck.de/suche/de/bayern/muenchen/wohnung-mieten"),
    ("Rosenberger Immobilien", "https://rosenbergerimmobilien.de/ff/immobilien/?schema=flat_rent&price=&ffpage=1&sort=date"),
    ("Pandion Service", "https://pandion-service.de/immobilien/?post_type=immomakler_object&paged=1&lang=de&vermarktungsart=miete&nutzungsart=&typ=&ort=muenchen"),
    ("Immobilie1", "https://www.immobilie1.de/immobilien/bayern/muenchen/wohnung/mieten?sort=-created_at&page=1"),
    ("Munich Property", "https://www.munich-property.de/properties/?sort=date_desc"),
    ("Idowa Altstadt-Lehel", "https://zuhause.idowa.de/suche/mieten-wohnung-in-muenchen-altstadt-lehel-bez-mit-balkon"),
    ("Immobilo", "https://www.immobilo.de/mieten/wohnung/muenchen-kreis?s=most_recently_updated_first"),
    ("Nuroa", "https://www.nuroa.de/mieten/munchen-wohnung?order=1&way=2"),
    ("LEG Wohnen", "https://www.leg-wohnen.de/immobilien/mietwohnungen#/geo/48.13329869584388,11.576734033343515,12"),
    ("GVG Net", "https://www.gvgnet.de/mietobjekte-category/wohnobjekte/#objekte"),
    ("Walser Immobiliengruppe", "https://www.walser-immobiliengruppe.de/miete/"),
    ("KLN Immobilien", "https://kln-immobilien.de/vermietung-2/wohnungen/"),
    ("TUM Living", "https://living.tum.de/listings?viewMode=list&tumLocation=MUNICH&type=APARTMENT&rentTo=1550"),
    # --- Tageszeitungs- & Privat-Vermieter-Portale ---
    ("ohne-makler.net", "https://www.ohne-makler.net/immobilien/wohnung-mieten/bayern/munchen/", False),
    ("Münchner Wochenanzeiger", "https://www.wochenanzeiger.de/immobilien", False),
    # Entfernt (alle permanent tot seit Wochen):
    # - Wohnungsbörse München (DNS NXDOMAIN)
    # - meinestadt.de München: drin gelassen (HTTP 403, könnte zurückkommen)
    # - Abendzeitung München (HTTP 404)
    # - Münchner Merkur Immo (SSL Cert Mismatch)
    ("meinestadt.de München", "https://www.meinestadt.de/muenchen/immobilien/wohnungen"),
    ("Drescher Immobilien", "https://drescher-immobilien.de/mietangebote"),
    ("EP Immobilien", "https://www.ep-immobilien.com/?post_type=immomakler_object&vermarktungsart=miete&nutzungsart=wohnen"),
    ("Fleckenstein Immobilien", "https://fleckenstein-immobilien.com/mieten/"),
    ("Mutzhas Immobilien", "https://mutzhas-immobilien.de/immobilien/"),
    ("Harinali", "https://www.harinali.de/immobilienangebote/"),
    ("Hegerich Immobilien", "https://www.hegerich-immobilien.de/Mietangebote.htm"),
    ("Immobilien Lederer", "https://immobilien-lederer.de/angebote/angebote.html"),
    ("Dawonia", "https://www.dawonia.de/de/mieten?city=M%C3%BCnchen&items-per-page=100"),
    ("Vonovia", "https://www.vonovia.de/zuhause-finden/immobilien?rentType=miete&city=M%C3%BCnchen&immoType=wohnung"),
    ("Immobilien Schlamp", "https://www.immobilien-schlamp.de/index.php/mietangebote/"),
    ("Hausverwaltung-SG", "https://www.hausverwaltung-sg.de/"),
    ("RE/MAX Prime München", "https://prime-muenchen.remax.de/de/wohnung-mieten-in-muenchen/"),
    ("Wegener Immobilien", "https://www.wegenerimmobilien.de/Muenchen/Mietwohnungen-Muenchen.html"),
    ("Rogers Immobilien", "https://www.rogers-immobilien.de/immobilienangebote/"),
    # auto_discover=False für Sources mit spezifischen URLs/Query-Params
    # die sonst von Auto-Discovery überschrieben würden:
    ("KIP Immobilien", "https://www.kip.net/bayern/muenchen/mieten/wohnungen/1", False),
    ("Wohnreferat München", "https://www.wohnref-muenchen.de/immobilien/"),
    ("Garant Immo", "https://www.garant-immo.de/result.html?search=rent&t=rental-apartment&q=M%C3%BCnchen&qt=county", False),
    ("VR-Bank München Land", "https://www.vr-bank-muenchen-land.de/privatkunden/immobilie-und-wohnen/produkte/immobilien/immobiliensuche.html"),
    ("Lehmann Hueber", "https://lehmannhueber.de/immobilien/?post_type=immomakler_object&vermarktungsart=miete&nutzungsart=wohnen", False),
    ("Egger Immobilien", "https://egger-immo.de/immobilien/immobilien-muenchen/"),
    ("Immobilien PS", "https://www.immobilien-ps.de/aktuelle-mietangebote?slg=immomakler_object&mdf_cat=40&page_mdf=9134&order_by=mverfuegbarkeit&order=DESC", False),
    ("Roethig Immobilien", "https://www.roethig-immobilien.de/angebote/vermietung/", False),
    ("Pöttinger", "https://www.poettinger.com/de/miet-immobilien.html", False),
    ("ImmoSmart", "https://immosmart.de/mieten/"),
]

# ---------- HAUSVERWALTUNGEN ★ MITTEL (Auto-Discovery) ----------
# Aus der Excel "Hausverwaltungen_Muenchen_FINAL_SORT_2", gefiltert nach
# Lennarts Kern-Bezirken. Auto-Discovery findet Listing-Subpfade selbständig;
# EXCLUDE_PATH_KEYWORDS filtert Service-Pfade (Mieterwechsel, Vermieterservice
# etc.) raus. Die mit echten Listings liefern automatisch beim nächsten Run.
HAUSVERWALTUNGEN_MITTEL: list[tuple[str, str]] = [
    # --- Altstadt-Lehel ---
    ("DOMINO Haus- und Grundbesitz", "https://www.domino-muc.de"),
    ("Fries & Co Grundstücksverwaltung", "https://www.friesundco.de"),
    ("Hausverwaltung Heinz Zimmermann", "https://www.hausverwaltung-zimmermann.de"),
    ("Isaria Hausverwaltung", "https://www.isaria-hv.de"),
    ("Leuchtenberger Immobilien", "https://www.leuchtenberger-immobilien.de"),
    ("Stockmayr-Kielleuthner", "https://www.stockmayr.de"),
    ("Kribitzneck Anton Hausverwaltung", "https://www.hausverwaltung-kribitzneck.de"),
    # --- Maxvorstadt ---
    ("Arnold Ingeborg Immobilien", "https://www.arnold-immobilien-gmbh.de"),
    ("Concept-Real Hausverwaltungs", "https://concept-real.de"),
    ("Maneum Hausverwaltung", "https://www.maneum.de"),
    ("Ries Immobilien KG", "https://www.riesimmobilienkg.de"),
    ("Stoll Hausverwaltungen", "https://www.stoll-hv.de"),
    # --- Schwabing(-West) ---
    ("Dietzel GbR Vermietung", "https://dietzelgbr.de"),
    ("PARTNER Immobilien-Verwaltung", "https://www.partner-immobilienverwaltung.de"),
    ("DHG-Hausverwaltung Fischbaum", "https://www.ipg-gmbh.de"),
    ("EIGENSCHINK Grundstücksverwaltung", "https://www.eigenschink-gv.de"),
    ("Franke & Leal Hausverwaltung", "https://www.frankeundpartner.com"),
    ("Fritz Kuschel u Söhne", "https://www.hv-kuschel.de"),
    ("Günthert & Gollmann", "https://www.hausverwaltung-gollmann.de"),
    ("Hausverwaltung Potzler", "https://www.hv-potzler.de"),
    ("M-Haus Hausverwaltung", "https://www.m-haus.info"),
    ("MuM Real Estates / Winkler", "https://www.hv-winkler.de"),
    ("Schaefer Christian Hausverwaltung", "https://www.hausverwaltung-schaefer.de"),
    ("Interco Grundbesitz / Suedboden", "https://www.suedboden.com"),
    # --- Isarvorstadt / Ludwigsvorstadt ---
    ("B.I.G. Hausverwaltung", "https://www.big-hausverwaltung.de"),
    ("BC Hausverwaltung & Immobilien", "https://www.bc-verwaltung.de"),
    ("Enzenhöfer Hausverwaltung", "https://www.enzenhoefer-immobilien.de"),
    ("GATT Hausverwaltung", "https://www.gatt-immobilienverwaltung.de"),
    ("Hahn & Schmid Immobilien", "https://www.hahn-schmid.de"),
    ("HVK Grundbesitz", "https://www.hvk-grundbesitz.de"),
    ("Landlord Immobilien Verwaltung", "https://www.landlord-iv.de"),
    ("Dr. Hanns Maier / Hamabau", "https://www.hamabau.de"),
    ("MSH Immobilien", "https://www.msh-immobilien.de"),
    ("Schenk Mariele Hausverwaltung", "https://www.ra-schenk.de"),
    ("Schmid Stefan Hausverwaltung", "https://www.hv-schmid.de"),
    # --- Au-Haidhausen ---
    ("Brauner Fred Hausverwaltung", "https://www.hv-brauner.de"),
    ("Hausverwaltung Geisinger", "https://www.geisinger-hausverwaltung.de"),
    ("Gegenfurtner Helmut Hausverwaltung", "https://www.hv-gegenfurtner.de"),
    ("HAVAU Immobilien", "https://havau-hausverwaltung.de"),
    ("Prospera Immobilien", "https://www.prospera-immo.de"),
    # --- Sendling ---
    ("Grassl Gertraud Hausverwaltung", "https://www.grassl-hausverwaltung.de"),
    ("Hinterseer Peter Hausverwaltung", "https://www.hv-hinterseer.de"),
    ("Homewise GmbH", "https://www.homewise.de"),
    ("Küffel Werner Hausverwaltung", "https://www.kueffel-online.de"),
    ("J. Rüprich Hausverwaltungen", "https://www.rueprich.net"),
    # --- Schwanthalerhöhe / Westend ---
    ("Solitär Immobilienverwaltung", "https://immo.mbc1.de"),
    ("Teichmann Hausverwaltungen", "https://www.teichmanngmbh-online.de"),
    # --- Neuhausen / Nymphenburg ---
    ("Drost & Reidler / Voelkner", "https://www.voelkner-immo.de"),
    ("Hauskonzept Hausverwaltungs", "https://www.hauskonzept-gmbh.de"),
    ("Hausverwaltung Nymphenburg HVN", "https://www.hvny.de"),
    ("Merkl Haus- und Grundstücksverwaltung", "https://www.merkl-immob.com"),
    ("Nymphenburger Grund Verwaltung", "https://www.nygr.de"),
    ("Urbanski Hausverwaltung", "https://www.hv-urbanski.com"),
    # --- Bogenhausen ---
    ("Bayerische Hausbau Management", "https://www.bayerische-hausverwaltung.de"),
    ("Krautbauer Ernst Immobilien", "https://www.krautbauer.de"),
    ("Hausverwaltung Pharao", "https://www.pharaohaus.de"),
    ("VITA-Hausverwaltung", "https://www.vita-hausverwaltung.com"),
]

# ---------- HAUSVERWALTUNGEN AUDIT-POOL ----------
# Großzügig hinzugefügt nach Lennarts "so viele wie möglich"-Strategie.
# Auto-Discovery prüft selbst ob Listing-Seite existiert; EXCLUDE_PATH_KEYWORDS
# blockt Service-Pfade. Nach 3-4 Runs werden nicht-funktionierende rausgenommen.
HAUSVERWALTUNGEN_AUDIT: list[tuple[str, str]] = [
    # --- Chris-Quellen (vom User vorgemerkt) ---
    ("A&C Immobilien", "https://www.ac-immobilien-gmbh.de"),
    ("AV Immobilien", "https://www.av-immo.de"),
    ("Boos & Co Verwaltung", "https://www.boos-verwaltung.com"),
    ("CM CASA Hausverwaltung", "https://www.cm-casa-hausverwaltung.de"),
    ("conta Immobilien-Gruppe", "https://www.conta.eu"),
    ("DAHLER München", "https://www.dahlercompany.com"),
    ("Eichler Immobilien", "https://www.eichler.de"),
    ("Finestep Immobilien", "https://www.finestep.de"),
    ("Fritz N. Osterried Immobilien", "https://www.immobilien-osterried.de"),
    ("Hartlaub / Cocon Immobilienstiftung", "https://www.cocon.de"),
    ("HOMEFacilities Seelbach", "https://www.homefacilities.de"),
    ("IMCON Immobilien Consulting", "https://www.imcon.info"),
    ("Immobilien Zippold", "https://www.immobilien-zippold.de"),
    ("IntigrA Immobilien Management", "https://www.intigra-immobilien.de"),
    ("KITHAN GmbH", "https://www.kithan.de"),
    ("Norbert Marte Immobilien", "https://www.immobilienmarte.de"),
    ("Park Avenue Immobilien", "https://www.parkavenue.immobilien"),
    ("Projekt M Immobilien", "https://www.projektmimmobilien.de"),
    ("Schön Immobilien", "https://www.schoenimmobilien.de"),
    ("Westfalia Immobilienverwaltung", "https://www.westfalia-gmbh.de"),
    ("Andreas Hage Immobilien", "https://www.hage-immobilien.net"),
    ("Immobilien Boos", "https://www.immobilien-boos.de"),
    ("Immovision München", "https://www.immovision.de"),
    ("KLATTE Immobilien", "https://www.klatte-immobilien.de"),
    ("Tectareal Property Management", "https://www.tectareal.de"),

    # --- Weitere München-HVs (alle URLs aus Excel) ---
    ("Bayerische Immobilien Management", "https://www.bi-m.de"),
    ("Gruber Günther Hausverwaltung", "https://www.wohnungsangebote-muenchen.de"),
    ("ACM Immobilien Hausverwaltung", "https://www.acmgmbh.de"),
    ("anima Immobilien Verwaltung", "https://www.animare-immobilien.de"),
    ("ARCO / Zinkl Hausverwaltung", "https://www.hvzinkl.de"),
    ("Arendt Hausverwaltung", "https://www.arendt-hausverwaltung.de"),
    ("ASI Immobilienverwaltungen", "https://www.asi-iv.de"),
    ("Bettinger Norbert Hausverwaltung", "https://www.beno-immobilien.de"),
    ("BPV Hausverwaltung", "https://www.bpv-muenchen.de"),
    ("Cohaus München", "https://www.cohaus-muenchen.de"),
    ("Dall'Armi Immobilienverwaltung", "https://www.lunovalinner.de"),
    ("Dimperl & Sohn Hausverwaltung", "https://www.dimperl-muenchen.de"),
    ("Etcos Immobilien Management", "https://www.etcos-gmbh.de"),
    ("F. Schlagenhaufer Hausverwaltung", "https://www.immobilien-schlagenhaufer.de"),
    ("Fischer / Keilich Hausverwaltung", "https://www.hausverwaltung-keilich-muenchen.de"),
    ("Frommhold Maximilian Hausverwaltung", "https://www.maximilian-frommhold.de"),
    ("GFF Hausverwaltung", "https://www.gff-hv.de"),
    ("Hausgrund München", "https://www.hausgrund-muenchen.de"),
    ("Hausverwaltung Moosach / Meinhart", "https://www.hv-meinhart.de"),
    ("Hausverwaltung Schmidt", "https://www.schmidt-hausverwaltung.net"),
    ("Hausverwaltung WEMA", "https://www.wema-hausverwaltung.de"),
    ("E. Schmaus Hausverwaltung", "https://www.schmaus-immob-int.de"),
    ("HS-Immoteam", "https://hs-immoteam.jimdo.com"),
    ("Immler Martin Hausverwaltung", "https://www.immler.com"),
    ("Klaus Hausverwaltung", "https://www.klaus-immo.de"),
    ("Margot Ludl Immobilienbetreuung", "https://www.ludl-immobilien.de"),
    ("MHM Hausverwaltungs", "https://www.m-h-m.de"),
    ("mvh Immobilienverwaltung München", "https://www.mrh-immobilienverwaltung.de"),
    ("OBM Hausverwaltung München", "https://www.obm-hausverwaltung.de"),
    ("PARTNER Immobilien Vermittlung", "https://www.partnerimmobilienverwaltung.de"),
    ("Roth Immobilienverwaltung", "https://www.roth-immobilienverwaltung.de"),
    ("S2H Immobilienmanagement", "https://www.s2h-muenchen.de"),
    ("Schwerdt Tobias Immobilien", "https://www.schwerdt-immobilien.de"),
    ("SEHAG Hausverwaltung", "https://www.sehag.de"),
    ("Sollner Grundbesitzverwaltung", "https://www.sollner-grund.de"),
    ("Sonntag Horst Hausverwaltung", "https://www.hausverwaltung-sonntag.de"),
    ("Walger Grundstücksverwaltung", "https://www.verwaltung123.de"),
    ("ADM GmbH Hausverwaltung", "https://www.adm-gmbh.net"),
    ("admincasa Hausverwaltung", "https://www.admincasa.de"),
    ("ADVISUM Hausverwaltung", "https://www.advisum.de"),
    ("AIMAG Immobilien-Management", "https://www.aimag.de"),
    ("Arivon Service", "https://www.arivon.de"),
    ("Aufbau West Innovationspark HV", "https://www.aufbau-west.org"),
    ("Castle Eigentum", "https://www.castle-hausverwaltung.de"),
    ("D. Baumann Immobilien", "https://www.dbi-germany.de"),
    ("Diez Grundstücks", "https://www.diez-verwaltung.de"),
    ("EFIMA AG", "https://www.efima-ag.eu"),
    ("Empetus Hausverwaltung", "https://www.empetus.de"),
    ("Erl Wilhelm Verwaltung", "https://www.wilhelm-erl.de"),
    ("GEMA Gebäudemanagement", "https://www.gema-gebaeudemanagement.de"),
    ("GLOBAL Institut Immobilien", "https://www.global-immobilien.de"),
    ("Graphigrund Hausverwaltung", "https://www.graphigrund.de"),
    ("Gruber Herbert Hausverwaltung", "https://www.hv-gruber.de"),
    ("HADIEFA Hausverwaltung", "https://www.hadiefa.de"),
    ("Hammerla Hausverwaltung", "https://www.hausverwaltung-hammerla.de"),
    ("Hartmann Immoinvest", "https://www.hartmann-immoinvest.de"),
    ("Haus-Treu-Süd", "https://www.haus-treu-sued.de"),
    ("Danhuber Haus- und Vermögensverwaltung", "https://www.hausverwaltung-danhuber.de"),
    ("HGSK Hausverwaltung", "https://www.hgsk.eu"),
    ("HI Wohnbau", "https://www.hi-wohnbau.de"),
    ("HIS Real Estate", "https://www.hisrealestate.de"),
    ("Häusl Peter Hausverwaltung", "https://www.haeusl-hausverwaltung.de"),
    ("ifena Hausverwaltung", "https://www.ifena.de"),
    ("ihr-WEGVerwalter", "https://www.ihr-wegverwalter.de"),
    ("Jugan Investmentverwaltung", "https://www.jugan.de"),
    ("Scheel Immobilien", "https://www.scheel-immobilien.de"),
    ("Herbst Immobilienverwaltung", "https://www.daniel-immo.eu"),
    ("Immobilienbüro 24", "https://www.immobilienbuero24.de"),
    ("Impro Hausverwaltung", "https://www.impro-hausverwaltung.de"),
    ("IMV Immobilien Management", "https://www.imv.eu"),
    ("Johann Landstorfer Immobilien", "https://www.landstorfer-immobilien.de"),
    ("Krinninger Immobilien", "https://www.krinninger-immobilien.de"),
    ("Ljubicic Hausverwaltung", "https://www.ljubicic-gmbh.com"),
    ("MG Haus- und Vermögensverwaltung", "https://www.ww-hausverwaltung.de"),
    ("München Inter Hausverwaltung", "https://www.muenchen-inter.de"),
    ("P. Traut Hausverwaltung", "https://www.hausverwaltung-traut.de"),
    ("Prager Liegenschaftsverwaltung", "https://www.liegenschaften-prager.de"),
    ("Schuhmann Verwaltung", "https://www.schuhmann-muenchen.de"),
    ("Strondl Hausverwaltung", "https://www.strondl.com"),
    ("VOGT Gebäudeverwaltung", "https://www.vogt-management.de"),
    ("VOGT Holger Immobilien", "https://www.vogt-immobilien.de"),
    ("Wottschal Marina / Immowot", "https://www.immowot.de"),
    ("Zenveo Hausverwaltung", "https://www.zenveo.de"),
]


def all_simple_adapters() -> List[GenericTextAdapter]:
    """Alle Quellen als GenericTextAdapter-Instanzen.

    Source-Tuple kann sein:
      (name, url)                       → auto_discover=True (Standard)
      (name, url, auto_discover_bool)   → explizit gesetzt
    """
    adapters = []
    for entry in (
        GENOSSENSCHAFTEN
        + HAUSVERWALTUNGEN_TOP
        + HAUSVERWALTUNGEN_HOCH
        + HAUSVERWALTUNGEN_MITTEL
        + HAUSVERWALTUNGEN_AUDIT
        + USER_SOURCES
    ):
        if len(entry) == 3:
            name, url, auto_discover = entry
        else:
            name, url = entry
            auto_discover = True
        adapters.append(
            GenericTextAdapter(name=name, list_url=url, auto_discover=auto_discover)
        )
    return adapters
