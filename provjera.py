# -*- coding: utf-8 -*-
"""Provjera podataka prije nego stranica i mailovi odu van.

Zasto postoji
=============
Svaku gresku koju smo dosad nasli nasao je covjek, slucajno i prekasno:

  * STEM stipendija je osvanula na stranici s rokom koji ne postoji, jer je
    model recenicu iz pravilnika ("javni poziv raspisuje ministar do 25.
    listopada") procitao kao rok prijave;
  * Koprivnicko-krizevacka i Velika Gorica tjednima se nisu vidjele, jer se
    iz raspona "od 1.10. do 18.10." uzimao prvi datum;
  * drzavna stipendija je zamalo otisla svima drugi put.

Dok takve stvari hvata oko, nista ne smije raditi bez nadzora. Ovo je ta
provjera: pokrece se poslije scrapera, a prije objave i slanja.

Sto radi s nalazom
==================
  STOP   zaustavlja slanje mailova. Stranica se svejedno objavi — bolje je
         imati stranicu s jednom sumnjivom karticom nego nikakvu.
  PAZI   ne zaustavlja nista, ali stoji u izvjestaju.

Izlazni kod: 0 kad nema STOP nalaza, 1 kad ima. Workflow po tome odlucuje
hoce li pokrenuti slanje.

    python provjera.py            # ispis + provjera.md
    python provjera.py --tiho     # samo izlazni kod
"""
import io
import json
import re
import os
import sys
from collections import Counter
from datetime import date, timedelta

from scraper import parse_hr_date, bez_kvacica
from web import opisna_stranica

IZLAZ = "provjera.md"
STANJE = ".provjera-stanje.json"

# Mjesecni iznos izvan ovog raspona gotovo sigurno nije mjesecni iznos nego
# godisnji, ukupni fond ili krivo procitana brojka. Donja granica je niska
# namjerno: ima opcina koje daju 50 EUR.
EUR_NAJMANJE, EUR_NAJVISE = 30, 1500

# Koliko se broj otvorenih smije promijeniti od proslog prolaza a da to ne
# bude sumnjivo. Natjecaji izlaze u valovima, pa je raspon sirok; sluzi za
# hvatanje pada na nulu i udvostrucenja, ne za sitne pomake.
PAD, SKOK = 0.5, 2.0


def _ucitaj(put, zadano):
    if not os.path.exists(put):
        return zadano
    try:
        with io.open(put, encoding="utf-8") as f:
            return json.load(f)
    except (ValueError, OSError):
        return zadano


def _adrese(r):
    out = set()
    for k in ("url", "poveznica_natjecaj", "poveznica", "_izvor_url"):
        v = (r.get(k) or "").strip().rstrip("/").lower()
        if v:
            out.add(v)
    return out


def _iso(r):
    """Datum roka iz statusa, pa iz teksta roka."""
    s = r.get("status") or ""
    if "(" in s and ")" in s:
        unutra = s[s.rfind("(") + 1:s.rfind(")")]
        unutra = unutra.split("—")[0].strip()
        if len(unutra) == 10 and unutra[4] == "-":
            return unutra
    d = parse_hr_date(r.get("rok_tekst") or "")
    return d.isoformat() if d else ""


_POD = None


def _podrucje(r):
    """Kojem podrucju zapis pripada — isto kako to racuna web.py.

    Zapisi iz output.json nemaju polje "podrucje"; ono se dobiva iz
    sources.json po adresi izvora. Nepoznata adresa racuna se kao cijela
    Hrvatska, kao i na stranici — tako je stroza provjera, a ne blaza."""
    global _POD
    if _POD is None:
        _POD = {}
        for s in _ucitaj("sources.json", []):
            u = (s.get("url") or "").strip().rstrip("/").lower()
            if u:
                _POD[u] = (s.get("podrucje") or "").strip()
    if r.get("podrucje"):
        return r["podrucje"].strip()
    for k in ("url", "_izvor_url"):
        v = (r.get(k) or "").strip().rstrip("/").lower()
        if v in _POD:
            return _POD[v]
    return "Cijela Hrvatska"


def _otvoren(r):
    return (r.get("status") or "").startswith("OTVORENO")


def _naslov(r):
    return (r.get("naslov_natjecaja") or r.get("naslov") or "").strip()


# ----------------------------------------------------------- pravila ----
def rok_u_proslosti(zapisi, _):
    danas = date.today().isoformat()
    for r in zapisi:
        iso = _iso(r)
        if _otvoren(r) and iso and iso < danas:
            yield "stop", (f"otvoren, a rok je prošao ({iso}): {_naslov(r)[:60]}")


