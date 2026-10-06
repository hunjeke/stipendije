# -*- coding: utf-8 -*-
"""
Stranice po skupini: ucenicke i studentske stipendije.

Zasto postoje. "Ucenicke stipendije" i "studentske stipendije" su medu
najtrazenijim upitima, a za njih nismo imali nijednu stranicu — naslovnica se
natjecala za sve odjednom, pa ni za sto dobro. Filter ucenik/student postoji u
pregledniku, ali nema vlastitu adresu, pa ga trazilica ne vidi kao zasebnu
stranicu.

Stranice nisu prazna ljuska oko filtriranog popisa: nose i podatke koje
posjetitelj inace mora sam skupljati — koliko se krecu iznosi, tko ih dodjeljuje
i u kojem dijelu godine se objavljuju.
"""
import os
from datetime import date

from zajednicko import CSS_KARTICE

SKUPINE = {
    "ucenik": {
        "datoteka": "ucenicke-stipendije.html",
        "h1": "Učeničke stipendije",
        "naslov": "Učeničke stipendije 2026./2027. — otvoreni natječaji i iznosi",
        "opis": ("Stipendije za učenike srednjih škola u Hrvatskoj: otvoreni "
                 "natječaji, iznosi, rokovi prijave i upute. Automatski "
                 "ažurirano dvaput tjedno."),
        "koga": "učenicima srednjih škola",
        "druga": ("student", "studentske-stipendije.html", "studentske stipendije"),
    },
    "student": {
        "datoteka": "studentske-stipendije.html",
        "h1": "Studentske stipendije",
        "naslov": "Studentske stipendije 2026./2027. — otvoreni natječaji i iznosi",
        "opis": ("Stipendije za studente u Hrvatskoj: otvoreni natječaji, "
                 "iznosi, rokovi prijave i upute za prijavu. Automatski "
                 "ažurirano dvaput tjedno."),
        "koga": "studentima",
        "druga": ("ucenik", "ucenicke-stipendije.html", "učeničke stipendije"),
    },
}

# Kartice nose vlastiti stil iz zajednickog modula — bez njega se na ovoj
# stranici iscrtaju kao goli popis, kao sto se dogodilo zupanijskim stranicama.
CSS = CSS_KARTICE + """
.sk{padding:2.4rem 0 0}
.sk h1{font-size:clamp(1.6rem,4.6vw,2.2rem);margin-bottom:.5rem}
.sk .lead{font-size:1.02rem;color:var(--tinta-2);max-width:56ch;margin:0 0 1.5rem}
.sk h2{font-size:1.14rem;margin:2.4rem 0 .4rem}
.sk p{font-size:.96rem;line-height:1.65;max-width:60ch}
.sk .uz{color:var(--tinta-2);font-size:.92rem;margin:0 0 1rem;max-width:58ch}
.tko-daje{display:flex;flex-wrap:wrap;gap:.45rem;margin:.6rem 0 0}
.tko-daje span{border:1px solid var(--linija);background:var(--karta);
  padding:.35rem .7rem;font-size:.85rem;color:var(--tinta-2)}
.tko-daje b{color:var(--tinta);font-weight:500}
.prijelaz{display:block;margin-top:2.2rem;padding-top:1.2rem;
  border-top:1px solid var(--linija);font-size:.94rem}
"""


def _raspon(otvorene, skupina, za_koga):
    """Od kojeg do kojeg iznosa idu mjesecne stipendije u ovoj skupini."""
    e = []
    for r, _, _ in otvorene:
        if za_koga(r) not in (skupina, "oba"):
            continue
        for i in (r.get("iznosi") or []):
            if i.get("razdoblje") == "mjesecno" and i.get("eur"):
                e.append(i["eur"])
    if not e:
        return ""
    lo, hi = int(min(e)), int(max(e))
    return f"{lo} €" if lo == hi else f"{lo} do {hi} €"


