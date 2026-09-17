#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
predlozi_izvore.py — trazi nove izvore za sources.json

Zasto postoji: stranica prati 120 izvora, a u Hrvatskoj je 127 gradova, 428
opcina i 20 zupanija. Svaki nepokriven grad je natjecaj koji nitko ne vidi.
Rucno dodavanje izvora je posao od nekoliko dana i nikad nije gotov.

Kako radi — bez ijednog poziva modelu, dakle bez troska:
  1. skine sluzbeni adresar jedinica lokalne samouprave (Ministarstvo pravosuda)
  2. iz njega izvuce ime i mreznu adresu svake jedinice
     (ako stupca s adresom nema, izvede domenu iz sluzbenog e-maila)
  3. na svakoj domeni proba uobicajene putanje: /stipendije, /natjecaji, ...
  4. zadrzi samo one koje se otvore I u tekstu stvarno spominju stipendiju
  5. izbaci one koje vec pratis i zapise prijedlog u prijedlozi_izvora.json

NIKAD ne dira sources.json. Ti pregledas prijedlog i odlucis sto ulazi.

Pokretanje:
    python predlozi_izvore.py              # gradovi i zupanije (147 jedinica)
    python predlozi_izvore.py --sve        # + 428 opcina (dugo traje)
    python predlozi_izvore.py --adresar put/do/adresar.xlsx   # bez skidanja
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCES_FILE = "sources.json"
IZLAZ = "prijedlozi_izvora.json"

ADRESAR_URL = ("https://mpudt.gov.hr/UserDocsImages/dokumenti/"
               "Adresar%20JLP(R)S.XLSX")

# Putanje po kojima hrvatske gradske stranice drze natjecaje. Poredane po
# korisnosti: stranica posvecena stipendijama vrijedi vise od opce rubrike.
PUTANJE = [
    "/stipendije",
    "/stipendije-grada",
    "/natjecaji-i-javni-pozivi",
    "/natjecaji",
    "/javni-natjecaji",
    "/javni-pozivi",
    "/natjecaji-i-pozivi",
    "/obavijesti",
]

# Stranica mora spominjati stipendiju, inace je to samo rubrika o nabavi.
TRAZI = ("stipendij", "školarin", "skolarin", "učenic", "ucenic", "student")

ZAGLAVLJA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
}
TIMEOUT = 8
NITI = 8


def bez_kvacica(s):
    z = {"č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d"}
    return "".join(z.get(x, x) for x in str(s).lower())


# ---------------------------------------------------------------- adresar

def skini_adresar(putanja=None):
    """Vrati putanju do XLSX-a, skinuvsi ga ako treba."""
    if putanja:
        return putanja
    lokalno = "_adresar.xlsx"
    if os.path.exists(lokalno):
        return lokalno
    print(f"Skidam adresar: {ADRESAR_URL}")
    r = requests.get(ADRESAR_URL, headers=ZAGLAVLJA, timeout=60, verify=False)
    r.raise_for_status()
    with open(lokalno, "wb") as f:
        f.write(r.content)
    print(f"  spremljeno ({len(r.content)//1024} kB)")
    return lokalno


def _domena_iz_maila(v):
    m = re.search(r"[\w.+-]+@([\w-]+\.[\w.-]+)", str(v))
    if not m:
        return None
    d = m.group(1).strip(" .;,")
    # sluzbeni mail zna biti na tudoj domeni — to nije stranica jedinice
    if any(d.endswith(x) for x in ("gmail.com", "yahoo.com", "outlook.com",
                                   "hotmail.com", "net.hr", "vip.hr")):
        return None
    return d


def _adresa_iz_stupca(v):
    t = str(v).strip()
    if not t or t.lower() in ("nan", "none", "-"):
        return None
    m = re.search(r"((?:https?://)?(?:www\.)?[\w-]+\.[\w.-]+)", t)
    if not m:
        return None
    d = m.group(1).replace("https://", "").replace("http://", "").strip("/ ")
    return d or None


def procitaj_adresar(putanja, samo_gradovi=True):
    """Izvuci (ime, vrsta, domena) za svaku jedinicu.

    Stupci u sluzbenim tablicama nisu ujednaceni ni po imenu ni po redoslijedu,
    pa se traze po sadrzaju zaglavlja, a ne po polozaju. Ako stupca s mreznom
    adresom nema, domena se izvodi iz sluzbenog e-maila — sto je za gradove
    gotovo uvijek ista domena."""
    try:
        import pandas as pd
    except ImportError:
        print("GRESKA: nedostaje 'pandas'. Instaliraj: pip install pandas openpyxl")
        sys.exit(1)

    listovi = pd.read_excel(putanja, sheet_name=None, dtype=str)
    print(f"Adresar: {len(listovi)} list(ova) — {', '.join(list(listovi)[:5])}")

    jedinice, vidjene = [], set()
    for ime_lista, df in listovi.items():
        df.columns = [bez_kvacica(c) for c in df.columns]
        st_ime = next((c for c in df.columns
                       if "naziv" in c or "ime" in c or "jedinic" in c), None)
        st_web = next((c for c in df.columns
                       if "web" in c or "intern" in c or "stranic" in c), None)
        st_mail = next((c for c in df.columns if "mail" in c or "epos" in c), None)
        st_vrsta = next((c for c in df.columns if "vrsta" in c or "tip" in c), None)
        if not st_ime:
            print(f"  ! list '{ime_lista}': ne prepoznajem stupac s nazivom, preskacem")
            continue
        print(f"  list '{ime_lista}': naziv='{st_ime}' web='{st_web}' mail='{st_mail}'")

        for _, red in df.iterrows():
            ime = str(red.get(st_ime) or "").strip()
            if not ime or ime.lower() == "nan":
                continue
            domena = (_adresa_iz_stupca(red.get(st_web)) if st_web else None)
            if not domena and st_mail:
                domena = _domena_iz_maila(red.get(st_mail))
            if not domena:
                continue
            vrsta = str(red.get(st_vrsta) or "").strip() if st_vrsta else ""
            if not vrsta:
                nl = bez_kvacica(ime)
                vrsta = ("Županija" if "zupanij" in nl else
                         "Općina" if nl.startswith("opcina") else "Grad")
            if domena in vidjene:
                continue
            vidjene.add(domena)
            jedinice.append({"naziv": ime, "vrsta": vrsta, "domena": domena})

    if samo_gradovi:
        jedinice = [j for j in jedinice if j["vrsta"] != "Općina"]
    return jedinice


