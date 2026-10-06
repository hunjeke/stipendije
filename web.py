# -*- coding: utf-8 -*-
"""
Gradi javnu stranicu iz output.json:
  docs/index.html      natjecaji + filter
  docs/vodic.html      kako do stipendije
  docs/impressum.html  podaci o pruzatelju

Tehnicki statusi (GRESKA, PROVJERITI) se NE prikazuju javno.
"""
import json
import os
import re
from datetime import datetime

from zajednicko import CSS_KARTICE, glava, navigacija, podnozje, oblik, EMAIL, DOMENA, BAZA

ULAZ = "output.json"
IZVORI = "sources.json"
MAPA = "docs"
SVI = "Cijela Hrvatska"

# Kad je odabrana zupanija, sto s drzavnim izvorima u popisu pracenih?
#   True  = skupe se iza gumba (kraca stranica, manje suma)
#   False = svi ostaju vidljivi (duza stranica, vise sadrzaja odjednom)
# Otvoreni natjecaji su UVIJEK vidljivi, neovisno o ovoj postavci.
SKLOPI_DRZAVNE = True

# boja po vrsti izvora — i informacija i vizualni ritam
BOJE = {
    "Grad": "grad", "Općina": "grad", "Županija": "zup",
    "Sveučilište": "sve", "Zaklada": "zak", "Tvrtka": "tvr",
    "Ministarstvo": "drz", "Međunarodno": "med", "Agregator": "drz",
}


def esc(v):
    if v is None or str(v).strip() == "":
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def iso_rok(status):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", status or "")
    return m.group(1) if m else ""


def ucitaj_izvore():
    """URL -> (podrucje, zupanija, ocekivani mjesec, je li usko usmjeren)."""
    p, z, o, u = {}, {}, {}, {}
    if os.path.exists(IZVORI):
        for s in json.load(open(IZVORI, encoding="utf-8")):
            k = s["url"].rstrip("/")
            p[k] = s.get("podrucje") or SVI
            z[k] = s.get("zupanija") or ""
            o[k] = s.get("ocekivano") or ""
            u[k] = bool(s.get("usko"))
    return p, z, o, u


CSS_INDEX = CSS_KARTICE + """
/* --- hero --- */
.hero{padding:3.2rem 0 .4rem}
.hero .oznaka{display:inline-block;margin-bottom:1rem}

/* prazno stanje */
.prazno{margin-top:1.8rem;border:1.5px solid var(--tinta);background:var(--karta);
  padding:1.3rem 1.15rem}
.prazno .kad{font-family:"Bricolage",sans-serif;font-weight:700;
  font-size:1.35rem;letter-spacing:-.02em;margin:0 0 .35rem}
.prazno p{margin:.35rem 0;font-size:.92rem;color:var(--tinta-2)}

/* --- traka s brojkama --- */
.brojke{display:flex;flex-wrap:wrap;gap:.4rem 2.2rem;margin:1.1rem 0 0;
  padding:.85rem 0;border-top:1px solid var(--linija);
  border-bottom:1px solid var(--linija)}
.brojke span{display:flex;align-items:baseline;gap:.4rem}
.brojke b{font-family:"PlexMono",monospace;font-size:1.22rem;font-weight:500;
  color:var(--tinta);line-height:1.1}
.brojke i{font-style:normal;font-size:.8rem;color:var(--tinta-2)}
.brojke .hitno{color:var(--hitno)}

/* --- filter --- */
.filteri{margin:1.5rem 0 0;background:var(--karta);border:2px solid var(--plava);
  padding:1.15rem 1.2rem 1.25rem}
.red-f{display:flex;gap:.7rem;flex-wrap:wrap;align-items:center}
.red-f #zupanija{flex:1;min-width:13rem;margin:0}
/* tipke "za koga": pola otvorenih je samo za ucenike, pola samo za studente */
.za-koga{display:flex;flex-shrink:0}
.cip{font-family:"Plex",sans-serif;font-size:.9rem;font-weight:500;
  padding:.72rem .85rem;border:1.5px solid var(--tinta);border-left-width:0;
  background:var(--papir);color:var(--tinta-2);cursor:pointer}
.cip:first-child{border-left-width:1.5px}
.cip:hover{background:#fff;color:var(--tinta)}
.cip.odabran{background:var(--tinta);color:#fff;border-color:var(--tinta)}
.oznaka-f{display:block;font-family:"Bricolage",sans-serif;
  font-weight:700;font-size:1.06rem;letter-spacing:-.012em;
  color:var(--tinta);margin-bottom:.65rem}
#zupanija{width:100%;max-width:460px;background:var(--papir);
  border:1.5px solid var(--tinta);border-radius:0;padding:.78rem 2.6rem .78rem .9rem;
  font-family:"Plex",sans-serif;font-size:1rem;font-weight:500;
  color:var(--tinta);cursor:pointer;appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='8'%3E%3Cpath d='M1 1l5.5 5.5L12 1' stroke='%231D4ED8' stroke-width='2' fill='none'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 1rem center}
#zupanija:hover,#zupanija:focus{border-color:var(--plava);background-color:#fff}
.pojasnjenje{margin:.7rem 0 0;font-size:.85rem;color:var(--tinta-2);max-width:48ch}


/* --- zbijeni popis zatvorenih izvora --- */
.rd{display:flex;align-items:center;gap:.75rem;padding:.62rem .3rem;
  border-bottom:1px solid var(--linija);text-decoration:none;color:var(--tinta);
  font-size:.92rem}
.rd:first-of-type{border-top:1px solid var(--linija)}
.rd:hover{background:var(--karta)}
.rd-naziv{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.rd-pod{font-family:"PlexMono",monospace;font-size:.68rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--tinta-2);white-space:nowrap;flex-shrink:0}
.rd-str{color:var(--tinta-2);font-size:.85rem;flex-shrink:0}
.rd:hover .rd-str{color:var(--otvoreno)}
.tocka,i.tocka{width:8px;height:8px;flex-shrink:0;border-radius:50%;display:inline-block}
.tocka.grad{background:#15803D}
.tocka.zup{background:#1D4ED8}
.tocka.sve{background:#7A4E9E}
.tocka.zak{background:#B8860B}
.tocka.tvr{background:#B91C1C}
.tocka.drz{background:#141B2D}
.tocka.med{background:#0F8A8A}
.legenda{display:flex;flex-wrap:wrap;gap:.5rem 1.1rem;margin:.2rem 0 1.1rem;
  font-size:.74rem;color:var(--tinta-2)}
.legenda span{display:flex;align-items:center;gap:.35rem}
@media(max-width:600px){
  .rd{font-size:.88rem;gap:.55rem;padding:.6rem .2rem}
  .rd-pod{display:none}
}
.popis-zup{display:flex;flex-wrap:wrap;gap:.45rem}
.popis-zup a{font-size:.88rem;color:var(--tinta);text-decoration:none;
  border:1px solid var(--linija);background:var(--karta);padding:.42rem .75rem}
.popis-zup a:hover{border-color:var(--plava);color:var(--plava)}
/* kad je odabrana zupanija, lokalne stipendije idu prve */
.grupa{display:flex;flex-direction:column}
.grupa .k{order:0}
.grupa .k.drzavna{order:1}
.grupa .nema-rez{order:2}
.medja{order:1;display:none;margin:.5rem 0 .9rem;
  font-family:"PlexMono",monospace;font-size:.7rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--tinta-2);
  border-top:1px solid var(--linija);padding-top:.85rem}
.medja.vidljiva{display:block}
/* sklapanje drzavnih izvora kad je odabrana zupanija */
.k.drzavna.sklopljena{display:none}
.prekidac{order:1;display:none;background:var(--karta);
  border:1px dashed var(--linija);width:100%;padding:.75rem 1rem;
  font-family:"Plex",sans-serif;font-size:.88rem;color:var(--tinta-2);
  cursor:pointer;text-align:left;margin-bottom:.9rem}
.prekidac:hover{border-color:var(--plava);color:var(--tinta)}
.prekidac.vidljiv{display:block}
@media(max-width:600px){
  /* hero */
  .hero{padding:2rem 0 .4rem}

  .prazno{padding:1.05rem .95rem}
  .prazno .kad{font-size:1.2rem}

  /* traka s brojkama — jedan redak, da ne potisne prvu karticu ispod ruba */
  .brojke{gap:.3rem 1.1rem;padding:.6rem 0;margin:.9rem 0 0}
  .brojke span{flex-direction:column;gap:0}
  .brojke b{font-size:1.02rem}
  .brojke i{font-size:.72rem}

  /* filter */
  .filteri{margin:1rem 0 0;padding:.8rem .8rem .85rem}
  .oznaka-f{font-size:1rem}
  .red-f{gap:.5rem;flex-wrap:nowrap}
  .red-f #zupanija{min-width:0;flex:1 1 auto}
  #zupanija{max-width:100%;font-size:.95rem;padding:.62rem 2rem .62rem .7rem;
    background-position:right .7rem center}
  .cip{padding:.62rem .5rem;font-size:.84rem}
  .pojasnjenje{font-size:.76rem;margin-top:.5rem}
  .medja{font-size:.66rem;margin:.35rem 0 .8rem}

  /* sekcije */
  .sek{padding:2rem 0 0}
  h2{font-size:1.06rem}
  .sek-vrh{gap:.5rem}
  .sek-vrh .broj{font-size:.86rem}

}
@media(max-width:380px){
}
"""


