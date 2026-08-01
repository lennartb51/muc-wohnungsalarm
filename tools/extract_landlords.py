#!/usr/bin/env python3
"""Vermieter-Namen aus den eigenen Portal-Alert-Mails extrahieren.

Zweck
-----
Jede IS24-/Immowelt-Alert-Mail nennt den Anbieter des Inserats. Über Wochen
sammelt sich im Alert-Postfach damit automatisch eine Liste genau derjenigen
Vermieter, die in DEINEN Suchgebieten tatsächlich inserieren — gewichtet nach
Häufigkeit. Das ist zielgenauer als jede allgemeine Maklerliste.

Dieses Skript liest das Postfach, extrahiert die Anbieternamen, zählt sie und
gibt eine Rangliste aus. Die Top-Namen googelst du kurz, und wenn sie eine
eigene Angebotsseite haben, wandern sie in sources.py.

Wichtig: das Skript liest nur DEIN Postfach. Es greift nicht auf die
Anbieter-Datenbanken der Portale zu — die ist durch deren Nutzungsbedingungen
gegen automatisiertes Auslesen geschützt.

Aufruf
------
    export EMAIL_IMAP_USER="lennart.wohnungsalarm@gmail.com"
    export EMAIL_IMAP_PASSWORD="<16-stelliges App-Passwort>"

    python3 tools/extract_landlords.py                  # letzte 500 Mails
    python3 tools/extract_landlords.py --limit 2000     # mehr Historie
    python3 tools/extract_landlords.py --folder "[Gmail]/Alle Nachrichten"
    python3 tools/extract_landlords.py --min-count 3    # nur ab 3 Treffern
    python3 tools/extract_landlords.py --csv out.csv

Read-only: setzt keine Flags, verändert keine Mails, markiert nichts als
gelesen (nutzt BODY.PEEK).
"""
from __future__ import annotations

import argparse
import email
import html as htmllib
import imaplib
import os
import re
import sys
from collections import Counter
from email.message import Message

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("Fehlt: beautifulsoup4  →  pip install beautifulsoup4", file=sys.stderr)
    sys.exit(1)


KNOWN_PORTAL_SENDERS = (
    "immobilienscout24", "immowelt", "immonet", "kleinanzeigen",
    "wg-gesucht", "wohnungsboerse", "ohne-makler", "immobilo", "nuroa",
    "sueddeutsche", "immobilienmarkt",
)

# Muster, mit denen Portale den Anbieter im Mail-Body auszeichnen.
# Reihenfolge = Priorität: spezifischere Muster zuerst.
PROVIDER_PATTERNS = (
    re.compile(r"Anbieter\s*[:\-]?\s*([^\n<|•·]{3,70})", re.I),
    re.compile(r"Angeboten\s+von\s*[:\-]?\s*([^\n<|•·]{3,70})", re.I),
    re.compile(r"Inseriert\s+von\s*[:\-]?\s*([^\n<|•·]{3,70})", re.I),
    re.compile(r"Vermieter\s*[:\-]?\s*([^\n<|•·]{3,70})", re.I),
    re.compile(r"Ihr\s+Ansprechpartner\s*[:\-]?\s*([^\n<|•·]{3,70})", re.I),
    re.compile(r"Kontakt\s*[:\-]?\s*([^\n<|•·]{3,70})", re.I),
)

# Firmen-Rechtsformen und Branchenwörter — ein Treffer hier ist ein starkes
# Signal, dass die Zeile wirklich ein Anbietername ist und nicht Fließtext.
COMPANY_MARKERS = (
    "gmbh", "mbh", "ag", "kg", "ohg", "gbr", "e.g.", " eg", "e. g.",
    "immobilien", "hausverwaltung", "verwaltung", "immo", "makler",
    "wohnbau", "wohnungsbau", "baugenossenschaft", "genossenschaft",
    "bauverein", "grundbesitz", "grundstueck", "grundstücks",
    "real estate", "properties", "property", "estate", "wohnen",
    "hausbau", "siedlung", "treuhand", "asset", "invest",
)