def rok_predaleko(zapisi, _):
    granica = (date.today() + timedelta(days=430)).isoformat()
    for r in zapisi:
        iso = _iso(r)
        if _otvoren(r) and iso and iso > granica:
            yield "stop", (f"rok je {iso}, više od godine dana unaprijed — "
                           f"vjerojatno kriva godina: {_naslov(r)[:50]}")


def rok_bez_godine(zapisi, _):
    """Rok bez godine znaci da je godina pogodena, ne procitana.

    Tako je nastala STEM stipendija s rokom 25. listopada: u tekstu je
    stajalo "do 25. listopada", bez godine, iz recenice o tome kad se poziv
    raspisuje."""
    for r in zapisi:
        t = r.get("rok_tekst") or ""
        if not _otvoren(r) or not t:
            continue
        if any(g in t for g in ("202", "203")):
            continue
        # Kad takav natjecaj vrijedi za cijelu Hrvatsku, pogodena godina ide
        # na mail svima. STEM je tocno to bio: recenica iz pravilnika, bez
        # godine, pretvorena u rok za 12.000 ljudi. Tu se staje.
        svima = _podrucje(r).lower() == "cijela hrvatska"
        yield ("stop" if svima else "pazi",
               f"rok bez godine, pogođena je: {t[:40]!r} — {_naslov(r)[:46]}")


def izmisljen_mjesec(zapisi, _):
    """Rok s imenom mjeseca koje ne postoji.

    Model je kod jednog izvora vratio "do 6. christie do 13:00 sati". Takav
    se rok ne procita, natjecaj nestane s popisa i nitko ne zna zasto. Kad
    u roku stoji rijec koja izgleda kao mjesec a nije, bolje je to reci."""
    from scraper import HR_MONTHS
    for r in zapisi:
        t = (r.get("rok_tekst") or "").lower()
        if not t:
            continue
        for m in re.finditer(r"\b\d{1,2}\.?\s+([a-zčćšđž]{4,})\b", t):
            rijec = m.group(1)
            if rijec in HR_MONTHS or rijec in (
                    "dana", "dan", "sati", "sat", "sata", "mjeseci",
                    "mjesec", "tjedna", "tjedan", "godine", "godina",
                    "ujutro", "navecer", "ponoci", "podne"):
                continue
            yield "pazi", (f"u roku stoji {rijec!r}, a to nije mjesec: "
                           f"{_naslov(r)[:44]}")
            break


def iznos_izvan_raspona(zapisi, _):
    for r in zapisi:
        if not _otvoren(r) or r.get("iznos_je_fond"):
            continue
        for i in (r.get("iznosi") or []):
            eur = i.get("eur")
            if not eur or i.get("razdoblje") != "mjesecno":
                continue
            if not (EUR_NAJMANJE <= eur <= EUR_NAJVISE):
                yield "stop", (f"mjesečni iznos {eur:.0f} € izvan raspona "
                               f"{EUR_NAJMANJE}–{EUR_NAJVISE}: {_naslov(r)[:46]}")


def bez_roka_i_iznosa(zapisi, _):
    for r in zapisi:
        if not _otvoren(r):
            continue
        ima_iznos = bool((r.get("iznosi") or []) or (r.get("iznos") or "").strip())
        if not _iso(r) and not ima_iznos:
            yield "pazi", (f"otvoren, a nema ni rok ni iznos: {_naslov(r)[:55]}")


def ista_adresa_razlicit_rok(zapisi, _):
    """Dva otvorena zapisa na istoj adresi s razlicitim rokom su jedan
    natjecaj procitan dvaput, a na stranici stoje kao dva."""
    po_adresi = {}
    for r in zapisi:
        if not _otvoren(r):
            continue
        a = (r.get("poveznica_natjecaj") or r.get("url") or "").rstrip("/").lower()
        if a:
            po_adresi.setdefault(a, []).append(r)
    for a, grupa in po_adresi.items():
        rokovi = {_iso(r) for r in grupa if _iso(r)}
        if len(rokovi) > 1:
            yield "pazi", (f"ista adresa, {len(rokovi)} različita roka "
                           f"({', '.join(sorted(rokovi))}): {a[:60]}")


def svima_a_nije_drzavna(zapisi, _):
    """Natjecaj koji bi isao na mail svima mora biti drzavna stipendija.

    Ovo je zadnja brana prije nego nesto krivo ode na cijelu listu."""
    for r in zapisi:
        if not _otvoren(r):
            continue
        if _podrucje(r).lower() != "cijela hrvatska":
            continue
        n = bez_kvacica(_naslov(r))
        adrese = " ".join(_adrese(r))
        drzavna = "mzom.gov.hr" in adrese and ("drzavn" in n or "stem" in n)
        if drzavna and not _iso(r):
            yield "stop", (f"državna stipendija bez pouzdanog roka: "
                           f"{_naslov(r)[:50]}")


