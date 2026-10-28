# -*- coding: utf-8 -*-
"""
Stranica po natjecaju — i arhiv koji ih cuva kad rok prode.

Zasto postoji. Dosad su svi natjecaji zivjeli na jednoj stranici, pa je cijela
stranica konkurirala za jedan upit ("stipendije"). Covjek koji trazi "stipendija
grada Poreca" nalazio je Porecevu stranicu, a ne nas. Svaki natjecaj sa svojom
stranicom znaci stotinu upita s malom konkurencijom umjesto jednog s velikom.

Arhiv resava i drugu rupu. Kad natjecaj zatvori, gradska se stranica vrati na
obicnu i sljedece citanje javi "nema aktivnog natjecaja" — iznos i rok nestanu
zauvijek. Zato se svaki otvoreni natjecaj ovdje zapise i ostaje: stranica i
poslije roka govori koliko je bilo i kad se objavljuje, sto je korisno osam
mjeseci u godini kad natjecaja nema.
"""
import json
import os
import re
import unicodedata
from datetime import date, datetime

ARHIV = "natjecaji.json"
MAPA_NATJECAJA = "natjecaj"

from zajednicko import BAZA   # https://stipendije.hr


def _bez_kvacica(t):
    z = {"č": "c", "ć": "c", "ž": "z", "š": "s", "đ": "d",
         "Č": "C", "Ć": "C", "Ž": "Z", "Š": "S", "Đ": "D"}
    t = "".join(z.get(x, x) for x in str(t))
    return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode()


# rijeci koje su u svakom naslovu pa ga ne razlikuju; izlaze iz adrese
_SUVISNO = {"natjecaj", "natjecaja", "javni", "poziv", "za", "dodjelu", "i",
            "u", "na", "od", "do", "s", "sa", "te", "iz", "po"}


def slug_natjecaja(naslov, podrucje, godina):
    """'Stipendije darovitim ucenicima' + 'Pozega' -> 'pozega-stipendije-darovitim-ucenicima-2026'.

    Adresa mora biti stabilna kroz godine, jer se na nju vezu poveznice i
    Googleov indeks. Zato ulazi godina: natjecaj iz 2027. dobiva svoju stranicu,
    a proslogodisnja ostaje na svojoj adresi."""
    def ocisti(t):
        t = _bez_kvacica(t).lower()
        # godina ili skolska godina u naslovu ("2026./2027.") izlazi iz adrese:
        # godina se ionako dodaje na kraj, pa bi inace ispalo "...-2026-2027-2026"
        t = re.sub(r"\b20\d\d\s*[./-]?\s*20\d\d\b", " ", t)
        t = re.sub(r"\b20\d\d\b", " ", t)
        t = re.sub(r"[^a-z0-9]+", " ", t)
        return [w for w in t.split() if w and w not in _SUVISNO]

    # "Cijela Hrvatska" u adresi nista ne govori, a drzavne natjecaje gura u
    # upit po kojem ih nitko ne trazi
    pod = "" if _bez_kvacica(podrucje).lower().strip() == "cijela hrvatska" else podrucje
    rijeci = ocisti(pod)[:3] + ocisti(naslov)[:7]
    vidjeno, red = set(), []
    for w in rijeci:
        if w not in vidjeno:
            vidjeno.add(w)
            red.append(w)
    osnova = "-".join(red)[:70].strip("-")
    return f"{osnova}-{godina}" if osnova else f"natjecaj-{godina}"


def adresa_natjecaja(z):
    """Adresa po kojoj se natjecaj prepoznaje, ili "" kad je nema.

    Uzima se poveznica na sam natjecaj; tek ako je nema, adresa izvora.
    Sidro se zadrzava: FER na jednoj stranici drzi vise stipendija koje se
    razlikuju samo po #news_12345, pa bi bez sidra ispale kao jedna.

    Gola domena ("https://privrednik.hr/") nije adresa natjecaja nego
    rubrike. Tri Privrednikova fonda imaju istu takvu adresu i isti rok, pa
    bi se po njoj stopila u jedan — zato se takva adresa ne prihvaca."""
    from urllib.parse import urlsplit
    for k in ("poveznica", "poveznica_natjecaj", "url"):
        v = (z.get(k) or "").strip()
        if not v:
            continue
        d = urlsplit(v)
        put = d.path.rstrip("/")
        if not put:
            continue
        return (d.netloc + put
                + ("#" + d.fragment if d.fragment else "")).lower()
    return ""