# Zeilen, die nach Anbietername aussehen, aber keiner sind.
NOISE_PATTERNS = (
    re.compile(r"^\s*(privat|privatanbieter|privatperson)\s*$", re.I),
    re.compile(r"immobilienscout|immowelt|immonet|kleinanzeigen|wg-gesucht", re.I),
    re.compile(r"newsletter|abmelden|unsubscribe|datenschutz|impressum", re.I),
    re.compile(r"^\s*(mehr|details|weiter|hier|jetzt|zum)\b", re.I),
    re.compile(r"^\s*\d+[\s.,]*$"),
    re.compile(r"@"),               # Mailadressen
    re.compile(r"^\s*https?://", re.I),
)


def clean_name(raw: str) -> str | None:
    """Normalisiert einen Kandidaten. Gibt None zurück, wenn unbrauchbar."""
    if not raw:
        return None
    s = htmllib.unescape(raw)
    s = re.sub(r"\s+", " ", s).strip(" \t\r\n-–—:;,.|•·*")
    # Alles nach einem Trennzeichen abschneiden (oft folgt Adresse/Telefon)
    s = re.split(r"\s{2,}|\||•|·|\bTel\.?\b|\bTelefon\b", s)[0].strip(" -–—:,.")
    if not (3 <= len(s) <= 70):
        return None
    if any(p.search(s) for p in NOISE_PATTERNS):
        return None
    if not any(m in s.lower() for m in COMPANY_MARKERS):
        return None
    # Reine Großschreibung leserlich machen ("MEIER IMMOBILIEN GMBH")
    if s.isupper() and len(s) > 8:
        s = s.title()
    return s


def body_text(msg: Message) -> str:
    """HTML- oder Text-Body als reinen Text."""
    def decode(part: Message) -> str:
        payload = part.get_payload(decode=True)
        if not payload:
            return ""
        charset = part.get_content_charset() or "utf-8"
        try:
            return payload.decode(charset, errors="replace")
        except LookupError:
            return payload.decode("utf-8", errors="replace")

    html_parts, text_parts = [], []
    if msg.is_multipart():
        for part in msg.walk():
            ctype = part.get_content_type()
            if ctype == "text/html":
                html_parts.append(decode(part))
            elif ctype == "text/plain":
                text_parts.append(decode(part))
    else:
        (html_parts if msg.get_content_type() == "text/html" else text_parts).append(decode(msg))

    if html_parts:
        return BeautifulSoup("\n".join(html_parts), "html.parser").get_text("\n", strip=True)
    return "\n".join(text_parts)


