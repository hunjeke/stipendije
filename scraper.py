#!/usr/bin/env python3
"""
stipendije.hr scraper — v3
===========================
Cita popis izvora iz sources.json, dohvaca svaku stranicu (HTML ili PDF),
salje sadrzaj Claude API-ju da izvuce strukturirane podatke o stipendiji,
i SAM PROGRAMSKI racuna je li natjecaj OTVOREN / ROK ISTEKAO
na temelju stvarnog danasnjeg datuma.

Novo u v3:
  - slijedi poveznice na PDF natjecaje (najava na stranici, tekst u PDF-u)
  - prepoznaje kad stranica kaze da natjecaja NEMA, pa ne cita datume iz arhive
  - vraca izravnu poveznicu na natjecaj kad ju nade

Iz v2:
  - cita PDF-ove, 4 formata datuma, cache, --force

Pokretanje:
    export ANTHROPIC_API_KEY="sk-ant-..."
    python3 scraper.py
    python3 scraper.py --force     # ignoriraj cache, obradi sve ispocetka
"""

import json
import csv
import os
import re
import sys
import time
import hashlib
import argparse
from datetime import datetime, date
from io import BytesIO
from urllib.parse import urljoin, urlparse

import requests
import urllib3
from bs4 import BeautifulSoup

# Neke gradske stranice imaju neispravan SSL certifikat pa ih dohvacamo
# s verify=False. Ovo utisava upozorenje koje bi inace zatrpalo ispis.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

try:
    import anthropic
except ImportError:
    print("GRESKA: nedostaje 'anthropic' paket. Instaliraj s: pip install anthropic")
    sys.exit(1)

try:
    from pypdf import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

SOURCES_FILE = "sources.json"
OUTPUT_JSON = "output.json"
OUTPUT_CSV = "output.csv"
OUTPUT_HTML = "output.html"
CACHE_FILE = ".cache.json"
# Dva posla, dva modela.
# Prva razina je trijaza: "ima li na ovoj rubrici ista o stipendijama" — to
# Haiku radi dobro i vrti se 120 puta po radu, pa mora biti jeftin.
# Druga razina cita sam natjecaj i iz njega vadi iznos, rok i uvjete. Ondje se
# grijesi i ondje greska boli, a dogada se tek desetak puta po radu — zato Sonnet.
MODEL = "claude-haiku-4-5-20251001"
MODEL_NATJECAJ = "claude-sonnet-5"
REQUEST_TIMEOUT = 25
DELAY_SEC = 2
MAX_CHARS = 15000

# Cache pamti rezultat dok se stranica ne promijeni. Kad se promijeni NACIN
# citanja (prompt, drugi prolaz po podstranicama), stari rezultati vise ne
# vrijede — podigni ovaj broj i cijeli cache se jednom ponovno procita.
VERZIJA_EKSTRAKCIJE = 3

# Gornja granica dodatnih poziva modelu u drugom prolazu, po jednom radu.
# Osigurac protiv skupog iznenadenja: ako bi neocekivano puno izvora trazilo
# drugu razinu, radije preskoci ostatak nego da run posalje tisuce poziva.
# Prvi rad nakon praznog cachea realno potrosi 100-160 od ovoga.
MAKS_DRUGI_PROLAZ = 250

HR_MONTHS = {
    "siječnja": 1, "sijecnja": 1, "siječanj": 1,
    "veljače": 2, "veljace": 2, "veljača": 2,
    "ožujka": 3, "ozujka": 3, "ožujak": 3,
    "travnja": 4, "travanj": 4,
    "svibnja": 5, "svibanj": 5,
    "lipnja": 6, "lipanj": 6,
    "srpnja": 7, "srpanj": 7,
    "kolovoza": 8, "kolovoz": 8,
    "rujna": 9, "rujan": 9,
    "listopada": 10, "listopad": 10,
    "studenoga": 11, "studenog": 11, "studeni": 11,
    "prosinca": 12, "prosinac": 12,
}