def kljuc_zapisa(z, pricuva=""):
    """Pod cime natjecaj stoji u arhivi.

    Dosad je to bio slug izveden iz naslova koji model procita. Procita li
    ga sljedeci put drugim rijecima — a to se dogada stalno — nastane drugi
    kljuc i isti natjecaj dobije drugi zapis. Odatle su dolazili duplikati
    na stranici, duple poruke u mailu i tri zasebna mjesta u kodu koja ih
    poslije spajaju.

    Adresa i rok se ne mijenjaju kako model raspolozi, pa su pouzdan kljuc.
    Kad adrese nema, ostaje stari nacin — bolje zaseban zapis nego krivo
    spojen."""
    ad = adresa_natjecaja(z)
    if not ad:
        return pricuva or (z.get("slug") or "")
    return f"{ad}|{z.get('rok_iso') or ''}"


def _bogatstvo(z):
    return sum(1 for k in ("iznos", "iznosi", "uvjeti", "upute_za_prijavu",
                           "rok_tekst", "napomena", "poveznica")
               if z.get(k))


def prekljucaj(arhiv, poslani_slugovi=()):
    """Stara arhiva (kljuc = slug) -> nova (kljuc = adresa + rok).

    Vraca (nova_arhiva, popis_spajanja). Zapis koji je vec javljen mailom
    zadrzava svoj slug, da ga poslano.json i dalje prepoznaje; inace bi
    natjecaj o kojem je javljeno izgledao kao nov i otisao drugi put."""
    nova, spojeno = {}, []
    for s, zap in sorted(arhiv.items()):
        zap = dict(zap)
        zap.setdefault("slug", s)
        k = kljuc_zapisa(zap, pricuva=s)
        if k not in nova:
            nova[k] = zap
            continue
        stari = nova[k]
        spojeno.append((k, stari.get("slug"), zap.get("slug")))
        bolji = zap if _bogatstvo(zap) > _bogatstvo(stari) else stari
        slabiji = stari if bolji is zap else zap
        spoj = dict(slabiji)
        spoj.update({kk: vv for kk, vv in bolji.items() if vv})
        # slug koji je vec poslan ima prednost, inace onaj od bogatijeg zapisa
        for kandidat in (stari.get("slug"), zap.get("slug")):
            if kandidat in poslani_slugovi:
                spoj["slug"] = kandidat
                break
        else:
            spoj["slug"] = bolji.get("slug") or slabiji.get("slug")
        prvi = [x for x in (stari.get("prvi_put"), zap.get("prvi_put")) if x]
        if prvi:
            spoj["prvi_put"] = min(prvi)
        nova[k] = spoj
    return nova, spojeno


def ucitaj_arhiv(mapa_korijen="."):
    put = os.path.join(mapa_korijen, ARHIV)
    if not os.path.exists(put):
        return {}
    try:
        with open(put, encoding="utf-8") as f:
            arhiv = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    # Stara arhiva je kljucana slugom; prepoznaje se po tome sto u kljucu
    # nema uspravne crte. Prekljucava se jednom, pri prvom citanju.
    if arhiv and not any("|" in k for k in arhiv):
        poslani = set()
        try:
            with open(os.path.join(mapa_korijen, "poslano.json"),
                      encoding="utf-8") as f:
                poslani = set(json.load(f).get("slugovi", []))
        except (json.JSONDecodeError, OSError):
            pass
        arhiv, spojeno = prekljucaj(arhiv, poslani)
        if spojeno:
            print(f"  arhiva prekljucana: spojeno {len(spojeno)} dvojnika")
            for k, a, b in spojeno:
                print(f"    {a}  +  {b}")
    return arhiv


