#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
provjeri_tisinu.py — hvata TIHE greske.

Najopasniji kvar nije kad scraper pukne (to se vidi), nego kad grad
redizajnira stranicu pa AI vise ne prepozna natjecaj. Sustav tada mirno
javi "nema aktivnog natjecaja" i sve izgleda uredno.

Ova skripta usporeduje ocekivani mjesec objave (polje "ocekivano" u
sources.json) sa stvarnim stanjem. Ako je mjesec prosao, a izvor jos
uvijek suti, ispisuje upozorenje.

Pokrece se iz workflowa nakon scrapera. Izlazni kod je uvijek 0 —
ovo je obavijest, ne greska.
"""
import json
import os
import sys
from datetime import date

IZVORI = "sources.json"
IZLAZ = "output.json"
PORUKA = "tisina.md"

MJESECI = {
    "siječanj": 1, "sijecanj": 1, "veljača": 2, "veljaca": 2,
    "ožujak": 3, "ozujak": 3, "travanj": 4, "svibanj": 5, "lipanj": 6,
    "srpanj": 7, "kolovoz": 8, "rujan": 9, "listopad": 10,
    "studeni": 11, "prosinac": 12,
}


def mjesec_iz(tekst):
    """'početak listopada' -> 10. Vraca None ako ne prepozna."""
    if not tekst:
        return None
    t = tekst.lower()
    najraniji = None
    for ime, br in MJESECI.items():
        korijen = ime[:-1] if len(ime) > 4 else ime
        poz = t.find(korijen)
        if poz != -1 and (najraniji is None or poz < najraniji[0]):
            najraniji = (poz, br)
    return najraniji[1] if najraniji else None


def main():
    if not (os.path.exists(IZVORI) and os.path.exists(IZLAZ)):
        print("Nema potrebnih datoteka, preskacem.")
        return

    izvori = {s["url"].rstrip("/"): s
              for s in json.load(open(IZVORI, encoding="utf-8"))}
    rezultati = json.load(open(IZLAZ, encoding="utf-8"))

    danas = date.today()
    tihi = []

    for r in rezultati:
        k = (r.get("url") or "").rstrip("/")
        s = izvori.get(k)
        if not s:
            continue
        ocek = mjesec_iz(s.get("ocekivano"))
        if not ocek:
            continue

        status = r.get("status") or ""
        if status.startswith("OTVORENO"):
            continue                      # sve u redu

        # koliko je mjeseci proslo od ocekivanog (unutar iste sezone)
        razlika = (danas.month - ocek) % 12
        # javljamo tek nakon punog mjeseca zakasnjenja, i to najvise
        # dva mjeseca — poslije toga je natjecaj vjerojatno stvarno zavrsio
        if 1 <= razlika <= 2:
            tihi.append({
                "naziv": s.get("naziv", ""),
                "podrucje": s.get("podrucje", ""),
                "ocekivano": s.get("ocekivano", ""),
                "status": status,
                "url": s.get("url", ""),
            })

    if not tihi:
        print("Nema izvora koji sute duze od ocekivanog.")
        if os.path.exists(PORUKA):
            os.remove(PORUKA)
        return

    redovi = [
        "Ovi izvori trebali su objaviti natječaj, a sustav kod njih ništa "
        "ne nalazi. Vjerojatno je stranica promijenjena pa je više ne "
        "prepoznajemo — vrijedi provjeriti ručno.\n",
    ]
    for t in tihi:
        redovi.append(
            f"- **{t['naziv']}** ({t['podrucje']})\n"
            f"  - očekivano: {t['ocekivano']}\n"
            f"  - trenutno: {t['status']}\n"
            f"  - {t['url']}"
        )
    open(PORUKA, "w", encoding="utf-8").write("\n".join(redovi))

    print(f"UPOZORENJE: {len(tihi)} izvora suti duze od ocekivanog:")
    for t in tihi:
        print(f"  - {t['naziv']} (ocekivano {t['ocekivano']})")

    # zapisi broj za workflow
    izlaz = os.environ.get("GITHUB_OUTPUT")
    if izlaz:
        with open(izlaz, "a") as f:
            f.write(f"broj_tihih={len(tihi)}\n")


if __name__ == "__main__":
    main()