EXTRACTION_PROMPT = """Analiziraj tekst stranice o stipendijama i vrati TOCNO ovaj JSON, bez ikakvog dodatnog teksta:

{{
  "naslov_natjecaja": "KRATAK naslov onoga sto se dodjeljuje, najvise 6 rijeci, ili null",
  "iznos": "iznos stipendije kako je naveden (npr. '200 EUR mjesecno, 10 mjeseci') ili null",
  "iznosi": [{{"eur": 380, "razdoblje": "mjesecno", "mjeseci": 10, "za": "ucenici", "do": false}}],
  "iznos_je_fond": true/false — je li broj UKUPAN proracun programa, a ne iznos po korisniku,
  "dokaz_iznos": "recenica PREPISANA DOSLOVNO sa stranice u kojoj pise iznos, ili null",
  "dokaz_rok": "recenica PREPISANA DOSLOVNO sa stranice u kojoj pise rok, ili null",
  "rok_tekst": "rok prijave DOSLOVNO kako pise u tekstu (npr. '4. studenoga 2025.') ili null ako nema konkretnog trenutnog natjecaja",
  "uvjeti": "tko se moze prijaviti, 1-2 recenice, ili null",
  "upute_za_prijavu": "3-6 kratkih koraka odvojenih s ' | ', ili null",
  "ima_otvoren_natjecaj": true/false — je li ocito da JE objavljen konkretan natjecaj (ne samo opca stranica o programu),
  "napomena": "bilo sto neuobicajeno sto covjek treba znati, ili null",
  "poveznica_natjecaj": "ako na stranici postoji poveznica koja vodi IZRAVNO na tekst natjecaja (a ne na popis), upisi ju ovdje; inace null"
}}

DOKAZI: uz iznos i rok prepisi recenicu iz koje si ih procitao — DOSLOVNO,
znak po znak, onako kako stoji u tekstu gore, bez skracivanja i preoblikovanja.
Ta se recenica strojno trazi u tekstu stranice; ako je ne nade, podatak se
odbacuje. Zato nemoj sastavljati recenicu koja "otprilike odgovara" niti
prepisivati iz vlastitog znanja — ako recenice s tim podatkom nema u tekstu,
vrati null i za dokaz i za sam podatak.

IZNOSI: "iznos" ostavi doslovno kako pise. Uz to rastavi isti podatak u polje
"iznosi", da se stipendije mogu usporedivati:
  "eur"       — samo broj, bez valute i bez tocke za tisuce (2325, 380, 1250.50)
  "razdoblje" — "mjesecno", "godisnje" ili "jednokratno"
  "mjeseci"   — koliko mjeseci traje isplata, ili null ako ne pise
  "za"        — kome pripada TAJ iznos, jedna-dvije rijeci ("ucenici", "studenti",
                "ucenici izvan grada"), ili null ako je iznos jedinstven
  "do"        — true ako je to gornja granica ("do 3000 EUR"), inace false
Ako natjecaj ima vise razreda, upisi SVAKI kao zaseban unos: "380 EUR za ucenike,
520 EUR za studente, 10 mjeseci" daje dva unosa, oba s mjeseci=10. Ako iznos nije
naveden brojem ("potpuno financiran studij"), vrati praznu listu [].

"iznos_je_fond" je true samo kad je broj ukupan novac koji davatelj dijeli svima
zajedno (npr. "144.000,00 eura osigurano je u proracunu za ovu mjeru"), a ne ono
sto dobiva pojedini ucenik. To je vazno: takav broj prikazan kao iznos stipendije
grubo obmanjuje prijavitelja.

NASLOV: "naslov_natjecaja" je ono sto pise na kartici na stranici, pa mora
covjeku odmah reci STO se dodjeljuje. Izbaci "Natjecaj za dodjelu", ime grada,
skolsku godinu i broj klase — to se vec vidi drugdje. Dobro: "Stipendije za
deficitarna zanimanja", "Stipendije za ucenike i studente", "Stipendije za
studij u Britaniji". Lose: "Natjecaj za dodjelu stipendija Grada X za ucenike
prvih razreda za skolsku godinu 2026./2027.". Ako natjecaja nema, vrati null.

PRVO PROVJERI O CEMU JE NATJECAJ. Zanimaju nas ISKLJUCIVO stipendije i novcane
potpore za SKOLOVANJE ucenika i studenata. Ako je natjecaj o bilo cemu drugom —
subvencije za solarne panele, energetska obnova, poticaji poduzetnicima,
sufinanciranje vrtica, javna nabava, zaposljavanje, najam stanova, komunalno —
vrati sve null i ima_otvoren_natjecaj=false, cak i ako ima jasan rok i iznos.

POSEBNO PAZI na potpore koje idu ZAPOSLENIM ljudima, a ne ucenicima i studentima:
npr. potpore lijecnicima specijalistima, uciteljima ili drugim deficitarnim
zanimanjima ZA RAD u nekom gradu, potpore za stambeno zbrinjavanje, naknade za
novorodence. To NISU stipendije, bez obzira sto se ponekad zovu "potpora" i
imaju mjesecni iznos. Stipendija se dodjeljuje osobi koja se JOS SKOLUJE
(ucenik ili student), za vrijeme trajanja skolovanja.
Opce rubrike "natjecaji i javni pozivi" sadrze svakakve natjecaje; uzmi u obzir
samo one o stipendijama, skolarinama i potporama za ucenike i studente.

VAZNO: za "rok_tekst" prepisi datum doslovno iz teksta. Ne racunaj i ne zakljucuj je li rok prosao — to radi program zasebno.
Ako stranica nema jasan natjecaj (samo meni/navigacija), vrati sve null i ima_otvoren_natjecaj=false.

NAJVAZNIJE PRAVILO: ako stranica bilo gdje kaze da trenutno NEMA otvorenih natjecaja
(npr. "trenutacno nema otvorenih natjecaja", "natjecaj je zatvoren", "natjecaj ce biti
objavljen u...", "prijave su zavrsene"), tada OBAVEZNO vrati ima_otvoren_natjecaj=false
i rok_tekst=null — bez obzira na to koliko datuma vidis na stranici. Datumi zatvorenih
natjecaja, arhiva i najave buducih objava NISU rok za prijavu.
Rok upisi SAMO ako je jasno da se na taj natjecaj moze prijaviti upravo sada.

POPISNE STRANICE: rubrika koja nabraja vise natjecaja NIJE sama po sebi razlog
da vratis false. Ako na popisu stoji barem jedan natjecaj za stipendiju ucenika
ili studenta i uz njega se vidi rok prijave, uzmi taj natjecaj (onaj s najblizim
rokom koji jos nije prosao) i vrati ima_otvoren_natjecaj=true. Ako je na popisu
samo naslov natjecaja bez roka, vrati ima_otvoren_natjecaj=false i rok_tekst=null
— taj natjecaj se cita sa svoje podstranice, ne odavde.

Ako tekst sadrzi odjeljak "--- TEKST IZ PRILOZENOG PDF-a ---", taj dio je sam natjecaj
i ima prednost pred kratkom najavom sa stranice.

TEKST STRANICE:
---
{page_text}
---
"""


# Druga razina: vec smo na stranici pojedinog natjecaja. Pitanje vise nije
# "ima li ovdje ista", nego "procitaj ovo tocno". Zato zaseban prompt: bez
# opreza koji na popisnoj stranici sprjecava laznu uzbunu, a s naglaskom na
# tocnost brojki — ovo je jedini tekst koji ce itko procitati o toj stipendiji.
NATJECAJ_PROMPT = """Pred tobom je tekst JEDNOG natjecaja za stipendiju. Vrati TOCNO ovaj JSON, bez ikakvog dodatnog teksta:

{{
  "naslov_natjecaja": "KRATAK naslov onoga sto se dodjeljuje, najvise 6 rijeci, ili null",
  "iznos": "iznos stipendije doslovno kako pise, ili null",
  "iznosi": [{{"eur": 380, "razdoblje": "mjesecno", "mjeseci": 10, "za": "ucenici", "do": false}}],
  "iznos_je_fond": true/false — je li broj UKUPAN proracun programa, a ne iznos po korisniku,
  "dokaz_iznos": "recenica PREPISANA DOSLOVNO iz teksta u kojoj pise iznos, ili null",
  "dokaz_rok": "recenica PREPISANA DOSLOVNO iz teksta u kojoj pise rok, ili null",
  "rok_tekst": "rok prijave DOSLOVNO kako pise, ili null",
  "uvjeti": "tko se moze prijaviti, 1-2 recenice, ili null",
  "upute_za_prijavu": "3-6 kratkih koraka odvojenih s ' | ', ili null",
  "ima_otvoren_natjecaj": true/false,
  "napomena": "bilo sto neuobicajeno sto covjek treba znati, ili null",
  "poveznica_natjecaj": null
}}

OVA STRANICA JE SAM NATJECAJ, ne rubrika s popisom. Ako u tekstu stoji natjecaj
za stipendiju ucenika ili studenata, vrati ima_otvoren_natjecaj=true i popuni
polja. Nemoj vracati false samo zato sto nesto nedostaje — natjecaj bez
navedenog iznosa i dalje je natjecaj.

Vrati ima_otvoren_natjecaj=false samo ako: tekst nije o stipendiji za skolovanje
(npr. potpora zaposlenima, subvencija, javna nabava), ili je ovo obavijest o
REZULTATIMA odnosno rang-lista, ili tekst izricito kaze da su prijave zavrsene.

ROK: prepisi datum doslovno. Ako je naveden raspon ("od 7. do 30. rujna"),
prepisi cijeli raspon — program sam racuna koji je datum zadnji. Ne racunaj i ne
zakljucuj je li rok prosao.

IZNOSI: "iznos" ostavi doslovno. Uz to rastavi isti podatak u "iznosi":
  "eur" — samo broj (2325, 380, 1250.50); "razdoblje" — "mjesecno", "godisnje"
  ili "jednokratno"; "mjeseci" — trajanje isplate ili null; "za" — kome pripada
  taj iznos ("ucenici", "studenti") ili null ako je jedinstven; "do" — true kad
  je gornja granica. Svaki razred ide kao zaseban unos. Ako iznos nije naveden
  brojem, vrati praznu listu [].
Iznos u drugoj valuti (CAD, USD) NE upisuj u "eur" — ostavi praznu listu, a
doslovni tekst zadrzi u "iznos".

DOKAZI: uz iznos i rok prepisi recenicu iz koje si ih procitao, DOSLOVNO, znak
po znak. Ta se recenica strojno trazi u tekstu gore; ako je ne nade, podatak se
odbacuje. Ne sastavljaj recenicu po sjecanju i ne dopunjuj je — ako recenice s
tim podatkom nema, vrati null i za dokaz i za podatak.

TEKST NATJECAJA:
---
{page_text}
---
"""