_MJESECI = {"siječnja": 1, "sijecnja": 1, "veljače": 2, "veljace": 2,
            "ožujka": 3, "ozujka": 3, "travnja": 4, "svibnja": 5,
            "lipnja": 6, "srpnja": 7, "kolovoza": 8, "rujna": 9,
            "listopada": 10, "studenoga": 11, "studenog": 11, "prosinca": 12}

_MJ_UZORAK = "|".join(_MJESECI)
# "30. rujna 2026." — dan, mjesec rijecju, godina
_DATUM_G = re.compile(r"\b(\d{1,2})\.\s*(" + _MJ_UZORAK + r")\s*(\d{4})\.?",
                      re.IGNORECASE)
# "7. rujna" — dan i mjesec rijecju, bez godine (pocetak raspona)
_DATUM_BG = re.compile(r"\b(\d{1,2})\.\s*(" + _MJ_UZORAK + r")\b", re.IGNORECASE)
# "4.11.2026." — vec brojkama, ali bez vodece nule
_DATUM_N = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\.?")


def datumi_u_brojke(tekst):
    """'do 30. rujna 2026.' -> 'do 30.09.2026.'

    Datumi se provlace i kroz uvjete, upute i napomene, gdje ih model prepisuje
    onako kako pisu na izvoru. Ovdje se izjednacuju s rokom na kartici da na
    istoj kartici ne stoje dva zapisa istog datuma u dva oblika.

    Dira samo ono sto ima dan: "30. rujna 2026." i "7. rujna" u rasponu, te
    dodaje vodecu nulu vec brojcanim datumima. Recenice poput "objavljuje se
    izmedu rujna i prosinca" nemaju dan i ostaju netaknute, kao i skolska
    godina "2026./2027." koja nije datum."""
    if not tekst:
        return tekst
    t = str(tekst)
    t = _DATUM_G.sub(lambda m: "%02d.%02d.%s." % (int(m.group(1)),
                                                  _MJESECI[m.group(2).lower()],
                                                  m.group(3)), t)
    t = _DATUM_N.sub(lambda m: "%02d.%02d.%s." % (int(m.group(1)), int(m.group(2)),
                                                  m.group(3)), t)
    t = _DATUM_BG.sub(lambda m: "%02d.%02d." % (int(m.group(1)),
                                                _MJESECI[m.group(2).lower()]), t)
    return t


def rok_brojkama(r):
    """Rok uvijek u istom obliku: 30.09.2026.

    Izvori pisu rok kako im padne na pamet — "30. rujna 2026. godine do 12:00
    sati", "14. do 23. rujna 2026.", "6. listopada 2026. do 13:00". Na kartici
    to izgleda neuredno i tesko se usporeduje. Datum se zato ne prepisuje sa
    stranice nego se ispisuje iz onoga sto je program vec isparsirao, pa se
    prikazani datum nikad ne moze razici s odbrojavanjem dana.

    Sat se zadrzava kad ga izvor navodi — kod roka u 12:00 to je razlika izmedu
    predane i propustene prijave. Ako datum nije isparsiran, ostaje izvorni
    tekst: bolje nesto nego prazno polje."""
    iso = iso_rok(r.get("status") or "")
    izvorni = r.get("rok_tekst") or ""
    if not iso:
        return esc(izvorni)
    g, m, d = iso.split("-")
    out = f"{d}.{m}.{g}."
    sat = re.search(r"\b(\d{1,2}):(\d{2})\b", izvorni)
    if sat:
        out += f" do {int(sat.group(1)):02d}:{sat.group(2)}"
    return esc(out)


def eur(n):
    """1250.0 -> '1.250 €' ; 2250.5 -> '2.250,50 €' (hrvatski zapis)"""
    cijeli = int(n)
    ost = int(round((float(n) - cijeli) * 100))
    s = f"{cijeli:,}".replace(",", ".")
    return f"{s},{ost:02d} €" if ost else f"{s} €"


_RAZDOBLJE_RIJEC = {"mjesecno": "mjesečno", "godisnje": "godišnje",
                    "jednokratno": "jednokratno"}


def _dinamika(s):
    """'mjesečno · 10 mjeseci' — kako se i koliko dugo isplacuje."""
    d = _RAZDOBLJE_RIJEC.get(s.get("razdoblje") or "", "")
    if s.get("mjeseci"):
        mj = f"{s['mjeseci']} " + oblik(s["mjeseci"], "mjesec", "mjeseca", "mjeseci")
        d = f"{d} · {mj}" if d else mj
    return d


