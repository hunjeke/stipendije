# -*- coding: utf-8 -*-
"""
strazar.py — gleda izlazi li natjecaj za drzavnu stipendiju

Redovna provjera ide ponedjeljkom i cetvrtkom. Za drzavnu stipendiju to je
premalo: ministarstvo je zna objaviti u utorak poslijepodne, a rok je kratak,
pa bi se za nju saznalo tek u cetvrtak ujutro — dva dana kasnije, a to su
dva dana od petnaest.

Ova skripta zato gleda samo dvije stranice ministarstva, nekoliko puta na dan.
Ne koristi Claude API — samo dohvati tekst i potrazi u njemu natjecaj za
tekucu akademsku godinu. Zato je jeftina koliko i obican posjet stranici.

Radije lazna uzbuna nego propusten natjecaj: ako nesto samo lici na objavu,
javlja. Pogledati i vidjeti da nije nista kosta minutu; propustiti objavu
kosta cijeli dogadaj.

Kad nesto nade, ne stane na dojavi: otvori stranicu natjecaja, izvuce rok,
iznos i broj stipendija, i napise gotove tekstove — poruku za kanal i mail
pretplatnicima — s vec upisanim brojkama. Ti ih samo pogledas i posaljes.
Sto nije uspjelo procitati ostavlja kao {ROK} ili {IZNOS}, da se vidi da
tu treba upisati rukom, umjesto da ponudi brojku u koju se ne moze vjerovati.

Pokretanje:
    python strazar.py           provjeri i javi ako ima novo
    python strazar.py --reset   zaboravi sto je vec javljeno
"""
import json
import os
import re
import sys
from urllib.parse import urljoin

from scraper import fetch_content, bez_kvacica, parse_hr_date

# Stranice koje se gledaju. Prva je stranica same drzavne stipendije,
# druga je opci popis natjecaja — objava zna osvanuti na bilo kojoj.
STRANICE = [
    ("Drzavne stipendije (socio-ekonomski status)",
     "https://mzom.gov.hr/istaknute-teme/odgoj-i-obrazovanje/visoko-obrazovanje/"
     "drzavne-stipendije/drzavne-stipendije-za-studente-nizega-socio-"
     "ekonomskoga-statusa/1563"),
    ("Svi natjecaji ministarstva",
     "https://mzom.gov.hr/natjecaji-196/196"),
]

PAMCENJE = "strazar.json"

# Akademska godina se pise na vise nacina; svi se svode na isto.
GODINA = re.compile(r"20(\d\d)\s*\.?\s*/\s*\.?\s*20(\d\d)")


def _godina_se_poklapa(s, od):
    """Je li u tekstu akademska godina koja pocinje ove jeseni."""
    for m in GODINA.finditer(s):
        if int("20" + m.group(1)) == od:
            return True
    return False


def _pocetna_godina():
    """Akademska godina koja je u tijeku ili tek krece.

    Od sijecnja do lipnja jos traje ona koja je pocela lani, ali natjecaj
    koji tad izade odnosi se na sljedecu. Granicu stavljamo na srpanj."""
    from datetime import date
    d = date.today()
    return d.year if d.month >= 7 else d.year - 1


def nalazi(tekst, od):
    """Retci koji izgledaju kao objava natjecaja za akademsku godinu 'od'."""
    pogoci = []
    for red in tekst.splitlines():
        r = bez_kvacica(red)
        if "stipendij" not in r:
            continue
        if not ("natjecaj" in r or "javni poziv" in r or "prijave" in r):
            continue
        if not _godina_se_poklapa(red, od):
            continue
        red = red.strip()
        if 10 < len(red) < 400:
            pogoci.append(red)
    return pogoci


# --- citanje pojedinosti iz natjecaja -------------------------------------

HR_MJESEC = ("sijecnja|veljace|ozujka|travnja|svibnja|lipnja|srpnja|kolovoza|"
             "rujna|listopada|studenoga|prosinca")