def spremi_arhiv(arhiv, mapa_korijen="."):
    put = os.path.join(mapa_korijen, ARHIV)
    with open(put, "w", encoding="utf-8") as f:
        json.dump(arhiv, f, ensure_ascii=False, indent=2, sort_keys=True)


def _rok_iso(status):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", status or "")
    return m.group(1) if m else ""


def azuriraj(arhiv, otvorene):
    """Upise svaki trenutno otvoren natjecaj u arhiv. Vraca broj novih.

    Postojeci zapis se dopunjuje, ne prepisuje: ako je model danas vratio manje
    nego prosli put (npr. izgubio iznos), stari podatak ostaje. Podatak koji smo
    jednom imali ne smije nestati zato sto je jedno citanje bilo slabije."""
    novih = 0
    danas = date.today().isoformat()
    for r, podrucje, zupanija in otvorene:
        rok = _rok_iso(r.get("status") or "")
        godina = (rok[:4] if rok else str(date.today().year))
        naslov = r.get("naslov_natjecaja") or r.get("naziv") or ""
        zapis_za_kljuc = {"poveznica": r.get("poveznica_natjecaj") or "",
                          "url": r.get("url") or "", "rok_iso": rok}
        kljuc = kljuc_zapisa(zapis_za_kljuc,
                             pricuva=slug_natjecaja(naslov, podrucje, godina))
        stari = arhiv.get(kljuc, {})
        if not stari:
            novih += 1
        # Slug je adresa stranice natjecaja i oznaka u poslano.json — kad
        # zapis vec postoji, zadrzava se onaj od prvi put, i ako je model u
        # meduvremenu naslov procitao drugim rijecima.
        s = stari.get("slug") or slug_natjecaja(naslov, podrucje, godina)
        novi = {
            "slug": s,
            "naslov": naslov,
            "podrucje": podrucje,
            "zupanija": zupanija,
            "izvor_naziv": r.get("naziv") or "",
            "url": r.get("url") or "",
            "poveznica": r.get("poveznica_natjecaj") or "",
            "rok_iso": rok,
            "rok_tekst": r.get("rok_tekst") or "",
            "iznos": r.get("iznos") or "",
            "iznosi": r.get("iznosi") or [],
            "iznos_je_fond": bool(r.get("iznos_je_fond")),
            "uvjeti": r.get("uvjeti") or "",
            "upute_za_prijavu": r.get("upute_za_prijavu") or "",
            "napomena": r.get("napomena") or "",
            "rucni": bool(r.get("_rucni")),
            "zasto_rucno": r.get("zasto_rucno") or "",
            "potvrda": r.get("potvrda") or "",
            "prvi_put": stari.get("prvi_put") or danas,
            "zadnji_put": danas,
        }
        # ne gubi ono sto smo vec znali
        for k, v in stari.items():
            if k not in ("zadnji_put",) and v and not novi.get(k):
                novi[k] = v
        arhiv[kljuc] = novi
    return novih


# --- stranica pojedinog natjecaja -----------------------------------------