# Model vraca "za" bez kvacica jer su i primjeri u uputi napisani tako
# ("ucenici"). Popis je kratak namjerno: ovo nije pokusaj da se kvacice vrate
# bilo kojoj rijeci, nego da se isprave one koje se ovdje stvarno pojavljuju.
_KVACICE = {
    "ucenici": "učenici", "ucenika": "učenika", "ucenik": "učenik",
    "ucenicima": "učenicima", "ucenice": "učenice", "ucenicama": "učenicama",
    "srednjoskolci": "srednjoškolci", "srednjoskolac": "srednjoškolac",
    "srednjoskolaca": "srednjoškolaca", "srednjoskolce": "srednjoškolce",
    "osnovnoskolci": "osnovnoškolci", "osnovnoskolac": "osnovnoškolac",
    "djaci": "đaci", "djak": "đak", "djaka": "đaka",
    "sportasi": "sportaši", "sportas": "sportaš",
    "strucni": "stručni", "strucnih": "stručnih", "strucni studiji": "stručni studiji",
    "ucilista": "učilišta", "ucilistu": "učilištu", "ucilisti": "učilišti",
    "skole": "škole", "skola": "škola", "skoli": "školi", "skolske": "školske",
    "skolskih": "školskih", "srednjih": "srednjih",
    "nastavnicki": "nastavnički", "nastavnickih": "nastavničkih",
    "drustvene": "društvene", "drustvenih": "društvenih", "drustv": "društv",
    "prirodoslovni": "prirodoslovni", "visokoskolci": "visokoškolci",
}


def s_kvacicama(t):
    """Vrati kvacice rijecima koje ih je model ispustio ('ucenici' -> 'učenici').

    Dira samo rijeci s popisa i samo ako su cijele male — 'Ucenici' na pocetku
    recenice ostaje, a broj i interpunkcija se ne mijenjaju."""
    def zamijeni(m):
        return _KVACICE.get(m.group(0), m.group(0))
    return re.sub(r"[a-zćčžšđ]+", zamijeni, str(t))


def ocisti_oznaku(t):
    """Makni rep odrezane rijeci iz oznake koja je nastala prije popravka.

    Stariji zapisi u kesu imaju "za" odsjeceno na tocno 40 znakova, usred
    rijeci ("studenti poslijediplomskoga doktorskog s"). Dok se izvor ponovno
    ne procita, takav rep se ovdje odreze da se na kartici ne vidi.
    """
    t = str(t or "").strip()
    if len(t) < 38 or t.endswith((".", ")", "%")):
        return t
    zadnja = t.rsplit(" ", 1)[-1]
    # rijec od 1-2 slova na kraju duge oznake je gotovo sigurno odsjecena
    if len(zadnja) <= 2 and " " in t:
        return t.rsplit(" ", 1)[0].rstrip(" ,;-")
    return t


def spoji_raspone(stavke):
    """'od 1.025,50 do 1.470 € poslijedoktorandima' je JEDAN raspon, ne dvije
    stipendije. Model ga vraca kao dva unosa s istom oznakom, od kojih drugi
    ima do=True. Dva retka citaju se kao dva razlicita novca, pa se spajaju."""
    ishod, preskoci = [], set()
    for i, s in enumerate(stavke):
        if i in preskoci:
            continue
        par = None
        for j in range(i + 1, len(stavke)):
            d = stavke[j]
            if (j not in preskoci and d.get("za") == s.get("za")
                    and d.get("razdoblje") == s.get("razdoblje")
                    and bool(d.get("do")) != bool(s.get("do"))):
                par = (j, d)
                break
        if par and not s.get("do"):
            j, d = par
            if d["eur"] > s["eur"]:
                preskoci.add(j)
                s = dict(s, raspon_do=d["eur"], do=False)
        ishod.append(s)
    return ishod


def iznos_polja(r, otvorena=False, ima_vezu=False):
    """Iznos razlozen u retke tablice: [(oznaka, sadrzaj, monospace), ...].

    Skoro pola izvora ima vise razreda — ucenici jedno, studenti drugo, pa jos
    treci iznos za one izvan grada. Svaki razred ide u svoj redak, inace se ne
    daju usporedivati.

    Kad svi razredi dijele istu dinamiku isplate, ona se izdvaja u zaseban
    redak umjesto da se ponavlja uz svaki iznos. Time redak ostaje kratak, sto
    je jedino sto na mobitelu stane u sirinu kartice.

    Kad je broj ukupan proracun programa, a ne iznos po korisniku, mijenja se
    i oznaka: 144.000 € pod "Iznos" citalo bi se kao da toliko dobiva jedan
    ucenik."""
    stavke = r.get("iznosi") or []
    if not stavke:
        # scraper nije uspio rastaviti — ostaje doslovni tekst s izvora,
        # obicnim pismom jer je to recenica, a ne brojka
        t = datumi_u_brojke(r.get("iznos"))
        if t:
            return [("Iznos", esc(t), False)]
        if not otvorena:
            return []
        # Kod dijela zupanija iznos stoji samo u prilozenom pravilniku ili
        # odluci. Prazno polje izgleda kao propust stranice, pa se kaze da
        # podatka nema i uputi se onamo gdje jest.
        poruka = ("piše u tekstu natječaja" if ima_vezu
                  else "nije naveden na stranici izvora")
        return [("Iznos", f'<span class="nema">{poruka}</span>', False)]

    # Kad su svi razredi na istom novcu, razredi ne znace nista — Baska je
    # vratila tri stavke od 125 € samo zato sto nabraja tri vrste skola.
    # Tri jednaka retka ne govore vise od jednoga.
    bez_za = {(s["eur"], s.get("razdoblje"), s.get("mjeseci"), s.get("do"))
              for s in stavke}
    if len(bez_za) == 1:
        stavke = [dict(stavke[0], za=None)]
    stavke = spoji_raspone(stavke)

    oznaka = "Ukupni fond" if r.get("iznos_je_fond") else "Iznos"
    dinamike = {_dinamika(s) for s in stavke}
    zajednicka = dinamike.pop() if len(dinamike) == 1 else None

    polja = []
    for i, s in enumerate(stavke):
        dio = ("do " if s.get("do") else "") + eur(s["eur"])
        if s.get("raspon_do"):
            dio = eur(s["eur"]) + " – " + eur(s["raspon_do"])
        if zajednicka is None:
            d = _dinamika(s)
            if d:
                dio += " " + d
        if s.get("za") and len(stavke) > 1:
            dio = (f'<span class="za">{esc(s_kvacicama(ocisti_oznaku(s["za"])))}</span> '
                   + dio)
        polja.append((oznaka if i == 0 else "", dio, True))

    if zajednicka:
        # jedan iznos: dinamika stane uz njega; vise njih: ide u svoj redak
        if len(polja) == 1:
            polja[0] = (polja[0][0], polja[0][1] + " " + zajednicka, True)
        else:
            polja.append(("Isplata", zajednicka, False))
    return polja


def naslov_kartice(r):
    """Sto pise na vrhu kartice.

    Ime izvora ("MZO — svi natjecaji") ne govori ucieniku nista o tome sto
    dobiva. Kad scraper zna naslov samog natjecaja, ide on; ime izvora ostaje
    na poveznici pri dnu kartice."""
    return r.get("naslov_natjecaja") or r.get("naziv")


# Iznad ovoliko znakova recenica o uvjetima prelazi dva retka i kartica
# naraste; tada se skracuje i dobiva "vise".
GRANICA_SKRACIVANJA = 110

# Kome je natjecaj namijenjen. Sluzi filtru "ucenik / student": student ne
# treba prelaziti preko sest natjecaja za srednjoskolce da bi nasao svoja tri.
_ZA_UCENIKA = re.compile(r"ucenic|ucenik|srednjoskol|srednje skole|"
                         r"srednjih skola|osnovnoskol|maturant")