def nagla_promjena(zapisi, staro):
    sada = sum(1 for r in zapisi if _otvoren(r))
    prije = staro.get("otvorenih")
    if not prije:
        return
    if sada < prije * PAD:
        yield "stop", (f"otvorenih natječaja {sada}, prošli put {prije} — "
                       f"pad za više od pola")
    elif sada > prije * SKOK:
        yield "pazi", (f"otvorenih natječaja {sada}, prošli put {prije} — "
                       f"više nego dvostruko")


def previse_gresaka(zapisi, staro):
    greske = sum(1 for r in zapisi if (r.get("status") or "").startswith("GREŠKA"))
    prije = staro.get("gresaka")
    if greske > 20:
        yield "stop", f"{greske} izvora nije dohvaćeno — nešto je s mrežom"
    elif prije is not None and greske > prije + 5:
        yield "pazi", f"{greske} nedohvatljivih izvora, prošli put {prije}"


PRAVILA = [rok_u_proslosti, rok_predaleko, rok_bez_godine, izmisljen_mjesec,
           iznos_izvan_raspona, bez_roka_i_iznosa, ista_adresa_razlicit_rok,
           svima_a_nije_drzavna, nagla_promjena, previse_gresaka]


# -------------------------------------------------------------- main ----
def main():
    tiho = "--tiho" in sys.argv
    svi = _ucitaj("output.json", []) + _ucitaj("rucni.json", [])
    # Zapisi s opisnih stranica ne idu ni na stranicu ni na mail, pa ih ni
    # provjera ne gleda — inace bi zaustavljala svaki prolaz zbog necega
    # sto je vec rijeseno.
    zapisi = [r for r in svi if not opisna_stranica(r)]
    izbaceno = len(svi) - len(zapisi)
    if not zapisi:
        print("Nema output.json — provjera nema što provjeriti.")
        return 1
    staro = _ucitaj(STANJE, {})

    nalazi = []
    if izbaceno:
        nalazi.append(("pazi", "opisne_stranice",
                       f"{izbaceno} zapisa je s opisnih stranica ministarstva "
                       f"— ne idu ni na stranicu ni na mail"))
    for pravilo in PRAVILA:
        for razina, poruka in pravilo(zapisi, staro):
            nalazi.append((razina, pravilo.__name__, poruka))

    stopovi = [n for n in nalazi if n[0] == "stop"]
    pazi = [n for n in nalazi if n[0] == "pazi"]
    otvorenih = sum(1 for r in zapisi if _otvoren(r))

    L = [f"# Provjera podataka — {date.today().strftime('%d.%m.%Y.')}", "",
         f"Zapisa: {len(zapisi)}  ·  otvorenih: {otvorenih}  ·  "
         f"zaustavljanja: **{len(stopovi)}**  ·  upozorenja: {len(pazi)}", ""]
    if stopovi:
        L += ["## Zaustavlja slanje", "",
              "Stranica se objavljuje, mailovi se ne šalju dok se ovo ne "
              "riješi ili dok ne potvrdiš da je u redu.", ""]
        for _, pravilo, p in stopovi:
            L.append(f"- **{p}**  \n  `{pravilo}`")
        L.append("")
    if pazi:
        L += ["## Za pogledati", ""]
        for _, pravilo, p in pazi:
            L.append(f"- {p}  \n  `{pravilo}`")
        L.append("")
    if not nalazi:
        L += ["Sve provjere prolaze.", ""]
    io.open(IZLAZ, "w", encoding="utf-8", newline="\n").write("\n".join(L) + "\n")

    json.dump({"otvorenih": otvorenih,
               "gresaka": sum(1 for r in zapisi
                              if (r.get("status") or "").startswith("GREŠKA")),
               "datum": date.today().isoformat()},
              io.open(STANJE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    if not tiho:
        for razina, pravilo, p in nalazi:
            print(f"  {'STOP' if razina == 'stop' else 'pazi'}  {p}")
        print(f"\nZapisa {len(zapisi)}, otvorenih {otvorenih}. "
              f"Zaustavljanja: {len(stopovi)}, upozorenja: {len(pazi)}.")
        print(f"Izvještaj: {IZLAZ}")
    return 1 if stopovi else 0


if __name__ == "__main__":
    sys.exit(main())
