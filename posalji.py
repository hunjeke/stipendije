# -*- coding: utf-8 -*-
"""Slanje tjednih obavijesti kroz Brevo API.

Zasto postoji
=============
Rucno slanje je znacilo 9 do 27 prolazaka kroz Brevo sucelje, a filtar u
sucelju ne zna "samo moj grad": moglo se birati ima li covjek upisan grad
ili nema, ali ne i koji. Zato su gradski natjecaji isli cijeloj zupaniji.

Ovdje publiku racuna skripta, pa pravilo moze biti tocno:

  * tko je upisao grad   -> natjecaji svoga grada + svoje zupanije
  * tko nije upisao grad -> svi natjecaji zupanije, ukljucivo gradske,
                            i zamolba da upise mjesto
  * drzavna stipendija   -> svima, zasebnom porukom

Salje se kao kampanja, ne transakcijski mail, pa odjava i obrada privole
ostaju iste kao dosad.

Kako se pokrece
===============
    python posalji.py                # proba: ispise kome bi sto islo
    python posalji.py --nacrt        # napravi kampanje u Brevu, ne salje
    python posalji.py --salji        # napravi i posalje

Proba je zadano stanje. Nista se ne salje dok se ne napise --salji.

Treba BREVO_API_KEY u okolini (u Actionsima: Settings -> Secrets).
"""
import json
import os
import re
import sys
import time
from datetime import date

import requests

from novosti import (novi_natjecaji, vec_javljeno, _spoji_iste, _kome,
                     _skupina, _iznos, _rok, _drzavna, _poruka, POSLANO)

API = "https://api.brevo.com/v3"
# Lista se bira po ID-u ako je zadan, inace po nazivu. ID je pouzdaniji:
# naziv se trazi doslovno, pa "Obavijesti" i "Obavjesti" nisu ista stvar i
# jedno slovo razlike zaustavi cijelo slanje. ID se u Brevu vidi u adresi
# liste i ne mijenja se kad se lista preimenuje.
LISTA_ID = os.environ.get("BREVO_LISTA_ID", "").strip()
LISTA = os.environ.get("BREVO_LISTA", "Obavijesti")
POSILJATELJ = {"name": "Stipendije.hr",
               "email": os.environ.get("BREVO_FROM", "obavijesti@stipendije.hr")}
# Obrazac za promjenu postavki (EMAIL + GRAD). Bez njega {{ update_profile }}
# vodi na Brevov standardni obrazac u kojem nema polja za grad.
OBRAZAC_ID = int(os.environ.get("BREVO_UPDATE_FORM_ID", "0") or 0)

STRANICA = "https://stipendije.hr"
DRZAVNA_STRANICA = "https://stipendije.hr/drzavna-stipendija.html"

# Koliko najvise poruka smije otici u jednom pokretanju. Besplatni plan ima
# 300 dnevno; ovo je zastita od petlje koja se otme, ne od plana.
NAJVISE = 400

# Koliko mailova Brevo pusti u jednom danu. Besplatni plan: 300.
# Ovo nije sitnica nego jedina stvar koja dijeli ispravno slanje od tihog
# gubitka: bez nje bi se kampanje slale redom dok Brevo ne pocne odbijati,
# a poslano.json bi svejedno zapisao sve natjecaje kao poslane — pa se
# zadnjim skupinama ne bi javilo ni sljedeci tjedan.
DNEVNO = int(os.environ.get("BREVO_DNEVNO", "300") or 300)

ZA_KOGA = {"ucenik": " — samo za učenike",
           "student": " — samo za studente",
           "oba": ""}


# ---------------------------------------------------------------- API ----
def _kljuc():
    k = os.environ.get("BREVO_API_KEY", "").strip()
    if not k:
        sys.exit("Nema BREVO_API_KEY u okolini. Bez njega se ne može ništa.")
    return k


def zovi(put, nacin="GET", tijelo=None, tiho=False):
    """Jedan poziv na Brevo. Puca glasno: tiha greska pri slanju je gora
    od srusene skripte, jer se ne vidi je li posla posla ili nije."""
    odg = requests.request(
        nacin, API + put, timeout=60,
        headers={"api-key": _kljuc(), "accept": "application/json",
                 "content-type": "application/json"},
        data=json.dumps(tijelo) if tijelo is not None else None)
    if odg.status_code >= 400:
        if tiho:
            return None
        raise RuntimeError(f"{nacin} {put} -> {odg.status_code} {odg.text[:400]}")
    if not odg.content:
        return {}
    return odg.json()


