# -*- coding: utf-8 -*-
"""
Stranica "Rokovi natjecaja": otvoreni natjecaji poredani po datumu isteka
i grupirani po mjesecima. Nema vlastitih podataka — sve dolazi iz kartica.
Mjeseci (a ne "ovaj tjedan") da stranica ne zastari izmedu dva builda.
"""
import os
import re

MJESECI = ["", "Siječanj", "Veljača", "Ožujak", "Travanj", "Svibanj",
           "Lipanj", "Srpanj", "Kolovoz", "Rujan", "Listopad", "Studeni",
           "Prosinac"]


def stranica(mapa, otvorene, kartica, oblik, glava, navigacija, podnozje,
             broj_izvora, vrijeme, iso_rok, adrese=None, poziv_kanal=None):
    adrese = adrese or {}
    sa_rokom, bez_roka = [], []
    for r, p, z in otvorene:
        iso = iso_rok(r.get("status") or "") or r.get("rok_iso") or ""
        (sa_rokom if re.match(r"^\d{4}-\d{2}-\d{2}", iso or "") else
         bez_roka).append((iso[:10], r, p, z))
    sa_rokom.sort(key=lambda t: t[0])
    n = len(otvorene)
    grupe = {}
    for iso, r, p, z in sa_rokom:
        grupe.setdefault(iso[:7], []).append((r, p, z))
    html_grupe = ""
    for ym, lista in grupe.items():
        g, m = int(ym[:4]), int(ym[5:7])
        k = "".join(kartica(r, True, p, z, adrese.get(id(r)))
                    for r, p, z in lista)
        html_grupe += (f'<div class="sek-vrh" style="margin-top:1.6rem">'
                       f'<h2 style="margin:0">Rok u mjesecu: {MJESECI[m].lower()} {g}.</h2>'
                       f'<span class="broj">{len(lista)} '
                       f'{oblik(len(lista), "natječaj", "natječaja", "natječaja")}'
                       f'</span></div><div class="grupa">{k}</div>')
    if bez_roka:
        k = "".join(kartica(r, True, p, z, adrese.get(id(r)))
                    for _i, r, p, z in bez_roka)
        html_grupe += ('<div class="sek-vrh" style="margin-top:1.6rem">'
                       '<h2 style="margin:0">Rok nije naveden ili se računa od objave</h2>'
                       f'</div><div class="grupa">{k}</div>')
    naslov = "Rokovi stipendija 2026./2027. — što ističe prvo"
    opis = ("Otvoreni natječaji za stipendije poredani po roku prijave: "
            "pogledaj što ističe sljedeće i ne propusti prijavu.")
    poziv = poziv_kanal() if poziv_kanal else ""
    html = glava(naslov, opis, __import__("skupine").CSS)
    html += navigacija("natjecaji")
    html += f"""<main class="w"><section class="sk">
<h1>Rokovi stipendija: što ističe prvo</h1>
<p class="lead">Trenutno je otvoreno <b>{n}</b> {oblik(n, 'natječaj', 'natječaja', 'natječaja')}. Poredani su po datumu isteka roka, od najbližeg prema najdaljem.</p>
<p>Rok vrijedi do kraja navedenog dana, ako natječaj ne kaže drugačije (neki istječu u podne). Provjeri točan rok u službenom natječaju prije prijave.</p>
{poziv}
{html_grupe}
<a class="prijelaz" href="./">Svi otvoreni natječaji &rarr;</a>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme)
    with open(os.path.join(mapa, "stipendije-rokovi.html"), "w",
              encoding="utf-8") as f:
        f.write(html)