CSS = """
.nat{padding:2.2rem 0 0}
.put{font-size:.85rem;color:var(--tinta-2);margin-bottom:.9rem}
.put a{color:var(--tinta-2);text-decoration:none;border-bottom:1px solid var(--linija)}
.put a:hover{color:var(--plava)}
.nat h1{font-size:clamp(1.5rem,4.4vw,2.1rem);margin-bottom:.4rem;line-height:1.18}
.nat .odakle{font-family:"PlexMono",monospace;font-size:.72rem;letter-spacing:.08em;
  text-transform:uppercase;color:var(--tinta-2);margin-bottom:1.3rem}
.stanje-n{display:inline-block;font-family:"PlexMono",monospace;font-size:.68rem;
  letter-spacing:.09em;text-transform:uppercase;padding:.25rem .6rem;margin-bottom:1.1rem}
.stanje-n.otv{background:#DCFCE7;color:var(--otvoreno)}
.stanje-n.zat{background:var(--papir);color:var(--tinta-2);border:1px solid var(--linija)}
.kutija{border:1px solid var(--linija);background:var(--karta);padding:1.1rem 1.15rem;
  margin-bottom:1.5rem}
.kutija dl{display:grid;grid-template-columns:9rem 1fr;gap:.45rem 1rem;margin:0;
  font-size:.95rem}
.kutija dt{color:var(--tinta-2)}
.kutija dd{margin:0}
.kutija dd.iznos{font-family:"PlexMono",monospace;font-weight:500}
.kutija .za{color:var(--tinta-2);font-weight:400}
.kutija .za::after{content:" —"}
.nat h2{font-size:1.1rem;margin:2rem 0 .5rem}
.nat p{font-size:.96rem;line-height:1.65;max-width:60ch}
.nat ol{padding-left:1.3rem;font-size:.96rem;line-height:1.6;max-width:60ch}
.nat ol li{margin-bottom:.45rem}
.izlaz{display:inline-block;margin-top:1.4rem;background:var(--plava);color:#fff;
  text-decoration:none;font-weight:600;font-size:.95rem;padding:.8rem 1.2rem}
.izlaz:hover{filter:brightness(1.12)}
.natrag-popis{display:block;margin-top:2.4rem;padding-top:1.2rem;
  border-top:1px solid var(--linija);font-size:.92rem}
.upoz-n{margin-top:1.6rem;border:1px dashed var(--linija);padding:.9rem 1rem;
  font-size:.9rem;color:var(--tinta-2);line-height:1.6}
@media(max-width:600px){
  .nat{padding:1.6rem 0 0}
  .kutija{padding:.9rem}
  .kutija dl{grid-template-columns:7rem 1fr;gap:.4rem .7rem;font-size:.92rem}
  .izlaz{display:block;text-align:center}
}
"""


def _hr_datum(iso):
    try:
        d = datetime.strptime(iso, "%Y-%m-%d").date()
        return f"{d.day:02d}.{d.month:02d}.{d.year}."
    except (ValueError, TypeError):
        return ""


def _skolska_godina(rok_iso):
    """"2026./2027." iz roka. Natjecaj s rokom u jesen vrijedi za godinu
    koja tada pocinje; rok u prvoj polovici godine jos pripada tekucoj."""
    try:
        g, m = int(rok_iso[:4]), int(rok_iso[5:7])
    except (TypeError, ValueError, IndexError):
        return ""
    prva = g if m >= 8 else g - 1
    return f"{prva}./{prva + 1}."


def _mjesto_vec_u(naslov, pod):
    """Je li mjesto vec u naslovu, makar u drugom padezu.

    "Stipendije Grada Zagreba" i podrucje "Grad Zagreb" su isto mjesto, ali
    se po punoj rijeci ne poklapaju — zato se usporeduje korijen. Bez toga
    je naslov glasio "Stipendije Grada Zagreba — Grad Zagreb"."""
    n = _bez_kvacica(naslov).lower()
    for rijec in re.findall(r"\w{4,}", _bez_kvacica(pod).lower()):
        if rijec in ("grad", "opcina", "cijela", "zupanija"):
            continue
        if rijec[:-2] and rijec[:-2] in n:
            return True
    return False