def stranica(mapa, kljuc, otvorene, zatvorene, za_koga, kartica, oblik,
             glava, navigacija, podnozje, broj_izvora, vrijeme, slug_zup,
             adrese=None):
    k = SKUPINE[kljuc]
    adrese = adrese or {}
    moji_otv = [(r, p, z) for r, p, z in otvorene
                if za_koga(r) in (kljuc, "oba")]
    moji_zat = [(r, p, z) for r, p, z in zatvorene
                if za_koga(r) in (kljuc, "oba")]

    # tko ih uopce dodjeljuje — brojevi, ne tvrdnje
    import collections
    vrste = collections.Counter()
    for r, p, z in moji_otv + moji_zat:
        vrste[r.get("_kategorija") or ""] += 1

    raspon = _raspon(otvorene, kljuc, za_koga)
    n = len(moji_otv)
    uvod = (f"Trenutno {oblik(n, 'je otvoren', 'su otvorena', 'je otvoreno')} "
            f"<b>{n}</b> {oblik(n, 'natječaj', 'natječaja', 'natječaja')} "
            f"za stipendije namijenjene {k['koga']}."
            if n else
            f"Trenutno nema otvorenih natječaja za stipendije namijenjenih "
            f"{k['koga']}.")
    if raspon:
        uvod += f" Mjesečni iznosi kreću se od {raspon}."

    kartice_otv = "".join(
        kartica(r, True, p, z, adrese.get(id(r))) for r, p, z in moji_otv)
    kartice_zat = "".join(kartica(r, False, p, z) for r, p, z in moji_zat[:40])

    sek_otv = ""
    if moji_otv:
        sek_otv = (f'<div class="sek-vrh" style="margin-top:1.6rem">'
                   f'<h2 style="margin:0">Otvoreno za prijave</h2>'
                   f'<span class="broj">{n} '
                   f'{oblik(n, "natječaj", "natječaja", "natječaja")}</span></div>'
                   f'<div class="grupa">{kartice_otv}</div>')

    sek_zat = ""
    if moji_zat:
        sek_zat = (f'<h2>Izvori koje pratimo</h2>'
                   f'<p class="uz">Ovi natječaji trenutno nisu otvoreni. '
                   f'Provjeravamo ih automatski svaki ponedjeljak i četvrtak, '
                   f'pa se pojave ovdje čim budu raspisani.</p>'
                   f'<div class="grupa">{kartice_zat}</div>')

    drugi_kljuc, drugi_put, drugi_naziv = k["druga"]
    html = glava(k["naslov"], k["opis"], CSS)
    html += navigacija("natjecaji")
    html += f"""<main class="w"><section class="sk">
<h1>{k['h1']}</h1>
<p class="lead">{uvod}</p>

<h2>Tko dodjeljuje stipendije {k['koga']}</h2>
<p>Najviše ih daju gradovi i općine — svaki po svojim pravilima, s vlastitim
rokom i obrascem. Uz njih stipendiraju i županije, ministarstva, zaklade,
sveučilišta i pojedine tvrtke. Zato ih je teško pratiti: nema jednog mjesta
na kojem se objavljuju, nego {broj_izvora} različitih stranica.</p>
<p>Ovu stranicu gradi program koji te izvore obilazi dvaput tjedno i s njih
čita iznos, rok i upute za prijavu. Ništa se ne upisuje ručno.</p>

<h2>Kad se objavljuju</h2>
<p>Većina natječaja izlazi između rujna i prosinca, a rokovi su kratki —
često samo 15 dana od objave. Dio gradova objavljuje i u studenom ili
siječnju, pa se isplati pogledati i izvan glavne sezone.</p>
{sek_otv}
{sek_zat}
<a class="prijelaz" href="{drugi_put}">Tražiš {drugi_naziv}? &rarr;</a>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme)
    with open(os.path.join(mapa, k["datoteka"]), "w", encoding="utf-8") as f:
        f.write(html)
    return k["datoteka"]