# Neki serveri (npr. gradske/zupanijske stranice) odbijaju ocite botove.
# Predstavljamo se kao obican preglednik i saljemo puno zaglavlje.
BROWSER_HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "hr-HR,hr;q=0.9,en;q=0.8",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}


def fetch_content(url, retries=2, tiho=False):
    """Dohvati stranicu. Vraca (tekst, hash, sirovi_html).

    Sirovi HTML sluzi da se u njemu potraze poveznice na PDF natjecaje;
    kod PDF-a je None. Pri neuspjehu vraca (None, None, None).
    Podrzava i HTML i PDF. Pokusava vise puta jer stranice znaju povremeno pasti."""
    resp = None
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.get(url, headers=BROWSER_HEADERS,
                                timeout=REQUEST_TIMEOUT, allow_redirects=True,
                                verify=False)
            resp.raise_for_status()
            break
        except requests.RequestException as e:
            last_error = e
            if attempt < retries:
                wait = 3 * (attempt + 1)
                print(f"  . pokusaj {attempt + 1} nije uspio, cekam {wait}s...")
                time.sleep(wait)
            else:
                if not tiho:
                    print(f"  ! Greska pri dohvatu nakon {retries + 1} pokusaja: {e}")
                return None, None, None
    if resp is None:
        if not tiho:
            print(f"  ! Greska pri dohvatu: {last_error}")
        return None, None, None

    content_type = resp.headers.get("Content-Type", "").lower()

    if "pdf" in content_type or url.lower().endswith(".pdf"):
        if not PDF_SUPPORT:
            print("  ! PDF stranica, ali 'pypdf' nije instaliran (pip install pypdf)")
            return None, None, None
        try:
            reader = PdfReader(BytesIO(resp.content))
            text = "\n".join((page.extract_text() or "") for page in reader.pages)
        except Exception as e:
            if not tiho:
                print(f"  ! Ne mogu procitati PDF: {e}")
            return None, None, None
        sirovi = None
    else:
        soup = BeautifulSoup(resp.text, "html.parser")
        for tag in soup(["script", "style", "nav", "footer", "header"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        sirovi = resp.text

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    cleaned = "\n".join(lines)[:MAX_CHARS]
    if not cleaned:
        if not tiho:
            print("  ! Stranica dohvacena ali prazna nakon ciscenja")
        return None, None, None
    content_hash = hashlib.sha256(cleaned.encode("utf-8")).hexdigest()[:16]
    return cleaned, content_hash, sirovi


def bez_kvacica(s):
    """'Natječaj za učenike' -> 'natjecaj za ucenike'.

    Kljucne rijeci nize pisane su bez kvacica, a tekst poveznica nije —
    bez ovoga 'natjeca' nikad ne pronade 'Natječaj'."""
    zamjena = {"č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d"}
    return "".join(zamjena.get(z, z) for z in str(s).lower())


# Rijeci koje odaju da poveznica vodi na ishod, a ne na natjecaj na koji se
# jos moze prijaviti. Citanje rang-liste kao natjecaja bila bi gadna greska.
NIJE_NATJECAJ = ("rezultat", "rang", "zapisnik", "zakljuc", "odluka",
                 "lista kandidata", "obavijest o rezultat", "ugovor",
                 "izvjes", "pravilnik", "obrazac", "privol", "izjav",
                 "arhiva", "ponisten", "isprav")


def natjecaj_poveznice(html, baza, maks=2):
    """Nadi poveznice s popisne stranice koje vode na sam natjecaj za stipendiju.

    Vecina gradova nema stranicu 'stipendije' nego rubriku 'javni natjecaji' na
    kojoj stoji samo naslov s poveznicom. Na takvoj stranici nema ni iznosa ni
    roka, pa model s pravom kaze da natjecaja nema — a natjecaj je jedan klik
    dalje. Zato takve poveznice ovdje otvaramo i citamo."""
    kandidati = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         html, re.I | re.S):
        href, tekst = m.group(1), m.group(2)
        if href.lower().startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        pun = _izravni(href, baza)        # ista domena i nije sama popisna stranica
        if not pun or pun.lower().endswith(".pdf"):   # PDF-ove hvata pdf_poveznice
            continue
        cist = bez_kvacica(re.sub(r"<[^>]+>", " ", tekst))
        spoj = cist + " " + bez_kvacica(href)
        # mora mirisati na stipendiju, a ne na bilo koji javni natjecaj
        if "stipendij" not in spoj and "skolarin" not in spoj:
            continue
        if any(k in spoj for k in NIJE_NATJECAJ):
            continue
        if pun not in kandidati:
            kandidati.append(pun)
        if len(kandidati) >= maks:
            break
    return kandidati


def pdf_poveznice(html, baza, maks=2):
    """Nadi poveznice na PDF koje djeluju kao natjecaj, s iste domene.

    Namjerno preskace rezultate, rang-liste i zapisnike — to nisu natjecaji,
    a citanje starih rezultata kao aktualnog natjecaja bila bi gadna greska.
    Ograniceno na 2 datoteke da se ne prokopa cijela arhiva."""
    kandidati = []
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+\.pdf[^"\']*)["\']([^>]*)>(.*?)</a>',
                         html, re.I | re.S):
        href, tekst = m.group(1), m.group(3)
        pun = urljoin(baza, href)
        if urlparse(pun).netloc != urlparse(baza).netloc:
            continue
        cist = bez_kvacica(re.sub(r"<[^>]+>", " ", tekst))
        spoj = cist + " " + bez_kvacica(href)
        if not any(k in spoj for k in ("natjeca", "javni poziv", "stipendij", "poziv")):
            continue
        if any(k in spoj for k in NIJE_NATJECAJ):
            continue
        if pun not in kandidati:
            kandidati.append(pun)
        if len(kandidati) >= maks:
            break
    return kandidati


def _pitaj_model(client, prompt, model):
    raw = ""
    try:
        response = client.messages.create(
            model=model,
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = response.content[0].text.strip()
        raw = re.sub(r"^```(json)?|```$", "", raw, flags=re.MULTILINE).strip()
        return json.loads(raw)
    except json.JSONDecodeError:
        print("  ! Model nije vratio valjan JSON")
        return {"greska": "neispravan JSON", "sirovi_odgovor": raw[:300]}
    except Exception as e:
        print(f"  ! Greska API-ja: {e}")
        return {"greska": str(e)}


def extract_with_claude(client, page_text):
    """Prva razina: rubrika s popisom natjecaja."""
    return _pitaj_model(client, EXTRACTION_PROMPT.format(page_text=page_text), MODEL)


def procitaj_natjecaj(client, page_text):
    """Druga razina: stranica pojedinog natjecaja, citana boljim modelom.

    Ako zeljeni model nije dostupan (promijenjen naziv, ogranicenje racuna),
    pitanje se ponavlja jeftinim modelom umjesto da izvor ostane bez podataka."""
    prompt = NATJECAJ_PROMPT.format(page_text=page_text)
    odgovor = _pitaj_model(client, prompt, MODEL_NATJECAJ)
    if "greska" in odgovor and "JSON" not in str(odgovor.get("greska")):
        print(f"  ! {MODEL_NATJECAJ} nije odgovorio — ponavljam s {MODEL}")
        odgovor = _pitaj_model(client, prompt, MODEL)
    return odgovor


def parse_hr_date(text):
    """Prepoznaje: '4. studenoga 2025.' | '15.10.2025.' | '2025-10-15' | '15/10/2025'"""
    if not text:
        return None
    t = str(text).lower()
    m = re.search(r"(\d{1,2})\.\s*([a-zčćšđž]+)\s*(\d{4})", t)
    if m:
        day, mon, yr = m.groups()
        month = HR_MONTHS.get(mon)
        if month:
            try: return date(int(yr), month, int(day))
            except ValueError: pass
    m = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.\s*(\d{4})", t)
    if m:
        day, mon, yr = m.groups()
        try: return date(int(yr), int(mon), int(day))
        except ValueError: pass
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        yr, mon, day = m.groups()
        try: return date(int(yr), int(mon), int(day))
        except ValueError: pass
    m = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", t)
    if m:
        day, mon, yr = m.groups()
        try: return date(int(yr), int(mon), int(day))
        except ValueError: pass
    return None


def _izravni(kandidat, baza):
    """Prihvati poveznicu samo ako je na istoj domeni i razlicita od popisa."""
    if not kandidat:
        return None
    pun = urljoin(baza, str(kandidat).strip())
    if not pun.startswith(("http://", "https://")):
        return None
    if urlparse(pun).netloc != urlparse(baza).netloc:
        return None
    if pun.rstrip("/") == baza.rstrip("/"):
        return None
    return pun


RAZDOBLJA = ("mjesecno", "godisnje", "jednokratno")


def sredi_iznose(sirovo, maks=4):
    """Provjeri i ocisti listu iznosa koju je vratio model.

    Model povremeno vrati broj kao "380,00 EUR", razdoblje koje nismo trazili
    ili praznu stavku. Sve sto ne prode provjeru se odbacuje — kriva brojka na
    kartici gora je od nikakve, jer po njoj covjek odlucuje hoce li se prijaviti.
    Doslovni "iznos" ionako ostaje kao zaliha."""
    if not isinstance(sirovo, list):
        return []
    ishod = []
    for s in sirovo[:maks]:
        if not isinstance(s, dict):
            continue
        eur = s.get("eur")
        if isinstance(eur, str):
            # "1.250,50" -> 1250.50 ; "380,00 EUR" -> 380
            t = re.sub(r"[^\d.,]", "", eur).replace(".", "").replace(",", ".")
            try:
                eur = float(t)
            except ValueError:
                continue
        if not isinstance(eur, (int, float)) or not 0 < eur < 10_000_000:
            continue
        razd = str(s.get("razdoblje") or "").strip().lower()
        if razd not in RAZDOBLJA:
            razd = None
        mj = s.get("mjeseci")
        mj = mj if isinstance(mj, int) and 0 < mj <= 60 else None
        za = s.get("za")
        za = re.sub(r"\s+", " ", str(za)).strip()[:40] if za else None
        ishod.append({"eur": round(float(eur), 2), "razdoblje": razd,
                      "mjeseci": mj, "za": za or None, "do": bool(s.get("do"))})
    return ishod


def _za_usporedbu(t):
    """Svedi tekst na golo slovo i broj — mala slova, bez kvacica i interpunkcije.

    Stranice se razlikuju u razmacima, navodnicima i crticama, a model to pri
    prepisivanju uredno ujednaci. Bez ovoga bi gotovo svaki tocan navod pao na
    razmaku ili na drugoj vrsti crtice."""
    t = bez_kvacica(str(t))
    return re.sub(r"[^a-z0-9]+", " ", t).strip()


def dokaz_vrijedi(dokaz, tekst_stranice, najmanje=25):
    """Pojavljuje li se navedena recenica doista na stranici.

    Ovo je jedina provjera u cijelom lancu koju model ne moze zaobici govoreci
    uvjerljivo: navod se strojno trazi u tekstu koji je skinut sa stranice.
    Izmisljen iznos trazi i izmisljenu recenicu, a nju usporedba ne nade.

    Vraca True (navod postoji), False (ne postoji) ili None (model ga nije dao,
    pa se nema sto provjeriti)."""
    if not dokaz or not tekst_stranice:
        return None
    d = _za_usporedbu(dokaz)
    if len(d) < najmanje:            # prekratko da bi išta dokazivalo
        return None
    return d in _za_usporedbu(tekst_stranice)


def _brojevi_iz_teksta(t):
    """Svi brojevi koji se pojavljuju u tekstu, u svim razumnim citanjima.

    Hrvatski pise "2.325,00" (tocka za tisuce), izvori na engleskom "3,000".
    Isti niz znamenki zato ide u skup u oba citanja — namjerno popustljivo,
    jer ovo je sito protiv izmisljenih brojki, a ne mjerenje."""
    out = set()
    for m in re.finditer(r"\d[\d.,]*", str(t)):
        s = m.group(0).rstrip(".,")
        kandidati = []
        if "," in s:                       # hrvatski decimalni zarez
            cijeli, _, dec = s.rpartition(",")
            kandidati.append(cijeli.replace(".", "") + "." + dec)
        else:
            kandidati.append(s.replace(".", ""))      # "2.325" -> 2325
        kandidati.append(s.replace(",", ""))          # "3,000" -> 3000
        for k in kandidati:
            try:
                out.add(round(float(k), 2))
            except ValueError:
                pass
    return out


def provjeri_iznose(stavke, doslovno):
    """Zadrzi samo iznose koji se stvarno pojavljuju u tekstu s izvora.

    Provjera oblika hvata neispravan zapis, ali ne i netocan broj: ako model
    procita 380 kao 830, brojka izgleda posve uredno i zavrsi na kartici, gdje
    po njoj covjek odlucuje hoce li se prijaviti. Zato se svaka brojka mora
    naci i u doslovnom tekstu koji je prepisan sa stranice.

    Kad doslovnog teksta nema, nema se s cime usporediti pa se odbacuje sve —
    radije prazno polje nego brojka za koju ne znamo odakle je."""
    if not stavke:
        return [], 0
    nadeni = _brojevi_iz_teksta(doslovno) if doslovno else set()
    ostaje = [s for s in stavke if round(float(s["eur"]), 2) in nadeni]
    return ostaje, len(stavke) - len(ostaje)


def cist_naslov(s, maks=70):
    """Sredi naslov natjecaja da stane na karticu.

    Model povremeno ipak vrati cijeli sluzbeni naslov; ovdje se skrati na
    granici rijeci umjesto da razbije izgled kartice."""
    if not s:
        return None
    s = re.sub(r"\s+", " ", str(s)).strip(" .;:-—")
    if not s:
        return None
    if len(s) > maks:
        rez = s[:maks].rsplit(" ", 1)[0]
        s = (rez or s[:maks]) + "…"
    return s[0].upper() + s[1:]


def compute_status(rok_tekst, ima_otvoren_natjecaj):
    """Status se racuna PROGRAMSKI, ne prepusta se modelu."""
    if not ima_otvoren_natjecaj:
        return "NEMA AKTIVNOG NATJEČAJA (opća stranica)"
    rok = parse_hr_date(rok_tekst) if rok_tekst else None
    if rok is None:
        return "PROVJERITI RUČNO (rok nije jasno parsiran)"
    today = date.today()
    if rok >= today:
        days = (rok - today).days
        if days <= 14:
            return f"OTVORENO — rok za {days} dana ({rok.isoformat()})"
        return f"OTVORENO (rok {rok.isoformat()})"
    return f"ROK ISTEKAO ({rok.isoformat()}) — čeka se novi ciklus"


def ucitaj_prethodno(putanja=None):
    """Rezultat prethodnog rada, po adresi izvora."""
    putanja = putanja or OUTPUT_JSON
    if not os.path.exists(putanja):
        return {}
    try:
        with open(putanja, "r", encoding="utf-8") as f:
            return {r.get("url"): r for r in json.load(f) if r.get("url")}
    except (json.JSONDecodeError, OSError, AttributeError):
        return {}


def zadrzi_ako_je_nestao(novi, stari):
    """Ne daj da jedno lose citanje izbrise natjecaj koji jos traje.

    Stranice gradova znaju jednom vratiti praznu ljusku ili samo poruku o
    ucitavanju, a model zna promasiti. Posljedica je bila da natjecaj s rokom
    za dva tjedna nestane sa stranice usred sezone — a to je upravo ono zbog
    cega stranica postoji.

    Zato zapis prezivi neuspjelo citanje sve dok mu rok ne prode. Rok je
    prirodan istek: kad dode, natjecaj ionako odlazi s popisa otvorenih, pa
    zadrzani zapis ne moze zauvijek visjeti."""
    if not stari:
        return novi, False
    if (novi.get("status") or "").startswith("OTVORENO"):
        return novi, False                      # novo citanje je uspjelo
    if not (stari.get("status") or "").startswith("OTVORENO"):
        return novi, False                      # ni prije nije bio otvoren
    rok = parse_hr_date(stari.get("rok_tekst") or "")
    if not rok or rok < date.today():
        return novi, False                      # rok je prosao — neka ode
    zadrzan = dict(stari)
    zadrzan["zadnje_provjereno"] = novi.get("zadnje_provjereno")
    zadrzan["_zadrzan"] = True
    zadrzan["_zadnja_potvrda"] = (stari.get("_zadnja_potvrda")
                                  or stari.get("zadnje_provjereno"))
    return zadrzan, True


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def save_cache(cache):
    with open(CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)


def write_html(results):
    """Napise output.html - otvara se duplim klikom u pregledniku.
    Ovo je radni pregled za tebe, nije javna stranica (to radi web.py)."""
    def status_class(s):
        if s.startswith("OTVORENO"):
            return "otvoreno"
        if s.startswith("ROK ISTEKAO"):
            return "isteklo"
        if s.startswith("GRE"):
            return "greska"
        if s.startswith("PROVJERITI"):
            return "provjeriti"
        return "neaktivno"

    def esc(v):
        if v is None or v == "":
            return "&mdash;"
        return (str(v).replace("&", "&amp;").replace("<", "&lt;")
                .replace(">", "&gt;").replace('"', "&quot;"))

    order = {"otvoreno": 0, "provjeriti": 1, "greska": 2, "neaktivno": 3, "isteklo": 4}
    rows = sorted(results, key=lambda r: order.get(status_class(r.get("status", "")), 9))

    otvorenih = sum(1 for r in results if r.get("status", "").startswith("OTVORENO"))
    provjera = sum(1 for r in results
                   if r.get("status", "").startswith(("PROVJERITI", "GRE")))

    cards = []
    for r in rows:
        cls = status_class(r.get("status", ""))
        upute = r.get("upute_za_prijavu") or ""
        koraci = "".join(f"<li>{esc(k.strip())}</li>"
                         for k in upute.split("|") if k.strip()) if upute else ""
        cards.append(f"""
    <article class="kartica {cls}">
      <div class="zaglavlje">
        <h2>{esc(r.get('naziv'))}</h2>
        <span class="oznaka {cls}">{esc(r.get('status'))}</span>
      </div>
      <dl>
        <dt>Iznos</dt><dd>{esc(r.get('iznos'))}</dd>
        <dt>Rok</dt><dd>{esc(r.get('rok_tekst'))}</dd>
        <dt>Uvjeti</dt><dd>{esc(r.get('uvjeti'))}</dd>
        <dt>Kategorija</dt><dd>{esc(r.get('kategorija'))}</dd>
      </dl>
      {f'<div class="upute"><strong>Kako se prijaviti</strong><ol>{koraci}</ol></div>' if koraci else ''}
      <a class="izvor" href="{esc(r.get('poveznica_natjecaj') or r.get('url'))}" target="_blank">Otvori sluzbeni natjecaj &rarr;</a>
      <div class="provjereno">Provjereno: {esc(r.get('zadnje_provjereno'))}</div>
    </article>""")

    html = f"""<!DOCTYPE html>
<html lang="hr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>stipendije.hr &mdash; radni pregled</title>
<style>
  * {{ box-sizing: border-box; }}
  body {{ font-family: -apple-system, "Segoe UI", Roboto, sans-serif;
         margin: 0; padding: 2rem 1rem; background: #f4f5f7; color: #1a1a1a; }}
  .omot {{ max-width: 900px; margin: 0 auto; }}
  h1 {{ font-size: 1.6rem; margin: 0 0 .3rem; }}
  .podnaslov {{ color: #666; margin-bottom: 1.5rem; font-size: .9rem; }}
  .sazetak {{ display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 2rem; }}
  .broj {{ background: #fff; border-radius: 8px; padding: .8rem 1.2rem;
           border: 1px solid #e0e0e0; }}
  .broj b {{ display: block; font-size: 1.6rem; }}
  .broj span {{ font-size: .8rem; color: #666; }}
  .kartica {{ background: #fff; border-radius: 10px; padding: 1.2rem;
              margin-bottom: 1rem; border: 1px solid #e0e0e0;
              border-left: 5px solid #ccc; }}
  .kartica.otvoreno {{ border-left-color: #1a9c4a; }}
  .kartica.isteklo {{ border-left-color: #c0392b; opacity: .65; }}
  .kartica.greska {{ border-left-color: #e67e22; }}
  .kartica.provjeriti {{ border-left-color: #e6b800; }}
  .zaglavlje {{ display: flex; justify-content: space-between;
                align-items: flex-start; gap: 1rem; flex-wrap: wrap; }}
  h2 {{ font-size: 1.05rem; margin: 0 0 .6rem; }}
  .oznaka {{ font-size: .72rem; padding: .25rem .6rem; border-radius: 20px;
             white-space: nowrap; font-weight: 600; }}
  .oznaka.otvoreno {{ background: #d8f3e2; color: #0d6b32; }}
  .oznaka.isteklo {{ background: #fadbd8; color: #922b21; }}
  .oznaka.greska {{ background: #fdebd0; color: #a04000; }}
  .oznaka.provjeriti {{ background: #fcf3cf; color: #7d6608; }}
  .oznaka.neaktivno {{ background: #eee; color: #555; }}
  dl {{ display: grid; grid-template-columns: 110px 1fr; gap: .35rem 1rem;
        margin: .5rem 0; font-size: .9rem; }}
  dt {{ color: #777; }}
  dd {{ margin: 0; }}
  .upute {{ background: #f8f9fa; border-radius: 6px; padding: .8rem;
            margin: .8rem 0; font-size: .88rem; }}
  .upute ol {{ margin: .5rem 0 0; padding-left: 1.2rem; }}
  .upute li {{ margin-bottom: .3rem; }}
  .izvor {{ display: inline-block; margin-top: .5rem; color: #1558d6;
            text-decoration: none; font-size: .9rem; }}
  .izvor:hover {{ text-decoration: underline; }}
  .provjereno {{ font-size: .75rem; color: #999; margin-top: .6rem; }}
</style>
</head>
<body>
<div class="omot">
  <h1>stipendije.hr &mdash; radni pregled izvora</h1>
  <p class="podnaslov">Automatski generirano {datetime.now().strftime('%d.%m.%Y. u %H:%M')}
     &middot; {len(results)} izvora</p>
  <div class="sazetak">
    <div class="broj"><b>{otvorenih}</b><span>trenutno otvorenih</span></div>
    <div class="broj"><b>{provjera}</b><span>treba provjeriti</span></div>
    <div class="broj"><b>{len(results)}</b><span>ukupno izvora</span></div>
  </div>
  {"".join(cards)}
</div>
</body>
</html>"""

    with open(OUTPUT_HTML, "w", encoding="utf-8") as f:
        f.write(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="ignoriraj cache, obradi sve")
    ap.add_argument("--samo", metavar="TEKST",
                    help="obradi samo izvore ciji naziv ili url sadrze TEKST "
                         "(za probu na jednom izvoru, bez trosenja na svih 120)")
    ap.add_argument("--limit", type=int, metavar="N",
                    help="obradi najvise N izvora")
    args = ap.parse_args()

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("GRESKA: nedostaje ANTHROPIC_API_KEY.")
        print("Postavi s: export ANTHROPIC_API_KEY='sk-ant-...'")
        sys.exit(1)

    if not os.path.exists(SOURCES_FILE):
        print(f"GRESKA: {SOURCES_FILE} ne postoji.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)
    with open(SOURCES_FILE, "r", encoding="utf-8") as f:
        sources = json.load(f)

    # Proba na dijelu izvora NE smije prepisati output.json — inace bi stranica
    # ostala samo s tih par izvora. Zato se u probnom radu nista ne zapisuje.
    proba = bool(args.samo or args.limit)
    if args.samo:
        t = bez_kvacica(args.samo)
        sources = [s for s in sources
                   if t in bez_kvacica(s.get("naziv", ""))
                   or t in bez_kvacica(s.get("url", ""))]
        if not sources:
            print(f"Nijedan izvor ne odgovara '{args.samo}'.")
            sys.exit(1)
    if args.limit:
        sources = sources[:args.limit]
    if proba:
        print(f"PROBNI RAD na {len(sources)} izvora — "
              f"output.json/csv/html i cache se NE mijenjaju.\n")

    cache = {} if args.force else load_cache()
    prethodno = ucitaj_prethodno()
    zadrzanih = 0
    results, needs_review, skipped = [], [], 0
    pdf_procitano = 0
    drugih_poziva = 0        # koliko je dodatnih poziva modelu otislo na podstranice
    nadeno_drugim = 0        # koliko je natjecaja naden tek na drugoj razini
    odbacenih_iznosa = 0     # brojke koje se nisu poklopile s tekstom izvora
    pao_dokaz_iznos = 0      # iznos ugasen jer navedene recenice nema na stranici
    pao_dokaz_rok = 0        # rok bez potvrde u tekstu — samo se prijavljuje
    bez_dokaza = 0           # model uopce nije dao navod
    granica_javljena = False

    if not PDF_SUPPORT:
        print("NAPOMENA: 'pypdf' nije instaliran — PDF natjecaji ce biti preskoceni.")
        print("Instaliraj s: pip install pypdf\n")

    print(f"Obradujem {len(sources)} izvora...\n")

    for i, src in enumerate(sources, 1):
        name, url = src["naziv"], src["url"]
        print(f"[{i}/{len(sources)}] {name}")

        text, content_hash, sirovi = fetch_content(url)
        now = datetime.now().isoformat(timespec="minutes")

        if text is None:
            r = {"naziv": name, "url": url, "kategorija": src.get("kategorija", ""),
                 "status": "GREŠKA — stranica nedostupna, provjeriti ručno",
                 "zadnje_provjereno": now}
            r, zadrzan = zadrzi_ako_je_nestao(r, prethodno.get(url))
            if zadrzan:
                zadrzanih += 1
                print(f"  = stranica nedostupna, ali rok jos traje -> zadrzan "
                      f"zapis od {r.get('_zadnja_potvrda')}")
            results.append(r); needs_review.append(r)
            continue

        # Ako je natjecaj samo najavljen, a sam tekst je u PDF-u iza poveznice,
        # dohvati i taj PDF i spoji ga s tekstom stranice.
        if sirovi and PDF_SUPPORT:
            for pdf_url in pdf_poveznice(sirovi, url):
                pdf_text, _, _ = fetch_content(pdf_url, retries=0, tiho=True)
                if pdf_text:
                    print(f"  + procitan PDF: {pdf_url.rsplit('/', 1)[-1][:50]}")
                    text = (text + "\n\n--- TEKST IZ PRILOZENOG PDF-a ---\n"
                            + pdf_text)[:MAX_CHARS * 2]
                    pdf_procitano += 1
                time.sleep(1)
            # hash se racuna nakon spajanja da cache prati i sadrzaj PDF-a
            content_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]

        kljuc = f"v{VERZIJA_EKSTRAKCIJE}:{content_hash}"
        cached = cache.get(url)
        if cached and cached.get("hash") == kljuc:
            r = dict(cached["result"])
            r["zadnje_provjereno"] = now
            # status se PONOVO racuna jer se datum promijenio i ako se stranica nije
            r["status"] = compute_status(r.get("rok_tekst"), r.get("_ima_otvoren", False))
            results.append(r)
            skipped += 1
            print(f"  = nepromijenjeno (cache) -> {r['status']}")
            if "PROVJERITI" in r["status"]:
                needs_review.append(r)
            continue

        extracted = extract_with_claude(client, text)

        if "greska" in extracted:
            r = {"naziv": name, "url": url, "kategorija": src.get("kategorija", ""),
                 "status": f"GREŠKA — {extracted['greska']}, provjeriti ručno",
                 "zadnje_provjereno": now}
            r, zadrzan = zadrzi_ako_je_nestao(r, prethodno.get(url))
            if zadrzan:
                zadrzanih += 1
                print(f"  = model nije uspio, ali rok jos traje -> zadrzan "
                      f"zapis od {r.get('_zadnja_potvrda')}")
            results.append(r); needs_review.append(r)
            time.sleep(DELAY_SEC)
            continue

        ima_otvoren = extracted.get("ima_otvoren_natjecaj", False)
        izvor_natjecaja = None
        odbaceno_ovdje = 0
        # tekst iz kojeg je podatak stvarno izvucen — prema njemu se provjerava
        # navod; kad drugi prolaz uspije, to vise nije popisna stranica
        tekst_izvora = text

        # --- drugi prolaz: popisna stranica, natjecaj jedan klik dalje ---
        # Ako popisna stranica nije dala natjecaj s rokom, otvori do dvije
        # poveznice koje na njoj izgledaju kao natjecaj za stipendiju. Tek ako
        # ni ondje nema roka, ostaje "nema aktivnog natjecaja".
        pricuva = None
        if sirovi and not (ima_otvoren and extracted.get("rok_tekst")):
            for pod_url in natjecaj_poveznice(sirovi, url):
                if drugih_poziva >= MAKS_DRUGI_PROLAZ:
                    if not granica_javljena:
                        print(f"  ! dosegnuta granica od {MAKS_DRUGI_PROLAZ} "
                              f"dodatnih poziva — drugi prolaz se dalje preskace")
                        granica_javljena = True
                    break
                pod_text, _, pod_html = fetch_content(pod_url, retries=0, tiho=True)
                time.sleep(1)
                if not pod_text:
                    continue

                # Na podstranici natjecaja iznos cesto nije u tekstu nego u
                # prilozenom PDF-u ("dostupan je u prilozenim dokumentima").
                # Prva razina vec cita PDF-ove; bez ovoga bi druga ostala bez
                # njih i natjecaj bi zavrsio na stranici bez iznosa.
                if pod_html and PDF_SUPPORT:
                    for pdf_url in pdf_poveznice(pod_html, pod_url):
                        pdf_text, _, _ = fetch_content(pdf_url, retries=0, tiho=True)
                        if pdf_text:
                            print(f"  + procitan PDF uz natjecaj: "
                                  f"{pdf_url.rsplit('/', 1)[-1][:45]}")
                            pod_text = (pod_text
                                        + "\n\n--- TEKST IZ PRILOZENOG PDF-a ---\n"
                                        + pdf_text)[:MAX_CHARS * 2]
                            pdf_procitano += 1
                        time.sleep(1)

                pod = procitaj_natjecaj(client, pod_text)
                drugih_poziva += 1
                time.sleep(DELAY_SEC)
                if "greska" in pod:
                    continue
                if not pod.get("ima_otvoren_natjecaj"):
                    continue
                if pod.get("rok_tekst"):
                    print(f"  + natjecaj nadem na podstranici: {pod_url[:70]}")
                    extracted = pod
                    ima_otvoren = True
                    izvor_natjecaja = pod_url
                    tekst_izvora = pod_text
                    nadeno_drugim += 1
                    break
                # Natjecaj bez citljivog roka nije bezvrijedan — ide u pricuvu.
                # Ako nijedna druga poveznica ne da bolji, uzet ce se ovaj i
                # zavrsiti kao "provjeriti rucno", sto je posteno: postoji, ali
                # mu ne znamo rok. Prije se u tom slucaju gubio bez traga.
                if pricuva is None:
                    pricuva = (pod, pod_url, pod_text)

        if pricuva is not None and not ima_otvoren:
            pod, pod_url, pod_text = pricuva
            print(f"  + natjecaj bez citljivog roka: {pod_url[:60]}")
            extracted, ima_otvoren = pod, True
            izvor_natjecaja, tekst_izvora = pod_url, pod_text
            nadeno_drugim += 1

        status = compute_status(extracted.get("rok_tekst"), ima_otvoren)

        iznosi, odbaceno_ovdje = provjeri_iznose(
            sredi_iznose(extracted.get("iznosi")), extracted.get("iznos"))
        if odbaceno_ovdje:
            print(f"  ! odbacenih iznosa: {odbaceno_ovdje} "
                  f"(brojka se ne pojavljuje u tekstu izvora)")
            odbacenih_iznosa += odbaceno_ovdje

        # --- navod mora postojati na stranici ---
        # Novac se gasi odmah: krivi iznos je gori od nikakvog, a kartica ima
        # pristojno "nije naveden" za taj slucaj.
        ok_iznos = dokaz_vrijedi(extracted.get("dokaz_iznos"), tekst_izvora)
        if ok_iznos is False and iznosi:
            print("  ! iznos odbacen — navedena recenica ne postoji na stranici")
            iznosi = []
            pao_dokaz_iznos += 1
        elif ok_iznos is None and iznosi:
            bez_dokaza += 1

        # Rok se NE gasi: bez njega bi otvoren natjecaj nestao sa stranice, a
        # to je gore od dvojbenog datuma. Umjesto toga ide u prijavu za pregled.
        ok_rok = dokaz_vrijedi(extracted.get("dokaz_rok"), tekst_izvora)
        if ok_rok is False and extracted.get("rok_tekst"):
            print("  ! rok bez potvrde u tekstu — ide na rucnu provjeru")
            pao_dokaz_rok += 1

        r = {
            "naziv": name, "url": url, "kategorija": src.get("kategorija", ""),
            # naslov samog natjecaja; kartica ga pokazuje umjesto imena izvora,
            # jer se natjecaj sve cesce nalazi na podstranici drugog imena
            "naslov_natjecaja": cist_naslov(extracted.get("naslov_natjecaja")),
            "iznos": extracted.get("iznos"),
            # isti podatak rastavljen na brojke, da kartica moze prikazati
            # sve stipendije u istom obliku i da se daju usporedivati;
            # svaka brojka mora se naci i u doslovnom tekstu s izvora
            "iznosi": iznosi,
            "iznos_je_fond": bool(extracted.get("iznos_je_fond")),
            "rok_tekst": extracted.get("rok_tekst"),
            "uvjeti": extracted.get("uvjeti"),
            "upute_za_prijavu": extracted.get("upute_za_prijavu"),
            "napomena": extracted.get("napomena"),
            # ako je natjecaj nadem na podstranici, ona JE izravna poveznica
            "poveznica_natjecaj": (izvor_natjecaja
                                   or _izravni(extracted.get("poveznica_natjecaj"), url)),
            "status": status,
            "zadnje_provjereno": now,
            "_ima_otvoren": ima_otvoren,
        }
        # Natjecaj koji je jucer bio otvoren, a danas ga citanje ne vidi, ne
        # smije nestati dok mu rok ne prode — vidi zadrzi_ako_je_nestao.
        r, zadrzan = zadrzi_ako_je_nestao(r, prethodno.get(url))
        if zadrzan:
            zadrzanih += 1
            print(f"  = citanje ga vise ne vidi, ali rok jos traje -> zadrzan "
                  f"zapis od {r.get('_zadnja_potvrda')}")
            status = r.get("status") or status

        results.append(r)
        cache[url] = {"hash": kljuc, "result": r}

        if "PROVJERITI" in status or "GREŠKA" in status or ok_rok is False or zadrzan:
            needs_review.append(r)

        print(f"  -> {status}")
        time.sleep(DELAY_SEC)

    if proba:
        print(f"\n{'='*50}")
        print("PROBNI RAD — nista nije zapisano. Rezultat:")
        for r in results:
            print(f"  {r.get('status','')[:60]}")
            print(f"     {r.get('naziv','')}")
            if r.get("rok_tekst"):
                print(f"     rok: {r['rok_tekst']}   iznos: {r.get('iznos')}")
            if r.get("poveznica_natjecaj"):
                print(f"     natjecaj: {r['poveznica_natjecaj']}")
        return

    save_cache(cache)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    fields = ["naziv", "naslov_natjecaja", "url", "kategorija", "iznos",
              "iznos_je_fond", "rok_tekst", "uvjeti",
              "upute_za_prijavu", "napomena", "poveznica_natjecaj",
              "status", "zadnje_provjereno"]
    # utf-8-sig = UTF-8 s BOM oznakom -> Excel na Windowsu ispravno prikaze kvacice.
    # "sep=," u prvom retku -> Excel razdvoji podatke po stupcima umjesto da sve
    # nagura u stupac A (hrvatski Windows inace ocekuje tocka-zarez).
    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        f.write("sep=,\n")
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader(); w.writerows(results)

    write_html(results)

    otvoreni = [r for r in results if r.get("status", "").startswith("OTVORENO")]

    print(f"\n{'='*50}")
    print(f"Spremljeno: {OUTPUT_HTML}  <-- OTVORI OVU DATOTEKU")
    print(f"           {OUTPUT_JSON}, {OUTPUT_CSV}")
    print(f"Ukupno izvora:        {len(results)}")
    print(f"Preskoceno (cache):   {skipped}")
    print(f"Procitanih PDF-ova:   {pdf_procitano}")
    print(f"Dodatnih poziva:      {drugih_poziva} (drugi prolaz po podstranicama)")
    print(f"Nadeno tek 2. razinom:{nadeno_drugim}")
    print(f"Odbacenih iznosa:     {odbacenih_iznosa} "
          f"(brojka se nije nasla u tekstu izvora)")
    print(f"Zadrzano unatoc promasaju: {zadrzanih} "
          f"(rok jos traje, cekaju potvrdu)")
    print(f"--- provjera navoda ---")
    print(f"Iznos bez potvrde:    {pao_dokaz_iznos} (ugasen)")
    print(f"Rok bez potvrde:      {pao_dokaz_rok} (prijavljen, ostaje vidljiv)")
    print(f"Model nije dao navod: {bez_dokaza} (podatak zadrzan)")
    print(f"TRENUTNO OTVORENIH:   {len(otvoreni)}")
    print(f"Treba rucnu provjeru: {len(needs_review)}")
    if otvoreni:
        print("\nOTVORENE STIPENDIJE:")
        for r in otvoreni:
            print(f"  + {r['naziv']}: {r['status']}")
    if needs_review:
        print("\nZA RUCNU PROVJERU:")
        for r in needs_review:
            print(f"  - {r['naziv']}: {r['status']}")


if __name__ == "__main__":
    main()