def _naslov_za_google(naslov, pod, rok_iso, otvoren):
    """Naslov stranice u Googleovu ispisu.

    Stari oblik je bio "{naslov} — {pod} | stipendije.hr" i imao tri mane,
    koje se vide kad se usporedi sa zupanijskim stranicama: te imaju CTR
    9,6%, a stranice po natjecaju 5,1% uz 17.681 prikaz.

      1. Mjesto se ponavljalo ("Stipendije Grada Zagreba — Grad Zagreb"),
         a Google pokazuje oko 60 znakova.
      2. Nije bilo godine, a ljudi je tipkaju: "drzavna stipendija 2026 2027"
         je jedan od najjacih upita na ovoj stranici.
      3. Nije bilo roka. Rok je jedini podatak zbog kojeg netko klikne bas
         na ovaj rezultat, a ne na sljedeci.

    Sve preko 60 znakova Google odsijeca, pa se najprije gradi ono bitno, a
    ime stranice se dodaje samo ako jos ima mjesta."""
    sveopce = _bez_kvacica(pod or "").lower().strip() == "cijela hrvatska"
    mjesto = "" if (not pod or sveopce or _mjesto_vec_u(naslov, pod)) else pod
    god = _skolska_godina(rok_iso)
    if god and re.search(r"\b20\d\d", naslov):
        god = ""
    rok = ""
    if otvoren and rok_iso:
        try:
            d = datetime.strptime(rok_iso, "%Y-%m-%d")
            rok = f"rok {d.day}.{d.month}."
        except ValueError:
            rok = ""

    def slozi(s_mjestom, s_godinom, s_rokom, s_imenom):
        t = naslov
        if s_mjestom and mjesto:
            t = f"{t} — {mjesto}"
        if s_godinom and god:
            t = f"{t} {god}"
        if s_rokom and rok:
            t = f"{t} — {rok}"
        return f"{t} | stipendije.hr" if s_imenom else t

    # Kad sve ne stane u 65 znakova, ispada ono najmanje vrijedno, redom:
    # ime stranice, pa rok, pa godina. Mjesto ostaje najdulje — po njemu
    # se natjecaj trazi ("stipendije Bakar"), a rok je samo razlog da se
    # klikne na rezultat koji je ionako vec pronaden.
    for kombinacija in ((1, 1, 1, 1), (1, 1, 1, 0), (1, 1, 0, 0),
                        (1, 0, 0, 0), (0, 0, 0, 0)):
        t = slozi(*kombinacija)
        if len(t) <= 65:
            return t
    return naslov[:60].rsplit(" ", 1)[0] + "…"


def _opis_za_google(z, rok_hr, otvoren):
    """Opis ispod naslova u Googleovu ispisu.

    Stari opis je pocinjao doslovnim ponavljanjem naslova, a zavrsavao
    praznom recenicom "Uvjeti i upute za prijavu." — Google pokazuje oko
    155 znakova, pa je pola prostora odlazilo na nista. Sad prvo ide ono
    zbog cega netko klikne (iznos, rok), pa obecanje onoga sto na stranici
    stvarno pise. Duze od 155 znakova Google odsijeca, pa se krati ovdje,
    na razmaku, umjesto da recenica puca nasred rijeci."""
    def skrati(d, n=152):
        return d if len(d) <= n else d[:n].rsplit(" ", 1)[0] + "…"

    iznos = (z.get("iznos") or "").strip()
    if len(iznos) > 60:
        iznos = iznos[:60].rsplit(" ", 1)[0] + "…"
    if not otvoren:
        d = "Natječaj je zatvoren. "
        if iznos:
            d += f"Iznos je bio: {iznos}. "
        return skrati(d + "Javljamo čim izađe novi natječaj za ovo mjesto.")

    # Rok po skupinama zna biti recenica od stotinjak znakova
    # ("29.10.2026. do 13:00 za ucenike · 30.10.2026. ... za studente") —
    # u opisu je dovoljan prvi datum, puni rok pise na samoj stranici.
    rok = (rok_hr or "").strip()
    if len(rok) > 32:
        rok = _hr_datum(z.get("rok_iso")) or ""
    d = f"Iznos: {iznos}. " if iznos else ""
    if rok:
        d += f"Rok prijave {rok.rstrip('. ')}. "
    return skrati(d + "Tko se može prijaviti, koje dokumente treba i gdje se predaje.")


