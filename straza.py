# -*- coding: utf-8 -*-
"""
straza.py — javi se čim se natječaj pojavi na izvoru koji čekamo

Zasto postoji. Stranica o STEM stipendijama tvrdi da javni poziv jos nije
raspisan. To je tocno dok je tocno — a ministar ga po pravilniku mora
raspisati do 25. listopada. Onog trenutka kad izade, a stranica i dalje
tvrdi suprotno, ta se tvrdnja prenosi dalje: stipendije.hr vec citiraju
i AI trazilice, uz Ministarstvo i Sveuciliste. Kriva tvrdnja onda ne
steti samo nama nego ljudima kojima tada tece rok.

Redovni scrape ide ponedjeljkom i cetvrtkom. Poziv moze izaci u utorak.
Zato ova straza ide svaki dan, ne trosi model i ne dira stranicu — samo
dohvati stranicu izvora i javi.

Javlja se u dva slucaja:
  1. na stranici se pojavi tekst koji izgleda kao poziv za ovu godinu
  2. stranica se promijenila otkad smo je zadnji put gledali

Drugi slucaj postoji jer ne znamo kako ce poziv biti nazvan. Ministarstvo
ga zna objaviti kao "Javni poziv", "Natjecaj" ili samo kao poveznicu na
PDF. Promjena stranice je grublji znak, ali ne propusta.

Stanje se pamti u .straza.json i mijenja se tek kad covjek potvrdi da je
vidio — inace bi prva promjena ugasila stražu.
"""
import hashlib
import json
import os
import re
import sys

import requests
from bs4 import BeautifulSoup

STANJE = ".straza.json"
IZVJESTAJ = "straza.md"

# Sto se gleda. (kljuc, naziv, adresa, godina koja znaci "ovogodisnji")
STRAZE = [
    ("stem", "STEM stipendije",
     "https://mzom.gov.hr/drzavne-stipendije-za-studente-u-stem-podrucjima-znanosti/1562",
     "2026"),
]

ZAGLAVLJE = {"User-Agent": "stipendije.hr straza (+https://stipendije.hr)"}


def tekst(url):
    r = requests.get(url, headers=ZAGLAVLJE, timeout=30)
    r.raise_for_status()
    if "charset" not in (r.headers.get("Content-Type") or ""):
        r.encoding = r.apparent_encoding or r.encoding
    s = BeautifulSoup(r.text, "html.parser")
    for t in s(["script", "style", "nav", "footer", "header"]):
        t.decompose()
    redovi = [x.strip() for x in s.get_text("\n").splitlines() if x.strip()]
    return "\n".join(redovi), r.text


def poziv_za_godinu(cist, html, godina):
    """Izgleda li na stranici da je poziv za trazenu godinu vec objavljen.

    Trazi se poveznica ili recenica koja spominje i poziv i obje godine
    akademske godine. Lanjski poziv ima lanjske godine, pa ne upada."""
    sljedeca = str(int(godina) + 1)
    kandidati = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html, re.I | re.S):
        spoj = (m.group(1) + " " + re.sub(r"<[^>]+>", " ", m.group(2))).lower()
        if (("poziv" in spoj or "natjeca" in spoj)
                and godina in spoj and sljedeca in spoj):
            kandidati.append(m.group(1))
    for red in cist.splitlines():
        n = red.lower()
        if (("javni poziv" in n or "natječaj" in n)
                and godina in n and sljedeca in n):
            kandidati.append(red[:160])
    return kandidati[:5]


def main():
    staro = {}
    if os.path.exists(STANJE):
        try:
            staro = json.load(open(STANJE, encoding="utf-8"))
        except ValueError:
            staro = {}

    javi, novo = [], dict(staro)
    for kljuc, naziv, url, godina in STRAZE:
        try:
            cist, html = tekst(url)
        except Exception as e:
            print(f"  ! {naziv}: izvor se ne javlja ({e})")
            continue

        otisak = hashlib.sha256(cist.encode("utf-8")).hexdigest()[:16]
        prije = staro.get(kljuc) or {}
        nadeno = poziv_za_godinu(cist, html, godina)
        promjena = bool(prije.get("otisak")) and prije["otisak"] != otisak

        novo[kljuc] = {"otisak": otisak, "url": url}

        if nadeno:
            javi.append((naziv, url, "Poziv za ovu godinu izgleda objavljen.",
                         nadeno))
            print(f"  ! {naziv}: nađen poziv za {godina}./{int(godina)+1}.")
        elif promjena:
            javi.append((naziv, url, "Stranica se promijenila. Ne znamo što "
                                     "se promijenilo — pogledaj.", []))
            print(f"  ! {naziv}: stranica se promijenila")
        else:
            print(f"  = {naziv}: bez promjene")

    json.dump(novo, open(STANJE, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    if not javi:
        if os.path.exists(IZVJESTAJ):
            os.remove(IZVJESTAJ)
        return 0

    L = ["# Straža javlja", ""]
    for naziv, url, zasto, nadeno in javi:
        L += [f"## {naziv}", "", zasto, "", f"Izvor: {url}", ""]
        if nadeno:
            L += ["Što je nađeno:", ""]
            L += [f"- `{x[:150]}`" for x in nadeno]
            L.append("")
    L += ["---", "",
          "**Ako je poziv stvarno objavljen**, u `stem.py` postavi "
          "`OTVOREN = True`, upiši `ROK` i `POVEZNICA`, pa pokreni "
          "**Samo stranica**.", "",
          "Dok to ne napraviš, stranica tvrdi da poziv nije raspisan — a tu "
          "tvrdnju prenose dalje i tražilice.", ""]
    open(IZVJESTAJ, "w", encoding="utf-8").write("\n".join(L) + "\n")
    return 1


if __name__ == "__main__":
    sys.exit(main())