def id_liste(ime):
    """ID liste. Ako je BREVO_LISTA_ID zadan, naziv se ne gleda."""
    if LISTA_ID:
        try:
            return int(LISTA_ID)
        except ValueError:
            raise RuntimeError(f"BREVO_LISTA_ID nije broj: {LISTA_ID!r}")
    offset = 0
    while True:
        d = zovi(f"/contacts/lists?limit=50&offset={offset}")
        for l in d.get("lists", []):
            if l.get("name") == ime:
                return l["id"]
        offset += 50
        if offset >= d.get("count", 0):
            raise RuntimeError(
                f"Lista {ime!r} ne postoji u Brevu. Provjeri točan naziv u "
                f"Contacts → Lists, ili zadaj BREVO_LISTA_ID.")


def kontakti(list_id):
    """Svi pretplatnici s liste, s atributima. Preskacu se odjavljeni."""
    out, offset = [], 0
    while True:
        d = zovi(f"/contacts/lists/{list_id}/contacts?limit=500&offset={offset}")
        dio = d.get("contacts", [])
        for c in dio:
            if c.get("emailBlacklisted"):
                continue
            a = c.get("attributes") or {}
            out.append({
                "email": c["email"],
                "zupanija": (a.get("ZUPANIJA") or "").strip(),
                "grad": (a.get("GRAD") or "").strip(),
            })
        offset += 500
        if len(dio) < 500:
            return out


# ------------------------------------------------------------ publika ----
def razvrstaj_po_ljudima(zapisi, ljudi):
    """{kljuc: {"ljudi": [...], "zapisi": [...]}} — jedna poruka po skupini.

    Kljucevi:
      ("drzavna",)                 drzavna stipendija, svi
      ("mjesto", zupanija, grad)   tko je upisao grad
      ("zupanija", zupanija)       tko nije upisao grad
    """
    drzavne, zupanijski, gradski = [], {}, {}
    for z in zapisi:
        k = _kome(z)
        if k is None:
            continue
        if k[0] == "svi":
            drzavne.append(z)
        elif k[0] == "zupanija":
            zupanijski.setdefault(k[1], []).append(z)
        else:
            gradski.setdefault(k[2], {}).setdefault(k[1], []).append(z)

    grupe = {}
    if drzavne:
        grupe[("drzavna",)] = {"ljudi": list(ljudi), "zapisi": drzavne}

    for c in ljudi:
        zup, grad = c["zupanija"], c["grad"]
        if not zup:
            continue
        if grad:
            moji = zupanijski.get(zup, []) + gradski.get(zup, {}).get(grad, [])
            kljuc = ("mjesto", zup, grad)
        else:
            moji = list(zupanijski.get(zup, []))
            for g in sorted(gradski.get(zup, {})):
                moji += gradski[zup][g]
            kljuc = ("zupanija", zup)
        if not moji:
            continue
        g = grupe.setdefault(kljuc, {"ljudi": [], "zapisi": moji})
        g["ljudi"].append(c)

    for g in grupe.values():
        g["zapisi"].sort(key=lambda z: (z.get("rok_iso") or "9999",
                                        z.get("naslov") or ""))
    return grupe


def _oblik(n, jd, gjd, gmn):
    """1 osoba / 2-4 osobe / 5+ osoba, s iznimkom za 11-14 i 21, 31..."""
    z, d = abs(n) % 10, abs(n) % 100
    if 11 <= d <= 14:
        return gmn
    return jd if z == 1 else gjd if 2 <= z <= 4 else gmn


def _osoba(n):
    return _oblik(n, "osoba", "osobe", "osoba")


def _natjecaj(n):
    return _oblik(n, "natječaj", "natječaja", "natječaja")


def ime_skupine(k):
    if k[0] == "drzavna":
        return "Svi pretplatnici — državna stipendija"
    if k[0] == "mjesto":
        return f"{k[2]} ({k[1]})"
    return f"{k[1]} — bez upisanog mjesta"


# -------------------------------------------------------------- poruka ----
_URL = re.compile(r"https?://[^\s<>]+")


def _link(u, sam_u_redu):
    """Poveznica u mailu. Goli URL se ne pise — na mobitelu se prelomi."""
    if "/natjecaj/" in u and sam_u_redu:
        tekst = "Detalji i prijava &rarr;"
    else:
        tekst = u.split("//", 1)[-1].rstrip("/")
    return f'<a href="{u}" style="color:#1d4ed8">{tekst}</a>'


def _odlomak(p):
    """Jedan odlomak obicnog teksta u HTML."""
    p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    p = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", p)
    p = p.replace("{{ update_profile }}",
                  '<a href="{{ update_profile }}" style="color:#1d4ed8">'
                  'otvori postavke &rarr;</a>')
    redci = []
    for r in p.split("\n"):
        sam = bool(_URL.fullmatch(r.strip()))
        redci.append(_URL.sub(lambda m: _link(m.group(0), sam), r))
    return '<p style="margin:0 0 18px">' + "<br>".join(redci) + "</p>"


