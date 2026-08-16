# -*- coding: utf-8 -*-
import json
import os
from datetime import datetime

ULAZ = "output.json"
IZLAZ_MAPA = "docs"
IZLAZ = os.path.join(IZLAZ_MAPA, "index.html")


def esc(v):
    if v is None or str(v).strip() == "":
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def kartica(r, otvorena):
    naziv = esc(r.get("naziv"))
    url = esc(r.get("url"))
    iznos = esc(r.get("iznos"))
    rok = esc(r.get("rok_tekst"))
    uvjeti = esc(r.get("uvjeti"))
    kat = esc(r.get("kategorija"))

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
        upute_html = f'<details><summary>Kako se prijaviti</summary><ol>{koraci}</ol></details>'

    if otvorena:
        oznaka = '<span class="o ok">Otvoreno za prijave</span>'
        klasa = "k ok"
    else:
        oznaka = '<span class="o zat">Trenutno zatvoreno</span>'
        klasa = "k zat"

    return f"""<article class="{klasa}">
  <div class="zag"><h3>{naziv}</h3>{oznaka}</div>
  <div class="kat">{kat}</div>
  {redovi}
  {upute_html}
  <a class="izv" href="{url}" target="_blank" rel="noopener">Otvori službenu stranicu &rarr;</a>
</article>"""


def main():
    if not os.path.exists(ULAZ):
        print(f"GRESKA: nema {ULAZ}")
        return

    with open(ULAZ, encoding="utf-8") as f:
        d = json.load(f)

    otvorene, zatvorene = [], []
    for r in d:
        s = (r.get("status") or "")
        if s.startswith("OTVORENO"):
            otvorene.append(r)
        elif s.startswith("ROK ISTEKAO") or s.startswith("NEMA AKTIVNOG"):
            zatvorene.append(r)

    otvorene.sort(key=lambda r: r.get("naziv") or "")
    zatvorene.sort(key=lambda r: r.get("naziv") or "")

    if otvorene:
        sekcija_otv = ("<h2>Trenutno otvoreno "
                       f"<span class=\"br\">{len(otvorene)}</span></h2>"
                       + "".join(kartica(r, True) for r in otvorene))
    else:
        sekcija_otv = """<h2>Trenutno otvoreno</h2>
<div class="prazno">
  <p><strong>Trenutno nema otvorenih natječaja.</strong></p>
  <p>Većina natječaja za stipendije objavljuje se od rujna do prosinca.
     Ispod su izvori koje pratimo — kad se neki otvori, pojavit će se ovdje.</p>
</div>"""

    sekcija_zat = ""
    if zatvorene:
        sekcija_zat = ("<h2>Izvori koje pratimo "
                       f"<span class=\"br\">{len(zatvorene)}</span></h2>"
                       '<p class="pod">Ovi natječaji trenutno nisu otvoreni. '
                       'Provjeravamo ih automatski dvaput tjedno.</p>'
                       + "".join(kartica(r, False) for r in zatvorene))

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

{sekcija_otv}
{sekcija_zat}

<footer>
  <p>Zadnja provjera: {datetime.now().strftime('%d.%m.%Y. u %H:%M')}</p>
  <p>Pratimo {len(otvorene) + len(zatvorene)} izvora. Popis se stalno dopunjuje.</p>
  <p>Nedostaje neka stipendija ili si uočio grešku? Javi nam.</p>
</footer>
</div>
</body>
</html>"""

    os.makedirs(IZLAZ_MAPA, exist_ok=True)
    with open(IZLAZ, "w", encoding="utf-8") as f:
        f.write(html)

    skriveno = len(d) - len(otvorene) - len(zatvorene)
    print(f"Napisano {IZLAZ}")
    print(f"  otvorenih: {len(otvorene)}")
    print(f"  zatvorenih: {len(zatvorene)}")
    print(f"  sakriveno: {skriveno}")


if __name__ == "__main__":
    main()
