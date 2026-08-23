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


def esc(v):
    if v is None or str(v).strip() == "":
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def iso_rok(status):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", status or "")
    return m.group(1) if m else ""


def ucitaj_izvore():
    p, z = {}, {}
    if os.path.exists(IZVORI):
        for s in json.load(open(IZVORI, encoding="utf-8")):
            k = s["url"].rstrip("/")
            p[k] = s.get("podrucje") or SVI
            z[k] = s.get("zupanija") or ""
    return p, z


CSS_INDEX = """
/* --- hero --- */
.hero{padding:3.2rem 0 .4rem}
.hero .oznaka{display:inline-block;margin-bottom:1rem}
.hero p.teza{font-size:1.06rem;color:var(--tinta-2);max-width:46ch;margin:.4rem 0 0}

/* --- signature: traka roka --- */
.rok-traka{margin-top:1.8rem;border:1.5px solid var(--tinta);background:var(--karta)}
.rok-traka .gornje{display:flex;justify-content:space-between;align-items:baseline;
  gap:1rem;padding:.8rem 1.1rem .55rem;flex-wrap:wrap}
.rok-traka .naslov{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;
  font-size:1.02rem;letter-spacing:-.01em}
.odbroj{font-family:"IBM Plex Mono",monospace;font-weight:500;
  font-size:2.6rem;line-height:1;letter-spacing:-.04em;padding:0 1.1rem .1rem}
.odbroj .jed{font-size:.85rem;letter-spacing:.09em;text-transform:uppercase;
  color:var(--tinta-2);margin-left:.5rem}
.rok-traka .donje{padding:.35rem 1.1rem 1rem;font-size:.88rem;color:var(--tinta-2)}
.mjerka{height:5px;background:var(--linija);position:relative;overflow:hidden}
.mjerka i{position:absolute;inset:0 auto 0 0;background:var(--otvoreno);display:block}
.rok-traka.hitno{border-color:var(--hitno)}
.rok-traka.hitno .odbroj{color:var(--hitno)}
.rok-traka.hitno .mjerka i{background:var(--hitno)}

/* prazno stanje */
.prazno{margin-top:1.8rem;border:1.5px solid var(--tinta);background:var(--karta);
  padding:1.3rem 1.15rem}
.prazno .kad{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;
  font-size:1.35rem;letter-spacing:-.02em;margin:0 0 .35rem}
.prazno p{margin:.35rem 0;font-size:.92rem;color:var(--tinta-2)}

/* --- filter --- */
.filteri{margin:2.2rem 0 0;background:var(--karta);border:2px solid var(--tinta);
  padding:1.15rem 1.2rem 1.25rem}
.oznaka-f{display:block;font-family:"Bricolage Grotesque",sans-serif;
  font-weight:700;font-size:1.06rem;letter-spacing:-.012em;
  color:var(--tinta);margin-bottom:.65rem}
#zupanija{width:100%;max-width:460px;background:var(--papir);
  border:1.5px solid var(--tinta);border-radius:0;padding:.78rem 2.6rem .78rem .9rem;
  font-family:"IBM Plex Sans",sans-serif;font-size:1rem;font-weight:500;
  color:var(--tinta);cursor:pointer;appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='8'%3E%3Cpath d='M1 1l5.5 5.5L12 1' stroke='%231E2230' stroke-width='2' fill='none'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 1rem center}
#zupanija:hover,#zupanija:focus{border-color:var(--otvoreno);background-color:#fff}
.pojasnjenje{margin:.7rem 0 0;font-size:.85rem;color:var(--tinta-2);max-width:48ch}

/* --- kartice --- */
.k{background:var(--karta);border:1px solid var(--linija);
  padding:1.05rem 1.15rem;margin-bottom:.75rem}
.k.otv{border-left:3px solid var(--otvoreno)}
.k.skriveno{display:none}
.k .zag{display:flex;justify-content:flex-start;gap:.7rem;
  align-items:baseline;flex-wrap:wrap}
.znak{font-family:"IBM Plex Mono",monospace;font-size:.66rem;letter-spacing:.09em;
  text-transform:uppercase;padding:.2rem .5rem;white-space:nowrap;
  flex-shrink:0;align-self:flex-start;max-width:100%}
.znak.otv{background:#E2F0E7;color:var(--otvoreno)}
.znak.zat{background:var(--papir);color:var(--tinta-2)}
.znak.hitno{background:#F7E3DF;color:var(--hitno)}
.k .izvor{font-family:"IBM Plex Mono",monospace;font-size:.68rem;
  letter-spacing:.06em;text-transform:uppercase;color:var(--tinta-2);
  margin-bottom:.55rem}
.polja{display:grid;grid-template-columns:8.5rem 1fr;gap:.28rem .9rem;
  font-size:.9rem;margin:.5rem 0 0}
.polja dt{color:var(--tinta-2)}
.polja dd{margin:0}
.polja dd.iznos{font-family:"IBM Plex Mono",monospace;font-weight:500}
.k details{margin-top:.75rem;font-size:.88rem}
.k summary{cursor:pointer;color:var(--otvoreno);font-weight:500}
.k details ol{margin:.55rem 0 0;padding-left:1.25rem;color:var(--tinta-2)}
.k details li{margin-bottom:.3rem}
.veza{display:inline-block;margin-top:.8rem;font-size:.88rem;font-weight:500;
  color:var(--tinta);text-decoration:none;border-bottom:1.5px solid var(--otvoreno);
  padding-bottom:1px}
.veza:hover{color:var(--otvoreno)}
.nema-rez{display:none;border:1px dashed var(--linija);padding:1.05rem 1.15rem;
  color:var(--tinta-2);font-size:.9rem;margin:0}
.nema-rez.vidljivo{display:block}
.zatvoreni-omot{margin-top:.4rem}
.popis-zup{display:flex;flex-wrap:wrap;gap:.45rem}
.popis-zup a{font-size:.88rem;color:var(--tinta);text-decoration:none;
  border:1px solid var(--linija);background:var(--karta);padding:.42rem .75rem}
.popis-zup a:hover{border-color:var(--otvoreno);color:var(--otvoreno)}
/* kad je odabrana zupanija, lokalne stipendije idu prve */
.grupa{display:flex;flex-direction:column}
.grupa .k{order:0}
.grupa .k.drzavna{order:1}
.grupa .nema-rez{order:2}
.medja{order:1;display:none;margin:.5rem 0 .9rem;
  font-family:"IBM Plex Mono",monospace;font-size:.7rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--tinta-2);
  border-top:1px solid var(--linija);padding-top:.85rem}
.medja.vidljiva{display:block}
@media(max-width:600px){
  /* hero */
  .hero{padding:2rem 0 .4rem}
  .hero p.teza{font-size:.98rem}

  /* traka roka: brojka i tekst u dva reda da stanu */
  .rok-traka{margin-top:1.4rem}
  .rok-traka .gornje{padding:.7rem .85rem .45rem;gap:.4rem}
  .rok-traka .naslov{font-size:.95rem;line-height:1.3}
  .rok-traka .meta{font-size:.62rem}
  .odbroj{font-size:2.5rem;padding:0 .85rem .1rem}
  .odbroj .jed{font-size:.72rem;margin-left:.4rem}
  .rok-traka .donje{padding:.3rem .85rem .9rem;font-size:.85rem}
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
  .sek-vrh .broj{font-size:.72rem}

  /* kartice */
  .k{padding:.95rem .9rem}
  /* oznaka uvijek iznad naslova, da ne skace i ne izlazi van */
  .k .zag{flex-direction:column-reverse;align-items:flex-start;gap:.45rem}
  .k .zag h3{min-width:0;width:100%}
  h3{font-size:.97rem}
  .znak{font-size:.62rem;padding:.18rem .45rem}
  .polja{grid-template-columns:1fr;gap:.05rem}
  .polja dt{font-size:.76rem;margin-top:.45rem;color:#8A909E}
  .polja dd{font-size:.92rem}
  /* veca povrsina za prst */
  .k summary{padding:.35rem 0}
  .veza{padding:.4rem 0 .3rem}
}
@media(max-width:380px){
  .odbroj{font-size:2.1rem}
  .rok-traka .naslov{font-size:.9rem}
}
"""


