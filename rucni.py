# -*- coding: utf-8 -*-
"""
Rucno upisani natjecaji.

Dio izvora se ne da procitati automatski: neki server blokira dohvat, neki u
robots.txt izricito zabranjuje citanje svoje rubrike, neki objavljuje natjecaj
kao skenirani PDF iz kojeg se tekst ne moze izvuci. Dosad je to znacilo da
natjecaj naprosto ne postoji na stranici, iako za njega znamo — Novi Marof
daje 120 stipendija, a mi ih nismo mogli prikazati.

Ovdje se takav natjecaj upise rukom, u rucni.json, i dalje se ponasa kao svaki
drugi: ima isti oblik zapisa, status mu se racuna iz roka, sam nestaje kad rok
prode i dobiva vlastitu stranicu.

Jedno pravilo vrijedi i ovdje: upisuje se samo ono sto doslovno pise u izvoru.
Polje "potvrda" nosi adresu na kojoj se podatak moze provjeriti i ispisuje se
na stranici natjecaja, da se vidi odakle brojka dolazi.
"""
import json
import os

DATOTEKA = "rucni.json"

# polja koja zapis smije imati; sve ostalo se odbacuje da se greskom ne upise
# nesto sto ostatak programa ne ocekuje
POLJA = {"naziv", "naslov_natjecaja", "url", "poveznica_natjecaj", "podrucje",
         "zupanija", "kategorija", "iznos", "iznosi", "iznos_je_fond",
         "rok_tekst", "uvjeti", "upute_za_prijavu", "napomena", "potvrda",
         "zasto_rucno"}
OBVEZNA = ("naziv", "url", "podrucje", "rok_tekst")


def ucitaj(compute_status, sredi_iznose, korijen="."):
    """Vrati (zapisi, podrucja) spremne za spajanje s automatskim popisom.

    compute_status i sredi_iznose dolaze iz scrapera, da rucni zapis prolazi
    kroz istu obradu kao i procitani — isti racun roka, ista provjera iznosa.
    """
    put = os.path.join(korijen, DATOTEKA)
    if not os.path.exists(put):
        return [], {}
    try:
        with open(put, encoding="utf-8") as f:
            sirovo = json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"  ! {DATOTEKA} se ne da procitati: {e}")
        return [], {}
    if not isinstance(sirovo, list):
        print(f"  ! {DATOTEKA} mora biti lista zapisa")
        return [], {}

    zapisi, podrucja = [], {}
    for i, s in enumerate(sirovo, 1):
        if not isinstance(s, dict):
            continue
        fali = [k for k in OBVEZNA if not s.get(k)]
        if fali:
            print(f"  ! {DATOTEKA} zapis {i}: nedostaje {', '.join(fali)} — preskacem")
            continue
        r = {k: v for k, v in s.items() if k in POLJA}
        r["iznosi"] = sredi_iznose(r.get("iznosi"))
        r["_ima_otvoren"] = True
        r["_rucni"] = True
        r["status"] = compute_status(r.get("rok_tekst"), True)
        r.setdefault("poveznica_natjecaj", None)
        zapisi.append(r)
        podrucja[r["url"].rstrip("/")] = (r.get("podrucje") or "",
                                          r.get("zupanija") or "")
    if zapisi:
        print(f"  + rucno upisanih natjecaja: {len(zapisi)}")
    return zapisi, podrucja
