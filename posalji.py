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
import sys
import time
from datetime import date

import requests

from novosti import (novi_natjecaji, vec_javljeno, _spoji_iste, _kome,
                     _skupina, _iznos, _rok, _drzavna, POSLANO)

API = "https://api.brevo.com/v3"
LISTA = os.environ.get("BREVO_LISTA", "Obavijesti #3")
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
    offset = 0
    while True:
        d = zovi(f"/contacts/lists?limit=50&offset={offset}")
        for l in d.get("lists", []):
            if l.get("name") == ime:
                return l["id"]
        offset += 50
        if offset >= d.get("count", 0):
            raise RuntimeError(f"Lista {ime!r} ne postoji u Brevu.")


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
def _red_html(z):
    dio = [f"<strong>{z['naslov']}</strong>"]
    if z.get("podrucje"):
        dio.append(z["podrucje"])
    iz = _iznos(z)
    if iz:
        dio.append(iz)
    rok = _rok(z)
    if rok:
        dio.append("rok " + rok)
    veza = z.get("poveznica") or z.get("url") or ""
    redak = " · ".join(dio) + ZA_KOGA.get(_skupina(z), "")
    if veza:
        redak += (f'<br><a href="{veza}" style="color:#1d4ed8">'
                  f'Otvori natječaj &rarr;</a>')
    return f'<p style="margin:0 0 18px">{redak}</p>'


def predmet_i_html(kljuc, zapisi):
    n = len(zapisi)
    koliko = ("Jedan novi natječaj" if n == 1
              else f"{n} nova natječaja" if n <= 4
              else f"{n} novih natječaja")

    if kljuc[0] == "drzavna":
        predmet = (f"Otvoren natječaj: {zapisi[0]['naslov']}" if n == 1
                   else f"{koliko} za državnu stipendiju")
        uvod = ("Otvorio se natječaj za državnu stipendiju:" if n == 1
                else "Otvorili su se natječaji za državne stipendije:")
        dodatak = (f'<p style="margin:0 0 18px"><a href="{DRZAVNA_STRANICA}" '
                   f'style="color:#1d4ed8">Cijeli postupak prijave i '
                   f'bodovanje</a></p>')
        zasto = ("Ovo dobivaš jer si se prijavio na obavijesti. Državna "
                 "stipendija vrijedi za cijelu Hrvatsku, pa je dobivaju svi.")
    elif kljuc[0] == "mjesto":
        predmet = f"{koliko} — {kljuc[2]}"
        uvod = "Ovo se otvorilo otkad smo se zadnji put javili:"
        dodatak = ""
        zasto = (f"Ovo dobivaš jer si u postavkama upisao {kljuc[2]} kao "
                 f"svoje mjesto, pa šaljemo samo natječaje koji vrijede ondje "
                 f"i u cijeloj županiji.")
    else:
        predmet = f"{koliko} — {kljuc[1]}"
        uvod = "Ovo se otvorilo otkad smo se zadnji put javili:"
        # Ovi ljudi nemaju upisano mjesto, pa dobivaju cijelu zupaniju.
        # Zamolba stoji ovdje i nigdje drugdje: tko mjesto ima, nema je
        # zasto citati.
        dodatak = (
            '<p style="margin:0 0 18px;padding:14px 16px;background:#f4f6fb;'
            'border-radius:8px">Dio gornjih natječaja vjerojatno nije iz '
            'tvog mjesta — uvjet je gotovo uvijek prebivalište. '
            '<a href="{{ update_profile }}" style="color:#1d4ed8">Upiši svoje '
            'mjesto u postavkama</a> i ubuduće ti šaljemo samo ono što '
            'vrijedi za tebe.</p>')
        zasto = "Ovo dobivaš jer si se prijavio na obavijesti za svoju županiju."

    tijelo = "".join(_red_html(z) for z in zapisi)
    html = f"""<!doctype html>
<html lang="hr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;background:#f7f8fa;font-family:-apple-system,
 BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:#141b2d">
<div style="max-width:560px;margin:0 auto;padding:28px 20px">
  <p style="margin:0 0 24px;font-size:15px;font-weight:700">Stipendije.hr</p>
  <p style="margin:0 0 20px;font-size:15px">{uvod}</p>
  <div style="font-size:15px;line-height:1.55">{tijelo}</div>
  {dodatak}
  <p style="margin:24px 0 0;font-size:15px">
    <a href="{STRANICA}" style="color:#1d4ed8">Sve otvorene stipendije</a></p>
  <hr style="border:none;border-top:1px solid #e2e5ec;margin:28px 0 14px">
  <p style="margin:0;font-size:12px;color:#6b7280">{zasto}<br>
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

    napravljeno = []
    for k in sorted(grupe, key=lambda k: ime_skupine(k)):
        kid, lid = posalji_grupu(k, grupe[k], salji)
        napravljeno.append((ime_skupine(k), kid, lid))
        print(f"  {'poslano' if salji else 'nacrt  '}  "
              f"{ime_skupine(k):44} kampanja {kid}")
        time.sleep(1)

    if salji:
        slugovi = sorted({z["slug"] for g in grupe.values()
                          for z in g["zapisi"] if z.get("slug")}
                         | set(poslano) | set(ponovljeni))
        json.dump({"slugovi": slugovi}, open(POSLANO, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"\nPoslano {len(napravljeno)} kampanja. "
              f"Zabilježeno u {POSLANO} — ne treba --potvrdi.")
        print("Privremene liste ostaju u Brevu dok se slanje ne dovrši; "
              "obriši ih u sučelju kad kampanje pokažu statistiku.")
    else:
        print(f"\nNapravljeno {len(napravljeno)} nacrta. Pogledaj ih u Brevu "
              f"(Campaigns → Drafts) pa pošalji ondje, ili pokreni --salji.")


if __name__ == "__main__":
    main()