def kartica(r, otvorena, podrucje, zupanija):
    naziv, url = esc(r.get("naziv")), esc(r.get("url"))
    iznos, rok = esc(r.get("iznos")), esc(r.get("rok_tekst"))
    uvjeti = esc(r.get("uvjeti"))
    iso = iso_rok(r.get("status") or "")

    polja = ""
    if iznos:
        # monospace samo za kratke iznose ("200 EUR"); duge recenice
        # se u mono citaju tesko, pa idu obicnim pismom
        kl = "iznos" if len(iznos) <= 32 else ""
        polja += f'<dt>Iznos</dt><dd class="{kl}">{iznos}</dd>'
    if rok and otvorena:
        polja += f'<dt>Rok prijave</dt><dd>{rok}</dd>'
    if uvjeti:
        polja += f'<dt>Tko se prijavljuje</dt><dd>{uvjeti}</dd>'
    polja = f'<dl class="polja">{polja}</dl>' if polja else ""

    upute = r.get("upute_za_prijavu") or ""
    koraci = "".join(f"<li>{esc(k.strip())}</li>"
                     for k in upute.split("|") if k.strip())
    upute_html = (f'<details><summary>Kako se prijaviti</summary><ol>{koraci}</ol></details>'
                  if koraci and otvorena else "")

    if otvorena:
        znak = '<span class="znak otv" data-znak>Otvoreno</span>'
        klasa = "k otv"
    else:
        znak = '<span class="znak zat">Zatvoreno</span>'
        klasa = "k"

    return (f'<article class="{klasa}" data-podrucje="{esc(podrucje)}" '
            f'data-zupanija="{esc(zupanija)}" data-rok="{iso}">'
            f'<div class="zag"><h3>{naziv}</h3>{znak}</div>'
            f'<div class="izvor">{esc(podrucje)}</div>'
            f'{polja}{upute_html}'
            f'<a class="veza" href="{url}" target="_blank" rel="noopener">'
            f'Službeni natječaj &rarr;</a></article>')


