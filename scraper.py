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
MODEL = "claude-haiku-4-5-20251001"   # najjeftiniji; za bolju kvalitetu: "claude-sonnet-5"
REQUEST_TIMEOUT = 25
DELAY_SEC = 2
MAX_CHARS = 15000

# Cache pamti rezultat dok se stranica ne promijeni. Kad se promijeni NACIN
# citanja (prompt, drugi prolaz po podstranicama), stari rezultati vise ne
# vrijede — podigni ovaj broj i cijeli cache se jednom ponovno procita.
VERZIJA_EKSTRAKCIJE = 2

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
  "iznos": "iznos stipendije kako je naveden (npr. '200 EUR mjesecno, 10 mjeseci') ili null",
  "rok_tekst": "rok prijave DOSLOVNO kako pise u tekstu (npr. '4. studenoga 2025.') ili null ako nema konkretnog trenutnog natjecaja",
  "uvjeti": "tko se moze prijaviti, 1-2 recenice, ili null",
  "upute_za_prijavu": "3-6 kratkih koraka odvojenih s ' | ', ili null",
  "ima_otvoren_natjecaj": true/false — je li ocito da JE objavljen konkretan natjecaj (ne samo opca stranica o programu),
  "napomena": "bilo sto neuobicajeno sto covjek treba znati, ili null",
  "poveznica_natjecaj": "ako na stranici postoji poveznica koja vodi IZRAVNO na tekst natjecaja (a ne na popis), upisi ju ovdje; inace null"
}}

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


def extract_with_claude(client, page_text):
    prompt = EXTRACTION_PROMPT.format(page_text=page_text)
    raw = ""
    try:
        response = client.messages.create(
            model=MODEL,
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
    results, needs_review, skipped = [], [], 0
    pdf_procitano = 0
    drugih_poziva = 0        # koliko je dodatnih poziva modelu otislo na podstranice
    nadeno_drugim = 0        # koliko je natjecaja naden tek na drugoj razini
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
            results.append(r); needs_review.append(r)
            time.sleep(DELAY_SEC)
            continue

        ima_otvoren = extracted.get("ima_otvoren_natjecaj", False)
        izvor_natjecaja = None

        # --- drugi prolaz: popisna stranica, natjecaj jedan klik dalje ---
        # Ako popisna stranica nije dala natjecaj s rokom, otvori do dvije
        # poveznice koje na njoj izgledaju kao natjecaj za stipendiju. Tek ako
        # ni ondje nema roka, ostaje "nema aktivnog natjecaja".
        if sirovi and not (ima_otvoren and extracted.get("rok_tekst")):
            for pod_url in natjecaj_poveznice(sirovi, url):
                if drugih_poziva >= MAKS_DRUGI_PROLAZ:
                    if not granica_javljena:
                        print(f"  ! dosegnuta granica od {MAKS_DRUGI_PROLAZ} "
                              f"dodatnih poziva — drugi prolaz se dalje preskace")
                        granica_javljena = True
                    break
                pod_text, _, _ = fetch_content(pod_url, retries=0, tiho=True)
                time.sleep(1)
                if not pod_text:
                    continue
                pod = extract_with_claude(client, pod_text)
                drugih_poziva += 1
                time.sleep(DELAY_SEC)
                if "greska" in pod:
                    continue
                if pod.get("ima_otvoren_natjecaj") and pod.get("rok_tekst"):
                    print(f"  + natjecaj nadem na podstranici: {pod_url[:70]}")
                    extracted = pod
                    ima_otvoren = True
                    izvor_natjecaja = pod_url
                    nadeno_drugim += 1
                    break

        status = compute_status(extracted.get("rok_tekst"), ima_otvoren)

        r = {
            "naziv": name, "url": url, "kategorija": src.get("kategorija", ""),
            "iznos": extracted.get("iznos"),
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
        results.append(r)
        cache[url] = {"hash": kljuc, "result": r}

        if "PROVJERITI" in status or "GREŠKA" in status:
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

    fields = ["naziv", "url", "kategorija", "iznos", "rok_tekst", "uvjeti",
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
