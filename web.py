# -*- coding: utf-8 -*-
"""
Generira javnu stranicu iz output.json -> docs/index.html
Podrucje (grad/zupanija) cita iz sources.json i povezuje po URL-u,
tako da scraper.py ne treba mijenjati.
"""
import json
import os
from datetime import datetime

ULAZ = "output.json"
IZVORI = "sources.json"
IZLAZ_MAPA = "docs"
IZLAZ = os.path.join(IZLAZ_MAPA, "index.html")
SVI = "Cijela Hrvatska"


def esc(v):
    if v is None or str(v).strip() == "":
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def ucitaj_podrucja():
    """URL -> podrucje. Ako sources.json nema polje, vraca SVI."""
    m = {}
    if os.path.exists(IZVORI):
        for s in json.load(open(IZVORI, encoding="utf-8")):
            m[s["url"].rstrip("/")] = s.get("podrucje") or SVI
    return m


def kartica(r, otvorena, podrucje):
    naziv, url = esc(r.get("naziv")), esc(r.get("url"))
    iznos, rok = esc(r.get("iznos")), esc(r.get("rok_tekst"))
    uvjeti, kat = esc(r.get("uvjeti")), esc(r.get("kategorija"))

    upute = r.get("upute_za_prijavu") or ""
    koraci = "".join(f"<li>{esc(k.strip())}</li>"
                     for k in upute.split("|") if k.strip())

    redovi = ""
    if iznos:
        redovi += f'<div class="r"><span>Iznos</span><b>{iznos}</b></div>'
    if rok and otvorena:
        redovi += f'<div class="r"><span>Rok prijave</span><b>{rok}</b></div>'
    if uvjeti:
        redovi += f'<div class="r"><span>Tko se može prijaviti</span><b>{uvjeti}</b></div>'

    upute_html = ""
    if koraci and otvorena:
        upute_html = (f'<details><summary>Kako se prijaviti</summary>'
                      f'<ol>{koraci}</ol></details>')

    if otvorena:
        oznaka, klasa = '<span class="o ok">Otvoreno za prijave</span>', "k ok"
    else:
        oznaka, klasa = '<span class="o zat">Trenutno zatvoreno</span>', "k zat"

    return f"""<article class="{klasa}" data-podrucje="{esc(podrucje)}">
  <div class="zag"><h3>{naziv}</h3>{oznaka}</div>
  <div class="kat">{esc(podrucje)} &middot; {kat}</div>
  {redovi}
  {upute_html}
  <a class="izv" href="{url}" target="_blank" rel="noopener">Otvori službenu stranicu &rarr;</a>
</article>"""


