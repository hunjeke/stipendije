# -*- coding: utf-8 -*-
"""
Tematske stranice: stipendije za deficitarna zanimanja te stipendije tvrtki
i zaklada.

Zasto postoje (Search Console, 28 dana do 14.11.2026.): upiti o deficitarnim
zanimanjima imali su oko 420 prikaza na 6. mjestu, a o stipendijama tvrtki
(Rockwool, HEP...) oko 1.700 prikaza na 4.-9. mjestu — a za njih nije
postojala nijedna stranica, pa je Google nudio naslovnicu. Ista je stvar
prije rijesena stranicama za ucenike i studente.

Tekst ne prepisuje iznose ni uvjete: oni dolaze iz kartica, a kartice iz
natjecaja. Usporediti ucinak u Search Consoleu sredinom prosinca 2026.
"""
import os

from skupine import CSS


def _tekst(r):
    return " ".join(str(r.get(k) or "") for k in
                    ("naslov_natjecaja", "uvjeti", "iznos", "napomena")).lower()


TEME = [
    {
        "datoteka": "stipendije-deficitarna-zanimanja.html",
        "h1": "Stipendije za deficitarna zanimanja",
        "naslov": "Stipendije za deficitarna zanimanja 2026./2027. — otvoreni natječaji",
        "opis": ("Stipendije za učenike i studente koji se školuju za "
                 "deficitarna zanimanja: otvoreni natječaji gradova i županija, "
                 "iznosi i rokovi prijave."),
        "koga": "za deficitarna zanimanja",
        "filtar": lambda r: "deficit" in _tekst(r),
        "uvod": ("Gradovi i županije sami određuju koja su zanimanja kod njih "
                 "deficitarna, pa se popis razlikuje od mjesta do mjesta: "
                 "negdje su to obrtnička zanimanja, negdje medicina, "
                 "građevinarstvo ili nastavnički studiji. Vrijedi popis iz "
                 "natječaja tvoga grada ili županije."),
    },
    {
        "datoteka": "stipendije-tvrtki-i-zaklada.html",
        "h1": "Stipendije tvrtki i zaklada",
        "naslov": "Stipendije tvrtki i zaklada 2026./2027. — HEP, INA, Rockwool i druge",
        "opis": ("Stipendije koje dodjeljuju tvrtke i zaklade u Hrvatskoj: "
                 "otvoreni natječaji, iznosi i rokovi, te popis davatelja koje "
                 "pratimo."),
        "koga": "tvrtki i zaklada",
        "filtar": lambda r: (r.get("kategorija") or "") in ("Tvrtka", "Zaklada"),
        "uvod": ("Ove stipendije ne ovise o prebivalištu nego o studiju ili "
                 "zanimanju koje davatelj traži, a neke uz stipendiju nose i "
                 "praksu ili obvezu rada. Svaka tvrtka i zaklada raspisuje "
                 "u svoje vrijeme, pa ih pratimo sve na jednom mjestu."),
    },
]


def stranice(mapa, otvorene, zatvorene, kartica, oblik, glava, navigacija,
             podnozje, broj_izvora, vrijeme, adrese=None, poziv_kanal=None):
    adrese = adrese or {}
    napisano = []
    for t in TEME:
        otv = [(r, p, z) for r, p, z in otvorene if t["filtar"](r)]
        zat = [(r, p, z) for r, p, z in zatvorene if t["filtar"](r)]
        n = len(otv)
        stanje = (f"Trenutno {oblik(n, 'je otvoren', 'su otvorena', 'je otvoreno')} "
                  f"<b>{n}</b> {oblik(n, 'natječaj', 'natječaja', 'natječaja')} "
                  f"{t['koga']}." if n else
                  f"Trenutno nema otvorenih natječaja {t['koga']}.")
        k_otv = "".join(kartica(r, True, p, z, adrese.get(id(r)))
                        for r, p, z in otv)
        k_zat = "".join(kartica(r, False, p, z) for r, p, z in zat[:40])
        sek_otv = (f'<div class="sek-vrh" style="margin-top:1.6rem">'
                   f'<h2 style="margin:0">Otvoreno za prijave</h2>'
                   f'<span class="broj">{n} '
                   f'{oblik(n, "natječaj", "natječaja", "natječaja")}</span></div>'
                   f'<div class="grupa">{k_otv}</div>') if otv else ""
        sek_zat = (f'<h2>Izvori koje pratimo</h2>'
                   f'<p class="uz">Ovi natječaji trenutno nisu otvoreni. '
                   f'Provjeravamo ih svaki ponedjeljak i četvrtak, pa se '
                   f'pojave ovdje čim budu raspisani.</p>'
                   f'<div class="grupa">{k_zat}</div>') if zat else ""
        poziv = poziv_kanal() if poziv_kanal else ""
        html = glava(t["naslov"], t["opis"], CSS)
        html += navigacija("natjecaji")
        html += f"""<main class="w"><section class="sk">
<h1>{t['h1']}</h1>
<p class="lead">{stanje}</p>
<p>{t['uvod']}</p>
{sek_otv}
{poziv}
{sek_zat}
<a class="prijelaz" href="./">Svi otvoreni natječaji &rarr;</a>
</section></main>"""
        html += podnozje(broj_izvora, vrijeme)
        with open(os.path.join(mapa, t["datoteka"]), "w", encoding="utf-8") as f:
            f.write(html)
        napisano.append(t["datoteka"])
    return napisano