# ---------------------------------------------------------------- probanje

def provjeri_putanju(domena, putanja):
    """Vrati (url, naslov) ako se stranica otvara i govori o stipendijama."""
    for shema in ("https://", "http://"):
        url = urljoin(f"{shema}{domena}", putanja)
        try:
            r = requests.get(url, headers=ZAGLAVLJA, timeout=TIMEOUT,
                             verify=False, allow_redirects=True)
        except requests.RequestException:
            continue
        if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
            continue
        # bez deklariranog kodiranja requests pogadja latin-1 i kvacice puknu
        if "charset" not in r.headers.get("content-type", "").lower():
            try:
                r.encoding = r.apparent_encoding or r.encoding
            except Exception:
                pass
        # Puno stranica na nepostojecu putanju vrati 200 i stranicu "nema
        # rezultata". Zato ne vjerujemo kodu nego sadrzaju.
        juha = BeautifulSoup(r.text, "html.parser")
        for t in juha(["script", "style", "nav", "footer"]):
            t.decompose()
        tekst = bez_kvacica(juha.get_text(" ", strip=True))
        # Prag namjerno nizak: stranica koja ima samo naslov natjecaja i
        # poveznicu na PDF upravo je izvor kakav trazimo. Odluku nosi rijec
        # "stipendij", ne duljina — inace bi ispale najkorisnije stranice.
        if len(tekst) < 80:
            continue
        if "stipendij" not in tekst:      # ucenik/student sam po sebi nije dovoljan
            continue
        naslov = (juha.title.get_text(strip=True) if juha.title else "")[:90]
        return r.url, naslov
    return None, None


def istrazi(jedinica):
    """Prva putanja koja se otvori i spominje stipendije pobjeduje."""
    for p in PUTANJE:
        url, naslov = provjeri_putanju(jedinica["domena"], p)
        if url:
            return dict(jedinica, url=url, naslov=naslov, putanja=p)
    return None


# ---------------------------------------------------------------- glavni dio

def postojece_domene():
    if not os.path.exists(SOURCES_FILE):
        return set()
    with open(SOURCES_FILE, encoding="utf-8") as f:
        izvori = json.load(f)
    return {urlparse(i.get("url", "")).netloc.replace("www.", "")
            for i in izvori if i.get("url")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sve", action="store_true",
                    help="ukljuci i 428 opcina (puno dulje traje)")
    ap.add_argument("--adresar", help="putanja do vec skinutog XLSX-a")
    ap.add_argument("--limit", type=int, help="probaj samo prvih N jedinica")
    args = ap.parse_args()

    jedinice = procitaj_adresar(skini_adresar(args.adresar),
                                samo_gradovi=not args.sve)
    print(f"\nJedinica s poznatom domenom: {len(jedinice)}")

    poznate = postojece_domene()
    novi = [j for j in jedinice
            if j["domena"].replace("www.", "") not in poznate]
    print(f"Vec pratis: {len(jedinice) - len(novi)}  |  za provjeru: {len(novi)}")
    if args.limit:
        novi = novi[:args.limit]

    nadeno = []
    with ThreadPoolExecutor(max_workers=NITI) as bazen:
        poslovi = {bazen.submit(istrazi, j): j for j in novi}
        for i, gotov in enumerate(as_completed(poslovi), 1):
            j = poslovi[gotov]
            try:
                rez = gotov.result()
            except Exception as e:
                rez = None
                print(f"  ! {j['naziv'][:28]}: {type(e).__name__}")
            if rez:
                nadeno.append(rez)
                print(f"  + {rez['naziv'][:30]:32} {rez['url'][:56]}")
            if i % 25 == 0:
                print(f"  ... {i}/{len(novi)}, nadeno {len(nadeno)}")

    nadeno.sort(key=lambda r: bez_kvacica(r["naziv"]))
    prijedlozi = [{"naziv": f"{r['naziv']} — stipendije",
                   "url": r["url"],
                   "kategorija": r["vrsta"],
                   "podrucje": r["naziv"],
                   "zupanija": "",
                   "_naslov_stranice": r["naslov"]} for r in nadeno]

    with open(IZLAZ, "w", encoding="utf-8") as f:
        json.dump(prijedlozi, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*54}")
    print(f"Provjereno jedinica: {len(novi)}")
    print(f"Novih izvora nadeno: {len(nadeno)}")
    print(f"Zapisano u:          {IZLAZ}")
    print("\nPregledaj datoteku pa prenesi u sources.json one koje zelis.")
    print("Prije prenosenja popuni 'zupanija' — o njoj ovisi filter na stranici.")


if __name__ == "__main__":
    main()