def main():
    if not os.path.exists(ULAZ):
        print(f"GRESKA: nema {ULAZ}")
        return

    d = json.load(open(ULAZ, encoding="utf-8"))
    podrucja_map = ucitaj_podrucja()

    otvorene, zatvorene = [], []
    for r in d:
        s = r.get("status") or ""
        pod = podrucja_map.get((r.get("url") or "").rstrip("/"), SVI)
        if s.startswith("OTVORENO"):
            otvorene.append((r, pod))
        elif s.startswith("ROK ISTEKAO") or s.startswith("NEMA AKTIVNOG"):
            zatvorene.append((r, pod))
        # GRESKA / PROVJERITI se namjerno ne prikazuju javno

    otvorene.sort(key=lambda t: t[0].get("naziv") or "")
    zatvorene.sort(key=lambda t: t[0].get("naziv") or "")

    # popis podrucja za filtere, bez "Cijela Hrvatska" (ono je uvijek uklju\u010deno)
    sva = sorted({p for _, p in otvorene + zatvorene if p != SVI})
    gumbi = '<button class="f akt" data-f="sve">Sve</button>'
    gumbi += "".join(f'<button class="f" data-f="{esc(p)}">{esc(p)}</button>'
                     for p in sva)

    if otvorene:
        sekcija_otv = (f'<h2>Trenutno otvoreno <span class="br">{len(otvorene)}</span></h2>'
                       f'<div class="grupa">'
                       + "".join(kartica(r, True, p) for r, p in otvorene)
                       + '<p class="nema-rez">Nema otvorenih natječaja za odabrano područje.</p></div>')
    else:
        sekcija_otv = """<h2>Trenutno otvoreno</h2>
<div class="prazno">
  <p><strong>Trenutno nema otvorenih natječaja.</strong></p>
  <p>Većina natječaja objavljuje se od rujna do prosinca. Ispod su izvori koje
     pratimo — kad se neki otvori, pojavit će se ovdje.</p>
</div>"""

    sekcija_zat = ""
    if zatvorene:
        sekcija_zat = (f'<h2>Izvori koje pratimo <span class="br">{len(zatvorene)}</span></h2>'
                       '<p class="pod">Ovi natječaji trenutno nisu otvoreni. '
                       'Provjeravamo ih automatski dvaput tjedno.</p>'
                       '<div class="grupa">'
                       + "".join(kartica(r, False, p) for r, p in zatvorene)
                       + '<p class="nema-rez">Nema izvora za odabrano područje.</p></div>')

    html = f"""<!DOCTYPE html>
<html lang="hr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>stipendija.hr — stipendije u Hrvatskoj na jednom mjestu</title>
<meta name="description" content="Pregled aktivnih natječaja za stipendije u Hrvatskoj — iznosi, rokovi i upute za prijavu.">
<style>
*{{box-sizing:border-box}}
body{{margin:0;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;
background:#f5f6f8;color:#1a1d21;line-height:1.55}}
.w{{max-width:820px;margin:0 auto;padding:2rem 1rem 4rem}}
header h1{{font-size:1.9rem;margin:0 0 .3rem}}
header p{{margin:0;color:#5a6270}}
.upoz{{background:#fff8e6;border:1px solid #f0d99b;border-radius:8px;
padding:.9rem 1rem;margin:1.5rem 0;font-size:.88rem;color:#5c4a1a}}
.filteri{{margin:1.5rem 0 .5rem}}
.filteri-nasl{{font-size:.8rem;color:#6b7280;margin-bottom:.5rem;
text-transform:uppercase;letter-spacing:.03em}}
.f{{background:#fff;border:1px solid #d5dae0;border-radius:20px;
padding:.4rem .9rem;font-size:.85rem;cursor:pointer;margin:0 .35rem .45rem 0;
font-family:inherit;color:#3d4450;transition:.15s}}
.f:hover{{border-color:#9aa4b0}}
.f.akt{{background:#1a1d21;border-color:#1a1d21;color:#fff;font-weight:500}}
h2{{font-size:1.15rem;margin:2.5rem 0 .3rem;display:flex;align-items:center;gap:.6rem}}
.br{{background:#e3e6ea;color:#4a5260;font-size:.8rem;padding:.1rem .55rem;
border-radius:20px;font-weight:600}}
.pod{{margin:.2rem 0 1.2rem;color:#6b7280;font-size:.88rem}}
.prazno{{background:#fff;border:1px solid #e3e6ea;border-radius:10px;
padding:1.3rem;margin-top:1rem}}
.prazno p{{margin:.4rem 0;font-size:.93rem}}
.k{{background:#fff;border:1px solid #e3e6ea;border-radius:10px;
padding:1.1rem 1.2rem;margin-bottom:.9rem;border-left:4px solid #cbd2d9}}
.k.ok{{border-left-color:#1a9c4a}}
.k.zat{{opacity:.72}}
.k.skriveno{{display:none}}
.nema-rez{{display:none;background:#fff;border:1px solid #e3e6ea;
border-radius:10px;padding:1.1rem 1.2rem;color:#6b7280;font-size:.9rem;margin:0}}
.nema-rez.vidljivo{{display:block}}
.zag{{display:flex;justify-content:space-between;align-items:flex-start;
gap:.8rem;flex-wrap:wrap}}
h3{{font-size:1rem;margin:0 0 .2rem;flex:1;min-width:200px}}
.o{{font-size:.72rem;padding:.22rem .6rem;border-radius:20px;
font-weight:600;white-space:nowrap}}
.o.ok{{background:#d8f3e2;color:#0d6b32}}
.o.zat{{background:#eceef1;color:#5a6270}}
.kat{{font-size:.75rem;color:#8a919c;margin-bottom:.6rem}}
.r{{display:grid;grid-template-columns:150px 1fr;gap:.3rem .8rem;
font-size:.89rem;padding:.22rem 0}}
.r span{{color:#6b7280}}
.r b{{font-weight:500}}
details{{margin-top:.7rem;font-size:.88rem}}
summary{{cursor:pointer;color:#1558d6;font-weight:500}}
details ol{{margin:.6rem 0 0;padding-left:1.3rem;color:#3d4450}}
details li{{margin-bottom:.35rem}}
.izv{{display:inline-block;margin-top:.8rem;color:#1558d6;
text-decoration:none;font-size:.88rem;font-weight:500}}
.izv:hover{{text-decoration:underline}}
footer{{margin-top:3rem;padding-top:1.5rem;border-top:1px solid #e3e6ea;
font-size:.82rem;color:#6b7280}}
footer p{{margin:.5rem 0}}
@media(max-width:520px){{.r{{grid-template-columns:1fr}}.r span{{font-size:.8rem}}}}
</style>
</head>
<body>
<div class="w">
<header>
  <h1>stipendija.hr</h1>
  <p>Stipendije u Hrvatskoj na jednom mjestu — iznosi, rokovi i upute za prijavu.</p>
</header>

<div class="upoz">
  <strong>Važno:</strong> podaci se prikupljaju automatski i služe isključivo
  kao informacija. Rokovi i uvjeti mogu se promijeniti, a moguće su i greške u
  prikupljanju. <strong>Prije prijave uvijek provjerite službenu stranicu</strong>
  koja je linkana uz svaki natječaj. Ne odgovaramo za propuštene rokove ni za
  odluke donesene na temelju ovih podataka.
</div>

<div class="filteri">
  <div class="filteri-nasl">Filtriraj po području</div>
  {gumbi}
</div>

{sekcija_otv}
{sekcija_zat}

<footer>
  <p>Zadnja provjera: {datetime.now().strftime('%d.%m.%Y. u %H:%M')}</p>
  <p>Pratimo {len(otvorene) + len(zatvorene)} izvora. Popis se stalno dopunjuje.</p>
  <p>Nedostaje neka stipendija ili si uočio grešku? Javi nam.</p>
</footer>
</div>

<script>
(function () {{
  var SVI = {json.dumps(SVI, ensure_ascii=False)};
  var gumbi = document.querySelectorAll(".f");
  var kartice = document.querySelectorAll(".k");

  function filtriraj(odabir) {{
    kartice.forEach(function (k) {{
      var p = k.getAttribute("data-podrucje");
      // drzavne stipendije se prikazuju uz svaki grad jer vrijede za sve
      var pokazi = (odabir === "sve") || (p === odabir) || (p === SVI);
      k.classList.toggle("skriveno", !pokazi);
    }});
    document.querySelectorAll(".grupa").forEach(function (g) {{
      var ima = g.querySelectorAll(".k:not(.skriveno)").length > 0;
      var poruka = g.querySelector(".nema-rez");
      if (poruka) poruka.classList.toggle("vidljivo", !ima);
    }});
  }}

  gumbi.forEach(function (g) {{
    g.addEventListener("click", function () {{
      gumbi.forEach(function (x) {{ x.classList.remove("akt"); }});
      g.classList.add("akt");
      filtriraj(g.getAttribute("data-f"));
    }});
  }});
}})();
</script>
</body>
</html>"""

    os.makedirs(IZLAZ_MAPA, exist_ok=True)
    open(IZLAZ, "w", encoding="utf-8").write(html)

    print(f"Napisano {IZLAZ}")
    print(f"  otvorenih: {len(otvorene)}  zatvorenih: {len(zatvorene)}")
    print(f"  sakriveno: {len(d) - len(otvorene) - len(zatvorene)}")
    print(f"  filteri: Sve + {len(sva)} podrucja")


if __name__ == "__main__":
    main()