_ROK = [
    re.compile(r"\brok\s*:?\s*(\d{1,2}\.\s*(?:" + HR_MJESEC + r")\s*\d{4}\.?"
               r"(?:\s*(?:godine)?\s*do\s*\d{1,2}[.:]\d{2})?)", re.I),
    re.compile(r"rok za (?:podno[sš]enje|predaju|prijavu)[^.]{0,80}?je\s*"
               r"(\d{1,2}\.\s*(?:" + HR_MJESEC + r")\s*\d{4})", re.I),
    re.compile(r"prijave[^.]{0,60}?do\s*(\d{1,2}\.\s*(?:" + HR_MJESEC + r")\s*\d{4})", re.I),
]
_IZNOS = re.compile(r"iznos[^.\n]{0,120}?(\d[\d.\s]*,?\d*)\s*(?:EUR|eura|€)", re.I)
_BROJ = re.compile(r"(?:dodijelit [cć]e se|dodjeljuje se|natje[cč]aj za dodjelu)\s*"
                   r"([\d][\d.\s]{0,9}\d|\d)\s*(?:\w+\s+){0,3}stipendij", re.I)


def _cisto(s):
    return re.sub(r"\s+", " ", (s or "")).strip(" .,;")


def detalji(url):
    """Izvuci rok, iznose i broj stipendija sa stranice natjecaja.

    Vraca rjecnik s onim sto je naslo. Polje koje nije naslo naprosto
    izostaje — bolje prazno mjesto u tekstu nego brojka iz krive recenice."""
    tekst, _, _ = fetch_content(url, tiho=True)
    if not tekst:
        return {}
    d = {}

    for uzorak in _ROK:
        m = uzorak.search(tekst)
        if m:
            d["rok_tekst"] = _cisto(m.group(1))
            datum = parse_hr_date(d["rok_tekst"])
            if datum:
                d["rok_iso"] = datum.isoformat()
            break

    iznosi = []
    for red in tekst.splitlines():
        m = _IZNOS.search(red)
        if m and len(red) < 320:
            iznosi.append(_cisto(red))
        if len(iznosi) >= 4:
            break
    if iznosi:
        d["iznos_redci"] = iznosi

    m = _BROJ.search(tekst)
    if m:
        d["broj"] = _cisto(m.group(1))
    return d


def _popuni(sablona, d):
    """Zamijeni {ROK}, {IZNOS} i {BROJ} ako su procitani; inace ostavi oznaku."""
    rok = d.get("rok_tekst")
    broj = d.get("broj")
    iznos = None
    for red in d.get("iznos_redci") or []:
        m = re.search(r"(\d[\d.\s]*,?\d*)\s*(?:EUR|eura|€)", red, re.I)
        if m:
            iznos = _cisto(m.group(1)) + " EUR"
            break
    return (sablona
            .replace("{ROK}", rok or "{ROK}")
            .replace("{IZNOS}", iznos or "{IZNOS}")
            .replace("{BROJ}", broj or "{BROJ}"))


KANAL = """Državne stipendije su izašle 🎓

{BROJ} stipendija, {IZNOS} mjesečno.
Rok za prijavu: {ROK}

Prijava ide preko sustava VIDRA — vidra.srce.hr

Sve što trebaš znati, uvjeti i upute:
stipendije.hr/drzavna-stipendija.html

Ne ostavljaj za zadnji dan. Potvrdu o upisu referade ne izdaju
na licu mjesta."""

MAIL_PREDMET = "Državne stipendije su izašle — rok {ROK}"

MAIL = """Natječaj za državne stipendije je objavljen.

{BROJ} stipendija · {IZNOS} mjesečno · rok {ROK}

Prijava se predaje preko sustava VIDRA (vidra.srce.hr), elektronički.
Papirnata prijava se ne prima.

Uvjeti, bodovanje i popis dokumenata:
https://stipendije.hr/drzavna-stipendija.html

Dvije stvari zbog kojih ljudi propuste:
— potvrda o upisu se ne izdaje na licu mjesta, zatraži je odmah
— rok nije u ponoć ako natječaj kaže drugačije, provjeri sat

Sve ostale otvorene stipendije: https://stipendije.hr

Ovo dobivaš jer si se prijavio na obavijesti za svoju županiju."""


