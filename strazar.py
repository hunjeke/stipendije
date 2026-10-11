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

Pokretanje:
    python strazar.py           provjeri i javi ako ima novo
    python strazar.py --reset   zaboravi sto je vec javljeno
"""
import json
import os
import re
import sys

from scraper import fetch_content, bez_kvacica

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
        tekst, _, _ = fetch_content(url, tiho=True)
        if not tekst:
            print(f"  ! {ime}: stranica se ne da dohvatiti")
            continue
        for red in nalazi(tekst, od):
            kljuc = bez_kvacica(red)[:160]
            if kljuc in javljeno:
                continue
            javljeno.add(kljuc)
            novo.append((ime, url, red))

    _spremi(javljeno)

    if not novo:
        print(f"Nema novog natječaja za {od}./{od+1}.")
        _izlaz("naslo", "0")
        return

    redci = [f"## Moguća objava natječaja — {od}./{od+1}.", ""]
    for ime, url, red in novo:
        redci += [f"**{ime}**", "", f"> {red}", "", url, ""]
    redci += ["---", "",
              "Ovo je automatska dojava. Provjeri je li natječaj stvarno "
              "objavljen, pa:",
              "",
              "1. upiši `BROJ` i `IZNOS` u `drzavna.py` (`OTVOREN` ostavi `None`)",
              "2. pokreni „Provjera stipendija”",
              "3. provjeri stranicu, pa javi kanalu, pretplatnicima i portalima"]
    open("strazar.md", "w", encoding="utf-8").write("\n".join(redci) + "\n")

    print(f"NAŠAO: {len(novo)} — zapisano u strazar.md")
    _izlaz("naslo", str(len(novo)))


if __name__ == "__main__":
    main()
