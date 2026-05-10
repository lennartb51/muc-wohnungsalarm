# Münchner Wohnungsalarm

Pollt 17 Quellen (Portale, Genossenschaften, Hausverwaltungen) alle 20 Minuten,
filtert nach deinen Kriterien und schickt einen Telegram-Push, sobald ein
neues Inserat passt. Läuft komplett in GitHub Actions, **keine laufenden Kosten**.

## Aktive Quellen

**Portale (5)**
- Immowelt
- Kleinanzeigen.de
- Wohnungsboerse.net
- SZ Immobilien (Süddeutsche)
- WG-Gesucht (Filter: 1-Zi und Wohnungen, keine WG-Zimmer)

**Genossenschaften (10)**
- Wogeno · Wagnis · WGMW · VfV München · GIMA München (Aggregator)
- EBM München · Postbaugenossenschaft · HEIMAG
- BG Hartmannshofen · IWG

**Hausverwaltungen (2)**
- Rohrer Immobilien · Aigner Immobilien

Genossenschaften und Hausverwaltungen werden über einen `GenericTextAdapter`
abgewickelt, der jeden Block mit Listing-typischen Markern (m²/€/Zimmer) als
Wohnungsangebot erkennt — robust gegen die meisten HTML-Strukturänderungen.

## Architektur

```
GitHub Actions cron (alle 20 min)
    └── python -m src.main
        ├── 17 Adapter parallel ausgeführt → Listings
        │   ├── 5 spezifische Portal-Adapter (Immowelt, Kleinanzeigen, ...)
        │   └── 12 GenericTextAdapter (Genossenschaften, Hausverwaltungen)
        ├── State-Diff (data/seen.json)  → nur neue Inserate
        ├── Filter (config.yaml)          → nur passende Inserate
        └── Telegram-Bot                  → Push aufs Handy
```

State (gesehene Inserate) wird als JSON ins Repo zurück-committed —
einfach, debugbar, persistent über Runs hinweg.

## Setup (15 Minuten)

### 1. Repo aufsetzen

```bash
# Auf GitHub neues Repo "muc-wohnungsalarm" anlegen, dann:
git clone <dein-repo-url>
cd muc-wohnungsalarm
# Inhalt aus diesem Ordner reinkopieren
git add . && git commit -m "init" && git push
```

**Empfehlung:** Repo auf **public** stellen → GitHub Actions sind dann unbegrenzt
kostenlos. Bei private gilt das 2.000-min/Monat-Free-Tier; mit 20-min-Schedule
wirst du knapp drüber liegen, dann lieber `*/30 * * * *` im Workflow.

Secrets sind via GitHub Secrets verschlüsselt — auch in public Repos sicher.

### 2. Telegram-Bot erstellen