def _veza_na_natjecaj(sirovi_html, baza, naslov):
    """Poveznica iza naslova natjecaja na popisnoj stranici.

    Popis ministarstva nosi samo naslove; rok i iznos su jedan klik dalje.
    Trazi se poveznica ciji se tekst poklapa s naslovom koji smo nasli."""
    if not sirovi_html:
        return None
    cilj = bez_kvacica(naslov)[:60]
    for m in re.finditer(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                         sirovi_html, re.I | re.S):
        href, tekst = m.group(1), re.sub(r"<[^>]+>", " ", m.group(2))
        if href.lower().startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        if cilj and cilj in bez_kvacica(tekst):
            return urljoin(baza, href)
    return None


def _ucitaj():
    try:
        with open(PAMCENJE, encoding="utf-8") as f:
            return set(json.load(f).get("javljeno", []))
    except (OSError, ValueError):
        return set()


def _spremi(javljeno):
    with open(PAMCENJE, "w", encoding="utf-8") as f:
        json.dump({"javljeno": sorted(javljeno)}, f, ensure_ascii=False, indent=1)


def _izlaz(kljuc, vrijednost):
    """Posalji vrijednost u GitHub Actions, ako se ondje vrtimo."""
    put = os.environ.get("GITHUB_OUTPUT")
    if put:
        with open(put, "a", encoding="utf-8") as f:
            f.write(f"{kljuc}={vrijednost}\n")


def main():
    if "--reset" in sys.argv:
        _spremi(set())
        print("Pamćenje očišćeno.")
        return

    od = _pocetna_godina()
    javljeno = _ucitaj()
    novo = []

    for ime, url in STRANICE:
        tekst, _, sirovi = fetch_content(url, tiho=True)
        if not tekst:
            print(f"  ! {ime}: stranica se ne da dohvatiti")
            continue
        for red in nalazi(tekst, od):
            kljuc = bez_kvacica(red)[:160]
            if kljuc in javljeno:
                continue
            javljeno.add(kljuc)
            # Poveznica na sam natjecaj, ako je ima — ondje su rok i iznos.
            # Popisna stranica ima samo naslov.
            veza = _veza_na_natjecaj(sirovi, url, red) or url
            novo.append((ime, veza, red, detalji(veza)))

    _spremi(javljeno)

    if not novo:
        print(f"Nema novog natječaja za {od}./{od+1}.")
        _izlaz("naslo", "0")
        return

    redci = [f"## Moguća objava natječaja — {od}./{od+1}.", "",
             "Provjeri na izvoru prije nego išta pošalješ. Ovo je automatska "
             "dojava i zna javiti natječaj koji nije državna stipendija.", ""]

    for ime, url, red, d in novo:
        redci += [f"### {_cisto(red)}", "", f"Izvor: {ime}", "", url, ""]
        redci += ["| podatak | pročitano |", "|---|---|",
                  f"| rok | {d.get('rok_tekst') or '— nije pročitano'} |",
                  f"| broj stipendija | {d.get('broj') or '— nije pročitano'} |"]
        for i, iz in enumerate(d.get("iznos_redci") or []):
            redci.append(f"| iznos {i+1} | {iz} |")
        if not d.get("iznos_redci"):
            redci.append("| iznos | — nije pročitano |")
        redci += ["", "**Poruka za WhatsApp kanal**", "", "```",
                  _popuni(KANAL, d), "```", "",
                  "**Mail pretplatnicima**", "",
                  f"Predmet: `{_popuni(MAIL_PREDMET, d)}`", "", "```",
                  _popuni(MAIL, d), "```", ""]

    redci += ["---", "",
              "### Redoslijed",
              "",
              "1. upiši `BROJ` i `IZNOS` u `drzavna.py` (`OTVOREN` ostavi `None`)",
              "2. pokreni „Provjera stipendija”",
              "3. provjeri stranicu",
              "4. kanal → mail → Instagram → portali",
              "",
              "Gdje piše `{ROK}` ili `{IZNOS}`, pročitati nije uspjelo — "
              "upiši rukom prije slanja.",
              "",
              "Puni tekstovi i dojava portalima: `drzavna-paket.md`."]
    open("strazar.md", "w", encoding="utf-8").write("\n".join(redci) + "\n")

    print(f"NAŠAO: {len(novo)} — zapisano u strazar.md")
    _izlaz("naslo", str(len(novo)))


if __name__ == "__main__":
    main()
