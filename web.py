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

from zajednicko import glava, navigacija, podnozje, oblik, EMAIL, DOMENA, BAZA

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


CSS_INDEX = """
/* --- hero --- */
.hero{padding:3.2rem 0 .4rem}
.hero .oznaka{display:inline-block;margin-bottom:1rem}

/* prazno stanje */
.prazno{margin-top:1.8rem;border:1.5px solid var(--tinta);background:var(--karta);
  padding:1.3rem 1.15rem}
.prazno .kad{font-family:"Bricolage",sans-serif;font-weight:700;
  font-size:1.35rem;letter-spacing:-.02em;margin:0 0 .35rem}
.prazno p{margin:.35rem 0;font-size:.92rem;color:var(--tinta-2)}

/* --- filter --- */
.filteri{margin:2.2rem 0 0;background:var(--karta);border:2px solid var(--plava);
  padding:1.15rem 1.2rem 1.25rem}
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

/* --- kartice --- */
.k{background:var(--karta);border:1px solid var(--linija);
  padding:1.05rem 1.15rem;margin-bottom:.75rem}
.k.otv{border-left:3px solid var(--otvoreno)}
.k.skriveno{display:none}
.k .zag{display:flex;justify-content:flex-start;gap:.7rem;
  align-items:baseline;flex-wrap:wrap}
.status{font-family:"PlexMono",monospace;font-size:.66rem;letter-spacing:.09em;
  text-transform:uppercase;padding:.2rem .5rem;white-space:nowrap;
  flex-shrink:0;align-self:flex-start;max-width:100%}
.status.otv{background:#DCFCE7;color:var(--otvoreno)}
.status.zat{background:var(--papir);color:var(--tinta-2)}
.status.hitno{background:#FEE2E2;color:var(--hitno)}
.k .izvor{font-family:"PlexMono",monospace;font-size:.68rem;
  letter-spacing:.06em;text-transform:uppercase;color:var(--tinta-2);
  margin-bottom:.55rem}
.polja{display:grid;grid-template-columns:8.5rem 1fr;gap:.28rem .9rem;
  font-size:.9rem;margin:.5rem 0 0}
.polja dt{color:var(--tinta-2)}
.polja dd{margin:0}
.polja dd.iznos{font-family:"PlexMono",monospace;font-weight:500}
/* podatak kojeg na izvoru nema — vidljiv, ali tisi od stvarnog iznosa */
.polja .nema{color:var(--tinta-2);font-style:italic}
/* kome pripada koji iznos kad ih natjecaj ima vise (ucenici / studenti) */
.polja .za{color:var(--tinta-2);font-family:"Plex",sans-serif;font-weight:400}
.polja .za::after{content:" —";}
.k details{margin-top:.75rem;font-size:.88rem}
.k summary{cursor:pointer;color:var(--plava);font-weight:500}
.k details ol{margin:.55rem 0 0;padding-left:1.25rem;color:var(--tinta-2)}
.k details li{margin-bottom:.3rem}
.veza{display:inline-block;margin-top:.8rem;font-size:.88rem;font-weight:500;
  color:var(--tinta);text-decoration:none;border-bottom:1.5px solid var(--plava);
  padding-bottom:1px}
.veza:hover{color:var(--plava)}
.nema-rez{display:none;border:1px dashed var(--linija);padding:1.05rem 1.15rem;
  color:var(--tinta-2);font-size:.9rem;margin:0}
.nema-rez.vidljivo{display:block}
.zatvoreni-omot{margin-top:.4rem}

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

  /* filter */
  .filteri{margin:1.7rem 0 0;padding:1rem .9rem 1.05rem}
  .oznaka-f{font-size:1rem}
  #zupanija{max-width:100%;font-size:1rem;padding:.8rem 2.4rem .8rem .8rem}
  .pojasnjenje{font-size:.8rem}
  .medja{font-size:.66rem;margin:.35rem 0 .8rem}

  /* sekcije */
  .sek{padding:2rem 0 0}
  h2{font-size:1.06rem}
  .sek-vrh{gap:.5rem}
  .sek-vrh .broj{font-size:.86rem}

  /* kartice */
  .k{padding:.95rem .9rem}
  /* oznaka uvijek iznad naslova, da ne skace i ne izlazi van */
  .k .zag{flex-direction:column-reverse;align-items:flex-start;gap:.45rem}
  .k .zag h3{min-width:0;width:100%}
  h3{font-size:.97rem}
  .status{font-size:.62rem;padding:.18rem .45rem}
  .polja{grid-template-columns:1fr;gap:.05rem}
  .polja dt{font-size:.76rem;margin-top:.45rem;color:#8A909E}
  /* na uskom zaslonu nema stupca za poravnanje, pa prazna oznaka samo smeta */
  .polja dt:empty{display:none}
  .polja dd{font-size:.92rem}
  /* veca povrsina za prst */
  .k summary{padding:.35rem 0}
  .veza{padding:.4rem 0 .3rem}
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

    oznaka = "Ukupni fond" if r.get("iznos_je_fond") else "Iznos"
    dinamike = {_dinamika(s) for s in stavke}
    zajednicka = dinamike.pop() if len(dinamike) == 1 else None

    polja = []
    for i, s in enumerate(stavke):
        dio = ("do " if s.get("do") else "") + eur(s["eur"])
        if zajednicka is None:
            d = _dinamika(s)
            if d:
                dio += " " + d
        if s.get("za") and len(stavke) > 1:
            dio = f'<span class="za">{esc(s["za"])}</span> ' + dio
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


def kartica(r, otvorena, podrucje, zupanija):
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

    return (f'<article class="{klasa}" data-podrucje="{esc(podrucje)}" '
            f'data-zupanija="{esc(zupanija)}" data-rok="{iso}">'
            f'<div class="zag"><h3>{naziv}</h3>{znak}</div>'
            f'<div class="izvor">{esc(podrucje)}</div>'
            f'{polja}{upute_html}'
            f'<a class="veza" href="{url}" target="_blank" rel="noopener">'
            f'{tekst_veze} &rarr;</a></article>')


def _kljuc_naslova(s):
    """'Stipendije za deficitarna zanimanja!' -> 'stipendije za deficitarna zanimanja'"""
    z = {"č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d"}
    s = "".join(z.get(x, x) for x in str(s).lower())
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s)).strip()


def _popunjenost(r):
    """Koliko je zapis bogat — kod duplikata zadrzavamo potpuniji."""
    return sum(1 for k in ("iznos", "rok_tekst", "uvjeti", "upute_za_prijavu",
                           "poveznica_natjecaj") if r.get(k))


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
    opcije = '<option value="">Sve stipendije u Hrvatskoj</option>'
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

  var istekle=0;
  document.querySelectorAll(".k.otv[data-rok]").forEach(function(k){
    var n=dana(k.getAttribute("data-rok"));
    if(n===null) return;
    if(n<0){                       // rok je prosao — van iz otvorenih
      k.classList.add("isteklo");
      k.style.display="none";
      istekle++;
      return;
    }
    var z=k.querySelector("[data-znak]");
    if(!z) return;
    if(n===0){ z.className="status hitno"; z.textContent="Zadnji dan"; }
    else if(n<=7){ z.className="status hitno";
      z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
    else if(n<=21){ z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
  });

  if(!istekle) return;

  // brojke i naslovi moraju pratiti ono sto se stvarno vidi
  var ziv=document.querySelectorAll(".k.otv:not(.isteklo)").length;
  document.querySelectorAll("[data-broj-otv]").forEach(function(b){
    b.textContent = ziv+" "+oblik(ziv,"natječaj","natječaja","natječaja");
  });
  document.querySelectorAll("[data-broj-otv-n]").forEach(function(b){
    b.textContent = ziv;
  });
  if(ziv>0) return;

  var sek=document.getElementById("sek-otv");
  if(sek) sek.style.display="none";
  var prazno=document.getElementById("nema-otvorenih");
  if(prazno) prazno.style.display="";
  var sazetak=document.getElementById("sazetak-zup");
  if(sazetak && sazetak.getAttribute("data-nema"))
    sazetak.textContent=sazetak.getAttribute("data-nema");
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

  function osvjezi(){
    var z=izbor.value;
    kartice.forEach(function(k){
      var p=k.getAttribute("data-podrucje"),
          zk=k.getAttribute("data-zupanija")||"";
      // bez odabira sve; inace: drzavne uvijek + sve iz odabrane zupanije
      var ok = !z || p===SVI || zk===z || p===z;
      k.classList.toggle("skriveno",!ok);
    });
    document.querySelectorAll(".grupa").forEach(function(g){
      var ima=g.querySelectorAll(".k:not(.skriveno):not(.isteklo)").length>0;
      var por=g.querySelector(".nema-rez");
      if(por)por.classList.toggle("vidljivo",!ima);
    });
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
  osvjezi();
})();
"""


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
    ukupno = len(otvorene) + len(zatvorene)

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

    # ---------- sekcije ----------
    sek_otv = ""
    if otvorene:
        sek_otv = (f'<section class="sek" id="sek-otv">'
                   f'<div class="sek-vrh"><h2>Otvoreno za prijave</h2>'
                   f'<span class="broj" data-broj-otv>{len(otvorene)} '
                   f'{oblik(len(otvorene), "natječaj", "natječaja", "natječaja")}'
                   f'</span></div>'
                   f'<div class="grupa">'
                   + "".join(kartica(r, True, p, z) for r, p, z in otvorene)
                   + '<div class="medja">Otvoreno svima u Hrvatskoj</div>'
                   + '<p class="nema-rez">Za odabrano područje nema otvorenih natječaja. '
                     'Pogledaj popis izvora ispod.</p></div></section>')

    sek_zat = ""
    if zatvorene:
        sek_zat = (f'<section class="sek"><div class="sek-vrh"><h2>Izvori koje pratimo</h2>'
                   f'<span class="broj">{len(zatvorene)} '
                   f'{oblik(len(zatvorene), "izvor", "izvora", "izvora")}'
                   f'</span></div>'
                   f'<p class="uvod">Ovdje natječaj trenutno nije otvoren. '
                   f'Provjeravamo ih automatski svaki ponedjeljak i četvrtak.</p>'
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
  {hero}
  <div class="filteri">
    <label class="oznaka-f" for="zupanija">Odaberi županiju</label>
    <select id="zupanija">{izbornik(podrucja)}</select>
    <p class="pojasnjenje">Prikazuju se stipendije te županije, svih njezinih
      gradova i one državne, na koje imaju pravo svi.</p>
  </div>
</div></section>
<div class="w">{sek_otv}{sek_zat}{sek_zup}</div>
</main>
<script>{js}</script>"""
    html += podnozje(ukupno, vrijeme)

    os.makedirs(MAPA, exist_ok=True)
    open(os.path.join(MAPA, "index.html"), "w", encoding="utf-8").write(html)

    from stranice import (vodic, impressum, privatnost,
                          stranica_zupanije, sitemap, slug)
    vodic(MAPA, ukupno, vrijeme)
    impressum(MAPA, ukupno, vrijeme)
    privatnost(MAPA, ukupno, vrijeme)

    # --- zasebna stranica po zupaniji (za trazilice) ---
    sve_zup = sorted({z if z else p for _, p, z in otvorene + zatvorene
                      if p != SVI})
    putevi = [("", "1.0"), ("vodic.html", "0.7"),
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
                    + "".join(kartica(r, True, p, z) for r, p, z in otv_z))
        if zat_z:
            dio += ('<div class="sek-vrh" style="margin-top:2.2rem">'
                    '<h2>Izvori koje pratimo</h2>'
                    f'<span class="broj">{len(zat_z)}</span></div>'
                    + "".join(kartica(r, False, p, z) for r, p, z in zat_z))
        # i zupanijska stranica sama izbacuje istekle rokove
        dio += "<script>" + JS_ROKOVI + "</script>"
        popis = [(r.get("naziv") or "", r.get("url") or "")
                 for r, _, _ in otv_z + zat_z]
        put = stranica_zupanije(MAPA, zup, dio, len(otv_z),
                                len(otv_z) + len(zat_z), sve_zup,
                                ukupno, vrijeme, popis)
        putevi.append((put, "0.8"))

    sitemap(MAPA, putevi)
    print("  stranica po zupanijama: %d" % len(sve_zup))

    print("Napisano %s/index.html, vodic.html, impressum.html" % MAPA)
    print("  otvorenih: %d  zatvorenih: %d  sakriveno: %d"
          % (len(otvorene), len(zatvorene), len(d) - ukupno))
    print("  izbornik: %d zupanija" % len(podrucja))


if __name__ == "__main__":
    main()
