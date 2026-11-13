# -*- coding: utf-8 -*-
"""
Stranica "Potpore za studente i ucenike s invaliditetom".

Zasto postoji. Potpore za ovu skupinu raspisuju ministarstvo, gradovi i
sveucilista, svatko na svojoj stranici i s vlastitim rokom. Citateljica nam je
11.11.2026. javila da je ministarska potpora za prijevoz ostala neobjavljena u
kanalu, a nitko za nju nije cuo. Stranica skuplja ono sto vec pratimo.

Uvjeti i iznosi se ne prepisuju u ovaj tekst: dolaze iz kartica, a one iz
natjecaja. Ovdje stoji samo ono sto vrijedi za cijelu skupinu.

Pokus od 13.11.2026.: u Search Consoleu je za cijelu temu bilo oko 49 prikaza
u 90 dana. Usporediti nakon mjesec dana; ako nema upita, stranica ne treba
rasti.
"""
import os

from skupine import CSS as CSS_SK

DATOTEKA = "potpore-invaliditet.html"
NASLOV = "Potpore za studente i učenike s invaliditetom 2026./2027."
OPIS = ("Otvorene potpore i stipendije za studente i učenike s invaliditetom: "
        "prijevoz, gradske potpore i vodiči sveučilišta. Rokovi i uvjeti na "
        "jednom mjestu.")

# Vodici koje objavljuju sveucilista i fakulteti. Nisu natjecaji, ali ondje
# stoji sto fakultet nudi (prilagodbe, ured za studente s invaliditetom).
VODICI = [
    ("Sveučilište u Zagrebu — Edukacijsko-rehabilitacijski fakultet",
     "https://www.erf.unizg.hr/_download/repository/erfunizg_Potpora%20SSI_2025.pdf"),
    ("Sveučilište u Rijeci — brošura za studente s invaliditetom",
     "https://ssc.uniri.hr/wp-content/uploads/2023/09/BROSURA-ZA-SADASNJE-I-BUDUCE-STUDENTE-S-INVALIDITETOM.pdf"),
    ("Sveučilište u Splitu — vodič za studente s invaliditetom",
     "https://forenzika.unist.hr/wp-content/uploads/2026/05/Vodic-za-studente-s-invaliditetom.pdf"),
    ("Sveučilište Jurja Dobrile u Puli — brošura za studente s invaliditetom",
     "https://ffpu.unipu.hr/_news/97735/Brosura%20za%20studente%20s%20invaliditetom%20UNIPU.pdf"),
]

CSS = CSS_SK + """
.vodici{list-style:none;padding:0;margin:.7rem 0 0;max-width:46rem}
.vodici li{padding:.5rem 0;border-bottom:1px solid var(--linija);font-size:.94rem}
.vodici a{text-decoration:none}
"""


def _naslov(r):
    return " ".join(str(r.get(k) or "") for k in ("naslov_natjecaja", "naslov")
                    ).lower()


def _o_invaliditetu(r):
    """Samo natjecaji kojima je invaliditet u NASLOVU. Natjecaj koji ga
    spominje usput (Korcula, branitelji) nije ova stranica."""
    return "invalid" in _naslov(r)


def stranica(mapa, otvorene, zatvorene, kartica, oblik, glava, navigacija,
             podnozje, broj_izvora, vrijeme, adrese=None, poziv_kanal=None):
    adrese = adrese or {}
    moji_otv = [(r, p, z) for r, p, z in otvorene if _o_invaliditetu(r)]
    moji_zat = [(r, p, z) for r, p, z in zatvorene if _o_invaliditetu(r)]
    n = len(moji_otv)

    uvod = (f"Trenutno {oblik(n, 'je otvoren', 'su otvorena', 'je otvoreno')} "
            f"<b>{n}</b> {oblik(n, 'natječaj', 'natječaja', 'natječaja')} "
            f"namijenjenih osobama s invaliditetom."
            if n else
            "Trenutno nema otvorenih natječaja namijenjenih osobama s "
            "invaliditetom.")

    kartice_otv = "".join(
        kartica(r, True, p, z, adrese.get(id(r))) for r, p, z in moji_otv)
    kartice_zat = "".join(kartica(r, False, p, z) for r, p, z in moji_zat[:20])
    sek_otv = (f'<div class="sek-vrh" style="margin-top:1.6rem">'
               f'<h2 style="margin:0">Otvoreno za prijave</h2></div>'
               f'<div class="grupa">{kartice_otv}</div>') if moji_otv else ""
    sek_zat = (f'<h2>Prošli ciklusi</h2>'
               f'<p class="uz">Ovi natječaji trenutno nisu otvoreni. Slični se '
               f'obično raspisuju svake godine, pa ih pratimo.</p>'
               f'<div class="grupa">{kartice_zat}</div>') if moji_zat else ""
    vodici = "".join(f'<li><a href="{u}" target="_blank" rel="noopener">'
                     f'{t}</a></li>' for t, u in VODICI)
    poziv = poziv_kanal() if poziv_kanal else ""

    html = glava(NASLOV, OPIS, CSS)
    html += navigacija("natjecaji")
    html += f"""<main class="w"><section class="sk">
<h1>Potpore za studente i učenike s invaliditetom</h1>
<p class="lead">{uvod} Potpore raspisuju ministarstvo, gradovi i županije,
svatko na svojoj stranici i s vlastitim rokom, pa ih ovdje skupljamo na
jedno mjesto.</p>

{sek_otv}

<h2>Prije prijave</h2>
<p>Uvjeti se razlikuju od natječaja do natječaja: negdje se traži najmanje
60 % oštećenja organizma ili III. stupanj oštećenja funkcionalnih
sposobnosti, negdje upis u Registar osoba s invaliditetom, a negdje druga
dokumentacija. Točne uvjete uvijek provjeri u samom natječaju, na koji vodi
poveznica na svakoj kartici.</p>

<h2>Što nude fakulteti</h2>
<p>Uz natječaje, sveučilišta objavljuju vodiče o prilagodbama studija i
uredima za studente s invaliditetom. To nisu natječaji, ali ondje stoji što
tvoj fakultet nudi.</p>
<ul class="vodici">{vodici}</ul>
<p class="uz" style="margin-top:1rem">Na ovoj stranici nema prijave ni
obrasca i ne prikupljamo nikakve podatke o zdravlju.</p>

{poziv}
{sek_zat}
<a class="prijelaz" href="studentske-stipendije.html">Tražiš studentske stipendije? &rarr;</a>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme)
    with open(os.path.join(mapa, DATOTEKA), "w", encoding="utf-8") as f:
        f.write(html)
    return DATOTEKA
