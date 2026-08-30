#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dijagnostika.py — zdravstveni pregled svih izvora

Cita output.json i sources.json i slaze izvjestaj: koji izvori rade,
koji padaju i zasto, poredano po ozbiljnosti.

Pokretanje:
    python dijagnostika.py

Zapisuje dijagnostika.md (za citanje) i dijagnostika.csv (za Excel).
Ne mijenja nista drugo i ne trosi API.
"""
import csv
import json
import os
import re
from collections import Counter
from datetime import datetime

IZLAZ = "output.json"
IZVORI = "sources.json"
MD = "dijagnostika.md"
CSV = "dijagnostika.csv"


def razvrstaj(status):
    """Vrati (ozbiljnost, oznaka, objasnjenje). Manji broj = hitnije."""
    s = status or ""
    if s.startswith("GREŠKA"):
        if "nedostupna" in s:
            return 1, "NE RADI", "stranica se ne dohvaca (404, timeout ili blokada)"
        return 1, "NE RADI", "greska pri obradi"
    if s.startswith("PROVJERITI"):
        return 2, "SUMNJIVO", "natjecaj prepoznat, ali rok nije procitan"
    if s.startswith("OTVORENO"):
        return 4, "OTVORENO", "natjecaj je otvoren"
    if s.startswith("ROK ISTEKAO"):
        return 5, "ZATVORENO", "rok je prosao, ceka se novi ciklus"
    if s.startswith("NEMA AKTIVNOG"):
        return 3, "TIHO", "stranica radi, ali nista nije prepoznato"
    return 3, "TIHO", "nepoznat status"


def main():
    if not os.path.exists(IZLAZ):
        print(f"GRESKA: nema {IZLAZ}. Pokreni prvo scraper.")
        return

    rez = json.load(open(IZLAZ, encoding="utf-8"))
    izv = {}
    if os.path.exists(IZVORI):
        izv = {s["url"].rstrip("/"): s
               for s in json.load(open(IZVORI, encoding="utf-8"))}

    redovi = []
    for r in rez:
        oz, kratko, zasto = razvrstaj(r.get("status"))
        k = (r.get("url") or "").rstrip("/")
        s = izv.get(k, {})
        redovi.append({
            "ozbiljnost": oz,
            "stanje": kratko,
            "naziv": r.get("naziv", ""),
            "kategorija": r.get("kategorija", ""),
            "podrucje": s.get("podrucje", ""),
            "zasto": zasto,
            "status": r.get("status", ""),
            "iznos": r.get("iznos") or "",
            "rok": r.get("rok_tekst") or "",
            "url": r.get("url", ""),
        })
    redovi.sort(key=lambda x: (x["ozbiljnost"], x["naziv"]))

    broj = Counter(x["stanje"] for x in redovi)
    ukupno = len(redovi)
    radi = ukupno - broj["NE RADI"]
    postotak = (radi / ukupno * 100) if ukupno else 0

    # --- izvjestaj ---
    L = []
    L.append("# Dijagnostika izvora")
    L.append("")
    L.append(f"Napravljeno {datetime.now().strftime('%d.%m.%Y. u %H:%M')}")
    L.append(f"· {ukupno} izvora · {radi} dohvatljivo ({postotak:.0f}%)")
    L.append("")

    L.append("## Sažetak")
    L.append("")
    L.append("| Stanje | Broj | Znači |")
    L.append("|---|---|---|")
    opisi = [
        ("NE RADI", "stranica se ne dohvaca — **popraviti prije rujna**"),
        ("SUMNJIVO", "natjecaj postoji, rok nije procitan — provjeriti rucno"),
        ("OTVORENO", "natjecaj je otvoren upravo sad"),
        ("TIHO", "stranica radi, nista nije prepoznato (ocekivano izvan sezone)"),
        ("ZATVORENO", "rok je prosao"),
    ]
    for ime, opis in opisi:
        if broj.get(ime):
            L.append(f"| **{ime}** | {broj[ime]} | {opis} |")
    L.append("")

    if broj.get("NE RADI"):
        L.append("## Ne radi — popraviti")
        L.append("")
        L.append("Ovi izvori u rujnu **nece uhvatiti nista**, a stranica to nece")
        L.append("prikazati kao gresku. Svaki treba novi URL ili oznaku za rucnu provjeru.")
        L.append("")
        L.append("| Izvor | Područje | Problem |")
        L.append("|---|---|---|")
        for x in redovi:
            if x["stanje"] == "NE RADI":
                st = x["status"].replace("|", "/")[:70]
                L.append(f"| {x['naziv']} | {x['podrucje']} | {st} |")
        L.append("")

    if broj.get("SUMNJIVO"):
        L.append("## Sumnjivo — provjeriti ručno")
        L.append("")
        L.append("Sustav je prepoznao natjecaj, ali nije uspio procitati rok.")
        L.append("Ovo se javno **ne prikazuje**, pa student te stipendije ne vidi.")
        L.append("")
        L.append("| Izvor | Rok kako je procitan | URL |")
        L.append("|---|---|---|")
        for x in redovi:
            if x["stanje"] == "SUMNJIVO":
                L.append(f"| {x['naziv']} | {x['rok'] or '—'} | {x['url'][:60]} |")
        L.append("")

    if broj.get("OTVORENO"):
        L.append("## Otvoreno sada")
        L.append("")
        L.append("**Ovo su izvori za rucnu provjeru tocnosti.** Otvori svaki i usporedi")
        L.append("rok i iznos sa sluzbenom stranicom.")
        L.append("")
        L.append("| Izvor | Iznos | Rok | Provjereno? |")
        L.append("|---|---|---|---|")
        for x in redovi:
            if x["stanje"] == "OTVORENO":
                L.append(f"| {x['naziv']} | {x['iznos'][:34] or '—'} "
                         f"| {x['rok'][:26] or '—'} | ☐ |")
        L.append("")

    # tihi izvori po kategoriji — korisno za procjenu je li tisina ocekivana
    tihi = [x for x in redovi if x["stanje"] == "TIHO"]
    if tihi:
        L.append("## Tiho")
        L.append("")
        L.append(f"{len(tihi)} izvora radi, ali sustav na njima nista ne prepoznaje.")
        L.append("Izvan sezone je to ocekivano. **U listopadu vise nije** — tada")
        L.append("svaki tihi izvor treba provjeriti rucno.")
        L.append("")
        po_kat = Counter(x["kategorija"] for x in tihi)
        L.append("| Kategorija | Tihih |")
        L.append("|---|---|")
        for k, n in po_kat.most_common():
            L.append(f"| {k or 'bez kategorije'} | {n} |")
        L.append("")

    L.append("## Što dalje")
    L.append("")
    if broj.get("NE RADI"):
        L.append(f"1. Popravi {broj['NE RADI']} izvora koji ne rade — to je jedini")
        L.append("   posao koji stvarno mijenja ishod sezone")
    if broj.get("SUMNJIVO"):
        L.append(f"2. Provjeri {broj['SUMNJIVO']} sumnjivih — mozda skrivaju otvoren natjecaj")
    L.append("3. Kad promijenis URL, cache se sam osvjezava za taj izvor")
    L.append("4. Izvore koji uporno blokiraju oznaci kao rucne i ne gubi vrijeme")

    open(MD, "w", encoding="utf-8").write("\n".join(L) + "\n")

    with open(CSV, "w", encoding="utf-8-sig", newline="") as f:
        f.write("sep=,\n")
        w = csv.DictWriter(f, fieldnames=list(redovi[0].keys()))
        w.writeheader()
        w.writerows(redovi)

    # --- ispis u terminal ---
    print(f"\n{'='*54}")
    print(f"  {ukupno} izvora · {radi} dohvatljivo ({postotak:.0f}%)")
    print(f"{'='*54}")
    for ime, _ in opisi:
        if broj.get(ime):
            print(f"  {ime:11} {broj[ime]:3}")
    print()
    if broj.get("NE RADI"):
        print("NE RADI:")
        for x in redovi:
            if x["stanje"] == "NE RADI":
                print(f"  - {x['naziv'][:46]:48} {x['status'][:44]}")
        print()
    print(f"Detalji: {MD} i {CSV}")


if __name__ == "__main__":
    main()