def _strukturirano(z, naslov, pod, zup, slug_zup, opis, adresa):
    """JSON-LD za stranicu natjecaja.

    Dvije stvari, i vrijede razlicito:

    BreadcrumbList Google prikazuje u rezultatu — umjesto gole adrese stoji
    put "stipendije.hr > Istarska županija > Stipendije Grada Pazina". To je
    jedino sto se ovdje stvarno vidi u tražilici.

    EducationalOccupationalProgram se ne vidi nigdje: Google nema poseban
    prikaz za stipendije. Sluzi strojevima koji citaju stranicu da odgovore
    na pitanje — ChatGPT, Perplexity, Googleovi AI sazeci. Njima rok i
    izdavac u strukturiranom obliku znace razliku izmedu tocnog odgovora i
    nagadanja iz teksta.

    Pise se samo ono sto u zapisu stvarno postoji. Prazno polje se izostavlja
    — izmisljen podatak u strukturiranim podacima je gori od nikakvog, jer ga
    stroj uzima zdravo za gotovo."""
    import json as _json

    put = [{"@type": "ListItem", "position": 1, "name": "Sve stipendije",
            "item": f"{BAZA}/"}]
    if zup and slug_zup:
        put.append({"@type": "ListItem", "position": 2, "name": zup,
                    "item": f"{BAZA}/zupanija/{slug_zup}.html"})
    put.append({"@type": "ListItem", "position": len(put) + 1,
                "name": naslov, "item": adresa})

    program = {"@context": "https://schema.org",
               "@type": "EducationalOccupationalProgram",
               "name": naslov, "url": adresa, "description": opis,
               "inLanguage": "hr"}
    if z.get("rok_iso"):
        program["applicationDeadline"] = z["rok_iso"]
    izdavac = z.get("izvor_naziv") or pod
    if izdavac:
        program["provider"] = {"@type": "Organization", "name": izdavac}
    if z.get("uvjeti"):
        program["programPrerequisites"] = z["uvjeti"][:500]
    if pod:
        program["areaServed"] = {"@type": "AdministrativeArea", "name": pod}

    staze = {"@context": "https://schema.org", "@type": "BreadcrumbList",
             "itemListElement": put}
    return ("".join(
        f'<script type="application/ld+json">'
        f'{_json.dumps(d, ensure_ascii=False, separators=(",", ":"))}</script>'
        for d in (program, staze)))


