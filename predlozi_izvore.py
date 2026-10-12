#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
predlozi_izvore.py — trazi nove izvore za sources.json

Zasto postoji: stranica prati 120 izvora, a u Hrvatskoj je 127 gradova, 428
opcina i 20 zupanija. Svaki nepokriven grad je natjecaj koji nitko ne vidi.
Rucno dodavanje izvora je posao od nekoliko dana i nikad nije gotov.

Kako radi — bez ijednog poziva modelu, dakle bez troska:
  1. krene od ugradenog popisa svih 128 gradova i 20 zupanija
  2. iz imena izvede domenu (Grad Koprivnica -> koprivnica.hr, zupanije po
     kratici: Osjecko-baranjska -> obz.hr) i provjeri koja se stvarno otvara
  3. na zivoj domeni proba putanje: /stipendije, /natjecaji, /javni-pozivi, ...
  4. zadrzi samo one koje se otvore I u tekstu stvarno spominju stipendiju
  5. od svih takvih putanja uzme onu koja najvise lici na zivu rubriku:
     ima datum iz zadnjih 12 mjeseci i vise objava, a nije pojedinacni clanak
  6. izbaci one koje vec pratis i zapise prijedlog u prijedlozi_izvora.json

Zasto je korak 5 vazan: /stipendije na WordPressu ne vrati 404 nego skoci
na najblizi stari clanak s tom rijecju. Prijedlog tada ima status 200, ima
naslov sa stipendijom i izgleda ispravno, a vodi na objavu iz 2015. Od 14
prijedloga iz prvog prolaza takvih je bilo devet.

Uz --sve uzme sluzbeni popis svih 576 jedinica s data.gov.hr radi 428 opcina.
Ako portal ne odgovara, proba jos stari XLSX s ministarstva, a ako ni to ne
uspije gradovi i zupanije svejedno prolaze — ugradeni popis je u kodu upravo
zato sto je prva inacica ovisila o vanjskoj datoteci i zavrsila s nula
prijedloga.

NIKAD ne dira sources.json. Ti pregledas prijedlog i odlucis sto ulazi.

Pokretanje:
    python predlozi_izvore.py              # 148 gradova i zupanija
    python predlozi_izvore.py --sve        # + opcine iz adresara (dugo traje)
    python predlozi_izvore.py --adresar put/do/adresar.xlsx   # bez skidanja