_ZA_STUDENTA = re.compile(r"student|studij|fakultet|visoko ucilis|visokih ucilis|"
                          r"preddiplom|diplomsk|poslijediplom|doktorand|akademsk")


def za_koga(r):
    """'ucenik' | 'student' | 'oba'.

    Kad nismo sigurni, vraca 'oba' — bolje pokazati natjecaj objema skupinama
    nego ga sakriti onome tko na njega ima pravo."""
    izvori = [r.get("naslov_natjecaja"), r.get("uvjeti"), r.get("naziv")]
    izvori += [str(i.get("za") or "") for i in (r.get("iznosi") or [])]
    t = _kljuc_naslova(" ".join(x for x in izvori if x))
    uc = bool(_ZA_UCENIKA.search(t))
    st = bool(_ZA_STUDENTA.search(t))
    if uc and not st:
        return "ucenik"
    if st and not uc:
        return "student"
    return "oba"


def kartica(r, otvorena, podrucje, zupanija, vlastita=None):
    naziv = esc(naslov_kartice(r))
    # ako je scraper nasao izravnu poveznicu na natjecaj, koristi nju
    izravna = r.get("poveznica_natjecaj")
    url = esc(izravna or r.get("url"))
    tekst_veze = ("Otvori natječaj" if izravna and otvorena
                  else "Službena stranica")
    polja_iznosa = iznos_polja(r, otvorena, bool(izravna))
    rok = rok_brojkama(r)
    uvjeti = esc(datumi_u_brojke(r.get("uvjeti")))
    iso = iso_rok(r.get("status") or "")

    polja = ""
    # monospace ide na brojke, da se iznosi medusobno poravnaju; doslovne
    # recenice s izvora ostaju u obicnom pismu jer se u mono citaju tesko
    for oznaka, sadrzaj, mono in polja_iznosa:
        polja += (f'<dt>{oznaka}</dt>'
                  f'<dd class="{"iznos" if mono else ""}">{sadrzaj}</dd>')
    if rok and otvorena:
        polja += f'<dt>Rok prijave</dt><dd>{rok}</dd>'
    if uvjeti:
        # kratka recenica stane u dva retka sama; duga se skrati i otvara klikom
        if len(uvjeti) > GRANICA_SKRACIVANJA:
            polja += ('<dt>Tko se prijavljuje</dt>'
                      f'<dd class="skrati"><span class="tekst">{uvjeti}</span>'
                      '<button type="button" class="vise" data-vise>više</button>'
                      '</dd>')
        else:
            polja += f'<dt>Tko se prijavljuje</dt><dd>{uvjeti}</dd>'
    polja = f'<dl class="polja">{polja}</dl>' if polja else ""

    upute = datumi_u_brojke(r.get("upute_za_prijavu")) or ""
    koraci = "".join(f"<li>{esc(k.strip())}</li>"
                     for k in upute.split("|") if k.strip())
    upute_html = (f'<details><summary>Kako se prijaviti</summary><ol>{koraci}</ol></details>'
                  if koraci and otvorena else "")

    if otvorena:
        znak = '<span class="status otv" data-znak>Otvoreno</span>'
        klasa = "k otv"
    else:
        znak = '<span class="status zat">Zatvoreno</span>'
        klasa = "k"

    # Poveznica na vlastitu stranicu natjecaja. Kartica ostaje kratka, a tko
    # hoce cijele uvjete i upute ide na stranicu koja se moze i indeksirati.
    detalji = (f'<a class="detalji" href="{esc(vlastita)}">Detalji natječaja</a>'
               if vlastita else "")

    # najveci mjesecni iznos na kartici — traka na vrhu iz njih racuna "do X €"
    mjesecni = [i.get("eur") for i in (r.get("iznosi") or [])
                if i.get("razdoblje") == "mjesecno" and i.get("eur")]
    naj = f' data-eur="{int(max(mjesecni))}"' if mjesecni else ""

    return (f'<article class="{klasa}" data-podrucje="{esc(podrucje)}" '
            f'data-zupanija="{esc(zupanija)}" data-rok="{iso}"'
            f' data-za="{za_koga(r)}"{naj}>'
            f'<div class="zag"><h3>{naziv}</h3>{znak}</div>'
            f'<div class="izvor">{esc(podrucje)}</div>'
            f'{polja}{upute_html}'
            f'<div class="dno">'
            f'<a class="veza" href="{url}" target="_blank" rel="noopener">'
            f'{tekst_veze} &rarr;</a>{detalji}</div></article>')


