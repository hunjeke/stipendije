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
/* Brojke umjesto tvrdnji. Ova je stranica dosad gubila od naslovnice jer
   je bila filtrirana naslovnica uz nekoliko opcenitih recenica — 96 posto
   njezinih kartica stoji i ondje. Ovo je ono sto naslovnica ne moze reci,
   jer ona govori o svim stipendijama odjednom. */
.brojke-sk{display:grid;grid-template-columns:repeat(auto-fit,minmax(8.5rem,1fr));
  gap:.1rem;border:1px solid var(--linija);background:var(--linija);
  margin:1.4rem 0 .4rem}
.brojke-sk div{background:var(--papir);padding:.85rem .9rem}
.brojke-sk b{display:block;font-family:"PlexMono",monospace;font-size:1.26rem;
  font-weight:500;color:var(--tinta);line-height:1.2}
.brojke-sk span{display:block;font-size:.8rem;color:var(--tinta-2);
  margin-top:.2rem;line-height:1.35}
.tablica-sk{width:100%;border-collapse:collapse;margin:.7rem 0 0;
  font-size:.92rem;max-width:34rem}
.tablica-sk td{padding:.4rem .3rem;border-bottom:1px solid var(--linija)}
.tablica-sk td:last-child{text-align:right;font-family:"PlexMono",monospace;
  color:var(--tinta-2);white-space:nowrap}
.traka{display:inline-block;height:.5rem;background:var(--plava);
  opacity:.5;vertical-align:middle;margin-right:.45rem;min-width:2px}
.gdje-sk{display:flex;flex-wrap:wrap;gap:.4rem;margin:.7rem 0 0}
.gdje-sk a{border:1px solid var(--linija);background:var(--karta);
  padding:.3rem .65rem;font-size:.86rem;color:var(--tinta);
  text-decoration:none}
.gdje-sk a:hover{border-color:var(--plava);color:var(--plava)}
.gdje-sk a b{font-family:"PlexMono",monospace;font-weight:500;
  color:var(--tinta-2);margin-left:.3rem}