"""

import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

SOURCES_FILE = "sources.json"
IZLAZ = "prijedlozi_izvora.json"

# Sluzbena putanja ima dvostruke kose crte — tako stoji na stranici
# ministarstva. Drzimo vise oblika jer se takve poveznice znaju mijenjati.
ADRESAR_URLS = [
    "https://mpudt.gov.hr/UserDocsImages//dokumenti//Adresar JLP(R)S.XLSX",
    "https://mpudt.gov.hr/UserDocsImages/dokumenti/Adresar JLP(R)S.XLSX",
    "https://mpudt.gov.hr/UserDocsImages//MURH- arhiva/Uprava za politički sustav"
    "/JLRS//100613-Kopija opcine_gradovi_RH.xls",
]

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

# Popis svih gradova i zupanija u Hrvatskoj. Ugraden je namjerno, a ne citan
# iz datoteke: prvi pokusaj je ovisio o tablici s ministarstva, ona se nije
# skinula i skripta je zavrsila s nula prijedloga. Ovaj popis se mijenja
# jednom u nekoliko godina, pa je ovdje najsigurniji.
GRADOVI = [
    "Zagreb", "Split", "Rijeka", "Osijek", "Zadar", "Velika Gorica", "Pula",
    "Karlovac", "Slavonski Brod", "Varaždin", "Šibenik", "Sisak", "Dubrovnik",
    "Kaštela", "Bjelovar", "Samobor", "Vinkovci", "Koprivnica", "Čakovec", "Đakovo",
    "Solin", "Zaprešić", "Požega", "Vukovar", "Sinj", "Petrinja", "Virovitica",
    "Kutina", "Sveta Nedelja", "Križevci", "Dugo Selo", "Poreč", "Sveti Ivan Zelina",
    "Našice", "Jastrebarsko", "Metković", "Omiš", "Rovinj", "Makarska", "Vrbovec",
    "Ivanić-Grad", "Ivanec", "Knin", "Umag", "Nova Gradiška", "Trogir", "Slatina",
    "Novi Marof", "Krapina", "Ogulin", "Novska", "Opatija", "Gospić", "Labin",
    "Županja", "Duga Resa", "Crikvenica", "Valpovo", "Popovača", "Kastav",
    "Pleternica", "Daruvar", "Imotski", "Beli Manastir", "Benkovac", "Belišće",
    "Ploče", "Garešnica", "Trilj", "Zabok", "Otočac", "Vodice", "Pazin", "Otok",
    "Donji Miholjac", "Ludbreg", "Glina", "Čazma", "Rab", "Đurđevac", "Lepoglava",
    "Bakar", "Mali Lošinj", "Pakrac", "Prelog", "Drniš", "Pregrada", "Senj", "Ozalj",
    "Oroslavje", "Varaždinske Toplice", "Krk", "Mursko Središće", "Vodnjan", "Vrgorac",
    "Zlatar", "Kutjevo", "Buzet", "Biograd na Moru", "Grubišno Polje", "Ilok", "Lipik",
    "Donja Stubica", "Korčula", "Delnice", "Buje", "Orahovica", "Slunj",
    "Novi Vinodolski", "Novigrad", "Kraljevica", "Vrbovsko", "Hvar", "Supetar",
    "Novalja", "Pag", "Obrovac", "Skradin", "Čabar", "Opuzen", "Klanjec", "Nin",
    "Stari Grad", "Cres", "Hrvatska Kostajnica", "Vrlika", "Vis", "Komiža"
]

ZUPANIJE = [
    "Zagrebačka", "Krapinsko-zagorska", "Sisačko-moslavačka", "Karlovačka",
    "Varaždinska", "Koprivničko-križevačka", "Bjelovarsko-bilogorska",
    "Primorsko-goranska", "Ličko-senjska", "Virovitičko-podravska",
    "Požeško-slavonska", "Brodsko-posavska", "Zadarska", "Osječko-baranjska",
    "Šibensko-kninska", "Vukovarsko-srijemska", "Splitsko-dalmatinska", "Istarska",
    "Dubrovačko-neretvanska", "Međimurska"
]


def kanonska_zupanija(sirovo):
    """Ime zupanije onako kako ga pise sources.json.

    Sluzbena tablica zna napisati "OSJECKO-BARANJSKA", "Osjecko-baranjska" ili
    "Osjecko-baranjska zupanija". Stranica filtrira po tocnom nizu, pa jedna
    kriva varijanta znaci da natjecaj tog grada nikad ne stigne onome tko je
    u obrascu odabrao tu zupaniju."""
    s = bez_kvacica(str(sirovo or "")).strip()
    if not s or s in ("nan", "none", "-"):
        return ""
    # Sluzbeni popis zupanije broji rimskim brojem: "I ZAGREBACKA",
    # "XXI GRAD ZAGREB". Bez skidanja tog prefiksa nijedna se ne prepozna
    # i svaki prijedlog ostane bez zupanije.
    s = re.sub(r"^[ivxlc]+[\s.]+", "", s).strip()
    s = re.sub(r"\s*zupanija\s*$", "", s).strip()
    if "zagreb" in s and "zagrebacka" not in s:
        return "Grad Zagreb"
    for z in ZUPANIJE:
        if bez_kvacica(z) == s:
            return f"{z} županija"
    return ""


# Stranica mora spominjati stipendiju, inace je to samo rubrika o nabavi.
TRAZI = ("stipendij", "školarin", "skolarin", "učenic", "ucenic", "student")

ZAGLAVLJA = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
}
TIMEOUT = 8
NITI = 8

# Koliko stara smije biti najnovija objava da bismo rubriku smatrali zivom.
# Gradski natjecaji izlaze sezonski, pa godina dana nije strogo.
MJESECI_SVJEZINE = 12

_MJESEC = {
    "sij": 1, "velj": 2, "ozu": 3, "tra": 4, "svi": 5, "lip": 6,
    "srp": 7, "kol": 8, "ruj": 9, "lis": 10, "stu": 11, "pro": 12,
}

# "5. listopada 2026.", "lis 5, 2026", "05.10.2026.", "2026-10-05"
_D_RIJEC = re.compile(r"(\d{1,2})\.?\s+([a-z]{3})[a-z]*\s+(\d{4})")
_D_OBRNUT = re.compile(r"\b([a-z]{3})[a-z]*\s+(\d{1,2}),?\s+(\d{4})\b")
_D_TOCKE = re.compile(r"\b(\d{1,2})\.\s?(\d{1,2})\.\s?(\d{4})\b")
_D_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")


def _datum(g, m, d):
    try:
        return date(int(g), int(m), int(d))
    except ValueError:
        return None


def najnoviji_datum(tekst):
    """Najnoviji datum koji se na stranici da procitati, ili None.

    Datum je jedino sto pouzdano razlikuje zivu rubriku od starog clanka.
    Naslov ne pomaze: "Stipendije za ucenike i studente" stoji i na rubrici
    i na objavi iz 2015."""
    t = bez_kvacica(tekst)
    danas = date.today()
    nadeni = []
    for m in _D_RIJEC.finditer(t):
        mj = _MJESEC.get(m.group(2)[:3])
        if mj:
            nadeni.append(_datum(m.group(3), mj, m.group(1)))
    for m in _D_OBRNUT.finditer(t):
        mj = _MJESEC.get(m.group(1)[:3])
        if mj:
            nadeni.append(_datum(m.group(3), mj, m.group(2)))
    for m in _D_TOCKE.finditer(t):
        nadeni.append(_datum(m.group(3), m.group(2), m.group(1)))
    for m in _D_ISO.finditer(t):
        nadeni.append(_datum(m.group(1), m.group(2), m.group(3)))
    # Datum iz buducnosti je najcesce rok prijave i jednako dobro govori da
    # je stranica ziva, ali odbacujemo besmislice tipa 2099.
    nadeni = [d for d in nadeni if d and d.year <= danas.year + 1]
    return max(nadeni) if nadeni else None


def _star(d):
    """Koliko je mjeseci star datum. Buducnost racunamo kao 0."""
    if not d:
        return 9999
    dana = (date.today() - d).days
    return max(0, dana) / 30.4


def broj_stavki(juha):
    """Koliko stranica ima stavki koje izgledaju kao zasebne objave.

    Rubrika ih ima vise, pojedinacni clanak jednu. Broje se poveznice jer
    su one ono po cemu bi scraper uopce dalje isao."""
    veze = [a for a in juha.find_all("a", href=True)
            if len(a.get_text(strip=True)) > 24]
    return len(veze)


def bez_kvacica(s):
    z = {"č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d"}
    return "".join(z.get(x, x) for x in str(s).lower())


# ---------------------------------------------------------------- adresar

def skini_adresar(putanja=None):
    """Vrati putanju do tablice, skinuvsi je ako treba. None ako ne uspije."""
    if putanja:
        return putanja
    for url in ADRESAR_URLS:
        lokalno = "_adresar" + os.path.splitext(url)[1].lower()
        if os.path.exists(lokalno):
            return lokalno
        try:
            print(f"Skidam: {url}")
            r = requests.get(url, headers=ZAGLAVLJA, timeout=60, verify=False)
            if r.status_code != 200 or len(r.content) < 5000:
                print(f"  ! HTTP {r.status_code}, {len(r.content)} B — preskacem")
                continue
            with open(lokalno, "wb") as f:
                f.write(r.content)
            print(f"  spremljeno ({len(r.content)//1024} kB)")
            return lokalno
        except requests.RequestException as e:
            print(f"  ! {type(e).__name__}: {str(e)[:70]}")
    print("! Nijedan adresar se nije skinuo — idem samo po imenima jedinica.")
    return None


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


def domene_iz_imena(ime, vrsta):
    """Pogodi domenu iz imena jedinice.

    Hrvatske jedinice gotovo bez iznimke koriste isti obrazac: Grad Koprivnica
    je koprivnica.hr ili grad-koprivnica.hr. Pogadanje je ovdje posve sigurno
    jer se svaka domena ionako provjerava dohvatom, a stranica mora spominjati
    stipendije da bi usla u prijedlog. Kriva pogodba samo ne odgovori."""
    n = bez_kvacica(ime)
    n = re.sub(r"^(grad|opcina|zupanija)\s+", "", n).strip()
    n = re.sub(r"\s*zupanija$", "", n).strip()
    jezgra = re.sub(r"[^a-z0-9]+", "-", n).strip("-")
    if not jezgra:
        return []
    if vrsta == "Županija":
        # Zupanije gotovo bez iznimke koriste kraticu: Osjecko-baranjska je
        # obz.hr, Primorsko-goranska pgz.hr, Brodsko-posavska bpz.hr. Puno ime
        # u domeni je kod njih iznimka, pa kratice idu prve.
        slova = "".join(d[0] for d in jezgra.split("-") if d)
        kandidati = [f"{slova}z.hr", f"{slova}zupanija.hr", f"{slova}-zupanija.hr"]
        if len(slova) == 1:                       # jednoclane (Karlovacka)
            kandidati.insert(0, f"{jezgra[:2]}zup.hr")
        kandidati += [f"{jezgra}.hr", f"{jezgra}-zupanija.hr"]
        if "đ" in str(ime).lower():        # Medimurska je medjimurska-zupanija.hr
            dj = bez_kvacica(str(ime).lower().replace("đ", "dj"))
            dj = re.sub(r"\s*zupanija$", "", dj).strip()
            dj = re.sub(r"[^a-z0-9]+", "-", dj).strip("-")
            # ispred punog imena, jer se proba samo prvih nekoliko kandidata
            kandidati[3:3] = [f"{dj}-zupanija.hr", f"{dj}.hr"]
        return kandidati

    kandidati = [f"{jezgra}.hr"]
    if vrsta == "Grad":
        kandidati.append(f"grad-{jezgra}.hr")
    elif vrsta == "Općina":
        kandidati.append(f"opcina-{jezgra}.hr")
    # imena od dvije rijeci ("Novi Marof") idu i spojeno
    if "-" in jezgra:
        kandidati.append(jezgra.replace("-", "") + ".hr")
    # "Đakovo" je u domeni djakovo.hr, ne dakovo.hr
    if "đ" in str(ime).lower():
        dj = re.sub(r"[^a-z0-9]+", "-",
                    str(ime).lower().replace("đ", "dj")).strip("-")
        dj = re.sub(r"^(grad|opcina)-", "", bez_kvacica(dj))
        if f"{dj}.hr" not in kandidati:
            kandidati.insert(1, f"{dj}.hr")
    return kandidati


def _nadi_zaglavlje(putanja, list_ime, maks=10):
    """Pronadi redak koji je stvarno zaglavlje tablice.

    Sluzbene tablice cesto pocinju naslovom, praznim recima i spojenim celijama,
    pa je pravo zaglavlje tek peti ili sesti redak. Ako se cita od prvog, svi
    stupci se zovu 'Unnamed: 0' i nista se ne prepozna — upravo se to dogodilo
    u prvom pokusaju."""
    import pandas as pd
    for red in range(maks):
        try:
            df = pd.read_excel(putanja, sheet_name=list_ime, dtype=str, header=red)
        except Exception:
            continue
        stupci = [bez_kvacica(c) for c in df.columns]
        ima_ime = any("naziv" in c or "ime" in c or "jedinic" in c or "grad" in c
                      or "opcina" in c for c in stupci)
        if ima_ime and len(df) > 5:
            df.columns = stupci
            return df, red
    return None, None


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

    imena_listova = list(pd.read_excel(putanja, sheet_name=None, nrows=0))
    print(f"Tablica: {len(imena_listova)} list(ova) — {', '.join(imena_listova[:5])}")

    jedinice, vidjena_imena = [], set()
    for ime_lista in imena_listova:
        df, red_zaglavlja = _nadi_zaglavlje(putanja, ime_lista)
        if df is None:
            print(f"  ! list '{ime_lista}': ne prepoznajem zaglavlje, preskacem")
            continue
        st_ime = next((c for c in df.columns
                       if "naziv" in c or "ime" in c or "jedinic" in c), None) \
            or next((c for c in df.columns if "grad" in c or "opcina" in c), None)
        st_web = next((c for c in df.columns
                       if "web" in c or "intern" in c or "stranic" in c), None)
        st_mail = next((c for c in df.columns if "mail" in c or "epos" in c), None)
        st_vrsta = next((c for c in df.columns if "vrsta" in c or "tip" in c), None)
        # Zupanija iz iste sluzbene tablice. Bez nje bi je trebalo upisati
        # rukom za svaki prijedlog, a o njoj ovisi kome stranica salje mail.
        st_zup = next((c for c in df.columns if "zupanij" in c), None)
        print(f"  list '{ime_lista}': zaglavlje u {red_zaglavlja + 1}. retku, "
              f"{len(df)} redaka | naziv='{st_ime}' web='{st_web}' mail='{st_mail}'")
        if not st_ime:
            print(f"      stupci: {list(df.columns)[:8]}")
            continue

        for _, red in df.iterrows():
            ime = str(red.get(st_ime) or "").strip()
            if not ime or ime.lower() in ("nan", "none", "-"):
                continue
            kljuc = bez_kvacica(ime)
            if kljuc in vidjena_imena:
                continue
            vidjena_imena.add(kljuc)

            vrsta = str(red.get(st_vrsta) or "").strip() if st_vrsta else ""
            if not vrsta or vrsta.lower() == "nan":
                vrsta = ("Županija" if "zupanij" in kljuc else
                         "Općina" if kljuc.startswith("opcina") else "Grad")

            # Domena iz tablice ako je ima; inace se pogada iz imena i
            # provjerava dohvatom. Tako popis ne ovisi o tome sadrzi li
            # sluzbena tablica uopce mreznu adresu.
            domene = []
            if st_web:
                d = _adresa_iz_stupca(red.get(st_web))
                if d:
                    domene.append(d)
            if st_mail:
                d = _domena_iz_maila(red.get(st_mail))
                if d and d not in domene:
                    domene.append(d)
            domene += [d for d in domene_iz_imena(ime, vrsta) if d not in domene]
            if domene:
                zup = kanonska_zupanija(red.get(st_zup)) if st_zup else ""
                jedinice.append({"naziv": ime, "vrsta": vrsta,
                                 "zupanija": zup, "domene": domene})

    if samo_gradovi:
        jedinice = [j for j in jedinice if j["vrsta"] != "Općina"]
    return jedinice


# Sluzbeni popis svih 576 jedinica, kao JSON. Ovo je zamjena za skidanje
# XLSX-a s ministarstva: ta se poveznica vec jednom pomaknula i prolaz
# --sve je zavrsio s nula opcina. Ovdje podatak dolazi iz CKAN-a drzavnog
# portala otvorenih podataka, s trajnim identifikatorom izvora.
CKAN = ("https://data.gov.hr/ckan/api/3/action/datastore_search"
        "?resource_id=55ac291b-63bf-42ac-8d01-7aff77c62223&limit=1000")


def jedinice_iz_otvorenih_podataka():
    """Svih 576 jedinica s data.gov.hr, ili prazno ako portal ne odgovara.

    Stupci su "Zupanija", "Tip jedinice" i "Ime jedinice". Domena se ne
    nalazi u tom popisu, pa se i dalje pogada iz imena — ali ime i zupanija
    dolaze iz sluzbenog izvora, a o zupaniji ovisi kome stranica salje mail."""
    try:
        r = requests.get(CKAN, headers=ZAGLAVLJA, timeout=30, verify=False)
        r.raise_for_status()
        zapisi = r.json()["result"]["records"]
    except Exception as e:
        print(f"! data.gov.hr ne odgovara ({type(e).__name__}) — "
              f"nastavljam s ugradenim popisom gradova i zupanija.")
        return []

    jedinice = []
    for z in zapisi:
        ime = str(z.get("Ime jedinice") or "").strip()
        tip = str(z.get("Tip jedinice") or "").strip()
        if not ime or tip not in ("Grad", "Općina", "Županija"):
            continue
        naziv = ime if tip == "Županija" else f"{tip} {ime}"
        zup = (kanonska_zupanija(z.get("Zupanija"))
               or (f"{ime} županija" if tip == "Županija" else ""))
        domene = domene_iz_imena(ime, tip)
        if domene:
            jedinice.append({"naziv": naziv, "vrsta": tip,
                             "zupanija": zup, "domene": domene})
    print(f"data.gov.hr: {len(jedinice)} jedinica "
          f"({sum(1 for j in jedinice if j['vrsta'] == 'Općina')} općina)")
    return jedinice


def jedinice_iz_popisa(samo_gradovi=True):
    """Gradovi i zupanije iz ugradenog popisa — temelj koji ne moze zakazati.

    Prvi pokusaj je sve gradio na tablici s ministarstva. Ona se nije skinula,
    a zaliha je uzimala imena iz sources.json — dakle iskljucivo one izvore koje
    vec pratis, pa ih je dedupliciranje sve pobrisalo i ostalo je nula. Zato
    popis sada stoji u kodu."""
    jedinice = [{"naziv": f"Grad {g}", "vrsta": "Grad",
                 "domene": domene_iz_imena(g, "Grad")} for g in GRADOVI]
    jedinice += [{"naziv": f"{z} županija", "vrsta": "Županija",
                  "zupanija": f"{z} županija",
                  "domene": domene_iz_imena(z, "Županija")} for z in ZUPANIJE]
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
        # Zapisuje se ZAVRSNA adresa, ne ona koju smo trazili. Ranije se
        # zapisivala trazena i to je bila greska: /stipendije na WordPressu
        # ne vrati 404 nego skoci na najblizi stari clanak, pa je u popis
        # usla adresa koja uvijek vodi na objavu iz 2015.
        return {
            "url": r.url,
            "trazeno": url,
            "naslov": naslov,
            "datum": najnoviji_datum(tekst),
            "stavki": broj_stavki(juha),
        }
    return None


def ziva_domena(kandidati):
    """Koja se od pogodenih domena uopce otvara.

    Prvo se trazi ziva domena, pa tek onda putanje po njoj. Bez toga bi se
    osam putanja probalo na svakoj pogodenoj domeni i posao bi narastao
    nekoliko puta bez ikakve koristi."""
    for d in kandidati[:6]:
        for shema in ("https://", "http://"):
            try:
                r = requests.get(f"{shema}{d}", headers=ZAGLAVLJA, timeout=TIMEOUT,
                                 verify=False, allow_redirects=True)
            except requests.RequestException:
                continue
            if r.status_code == 200 and "html" in r.headers.get("content-type", ""):
                return urlparse(r.url).netloc or d
    return None


def _rang(r):
    """Koliko stranica izgleda kao ziva rubrika. Vece je bolje."""
    return (
        _star(r["datum"]) <= MJESECI_SVJEZINE,   # ima nesto iz zadnjih godinu
        not _CLANAK.search(r["url"] or ""),      # nije datirani clanak
        r["stavki"] >= 5,                        # ima vise objava, nije jedna
        -r["mjesto"],                            # ranija putanja je bolja
    )


def istrazi(jedinica):
    """Od svih putanja koje se otvore bira onu koja najvise lici na rubriku.

    Ranije je pobjedivala prva koja se otvori i spomene stipendiju. Zbog
    toga je za Sinj zapisan obrazac za prijavu umjesto popisa natjecaja, a
    za Novigrad se nikad nije stiglo do /natjecaji jer je ranija putanja
    vec "prosla"."""
    domena = ziva_domena(jedinica["domene"])
    if not domena:
        return None
    najbolji = None
    for i, p in enumerate(PUTANJE):
        r = provjeri_putanju(domena, p)
        if not r:
            continue
        r["mjesto"] = i
        if najbolji is None or _rang(r) > _rang(najbolji):
            najbolji = r
        # Ziva rubrika s vise objava — nema smisla trositi jos sedam zahtjeva.
        if _rang(r)[0] and _rang(r)[1] and _rang(r)[2]:
            break
    if not najbolji:
        return None
    return dict(jedinica, domena=domena, putanja=PUTANJE[najbolji["mjesto"]],
                **najbolji)


# Putanja koja zavrsi na datiranom clanku ili dugom naslovu nije rubrika nego
# jedna objava. Takav prijedlog nije bezvrijedan, ali trazi tvoje oko.
_CLANAK = re.compile(r"/(19|20)\d{2}[/-]|[/-](19|20)\d{2}/?$|\d{4}-\d{4}")


def sumnjiv(r):
    """Zasto prijedlog treba tvoje oko. None znaci: moze odmah u popis.

    Duljina zadnjeg dijela adrese vise nije mjerilo. Po njoj je ispao
    Novigrad, kojem je rubrika na /natjecaji-oglasi-javni-pozivi/ — a to
    je bio najbolji prijedlog u cijelom prolazu."""
    if _CLANAK.search(r.get("url") or ""):
        return "adresa izgleda kao datirani članak"
    d = r.get("datum")
    if d is None:
        return "na stranici nema nijednog datuma"
    if _star(d) > MJESECI_SVJEZINE:
        return f"najnovije na stranici je {d.strftime('%d.%m.%Y.')}"
    if r.get("stavki", 0) < 3:
        return "stranica ima samo jednu objavu, nije rubrika"
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

    # Temelj je ugradeni popis; tablica s ministarstva samo dodaje opcine i
    # prave domene ondje gdje ih zna. Tako izostanak tablice nista ne rusi.
    jedinice = jedinice_iz_popisa()
    poznata_imena = {bez_kvacica(j["naziv"]) for j in jedinice}

    dodatne = []
    if args.adresar:
        # Rucno predana tablica ima prednost — ako je vec imas, nema razloga
        # da se bilo sto skida.
        dodatne = procitaj_adresar(args.adresar, samo_gradovi=not args.sve)
    elif args.sve:
        dodatne = jedinice_iz_otvorenih_podataka()
        if not dodatne:
            tablica = skini_adresar()
            if tablica:
                dodatne = procitaj_adresar(tablica, samo_gradovi=False)

    if dodatne:
        novih = [j for j in dodatne if bez_kvacica(j["naziv"]) not in poznata_imena]
        print(f"Dodatno: {len(novih)} jedinica")
        jedinice += novih
        # Zupanija iz sluzbenog popisa je bolja od prazne u ugradenom.
        po_imenu = {bez_kvacica(j["naziv"]): j for j in dodatne}
        for j in jedinice:
            if not j.get("zupanija"):
                izvor = po_imenu.get(bez_kvacica(j["naziv"]))
                if izvor and izvor.get("zupanija"):
                    j["zupanija"] = izvor["zupanija"]
    if not jedinice:
        print("! Iz tablice nista — koristim ugradeni popis gradova i zupanija.")
    print(f"\nJedinica za provjeru: {len(jedinice)}")
    if not jedinice:
        print("! Nemam nijednu jedinicu. Provjeri ispis o zaglavlju iznad.")
        sys.exit(1)

    poznate = postojece_domene()
    novi = [j for j in jedinice
            if not any(d.replace("www.", "") in poznate for d in j["domene"])]
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

    # cisti prvi, sumnjivi na dno — da se odmah vidi sto se moze uzeti odmah
    nadeno.sort(key=lambda r: (bool(sumnjiv(r)), bez_kvacica(r["naziv"])))
    prijedlozi = []
    for r in nadeno:
        stavka = {"naziv": f"{r['naziv']} — stipendije",
                  "url": r["url"],
                  "kategorija": r["vrsta"],
                  "podrucje": r["naziv"],
                  "zupanija": r.get("zupanija", ""),
                  "_naslov_stranice": r["naslov"],
                  "_najnovije": r["datum"].isoformat() if r["datum"] else "",
                  "_stavki": r["stavki"]}
        if r["url"] != r["trazeno"]:
            stavka["_trazena_adresa"] = r["trazeno"]
        upozorenje = sumnjiv(r)
        if upozorenje:
            stavka["_provjeri"] = upozorenje
        prijedlozi.append(stavka)

    with open(IZLAZ, "w", encoding="utf-8") as f:
        json.dump(prijedlozi, f, ensure_ascii=False, indent=2)

    print(f"\n{'='*54}")
    print(f"Provjereno jedinica: {len(novi)}")
    cisti = sum(1 for r in nadeno if not sumnjiv(r))
    print(f"Novih izvora nadeno: {len(nadeno)}")
    print(f"  spremni za unos:   {cisti}")
    print(f"  trebaju pogled:    {len(nadeno) - cisti} (oznaceni s '_provjeri')")
    print(f"Zapisano u:          {IZLAZ}")
    print("\nPregledaj datoteku pa prenesi u sources.json one koje zelis.")
    print("Prije prenosenja popuni 'zupanija' — o njoj ovisi filter na stranici.")


if __name__ == "__main__":
    main()