def _kljuc_naslova(s):
    """'Stipendije za deficitarna zanimanja!' -> 'stipendije za deficitarna zanimanja'"""
    z = {"č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d"}
    s = "".join(z.get(x, x) for x in str(s).lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def _popunjenost(r):
    """Koliko je zapis bogat — kod duplikata zadrzavamo potpuniji."""
    n = sum(1 for k in ("iznos", "rok_tekst", "uvjeti", "upute_za_prijavu",
                        "poveznica_natjecaj") if r.get(k))
    # Isti natjecaj s dva izvora zna doci jednom s razdobljem isplate, a jednom
    # bez njega. "620 €" i "620 € mjesecno" nisu isti podatak, pa zapis koji zna
    # razdoblje vrijedi vise — inace pobijedi onaj koji je slucajno prvi.
    if any(i.get("razdoblje") for i in (r.get("iznosi") or [])):
        n += 1
    return n


# rijeci koje nista ne razlikuju — gotovo svaki natjecaj ih ima u naslovu
_OPCE = {"stipendija", "stipendije", "stipendijama", "stipendiranje",
         "natjecaj", "natjecaja", "javni", "poziv", "potpora", "potpore",
         "ucenik", "ucenici", "ucenike", "ucenicima", "student", "studenti",
         "studente", "studentima", "skolska", "skolsku", "godina", "godinu",
         "akademska", "akademsku", "dodjela", "dodjelu"}
_VEZNE = {"za", "u", "i", "na", "od", "do", "s", "sa", "te", "iz", "po", "koji"}


def _rijeci(s):
    return {w for w in _kljuc_naslova(s).split()
            if w not in _VEZNE and len(w) > 2}


def _isti_natjecaj(a, b, prag=0.5):
    """Jesu li dva naslova isti natjecaj isprican drugim rijecima.

    Model istom natjecaju zna dati dva naslova — Chevening je dosao kao
    "studij u Britaniji" s jednog izvora i "studij u UK-u" s drugog. Doslovna
    usporedba to ne uhvati, pa se gleda koliko se rijeci preklapa.

    Uz preklapanje mora postojati barem jedna zajednicka rijec koja nesto
    znaci. Bez toga bi se dva razlicita natjecaja, oba nazvana tek
    "Stipendije za studente", stopila u jedan i jedan bi nestao sa stranice."""
    A, B = _rijeci(a), _rijeci(b)
    if not A or not B:
        return False
    zajednicke = A & B
    if not (zajednicke - _OPCE):
        return False
    return len(zajednicke) / len(A | B) >= prag


def spoji_duplikate(otvorene):
    """Isti natjecaj zna doci preko dva izvora (Chevening i s MZO-a i s
    AMPEU-a) pa se na stranici pojavi dvaput.

    Spaja se samo unutar istog podrucja — inace bi se "Stipendije za
    deficitarna zanimanja" iz dva razlicita grada krivo slile u jednu, a to su
    dvije stipendije i dva novca. Uz to mora vrijediti jedno od dvoga:
      - naslovi su isti, a rokovi si ne proturjece, ili
      - rok je isti, a naslovi govore o istome drugim rijecima.
    Isti naslov uz razlicit rok najcesce znaci dva kruga istog programa, a njih
    ne treba skrivati."""
    ishod = []
    for par in otvorene:
        r, p, _ = par
        naslov = r.get("naslov_natjecaja")
        if not naslov:                       # bez naslova nema pouzdane usporedbe
            ishod.append(par)
            continue
        rok = iso_rok(r.get("status") or "")
        for i, (r2, p2, _) in enumerate(ishod):
            n2 = r2.get("naslov_natjecaja")
            if not n2 or _kljuc_naslova(p) != _kljuc_naslova(p2):
                continue
            rok2 = iso_rok(r2.get("status") or "")
            isti_rok = bool(rok) and rok == rok2
            doslovno = (_kljuc_naslova(naslov) == _kljuc_naslova(n2)
                        and (isti_rok or not rok or not rok2))
            if doslovno or (isti_rok and _isti_natjecaj(naslov, n2)):
                if _popunjenost(r) > _popunjenost(r2):
                    ishod[i] = par           # zadrzi potpuniji zapis
                break
        else:
            ishod.append(par)
    return ishod


# hrvatski abecedni red: ... S, Š, T, U, V, Z, Ž
_ABC = "aábcčćdđefghijklmnoprsštuvzž"
_RANG = {z: i for i, z in enumerate(_ABC)}


def hr_kljuc(s):
    """Sortiranje po hrvatskoj abecedi umjesto po kodovima znakova."""
    out = []
    for z in s.lower():
        out.append(_RANG.get(z, 99 + ord(z) % 50))
    return out


def legenda_html():
    stavke = [("grad", "Grad ili općina"), ("zup", "Županija"),
              ("sve", "Sveučilište"), ("zak", "Zaklada"),
              ("tvr", "Tvrtka"), ("drz", "Država"), ("med", "Međunarodno")]
    return ('<div class="legenda">'
            + "".join(f'<span><i class="tocka {k}"></i>{t}</span>'
                      for k, t in stavke) + '</div>')


def redak(r, podrucje, zupanija):
    """Zatvoreni izvor: jedan zbijen redak umjesto pune kartice."""
    kat = r.get("kategorija") or ""
    boja = BOJE.get(kat, "drz")
    return (f'<a class="rd k" href="{esc(r.get("url"))}" target="_blank" '
            f'rel="noopener" data-podrucje="{esc(podrucje)}" '
            f'data-zupanija="{esc(zupanija)}">'
            f'<span class="tocka {boja}" title="{esc(kat)}"></span>'
            f'<span class="rd-naziv">{esc(r.get("naziv"))}</span>'
            f'<span class="rd-pod">{esc(podrucje)}</span>'
            f'<span class="rd-str">&rarr;</span></a>')


def izbornik(podrucja):
    """Padajuci izbornik zupanija. Podrucje koje ne pripada nijednoj zupaniji
    (Grad Zagreb) stoji samo, s jasnom oznakom da je grad."""
    # kratko, jer uz njega na mobitelu stoje i tipke "Učenik / Student"
    opcije = '<option value="">Cijela Hrvatska</option>'
    for p in sorted(podrucja, key=hr_kljuc):
        naziv = p if "županija" in p else f"Grad {p}"
        opcije += f'<option value="{esc(p)}">{esc(naziv)}</option>'
    return opcije


# --- rokovi se racunaju u pregledniku, a ne pri gradnji stranice ---
# Stranica se gradi dvaput tjedno, a rok moze isteci bilo kojeg dana. Zato
# svaki posjetitelj iznova racuna dane iz data-rok: istekli natjecaji nestaju
# iz "Otvoreno za prijave" i prije nego skripta idući put prođe kroz izvore.
# Ovaj blok ide na naslovnicu I na stranice zupanija.
JS_ROKOVI = """
(function(){
  // 1 dan / 2-4 dana / 5+ dana; pazi na 11-14 i na 21, 31...
  function oblik(n,jd,gjd,gmn){
    var z=Math.abs(n)%10, d=Math.abs(n)%100;
    if(d>=11&&d<=14) return gmn;
    if(z===1) return jd;
    if(z>=2&&z<=4) return gjd;
    return gmn;
  }

  // Cijeli dani do roka po lokalnom kalendaru:
  //   n > 0  jos ima dana,  n === 0  danas je zadnji dan,  n < 0  rok je prosao.
  // Usporeduju se ponoci, pa doba dana i ljetno/zimsko vrijeme ne pomicu racun.
  function dana(iso){
    if(!iso) return null;
    var d=/^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(iso);
    if(!d) return null;
    var rok=new Date(+d[1], +d[2]-1, +d[3]);
    var s=new Date(), danas=new Date(s.getFullYear(), s.getMonth(), s.getDate());
    return Math.round((rok-danas)/86400000);
  }

  var istekle=0, najblizi=null, najveci=0;
  document.querySelectorAll(".k.otv[data-rok]").forEach(function(k){
    var n=dana(k.getAttribute("data-rok"));
    if(n===null) return;
    if(n>=0){
      if(najblizi===null||n<najblizi) najblizi=n;
      var e=parseInt(k.getAttribute("data-eur")||"0",10);
      if(e>najveci) najveci=e;
    }
    if(n<0){                       // rok je prosao — van iz otvorenih
      k.classList.add("isteklo");
      k.style.display="none";
      istekle++;
      return;
    }
    var z=k.querySelector("[data-znak]");
    if(!z) return;
    // tri stupnja: crveno kad gori, zuto kad se blizi, zeleno dok ima vremena
    if(n===0){ z.className="status hitno"; z.textContent="Zadnji dan"; }
    else if(n<=3){ z.className="status hitno";
      z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
    else if(n<=14){ z.className="status uskoro";
      z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
    else if(n<=30){ z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
  });

  // Traka na vrhu: brojke se racunaju ovdje, a ne pri gradnji stranice.
  // Stranica se gradi dvaput tjedno, pa bi "jos 3 dana" drugi dan bilo netocno.
  // Brojke i traka na vrhu moraju pratiti ono sto je NA EKRANU, a ne sve sto
  // postoji. Kad se odabere "Ucenik" ili zupanija, dio kartica se sakrije, pa
  // bi stari broj tvrdio da je otvoreno deset natjecaja dok se vidi troje.
  // Zato racun stoji u funkciji koju filter poziva nakon svake promjene.
  function osvjeziBrojke(){
    var otvB=0, zatB=0, blizi=null, maks=0;
    document.querySelectorAll(".k:not(.isteklo):not(.skriveno)").forEach(function(k){
      if(k.classList.contains("otv")){
        otvB++;
        var n=dana(k.getAttribute("data-rok"));
        if(n!==null && n>=0 && (blizi===null || n<blizi)) blizi=n;
        var e=parseInt(k.getAttribute("data-eur")||"0",10);
        if(e>maks) maks=e;
      } else { zatB++; }
    });
    document.querySelectorAll("[data-broj-otv]").forEach(function(b){
      b.textContent = otvB+" "+oblik(otvB,"natječaj","natječaja","natječaja");
    });
    document.querySelectorAll("[data-broj-otv-n]").forEach(function(b){
      b.textContent = otvB;
    });
    document.querySelectorAll("[data-broj-zat]").forEach(function(b){
      b.textContent = zatB+" "+oblik(zatB,"izvor","izvora","izvora");
    });
    document.querySelectorAll("[data-broj-zat-n]").forEach(function(b){
      b.textContent = zatB;
    });
    var bNaj=document.querySelector("[data-najblizi]");
    if(bNaj){
      bNaj.textContent = blizi===null ? "\\u2014"
        : (blizi===0 ? "danas" : blizi+" "+oblik(blizi,"dan","dana","dana"));
      bNaj.className = (blizi!==null && blizi<=3) ? "hitno" : "";
    }
    var bEur=document.querySelector("[data-najveci]");
    if(bEur) bEur.textContent = maks>0 ? maks+" \\u20AC/mj." : "\\u2014";
  }
  window.__osvjeziBrojke = osvjeziBrojke;
  osvjeziBrojke();

  if(!istekle) return;

  var ziv=document.querySelectorAll(".k.otv:not(.isteklo)").length;
  if(ziv>0) return;

  var sek=document.getElementById("sek-otv");
  if(sek) sek.style.display="none";
  var prazno=document.getElementById("nema-otvorenih");
  if(prazno) prazno.style.display="";
  var sazetak=document.getElementById("sazetak-zup");
  if(sazetak && sazetak.getAttribute("data-nema"))
    sazetak.textContent=sazetak.getAttribute("data-nema");
})();

// "vise / manje" na skracenoj recenici o uvjetima. Gumb se pokazuje tek kad
// je JS ziv, jer bez njega nema sto otvoriti.
(function(){
  document.documentElement.className += " js";
  document.addEventListener("click", function(e){
    var b = e.target.closest ? e.target.closest("[data-vise]") : null;
    if(!b) return;
    var dd = b.parentNode;
    b.textContent = dd.classList.toggle("skrati") ? "više" : "manje";
  });
})();
"""


JS = """
(function(){
  var SVI="Cijela Hrvatska";

  // 1 dan / 2-4 dana / 5+ dana; pazi na 11-14 i na 21, 31...
  function oblik(n,jd,gjd,gmn){
    var z=Math.abs(n)%10, d=Math.abs(n)%100;
    if(d>=11&&d<=14) return gmn;
    if(z===1) return jd;
    if(z>=2&&z<=4) return gjd;
    return gmn;
  }

  var izbor=document.getElementById("zupanija");
  if(!izbor) return;
  var kartice=document.querySelectorAll(".k");
  var cipovi=document.querySelectorAll("[data-za-f]");
  var zaOdabir="";

  function osvjezi(){
    var z=izbor.value;
    kartice.forEach(function(k){
      var p=k.getAttribute("data-podrucje"),
          zk=k.getAttribute("data-zupanija")||"";
      // bez odabira sve; inace: drzavne uvijek + sve iz odabrane zupanije
      var ok = !z || p===SVI || zk===z || p===z;
      if(ok && zaOdabir){
        var dz=k.getAttribute("data-za")||"oba";
        ok = dz==="oba" || dz===zaOdabir;
      }
      k.classList.toggle("skriveno",!ok);
    });
    document.querySelectorAll(".grupa").forEach(function(g){
      var ima=g.querySelectorAll(".k:not(.skriveno):not(.isteklo)").length>0;
      var por=g.querySelector(".nema-rez");
      if(por)por.classList.toggle("vidljivo",!ima);
    });
    if(window.__osvjeziBrojke) window.__osvjeziBrojke();
    sklopiDrzavne(!!z);
  }

  // Kad je odabrana zupanija, ZATVORENE drzavne se skupe iza gumba.
  // Otvorene ostaju vidljive uvijek: ako se mozes prijaviti danas,
  // nebitno je je li stipendija lokalna ili drzavna.
  var prekidac=document.getElementById("prekidac");
  var razmotano=__RAZMOTANO__;

  function sklopiDrzavne(aktivno){
    if(!prekidac) return;
    var omot=prekidac.parentNode;
    var drz=omot.querySelectorAll(".k.drzavna:not(.skriveno):not(.isteklo)");
    if(!aktivno || drz.length===0){
      prekidac.classList.remove("vidljiv");
      omot.querySelectorAll(".k.drzavna").forEach(function(k){
        k.classList.remove("sklopljena");
      });
      razmotano=false;
      return;
    }
    prekidac.classList.add("vidljiv");
    drz.forEach(function(k){ k.classList.toggle("sklopljena", !razmotano); });
    prekidac.textContent = razmotano
      ? "Sakrij dr\u017eavne izvore"
      : "Prika\u017ei jo\u0161 " + drz.length + " " +
        oblik(drz.length,"dr\u017eavni izvor","dr\u017eavna izvora","dr\u017eavnih izvora") +
        " koji vrijede za sve";
  }

  if(prekidac){
    prekidac.addEventListener("click", function(){
      razmotano=!razmotano;
      sklopiDrzavne(true);
    });
  }
  izbor.addEventListener("change",osvjezi);
  cipovi.forEach(function(c){
    c.addEventListener("click",function(){
      zaOdabir=c.getAttribute("data-za-f")||"";
      cipovi.forEach(function(d){ d.classList.toggle("odabran", d===c); });
      osvjezi();
    });
  });
  osvjezi();
})();
"""



# --- WhatsApp kanal ---
# Klik iz WhatsApp grupe je jednokratan: tko danas ne nade nista za sebe, ne
# vraca se. Poziv stoji odmah ispod otvorenih natjecaja, jer je to trenutak
# kad covjek vidi da za njega jos nema nista — i kad mu obavijest najvise treba.
WA_KANAL = "https://whatsapp.com/channel/0029Vb8yRo75Ui2aMzBAjv1a"


def poziv_kanal():
    """Blok s pozivom na kanal. Nosi vlastiti stil jer ide i na stranice
    zupanija, koje imaju drugi CSS. Plava, a ne zelena: zelena na stranici
    znaci samo "natjecaj je otvoren"."""
    return f"""<style>
.kanal{{margin:1.6rem 0 .4rem;border:1.5px solid var(--tinta);background:var(--karta);
  padding:1.1rem 1.15rem;display:flex;align-items:center;gap:1rem;flex-wrap:wrap}}
.kanal-txt{{flex:1;min-width:15rem}}
.kanal-txt b{{display:block;font-family:"Bricolage",sans-serif;font-weight:700;
  font-size:1.08rem;letter-spacing:-.012em;color:var(--tinta);margin-bottom:.2rem}}
.kanal-txt span{{font-size:.88rem;color:var(--tinta-2)}}
.kanal-gumb{{display:inline-block;background:var(--plava);color:#fff;
  text-decoration:none;font-weight:600;font-size:.92rem;padding:.72rem 1.1rem;
  white-space:nowrap}}
.kanal-gumb:hover{{filter:brightness(1.12)}}
@media(max-width:600px){{.kanal-gumb{{width:100%;text-align:center}}}}
</style>
<aside class="kanal">
  <div class="kanal-txt">
    <b>Ne propusti novi natječaj</b>
    <span>Rokovi su često samo 15 dana. Javimo ti na WhatsAppu čim se neki otvori.</span>
  </div>
  <a class="kanal-gumb" href="{WA_KANAL}" target="_blank" rel="noopener">Prati na WhatsAppu &rarr;</a>
</aside>"""


def main():
    if not os.path.exists(ULAZ):
        print("GRESKA: nema %s" % ULAZ)
        return

    d = json.load(open(ULAZ, encoding="utf-8"))
    pod_map, zup_map, _, usko_map = ucitaj_izvore()

    otvorene, zatvorene = [], []
    for r in d:
        s = r.get("status") or ""
        k = (r.get("url") or "").rstrip("/")
        par = (r, pod_map.get(k, SVI), zup_map.get(k, ""))
        if s.startswith("OTVORENO"):
            otvorene.append(par)
        elif s.startswith("ROK ISTEKAO") or s.startswith("NEMA AKTIVNOG"):
            zatvorene.append(par)

    otvorene = spoji_duplikate(otvorene)

    # najhitniji prvi
    otvorene.sort(key=lambda t: (iso_rok(t[0].get("status") or "") or "9999",
                                 t[0].get("naziv") or ""))
    zatvorene.sort(key=lambda t: t[0].get("naziv") or "")

    # popis za izbornik: zupanije + podrucja koja ne pripadaju nijednoj (npr. Grad Zagreb)
    podrucja = set()
    for _, p, z in otvorene + zatvorene:
        if p == SVI:
            continue
        podrucja.add(z if z else p)

    vrijeme = datetime.now().strftime("%d.%m.%Y.")
    ukupno = len(otvorene) + len(zatvorene)   # koliko ih je na stranici
    # Koliko izvora uopce pratimo — taj broj ide u podnozje i u vodic. Nije isto
    # sto i broj prikazanih: izvor kojemu citanje ovaj put nije uspjelo i dalje
    # pratimo, samo o njemu nemamo sto reci. Odbiti ga od ukupnog broja znacilo
    # bi tvrditi da ga ne pratimo.
    izvora_ukupno = len(d)

    # --- stranica po natjecaju + arhiv ---
    # Svaki otvoren natjecaj dobiva vlastitu stranicu i ostaje zapisan kad mu
    # rok prode. Bez arhiva bi iznos i rok nestali cim se gradska stranica vrati
    # na obicnu, pa bi osam mjeseci u godini stranica imala sto reci samo o
    # onome sto je bas tad otvoreno.
    from natjecaji import (ucitaj_arhiv, spremi_arhiv, azuriraj,
                           slug_natjecaja, stranica as stranica_natjecaja)
    from stranice import slug as _slug_zup
    arhiv = ucitaj_arhiv()
    novih_natjecaja = azuriraj(arhiv, otvorene)
    spremi_arhiv(arhiv)

    # adresa vlastite stranice po kljucu zapisa iz output.json
    adrese = {}
    for r, p, z in otvorene:
        iso = iso_rok(r.get("status") or "")
        god = iso[:4] if iso else str(datetime.now().year)
        s = slug_natjecaja(r.get("naslov_natjecaja") or r.get("naziv") or "", p, god)
        adrese[id(r)] = f"natjecaj/{s}.html"

    # ---------- hero ----------
    # Uski natjecaji (npr. samo za jedan studij) ostaju u popisu, ali ne idu
    # na vrh stranice — ondje ide nesto sto se tice vise ljudi. Ako su otvoreni
    # SAMO uski, na vrhu stoji opca poruka, a oni se vide u popisu ispod.
    siroke = [t for t in otvorene
              if not usko_map.get((t[0].get("url") or "").rstrip("/"), False)]

    # Poruka "nema otvorenih" uvijek postoji u HTML-u, samo je skrivena dok ima
    # otvorenih. Ako posjetitelju u pregledniku istekne zadnji rok, JS je otkrije
    # — bez toga bi stranica ostala prazna i bez objasnjenja.
    # Bez isticanja pojedinacnog natjecaja na vrhu: sto Zagrepcaninu znaci
    # rok u Sibeniku? Ide ravno na filter i popis.
    skrij = ' style="display:none"' if siroke else ''
    hero = f"""<div class="prazno" id="nema-otvorenih"{skrij}>
  <p class="kad">Sezona kreće u rujnu.</p>
  <p>Većina gradova, županija i sveučilišta natječaje objavljuje između rujna
     i prosinca. Rokovi su kratki, često 15 dana od objave.</p>
  <p>Izvore provjeravamo automatski dvaput tjedno. Čim se neki natječaj otvori,
     pojavit će se ovdje.</p>
</div>"""

    # ---------- traka s brojkama ----------
    # Posjetitelj s WhatsAppa u prvom ekranu dosad nije vidio nijednu brojku,
    # nego tvrdnju i padajuci izbornik. Ovdje stoje tri podatka koja sam ne bi
    # izracunao. Sve tri vrijednosti preglednik iznova racuna iz kartica, jer
    # se stranica gradi dvaput tjedno, a "jos 3 dana" stari svakog dana.
    traka = ""
    if otvorene:
        traka = (f'<div class="brojke" id="brojke">'
                 f'<span><b data-broj-otv-n>{len(otvorene)}</b> '
                 f'<i>{oblik(len(otvorene), "otvoren natječaj", "otvorena natječaja", "otvorenih natječaja")}</i></span>'
                 f'<span><b data-najblizi>—</b> <i>najbliži rok</i></span>'
                 f'<span><b data-najveci>—</b> <i>najveći iznos</i></span>'
                 f'</div>')

    # ---------- sekcije ----------
    sek_otv = ""
    if otvorene:
        sek_otv = (f'<section class="sek" id="sek-otv">'
                   f'<div class="sek-vrh"><h2>Otvoreno za prijave</h2>'
                   f'<span class="broj" data-broj-otv>{len(otvorene)} '
                   f'{oblik(len(otvorene), "natječaj", "natječaja", "natječaja")}'
                   f'</span></div>'
                   f'<div class="grupa">'
                   + "".join(kartica(r, True, p, z, adrese.get(id(r)))
                               for r, p, z in otvorene)
                   + '<div class="medja">Otvoreno svima u Hrvatskoj</div>'
                   + '<p class="nema-rez">Za odabrano područje nema otvorenih natječaja. '
                     'Pogledaj popis izvora ispod.</p></div></section>')

    sek_zat = ""
    if zatvorene:
        # Naslov mora govoriti sto popis JEST. "Izvori koje pratimo" je tvrdio
        # da pratimo samo njih, pa je broj ispadao manji od stvarnog — a otvoreni
        # natjecaji gore i izvori bez uspjesnog citanja takoder se prate.
        sek_zat = (f'<section class="sek"><div class="sek-vrh">'
                   f'<h2>Trenutno bez otvorenog natječaja</h2>'
                   f'<span class="broj" data-broj-zat>{len(zatvorene)} '
                   f'{oblik(len(zatvorene), "izvor", "izvora", "izvora")}'
                   f'</span></div>'
                   f'<p class="uvod">Ove izvore provjeravamo automatski svaki '
                   f'ponedjeljak i četvrtak. Čim se natječaj otvori, pojavi se gore.</p>'
                   f'<div class="grupa zatvoreni-omot">'
                   + "".join(kartica(r, False, p, z) for r, p, z in zatvorene)
                   + '<button type="button" class="prekidac" id="prekidac"></button>' 
                   + '<div class="medja">Otvoreno svima u Hrvatskoj</div>'
                   + '<p class="nema-rez">Za odabrano područje nemamo izvora. '
                     'Ako znaš neki, javi nam.</p></div></section>')

    # veze na stranice po zupanijama (i za korisnike i za trazilice)
    from stranice import slug as _slug
    _zup = sorted({z if z else p for _, p, z in otvorene + zatvorene if p != SVI})
    sek_zup = ('<section class="sek"><div class="sek-vrh">'
               '<h2>Pregled po županijama</h2></div>'
               '<p class="uvod">Svaka županija ima svoju stranicu s popisom '
               'natječaja i rokovima.</p><div class="popis-zup">'
               + "".join(f'<a href="zupanija/{_slug(z)}.html">'
                         f'{z.replace(" županija","")}</a>' for z in _zup)
               + '</div></section>')

    js = JS_ROKOVI + JS.replace("__RAZMOTANO__",
                                "false" if SKLOPI_DRZAVNE else "true")

    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Stipendije.hr",
        "alternateName": "Stipendije u Hrvatskoj",
        "url": BAZA + "/",
        "inLanguage": "hr-HR",
        "description": ("Pregled otvorenih natječaja za stipendije u Hrvatskoj "
                        "— iznosi, rokovi prijave i upute."),
    }, ensure_ascii=False)

    html = glava(
        "Stipendije u Hrvatskoj — otvoreni natječaji, iznosi i rokovi",
        "Svi otvoreni natječaji za stipendije u Hrvatskoj na jednom mjestu. "
        "Iznosi, rokovi prijave i upute — automatski ažurirano dvaput tjedno.",
        CSS_INDEX,
        '<script type="application/ld+json">' + ld + '</script>')
    html += navigacija("natjecaji")
    html += f"""<main>
<section class="hero"><div class="w">
  <span class="meta oznaka">Ažurirano {vrijeme}</span>
  <h1>Sve stipendije u Hrvatskoj<br>na jednom mjestu.</h1>
  {traka}
  {hero}
  <div class="filteri">
    <div class="red-f">
      <select id="zupanija" aria-label="Županija">{izbornik(podrucja)}</select>
      <div class="za-koga" role="group" aria-label="Za koga">
        <button type="button" class="cip odabran" data-za-f="">Svi</button>
        <button type="button" class="cip" data-za-f="ucenik">Učenik</button>
        <button type="button" class="cip" data-za-f="student">Student</button>
      </div>
    </div>
    <p class="pojasnjenje">Uz odabranu županiju vide se i državne stipendije,
      na koje imaju pravo svi.</p>
  </div>
</div></section>
<div class="w">{sek_otv}{poziv_kanal()}{sek_zat}{sek_zup}</div>
</main>
<script>{js}</script>"""
    html += podnozje(izvora_ukupno, vrijeme)

    os.makedirs(MAPA, exist_ok=True)
    open(os.path.join(MAPA, "index.html"), "w", encoding="utf-8").write(html)

    from stranice import (vodic, impressum, privatnost,
                          stranica_zupanije, sitemap, slug)
    vodic(MAPA, izvora_ukupno, vrijeme)
    # stranica o drzavnoj stipendiji — najveci natjecaj u godini, mora stajati
    # spremna tjednima prije nego natjecaj izade (vidi drzavna.py)
    from drzavna import stranica as drzavna_stranica
    drzavna_stranica(MAPA, izvora_ukupno, vrijeme)
    impressum(MAPA, izvora_ukupno, vrijeme)
    privatnost(MAPA, izvora_ukupno, vrijeme)

    # --- zasebna stranica po zupaniji (za trazilice) ---
    putevi_natjecaja = []
    sve_zup = sorted({z if z else p for _, p, z in otvorene + zatvorene
                      if p != SVI})
    # stranice natjecaja u sitemap: otvoreni visoko, istekli nize ali ostaju
    for s, z in sorted(arhiv.items()):
        rel, otv = stranica_natjecaja(
            MAPA, z, eur, iznos_polja, datumi_u_brojke, esc,
            glava, navigacija, podnozje, izvora_ukupno, vrijeme,
            _slug_zup(z["zupanija"]) if z.get("zupanija") else "")
        putevi_natjecaja.append((rel, "0.8" if otv else "0.4"))
    print("  stranica po natjecaju: %d (novih %d)"
          % (len(arhiv), novih_natjecaja))

    # stranice po skupini: "ucenicke stipendije" i "studentske stipendije" su
    # medu najtrazenijim upitima, a naslovnica se za njih natjecala zajedno sa
    # svime ostalim
    from skupine import stranica as stranica_skupine
    for kljuc in ("ucenik", "student"):
        stranica_skupine(MAPA, kljuc, otvorene, zatvorene, za_koga, kartica,
                         oblik, glava, navigacija, podnozje, izvora_ukupno,
                         vrijeme, _slug_zup, adrese)

    putevi = [("", "1.0"), ("drzavna-stipendija.html", "0.9"),
              ("ucenicke-stipendije.html", "0.9"),
              ("studentske-stipendije.html", "0.9"), ("vodic.html", "0.7"),
              ("impressum.html", "0.3"), ("privatnost.html", "0.3")]

    for zup in sve_zup:
        otv_z = [(r, p, z) for r, p, z in otvorene
                 if z == zup or p == zup]
        zat_z = [(r, p, z) for r, p, z in zatvorene
                 if z == zup or p == zup]
        dio = ""
        if otv_z:
            dio += ('<div class="sek-vrh" id="sek-otv"><h2>Otvoreno za prijave</h2>'
                    f'<span class="broj" data-broj-otv-n>{len(otv_z)}</span></div>'
                    + "".join(kartica(r, True, p, z,
                                      ("../" + adrese[id(r)]) if id(r) in adrese else None)
                              for r, p, z in otv_z))
        if zat_z:
            dio += ('<div class="sek-vrh" style="margin-top:2.2rem">'
                    '<h2>Trenutno bez otvorenog natječaja</h2>'
                    f'<span class="broj" data-broj-zat-n>{len(zat_z)}</span></div>'
                    + "".join(kartica(r, False, p, z) for r, p, z in zat_z))
        # i zupanijska stranica sama izbacuje istekle rokove
        dio += poziv_kanal()
        dio += "<script>" + JS_ROKOVI + "</script>"
        popis = [(r.get("naziv") or "", r.get("url") or "")
                 for r, _, _ in otv_z + zat_z]
        put = stranica_zupanije(MAPA, zup, dio, len(otv_z),
                                len(otv_z) + len(zat_z), sve_zup,
                                izvora_ukupno, vrijeme, popis)
        putevi.append((put, "0.8"))

    sitemap(MAPA, putevi + putevi_natjecaja)
    print("  stranica po zupanijama: %d" % len(sve_zup))

    print("Napisano %s/index.html, vodic.html, impressum.html" % MAPA)
    print("  otvorenih: %d  zatvorenih: %d  sakriveno: %d"
          % (len(otvorene), len(zatvorene), len(d) - ukupno))
    print("  izbornik: %d zupanija" % len(podrucja))


if __name__ == "__main__":
    main()