"""


def _raspon(otvorene, skupina, za_koga):
    """Od kojeg do kojeg iznosa idu mjesecne stipendije u ovoj skupini."""
    e = _mjesecni(otvorene, za_koga, skupina)
    if not e:
        return ""
    lo, hi = int(min(e)), int(max(e))
    return f"{lo} €" if lo == hi else f"{lo} do {hi} €"


# dva oblika: tablica trazi nominativ ("Listopad"), recenica lokativ
# ("najvise ih je u listopadu")
MJESEC = ("Siječanj", "Veljača", "Ožujak", "Travanj", "Svibanj", "Lipanj",
          "Srpanj", "Kolovoz", "Rujan", "Listopad", "Studeni", "Prosinac")
MJESEC_U = ("siječnju", "veljači", "ožujku", "travnju", "svibnju", "lipnju",
            "srpnju", "kolovozu", "rujnu", "listopadu", "studenom", "prosincu")


def _mjesecni(zapisi, za_koga, kljuc):
    """Svi mjesecni iznosi u skupini, bez tudih razreda.

    Nacionalni i slovacki program u istom natjecaju placaju i
    poslijedoktorande, do 1.470 € mjesecno. To nije studentska stipendija,
    a bez filtra je ulazilo u raspon pa je stranica tvrdila da studentske
    stipendije idu "do 1470 €". Ista greska vec je jednom stajala na
    naslovnici."""
    from web import za_ucenika_ili_studenta
    e = []
    for r, _, _ in zapisi:
        if za_koga(r) not in (kljuc, "oba"):
            continue
        for i in (r.get("iznosi") or []):
            if (i.get("razdoblje") == "mjesecno" and i.get("eur")
                    and za_ucenika_ili_studenta(i.get("za"))):
                e.append(float(i["eur"]))
    return sorted(e)


def _medijan(v):
    if not v:
        return 0
    s = len(v) // 2
    return v[s] if len(v) % 2 else (v[s - 1] + v[s]) / 2


def _tko_daje(zapisi):
    """{kategorija: koliko} — tko stvarno dodjeljuje, po brojkama.

    Dosad se brojalo po polju `_kategorija`, koje je prazno u svakom
    zapisu, pa je brojac uvijek bio nula i nitko to nije primijetio jer se
    rezultat nigdje nije ispisivao. Pravo polje je `kategorija`."""
    import collections
    c = collections.Counter()
    for r, _, _ in zapisi:
        k = (r.get("kategorija") or "").strip()
        if k and k != "Agregator":      # agregator nije davatelj
            c[k] += 1
    return c


def _rokovi_po_mjesecu(zapisi):
    """{mjesec: koliko} — kad rokovi stvarno istjecu.

    Racuna se iz svih zapisa, i otvorenih i isteklih, pa obuhvaca i
    prosle cikluse. Ovo je podatak koji naslovnica ne moze dati, a
    covjeku koji planira prijave govori kad da gleda."""
    import collections, re as _re
    c = collections.Counter()
    for r, _, _ in zapisi:
        m = _re.search(r"(\d{4})-(\d{2})-(\d{2})", r.get("status") or "")
        if m:
            c[int(m.group(2))] += 1
    return c


def _gdje_otvoreno(moji_otv, slug_zup):
    """[(zupanija, koliko, slug)] — gdje baš sada ima otvorenih."""
    import collections
    c = collections.Counter()
    for r, p, z in moji_otv:
        ime = z or p
        if ime and ime != "Cijela Hrvatska":
            c[ime] += 1
    out = []
    for ime, n in c.most_common():
        s = slug_zup(ime) if slug_zup else ""
        out.append((ime, n, s))
    return out


def stranica(mapa, kljuc, otvorene, zatvorene, za_koga, kartica, oblik,
             glava, navigacija, podnozje, broj_izvora, vrijeme, slug_zup,
             adrese=None, poziv_kanal=None):
    k = SKUPINE[kljuc]
    adrese = adrese or {}
    moji_otv = [(r, p, z) for r, p, z in otvorene
                if za_koga(r) in (kljuc, "oba")]
    moji_zat = [(r, p, z) for r, p, z in zatvorene
                if za_koga(r) in (kljuc, "oba")]

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

    # --- brojke koje naslovnica ne moze dati ---
    svi_moji = moji_otv + moji_zat
    iznosi = _mjesecni(moji_otv, za_koga, kljuc)
    med = _medijan(iznosi)
    naj = int(max(iznosi)) if iznosi else 0

    brojke = [(str(n), oblik(n, "otvoren natječaj", "otvorena natječaja",
                             "otvorenih natječaja"))]
    if iznosi:
        lo = int(min(iznosi))
        brojke.append((f"{lo}–{naj} €", "raspon mjesečnog iznosa"))
        brojke.append((f"{int(med)} €", "sredina raspona"))
    brojke.append((str(len(svi_moji)), "izvora koje pratimo za ovu skupinu"))
    blok_brojke = ('<div class="brojke-sk">'
                   + "".join(f"<div><b>{v}</b><span>{o}</span></div>"
                             for v, o in brojke) + "</div>")

    daje = _tko_daje(svi_moji)
    uk_daje = sum(daje.values()) or 1
    redci_daje = "".join(
        f'<tr><td><span class="traka" style="width:'
        f'{max(2, round(br / max(daje.values()) * 90))}px"></span>{ime}</td>'
        f'<td>{br}</td></tr>'
        for ime, br in daje.most_common())

    rokovi = _rokovi_po_mjesecu(svi_moji)
    naj_mj = max(rokovi.values()) if rokovi else 1
    redci_rok = "".join(
        f'<tr><td><span class="traka" style="width:'
        f'{max(2, round(rokovi[m] / naj_mj * 90))}px"></span>'
        f'{MJESEC[m - 1]}</td><td>{rokovi[m]}</td></tr>'
        for m in sorted(rokovi) if rokovi[m])
    vrh = [MJESEC_U[m - 1] for m, _ in rokovi.most_common(2)]
    vrh_mj = " i ".join(vrh) if vrh else ""

    gdje = _gdje_otvoreno(moji_otv, slug_zup)
    blok_gdje = "".join(
        (f'<a href="zupanija/{s}.html">{ime}<b>{br}</b></a>' if s
         else f'<a href="./">{ime}<b>{br}</b></a>')
        for ime, br, s in gdje[:14])

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

    # Ovo su stranice na koje Google salje ljude s pretrage. Bez poziva na
    # kanal posjetitelj procita i ode, a kanal je jedini nacin da mu se javimo
    # kad se otvori natjecaj koji danas jos ne postoji.
    vrh_rec = (f"Najviše ih je u {vrh_mj}." if vrh_mj else "")
    blok_gdje_sek = (
        f'<h2>Gdje su otvoreni sada</h2>'
        f'<p>Županije i gradovi u kojima je ovoga trenutka otvoren barem '
        f'jedan natječaj za ovu skupinu.</p>'
        f'<div class="gdje-sk">{blok_gdje}</div>') if blok_gdje else ""

    poziv = poziv_kanal() if poziv_kanal else ""
    drugi_kljuc, drugi_put, drugi_naziv = k["druga"]
    html = glava(k["naslov"], k["opis"], CSS)
    html += navigacija("natjecaji")
    html += f"""<main class="w"><section class="sk">
<h1>{k['h1']}</h1>
<p class="lead">{uvod}</p>
{blok_brojke}

<h2>Tko dodjeljuje stipendije {k['koga']}</h2>
<p>Ovo nije procjena nego prebrojeno stanje izvora koje pratimo za ovu
skupinu. Najviše ih je gradskih — svaki grad po svojim pravilima, s
vlastitim rokom i obrascem. Zato ih je teško pratiti: nema jednog mjesta
na kojem se objavljuju.</p>
<table class="tablica-sk">{redci_daje}</table>

<h2>Kad istječu rokovi</h2>
<p>Raspored rokova iz svih natječaja u arhivi, i otvorenih i isteklih.
{vrh_rec}</p>
<table class="tablica-sk">{redci_rok}</table>
<p class="uz">Rokovi su kratki — često petnaest dana od objave. Zato je
korisnije znati u kojem mjesecu gledati nego provjeravati svaki tjedan.</p>

{blok_gdje_sek}

{sek_otv}
{poziv}
{sek_zat}
<a class="prijelaz" href="{drugi_put}">Tražiš {drugi_naziv}? &rarr;</a>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme)
    with open(os.path.join(mapa, k["datoteka"]), "w", encoding="utf-8") as f:
        f.write(html)
    return k["datoteka"]