1. Telegram öffnen, [`@BotFather`](https://t.me/BotFather) anschreiben
2. `/newbot` schicken, Namen vergeben → du bekommst einen **Bot-Token**
   (sieht aus wie `8123456789:AAH...`)
3. Schreibe deinem neuen Bot einmal `/start`, damit er dir Nachrichten schicken
   darf
4. Deine **Chat-ID** ermitteln: Im Browser
   `https://api.telegram.org/bot<DEIN_TOKEN>/getUpdates` aufrufen,
   dort steht `"chat":{"id":123456789,...}` → das ist deine Chat-ID

### 3. Secrets im Repo eintragen

Repo auf GitHub → **Settings → Secrets and variables → Actions → New repository secret**:

| Name | Wert |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token vom BotFather |
| `TELEGRAM_CHAT_ID` | deine Chat-ID |

### 4. Filter einstellen

`config.yaml` öffnen, an deine Wünsche anpassen (max_price, Stadtteile,
Ausschluss-Keywords) und committen.

### 5. Manuell testen

Repo → **Actions → Wohnungsalarm → Run workflow** — startet sofort.
Im Log siehst du, was die Adapter gefunden haben.

Beim ersten Lauf landen **alle** aktuellen Inserate im State, ohne dich zu pingen
(weil State leer war → alles "neu" → in Telegram würden hunderte Nachrichten
landen). Falls du einen Trockenlauf willst:
- Setze TELEGRAM_BOT_TOKEN temporär leer
- Run starten → State befüllt sich
- Token wieder eintragen → ab da kommen nur noch wirklich neue Anzeigen

## Lokal entwickeln & debuggen

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
export TELEGRAM_BOT_TOKEN=...
export TELEGRAM_CHAT_ID=...
python -m src.main
```

Einzelnen Adapter testen:
```python
from src.adapters.wogeno import WogenoAdapter
for l in WogenoAdapter().fetch():
    print(l.title, l.price_cold, l.size_sqm, l.url)
```

## Neue Quelle hinzufügen

**Einfache Quelle (Genossenschaft, kleine Hausverwaltung)** — eine Zeile in
`src/adapters/sources.py`:

```python
GENOSSENSCHAFTEN = [
    # ...bestehende
    ("Mein Vermieter", "https://example.de/freie-wohnungen"),
]
```

Der `GenericTextAdapter` macht den Rest. Funktioniert bei ~80% der
Genossenschaften und kleinen Sites direkt.

**Komplexe Quelle (Portal, JS-rendered, eigene Logik nötig)** — eigenes File:

```python
# src/adapters/meine_quelle.py
from typing import Iterable
from bs4 import BeautifulSoup
from ..models import Listing
from .base import Adapter, parse_price, parse_sqm, parse_rooms

class MeineQuelleAdapter(Adapter):
    name = "Meine Quelle"
    URL = "https://example.de/wohnungen"

    def fetch(self) -> Iterable[Listing]:
        r = self.get(self.URL)
        soup = BeautifulSoup(r.text, "html.parser")
        for card in soup.select(".wohnung-card"):
            yield Listing(
                source=self.name,
                external_id=card["data-id"],
                url=card.find("a")["href"],
                title=card.select_one(".titel").text.strip(),
                price_cold=parse_price(card.select_one(".preis").text),
                size_sqm=parse_sqm(card.select_one(".groesse").text),
                rooms=parse_rooms(card.select_one(".zimmer").text),
            )
```

Dann in `src/adapters/__init__.py` zur `SPECIFIC_ADAPTER_CLASSES`-Liste.

## Weitere lohnende Quellen (noch nicht eingebaut)

- **Bauverein München** – bauverein-muenchen.de
- **WBG München-Süd** – wbg-muenchensued.de
- **EWG München** – ewg-muenchen.de
- **Baugenossenschaft München von 1871** (älteste DE-Genossenschaft)
- **Riedel Immobilien** – riedel-immobilien.de
- **Münchner Wohnen** (städtisch, 71k Wohnungen — aber WBS nötig)

Einfach in `sources.py` als `(Name, URL)`-Tupel ergänzen.

## Schwierige Quellen (Cloudflare/Anti-Bot)

ImmoScout24, Kleinanzeigen und teilweise Immowelt setzen Cloudflare ein. Wenn
HTTP 403/503 zurückkommt:

**Option A:** Adapter in `config.yaml` deaktivieren, kommerzielles Tool für
diese Quellen abonnieren (Wohnungshelden, Immosuchmaschine.de, ~5–15 €/Monat).
Hybrid-Strategie: Custom-Scraper für die Long-Tail-Quellen, kommerzielles Tool
für die großen Portale.

**Option B:** Auf Playwright umstellen — kann echte Browser-Sessions fahren.
Dafür `playwright` in requirements.txt, im Workflow `playwright install
chromium` ergänzen, im Adapter statt `self.get()` einen Playwright-Context
nutzen. Funktioniert, ist aber zäher (Run dauert 3–5 min statt 30 sek).

**Option C:** Bei Kleinanzeigen einen authentifizierten Search-Alarm anlegen
(per Email) und einen separaten Email-zu-Telegram-Forwarder (z.B. Mailgun
+ Webhook → Telegram). Out of scope für dieses Repo, aber mit minimal Aufwand
machbar.

## Troubleshooting

**"Kein State-Change, kein Commit"** – normal, heißt nur dass keine neuen
Inserate gefunden wurden.

**Telegram bekommt nichts, aber Logs zeigen Treffer** – Bot-Token oder Chat-ID
falsch, oder du hast dem Bot nicht einmal `/start` geschrieben.

**Ein Adapter wirft Exceptions** – kein Problem, die Fehler werden geloggt aber
killen den Run nicht. Die anderen Adapter laufen weiter. Den kaputten Adapter
in `config.yaml` unter `disabled_adapters` listen, bis du ihn fixt.

**Zu viele Pings** – Filter in `config.yaml` enger ziehen. Bei den ersten paar
Tagen kommt erfahrungsgemäß mehr durch, weil viele Quellen ältere Listings als
"neu" reporten — das pendelt sich nach 2–3 Tagen ein.

**Eine Quelle gibt 404 / 0 Listings zurück** – sehr wahrscheinlich hat sich
die "Freie Wohnungen"-URL der Site geändert. In `src/adapters/sources.py` die
URL korrigieren. Du findest sie meist über die Hauptdomain → Navigation
"Wohnen" oder "Aktuelle Angebote". Bis du fixt: in `config.yaml` unter
`disabled_adapters` listen.

**Eine Quelle liefert plötzlich tausende Listings** – passiert wenn der
GenericTextAdapter zu viele Blöcke als Listing einstuft. Die Heuristik
verlangt 2+ Marker (m²/€/Zimmer) im Text. Wenn eine Site Newsletter-Boxen
hat die zufällig "€" und "Zimmer" enthalten, hilfst du am besten mit einem
spezifischen Adapter (siehe oben).

## Rechtliches

- Höfliches Rate-Limit (2–4 Sek. zwischen Requests)
- Realistischer User-Agent
- Keine Speicherung personenbezogener Daten
- Nur öffentlich erreichbare Seiten
- Bei expliziten Hinweisen in robots.txt oder ToS: Adapter abschalten

Das System ist für deinen privaten Gebrauch. Kein Weiterverkauf der Daten.