# hrvatski abecedni red: ... S, Š, T, U, V, Z, Ž
_ABC = "aábcčćdđefghijklmnoprsštuvzž"
_RANG = {z: i for i, z in enumerate(_ABC)}


def hr_kljuc(s):
    """Sortiranje po hrvatskoj abecedi umjesto po kodovima znakova."""
    out = []
    for z in s.lower():
        out.append(_RANG.get(z, 99 + ord(z) % 50))
    return out


def izbornik(podrucja):
    """Padajuci izbornik zupanija. Podrucje koje ne pripada nijednoj zupaniji
    (Grad Zagreb) stoji samo, s jasnom oznakom da je grad."""
    opcije = '<option value="">Sve stipendije u Hrvatskoj</option>'
    for p in sorted(podrucja, key=hr_kljuc):
        naziv = p if "županija" in p else f"Grad {p}"
        opcije += f'<option value="{esc(p)}">{esc(naziv)}</option>'
    return opcije


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

  function dana(iso){
    if(!iso) return null;
    return Math.ceil((new Date(iso+"T23:59:59") - new Date())/86400000);
  }

  document.querySelectorAll("[data-rok]").forEach(function(k){
    var n=dana(k.getAttribute("data-rok")), z=k.querySelector("[data-znak]");
    if(n===null||!z) return;
    if(n<=7){ z.className="znak hitno";
      z.textContent = n<=0 ? "Zadnji dan" : ("Još "+n+" "+oblik(n,"dan","dana","dana")); }
    else if(n<=21){ z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
  });

  var t=document.getElementById("traka");
  if(t){
    var n=dana(t.getAttribute("data-rok"));
    if(n!==null){
      document.getElementById("brojka").textContent = n<0?0:n;
      document.getElementById("jedinica").textContent =
        oblik(n,"dan","dana","dana")+" do roka";
      document.getElementById("mjerka").style.width =
        Math.max(0,Math.min(100,(n/30)*100))+"%";
      if(n<=7) t.classList.add("hitno");
    }
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
      var ima=g.querySelectorAll(".k:not(.skriveno)").length>0;
      var por=g.querySelector(".nema-rez");
      if(por)por.classList.toggle("vidljivo",!ima);
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
    pod_map, zup_map = ucitaj_izvore()

    otvorene, zatvorene = [], []
    for r in d:
        s = r.get("status") or ""
        k = (r.get("url") or "").rstrip("/")
        par = (r, pod_map.get(k, SVI), zup_map.get(k, ""))
        if s.startswith("OTVORENO"):
            otvorene.append(par)
        elif s.startswith("ROK ISTEKAO") or s.startswith("NEMA AKTIVNOG"):
            zatvorene.append(par)

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
    if otvorene:
        prvi = otvorene[0]
        iso = iso_rok(prvi[0].get("status") or "")
        hero = f"""<div class="rok-traka" id="traka" data-rok="{iso}">
  <div class="gornje">
    <span class="naslov">{esc(prvi[0].get('naziv'))}</span>
    <span class="meta">najbliži rok</span>
  </div>
  <div class="odbroj"><span id="brojka">—</span><span class="jed" id="jedinica">do roka</span></div>
  <div class="donje">{esc(prvi[0].get('iznos') or 'iznos nije naveden')}</div>
  <div class="mjerka"><i id="mjerka" style="width:0"></i></div>
</div>"""
        n = len(otvorene)
        im = oblik(n, "natječaj", "natječaja", "natječaja")
        gl = oblik(n, "otvoren je", "otvorena su", "otvoreno je")
        podnaslov = f"Upravo sada {gl} {n} {im}."
    else:
        hero = """<div class="prazno">
  <p class="kad">Sezona kreće u rujnu.</p>
  <p>Većina gradova, županija i sveučilišta natječaje objavljuje između rujna
     i prosinca. Rokovi su kratki, često 15 dana od objave.</p>
  <p>Izvore provjeravamo automatski dvaput tjedno. Čim se neki natječaj otvori,
     pojavit će se ovdje na vrhu.</p>
</div>"""
        podnaslov = "Trenutno nema otvorenih natječaja."

    # ---------- sekcije ----------
    sek_otv = ""
    if otvorene:
        sek_otv = (f'<section class="sek"><div class="sek-vrh"><h2>Otvoreno za prijave</h2>'
                   f'<span class="broj">{len(otvorene)} '
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

    js = JS

    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "stipendije.hr",
        "alternateName": "Stipendije u Hrvatskoj",
        "url": BAZA + "/",
        "inLanguage": "hr-HR",
        "description": ("Pregled otvorenih natječaja za stipendije u Hrvatskoj "
                        "— iznosi, rokovi prijave i upute."),
    }, ensure_ascii=False)

    html = glava(
        "stipendije.hr — stipendije u Hrvatskoj na jednom mjestu",
        "Otvoreni natječaji za stipendije u Hrvatskoj: iznosi, rokovi i upute za prijavu.",
        CSS_INDEX,
        '<script type="application/ld+json">' + ld + '</script>')
    html += navigacija("natjecaji")
    html += f"""<main>
<section class="hero"><div class="w">
  <span class="meta oznaka">Ažurirano {vrijeme}</span>
  <h1>Sve stipendije u Hrvatskoj,<br>s rokovima koji vrijede.</h1>
  <p class="teza">{podnaslov}</p>
  {hero}
  <div class="filteri">
    <label class="oznaka-f" for="zupanija">Odaberi županiju</label>
    <select id="zupanija">{izbornik(podrucja)}</select>
    <p class="pojasnjenje">Prikazuju se stipendije te županije, svih njezinih
      gradova i one državne, na koje imaju pravo svi.</p>
  </div>
  <p class="upoz"><strong>Provjeri prije prijave.</strong> Podatke prikupljamo
    automatski, pa su greške moguće. Vrijede rok i uvjeti sa službene stranice
    natječaja, na koju vodi poveznica uz svaki unos.</p>
</div></section>
<div class="w">{sek_otv}{sek_zat}{sek_zup}</div>
</main>
<script>{js}</script>"""
    html += podnozje(ukupno, vrijeme)

    os.makedirs(MAPA, exist_ok=True)
    open(os.path.join(MAPA, "index.html"), "w", encoding="utf-8").write(html)

    from stranice import vodic, impressum, stranica_zupanije, sitemap, slug
    vodic(MAPA, ukupno, vrijeme)
    impressum(MAPA, ukupno, vrijeme)

    # --- zasebna stranica po zupaniji (za trazilice) ---
    sve_zup = sorted({z if z else p for _, p, z in otvorene + zatvorene
                      if p != SVI})
    putevi = [("", "1.0"), ("vodic.html", "0.7"), ("impressum.html", "0.3")]

    for zup in sve_zup:
        otv_z = [(r, p, z) for r, p, z in otvorene
                 if z == zup or p == zup]
        zat_z = [(r, p, z) for r, p, z in zatvorene
                 if z == zup or p == zup]
        dio = ""
        if otv_z:
            dio += ('<div class="sek-vrh"><h2>Otvoreno za prijave</h2>'
                    f'<span class="broj">{len(otv_z)}</span></div>'
                    + "".join(kartica(r, True, p, z) for r, p, z in otv_z))
        if zat_z:
            dio += ('<div class="sek-vrh" style="margin-top:2.2rem">'
                    '<h2>Izvori koje pratimo</h2>'
                    f'<span class="broj">{len(zat_z)}</span></div>'
                    + "".join(kartica(r, False, p, z) for r, p, z in zat_z))
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