def predmet_i_html(kljuc, zapisi):
    """Rijeci dolaze iz novosti.py, ovdje se samo oblikuju.

    Prije je ova datoteka imala svoju kopiju poruke — svoj predmet, svoj
    uvod, svoj redak natjecaja. Mail koji se salje rukom i mail koji
    salje skripta razlikovali su se u svemu osim u podacima, a svaka
    izmjena teksta morala se napraviti dvaput ili se zaboravila. Sada je
    jedno mjesto za rijeci i jedno za oblik.

    Kljucevi se razlikuju jer razvrstaj_po_ljudima dijeli po stvarnim
    pretplatnicima, a novosti.py po skupinama na koje se postavlja
    filtar u Brevu. Prevodi se ovdje."""
    if kljuc[0] == "drzavna":
        nk = ("drzavna",)
    elif kljuc[0] == "mjesto":
        nk = ("zup", kljuc[1], True)     # ima upisano mjesto
    else:
        nk = ("zup", kljuc[1], None)     # nema, dobiva cijelu zupaniju
    predmet, tekst = _poruka(zapisi, nk)

    tijelo = "".join(_odlomak(p) for p in tekst.split("\n\n") if p.strip())
    html = f"""<!doctype html>
<html lang="hr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f7f8fa;font-family:-apple-system,
 BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#141b2d">
<div style="max-width:560px;margin:0 auto;padding:28px 20px">
  <p style="margin:0 0 24px;font-size:15px;font-weight:700">Stipendije.hr</p>
  <div style="font-size:15px;line-height:1.55">{tijelo}</div>
  <hr style="border:none;border-top:1px solid #e2e5ec;margin:28px 0 14px">
  <p style="margin:0;font-size:12px;color:#6b7280">
    Podatke prikupljamo automatski — rok i uvjete provjeri na službenoj
    stranici natječaja.<br>
    <a href="{{{{ update_profile }}}}" style="color:#6b7280">Promijeni postavke</a>
    &nbsp;·&nbsp;
    <a href="{{{{ unsubscribe }}}}" style="color:#6b7280">Odjavi se</a></p>
</div></body></html>"""
    return predmet, html


# -------------------------------------------------------------- slanje ----
def posalji_grupu(kljuc, grupa, salji):
    """Privremena lista -> kampanja -> slanje -> lista se brise.

    Privremena lista postoji zato sto filtar u kampanji ne zna "samo ovaj
    grad". Brise se i kad slanje pukne, da se ne gomilaju u sucelju."""
    predmet, html = predmet_i_html(kljuc, grupa["zapisi"])
    oznaka = date.today().isoformat()
    ime = f"[auto] {oznaka} {ime_skupine(kljuc)}"[:60]

    lista = zovi("/contacts/lists", "POST",
                 {"name": ime[:50], "folderId": int(os.environ.get(
                     "BREVO_FOLDER_ID", "1"))})
    lista_id = lista["id"]
    try:
        emailovi = [c["email"] for c in grupa["ljudi"]]
        for i in range(0, len(emailovi), 150):
            zovi(f"/contacts/lists/{lista_id}/contacts/add", "POST",
                 {"emails": emailovi[i:i + 150]})

        kampanja = {"name": ime, "subject": predmet, "sender": POSILJATELJ,
                    "htmlContent": html,
                    "recipients": {"listIds": [lista_id]}}
        if OBRAZAC_ID:
            kampanja["updateFormId"] = OBRAZAC_ID
        k = zovi("/emailCampaigns", "POST", kampanja)
        if salji:
            zovi(f"/emailCampaigns/{k['id']}/sendNow", "POST")
        return k["id"], lista_id
    except Exception:
        zovi(f"/contacts/lists/{lista_id}", "DELETE", tiho=True)
        raise