def stranica(mapa, z, eur, iznos_polja_f, datumi_u_brojke, esc,
             glava, navigacija, podnozje, broj_izvora, vrijeme, slug_zup,
             poziv_kanal=None):
    """Napise docs/natjecaj/<slug>.html za jedan zapis iz arhiva."""
    otvoren = bool(z.get("rok_iso")) and z["rok_iso"] >= date.today().isoformat()
    from zajednicko import sredi_naslov
    naslov = sredi_naslov(z.get("naslov")) or "Natječaj za stipendiju"
    pod = z.get("podrucje") or ""
    zup = z.get("zupanija") or ""

    polja = ""
    for _redak in iznos_polja_f(
            {"iznosi": z.get("iznosi"), "iznos": z.get("iznos"),
             "iznos_je_fond": z.get("iznos_je_fond")},
            otvoren, bool(z.get("poveznica")), skrati=False):
        oznaka, sadrzaj, mono = _redak[0], _redak[1], _redak[2]
        polja += (f'<dt>{oznaka}</dt>'
                  f'<dd class="{"iznos" if mono else ""}">{sadrzaj}</dd>')
    # Natjecaj s rokom po skupini (Kastav: 30.10. ucenici, 20.11. studenti)
    # mora i ovdje pokazati oba roka, inace stranica natjecaja proturjeci
    # kartici s koje se na nju dolazi.
    from zajednicko import rok_po_skupinama_tekst
    rok_hr = (rok_po_skupinama_tekst(z.get("rok_tekst"))
              or _hr_datum(z.get("rok_iso")))
    if rok_hr:
        polja += f'<dt>Rok prijave</dt><dd>{rok_hr}</dd>'
    if z.get("uvjeti"):
        polja += (f'<dt>Tko se prijavljuje</dt>'
                  f'<dd>{esc(datumi_u_brojke(z["uvjeti"]))}</dd>')
    polja += f'<dt>Izvor</dt><dd>{esc(z.get("izvor_naziv") or pod)}</dd>'

    koraci = "".join(f"<li>{esc(k.strip())}</li>"
                     for k in (datumi_u_brojke(z.get("upute_za_prijavu")) or "").split("|")
                     if k.strip())
    upute = (f'<h2>Kako se prijaviti</h2><ol>{koraci}</ol>') if koraci else ""
    nap = (f'<h2>Obrati pažnju</h2><p>{esc(datumi_u_brojke(z["napomena"]))}</p>'
           if z.get("napomena") else "")
    # Rucno upisan natjecaj mora reci da je rucno upisan i gdje se provjerava.
    # Podnozje stranice tvrdi da se podaci prikupljaju automatski, pa bi sutjeti
    # o tome znacilo pustiti da ta tvrdnja vrijedi i za ono sto smo sami utipkali.
    if z.get("rucni"):
        p = esc(z.get("zasto_rucno") or
                "Ovaj natječaj upisali smo ručno jer ga nije moguće pročitati automatski.")
        if z.get("potvrda"):
            p += (f' Podatke smo preuzeli s <a href="{esc(z["potvrda"])}" '
                  f'target="_blank" rel="noopener">ove objave</a>.')
        nap += f'<p class="upoz-n">{p}</p>'

    veza = z.get("poveznica") or z.get("url") or ""
    if otvoren:
        stanje = '<span class="stanje-n otv">Otvoreno za prijave</span>'
        gumb = (f'<a class="izlaz" href="{esc(veza)}" target="_blank" '
                f'rel="noopener">Otvori službeni natječaj &rarr;</a>') if veza else ""
        upoz = ""
    else:
        stanje = '<span class="stanje-n zat">Rok je istekao</span>'
        gumb = (f'<a class="izlaz" href="{esc(veza)}" target="_blank" '
                f'rel="noopener">Službena stranica &rarr;</a>') if veza else ""
        upoz = ('<p class="upoz-n">Ovaj natječaj više nije otvoren. Podaci su '
                'zapisani onako kako su stajali dok je trajao, da se vidi koliki '
                'je iznos bio i u kojem se dijelu godine objavljuje. Novi se '
                'obično raspisuje u isto doba — čim izađe, pojavit će se na '
                '<a href="../">popisu otvorenih natječaja</a>.</p>')

    # Tko cita istekli natjecaj najvise treba obavijest kad izade novi.
    poziv = poziv_kanal() if poziv_kanal else ""
    put_gore = ""
    if zup and slug_zup:
        put_gore = (f' &rsaquo; <a href="../zupanija/{slug_zup}.html">'
                    f'{esc(zup)}</a>')

    naslov_seo = _naslov_za_google(naslov, pod, z.get("rok_iso"), otvoren)
    opis = _opis_za_google(z, rok_hr, otvoren)
    adresa = f"{BAZA}/{MAPA_NATJECAJA}/{z['slug']}.html"
    html = glava(naslov_seo, opis[:300], CSS,
                 _strukturirano(z, naslov, pod, zup, slug_zup,
                                opis[:300], adresa), "../")
    html += navigacija("natjecaji", "../")
    html += f"""<main class="w"><section class="nat">
<p class="put"><a href="../">Sve stipendije</a>{put_gore}</p>
{stanje}
<h1>{esc(naslov)}</h1>
<div class="odakle">{esc(pod)}</div>
<div class="kutija"><dl>{polja}</dl></div>
{upute}{nap}
{gumb}
{upoz}
{poziv}
<a class="natrag-popis" href="../">&larr; Svi otvoreni natječaji za stipendije</a>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme, "../")
    os.makedirs(os.path.join(mapa, MAPA_NATJECAJA), exist_ok=True)
    rel = f"{MAPA_NATJECAJA}/{z['slug']}.html"
    with open(os.path.join(mapa, rel), "w", encoding="utf-8") as f:
        f.write(html)
    return rel, otvoren