def extract_from_body(text: str) -> list[str]:
    found = []
    for pattern in PROVIDER_PATTERNS:
        for match in pattern.finditer(text):
            name = clean_name(match.group(1))
            if name and name not in found:
                found.append(name)
    # Fallback: Zeilen, die für sich schon wie ein Firmenname aussehen
    if not found:
        for line in text.split("\n"):
            line = line.strip()
            if 6 <= len(line) <= 70 and any(m in line.lower() for m in COMPANY_MARKERS):
                name = clean_name(line)
                if name and name not in found:
                    found.append(name)
                if len(found) >= 3:
                    break
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--folder", default="INBOX",
                    help='Postfach. Für die volle Historie: "[Gmail]/Alle Nachrichten"')
    ap.add_argument("--limit", type=int, default=500, help="Anzahl neuester Mails (default 500)")
    ap.add_argument("--min-count", type=int, default=2, help="Mindest-Trefferzahl (default 2)")
    ap.add_argument("--csv", help="Ergebnis zusätzlich als CSV schreiben")
    # or-Verknüpfung statt get-Default: GitHub Actions setzt fehlende Secrets
    # als leeren String, nicht als "nicht vorhanden".
    ap.add_argument("--host",
                    default=os.environ.get("EMAIL_IMAP_HOST") or "imap.gmail.com")
    ap.add_argument("--list-folders", action="store_true",
                    help="Nur die verfügbaren Postfächer anzeigen und beenden")
    args = ap.parse_args()

    user = os.environ.get("EMAIL_IMAP_USER")
    password = os.environ.get("EMAIL_IMAP_PASSWORD")
    if not user or not password:
        print("EMAIL_IMAP_USER und EMAIL_IMAP_PASSWORD müssen gesetzt sein.", file=sys.stderr)
        return 1

    if args.list_folders:
        try:
            with imaplib.IMAP4_SSL(args.host) as imap:
                imap.login(user, password)
                status, folders = imap.list()
                if status != "OK":
                    print("Postfach-Liste konnte nicht abgerufen werden.", file=sys.stderr)
                    return 1
                print("Verfügbare Postfächer:\n")
                for raw in folders:
                    line = raw.decode(errors="replace")
                    # Format: (\HasNoChildren) "/" "INBOX"
                    match = re.search(r'"([^"]*)"\s*$', line)
                    name = match.group(1) if match else line
                    print(f'  --folder "{name}"')
                print("\nFür die volle Historie ist der Ordner mit 'All' bzw. 'Alle' der richtige.")
        except Exception as exc:
            print(f"IMAP-Fehler: {exc}", file=sys.stderr)
            return 1
        return 0

    counter: Counter[str] = Counter()
    per_source: dict[str, Counter[str]] = {}
    scanned = portal_mails = 0

    try:
        with imaplib.IMAP4_SSL(args.host) as imap:
            imap.login(user, password)
            status, _ = imap.select(f'"{args.folder}"', readonly=True)
            if status != "OK":
                print(f"Postfach {args.folder!r} nicht gefunden.", file=sys.stderr)
                return 1

            status, data = imap.search(None, "ALL")
            if status != "OK":
                print("IMAP-Suche fehlgeschlagen.", file=sys.stderr)
                return 1

            ids = data[0].split()[-args.limit:]
            print(f"Durchsuche {len(ids)} Mails in {args.folder!r} …\n")

            for i, mid in enumerate(ids, 1):
                if i % 100 == 0:
                    print(f"  … {i}/{len(ids)}")
                # BODY.PEEK verändert das \Seen-Flag nicht
                status, payload = imap.fetch(mid, "(BODY.PEEK[])")
                if status != "OK" or not payload or not payload[0]:
                    continue
                scanned += 1
                msg = email.message_from_bytes(payload[0][1])
                sender = (msg.get("From") or "").lower()
                portal = next((p for p in KNOWN_PORTAL_SENDERS if p in sender), None)
                if not portal:
                    continue
                portal_mails += 1
                for name in extract_from_body(body_text(msg)):
                    counter[name] += 1
                    per_source.setdefault(portal, Counter())[name] += 1
    except Exception as exc:
        print(f"IMAP-Fehler: {exc}", file=sys.stderr)
        return 1

    print(f"\n{scanned} Mails gelesen, davon {portal_mails} Portal-Alerts.")
    print(f"{len(counter)} verschiedene Anbieter erkannt.\n")

    results = [(n, c) for n, c in counter.most_common() if c >= args.min_count]
    if not results:
        print(f"Keine Anbieter mit mindestens {args.min_count} Treffern. "
              f"Versuche --min-count 1 oder ein größeres --limit.")
        return 0

    width = min(max(len(n) for n, _ in results), 52)
    print(f"{'Anbieter':<{width}}  Inserate")
    print("─" * (width + 12))
    for name, count in results:
        print(f"{name[:width]:<{width}}  {count:>5}")

    print("\nNächster Schritt: die Namen von oben nach unten kurz googeln.")
    print("Wer eine eigene Angebotsseite hat, kommt in USER_SOURCES in")
    print("src/adapters/sources.py — Format: (\"Name\", \"https://…\"),")

    if args.csv:
        import csv
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            writer = csv.writer(fh)
            writer.writerow(["anbieter", "inserate_gesamt"] + sorted(per_source))
            for name, count in results:
                writer.writerow([name, count] + [per_source[p].get(name, 0)
                                                 for p in sorted(per_source)])
        print(f"\nCSV geschrieben: {args.csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