# ---------------------------------------------------------------- main ----
def main():
    nacrt = "--nacrt" in sys.argv
    salji = "--salji" in sys.argv
    proba = not (nacrt or salji)

    arhiv, poslano, otvoreni, novi = novi_natjecaji()
    ponovljeni = vec_javljeno(novi, arhiv, poslano)
    za_slanje = {s: z for s, z in novi.items() if s not in ponovljeni}
    zapisi = _spoji_iste(list(za_slanje.values()))
    if not zapisi:
        print("Nema novih natječaja. Ništa se ne šalje.")
        return

    ljudi = kontakti(id_liste(LISTA))
    grupe = razvrstaj_po_ljudima(zapisi, ljudi)
    ukupno = sum(len(g["ljudi"]) for g in grupe.values())

    print(f"Pretplatnika na listi: {len(ljudi)}"
          f"   ·   s upisanim mjestom: "
          f"{sum(1 for c in ljudi if c['grad'])}")
    print(f"Novih natječaja: {len(zapisi)}   ·   skupina: {len(grupe)}"
          f"   ·   poruka ukupno: {ukupno}\n")
    for k in sorted(grupe, key=lambda k: ime_skupine(k)):
        g = grupe[k]
        print(f"  {ime_skupine(k):44} {len(g['ljudi']):4} "
              f"{_osoba(len(g['ljudi'])):7} {len(g['zapisi']):2} "
              f"{_natjecaj(len(g['zapisi']))}")

    bez_zupanije = [c for c in ljudi if not c["zupanija"]]
    if bez_zupanije:
        print(f"\n  Bez upisane županije, ne dobivaju ništa osim državne: "
              f"{len(bez_zupanije)}")

    if ukupno > NAJVISE:
        sys.exit(f"\nStalo: {ukupno} poruka je više od granice {NAJVISE}. "
                 f"Provjeri je li račun publike ispravan.")

    if proba:
        os.makedirs("pregled-maila", exist_ok=True)
        for k, g in grupe.items():
            predmet, html = predmet_i_html(k, g["zapisi"])
            ime = ime_skupine(k).replace("/", "-")
            with open(f"pregled-maila/{ime}.html", "w", encoding="utf-8") as f:
                f.write(f"<!-- PREDMET: {predmet} -->\n" + html)
        print("\nProba. Ništa nije poslano ni napravljeno u Brevu.")
        print("Tekstovi su u mapi pregled-maila/ — otvori ih u pregledniku.")
        print("Kad su dobri:  python posalji.py --nacrt   pa  --salji")
        return

    # Najhitniji prvi. Kad u dan ne stane sve, mora otici ono cemu rok
    # istjece najranije — abecedni red bi ostavio Zagrebacku za sutra bez
    # obzira sto joj rok istjece danas.
    def hitnost(k):
        r = [z.get("rok_iso") or "9999" for z in grupe[k]["zapisi"]]
        return (min(r) if r else "9999", ime_skupine(k))

    redom = sorted(grupe, key=hitnost)

    stane, odgodeno, zbroj = [], [], 0
    for k in redom:
        n_ljudi = len(grupe[k]["ljudi"])
        if salji and zbroj + n_ljudi > DNEVNO:
            odgodeno.append(k)
            continue
        stane.append(k)
        zbroj += n_ljudi

    if odgodeno:
        print(f"\n  Dnevna granica je {DNEVNO} poruka. Danas ide {zbroj}, "
              f"a {len(odgodeno)} "
              f"{_oblik(len(odgodeno), 'skupina ostaje', 'skupine ostaju', 'skupina ostaje')} "
              f"za sutra:")
        for k in odgodeno:
            print(f"    - {ime_skupine(k)} ({len(grupe[k]['ljudi'])} "
                  f"{_osoba(len(grupe[k]['ljudi']))})")
        print("  Pokreni isti način sutra — poslano.json pamti što je otišlo.")

    napravljeno = []
    for k in stane:
        kid, lid = posalji_grupu(k, grupe[k], salji)
        napravljeno.append((ime_skupine(k), kid, lid))
        print(f"  {'poslano' if salji else 'nacrt  '}  "
              f"{ime_skupine(k):44} kampanja {kid}")
        time.sleep(1)

    if salji:
        # Natjecaj se smije oznaciti poslanim tek kad je otisao SVIMA kojih
        # se tice. Isti natjecaj zna biti u vise skupina; ako je jedna
        # odgodena, slug ceka — inace bi ga sutrasnje pokretanje preskocilo
        # i ti ljudi ga ne bi dobili nikad.
        ceka = {z.get("slug") for k in odgodeno
                for z in grupe[k]["zapisi"] if z.get("slug")}
        otislo = {z.get("slug") for k in stane
                  for z in grupe[k]["zapisi"] if z.get("slug")} - ceka
        slugovi = sorted(otislo | set(poslano) | set(ponovljeni))
        json.dump({"slugovi": slugovi}, open(POSLANO, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"\nPoslano {len(napravljeno)} kampanja. "
              f"Zabilježeno u {POSLANO} — ne treba --potvrdi.")
        if ceka:
            print(f"  {len(ceka)} natječaja nije zabilježeno jer ih dio "
                  f"ljudi još nije dobio.")
        print("Privremene liste ostaju u Brevu dok se slanje ne dovrši; "
              "obriši ih u sučelju kad kampanje pokažu statistiku.")
    else:
        print(f"\nNapravljeno {len(napravljeno)} nacrta. Pogledaj ih u Brevu "
              f"(Campaigns → Drafts) pa pošalji ondje, ili pokreni --salji.")


if __name__ == "__main__":
    main()
