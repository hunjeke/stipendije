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


def ucitaj_arhiv(mapa_korijen="."):
    put = os.path.join(mapa_korijen, ARHIV)
    if not os.path.exists(put):
        return {}
    try:
        with open(put, encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


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
        s = slug_natjecaja(naslov, podrucje, godina)
        stari = arhiv.get(s, {})
        if not stari:
            novih += 1
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
        arhiv[s] = novi
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


def stranica(mapa, z, eur, iznos_polja_f, datumi_u_brojke, esc,
             glava, navigacija, podnozje, broj_izvora, vrijeme, slug_zup,
             poziv_kanal=None):
    """Napise docs/natjecaj/<slug>.html za jedan zapis iz arhiva."""
    otvoren = bool(z.get("rok_iso")) and z["rok_iso"] >= date.today().isoformat()
    naslov = z.get("naslov") or "Natječaj za stipendiju"
    pod = z.get("podrucje") or ""
    zup = z.get("zupanija") or ""

    polja = ""
    for oznaka, sadrzaj, mono in iznos_polja_f(
            {"iznosi": z.get("iznosi"), "iznos": z.get("iznos"),
             "iznos_je_fond": z.get("iznos_je_fond")},
            otvoren, bool(z.get("poveznica"))):
        polja += (f'<dt>{oznaka}</dt>'
                  f'<dd class="{"iznos" if mono else ""}">{sadrzaj}</dd>')
    rok_hr = _hr_datum(z.get("rok_iso"))
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

    opis = (f"{naslov} — {pod}. "
            + (f"Iznos: {z.get('iznos')[:90]}. " if z.get("iznos") else "")
            + (f"Rok prijave {rok_hr} " if rok_hr else "")
            + "Uvjeti i upute za prijavu.")
    html = glava(f"{naslov} — {pod} | stipendije.hr", opis[:300], CSS, "", "../")
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
