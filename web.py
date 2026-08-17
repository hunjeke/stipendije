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

# ---- PODACI KOJE MIJENJAS PO POTREBI ----
EMAIL = "erik.hunjek@gmail.com"
DOMENA = "stipendije.hr"


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
.vodic{{margin-top:3.5rem;background:#fff;border:1px solid #e3e6ea;
border-radius:10px;padding:1.4rem}}
.vodic h2{{margin:0 0 .2rem}}
.vodic details{{border-top:1px solid #eef0f3;padding:.75rem 0 .3rem;margin:0}}
.vodic details:first-of-type{{border-top:none}}
.vodic summary{{color:#1a1d21;font-weight:600;font-size:.94rem}}
.vodic details p{{font-size:.89rem;color:#3d4450;margin:.6rem 0}}
.vodic details ul{{font-size:.89rem;color:#3d4450;padding-left:1.3rem;margin:.6rem 0}}
.vodic details li{{margin-bottom:.3rem}}
footer{{margin-top:3rem;padding-top:1.5rem;border-top:1px solid #e3e6ea;
font-size:.86rem;color:#4a5260}}
footer p{{margin:.6rem 0}}
footer a{{color:#1558d6}}
footer .meta{{font-size:.78rem;color:#8a919c;margin-top:1.2rem}}
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

<section class="vodic">
  <h2>Kako do stipendije</h2>
  <p class="pod">Ako prvi put tražiš stipendiju, ovo je ono što ti nitko ne kaže unaprijed.</p>

  <details>
    <summary>Kada se natječaji objavljuju</summary>
    <p>Većina natječaja otvara se <strong>od rujna do prosinca</strong>, za akademsku
    godinu koja je već počela. Rokovi su često kratki — nerijetko 15 dana od objave.</p>
    <p>Manji dio programa ide drugim ritmom: neki se objavljuju u <strong>svibnju
    i lipnju</strong>, prema kraju ljetnog semestra. Zato vrijedi provjeravati
    i izvan jeseni.</p>
  </details>

  <details>
    <summary>Ne možeš primati dvije javne stipendije istovremeno</summary>
    <p>Kod državnih stipendija vrijedi pravilo da za vrijeme primanja državne stipendije
    student ne može primati drugu stipendiju financiranu iz javnih izvora. Slično
    ograničenje traže i mnogi gradovi i županije — obično moraš potpisati izjavu
    da ne primaš drugu stipendiju.</p>
    <p>Praktično: ako se prijavljuješ na više njih, provjeri u tekstu svakog natječaja
    što se smije kombinirati. Privatne i korporativne stipendije nisu uvijek u istoj
    kategoriji kao javne, ali to piše u natječaju.</p>
  </details>

  <details>
    <summary>Što znači „deficitarno zanimanje"</summary>
    <p>Zanimanja za kojima postoji manjak kadra. Ako studiraš nešto s tog popisa,
    često imaš <strong>veće šanse i veći iznos</strong> — ponegdje su i pragovi
    prosjeka ocjena niži.</p>
    <p>Popis nije jedinstven: svaki grad i županija utvrđuje svoj, prema potrebama
    lokalnog tržišta rada. Isti studij može biti deficitaran u jednom gradu, a ne
    i u drugom. Popis je uvijek priložen natječaju.</p>
  </details>

  <details>
    <summary>Prebivalište je najčešći uvjet</summary>
    <p>Gradske i županijske stipendije gotovo uvijek traže prijavljeno prebivalište
    na njihovom području, često i određeno vrijeme unaprijed (npr. najmanje godinu
    dana prije objave natječaja).</p>
    <p>Bitno: mjesto <em>studiranja</em> i mjesto <em>prebivališta</em> su različite
    stvari. Možeš studirati u Zagrebu i primati stipendiju svog rodnog grada — kod
    nekih gradova iznos je čak <strong>veći</strong> ako studiraš izvan njih.</p>
  </details>

  <details>
    <summary>Što je SOM aplikacija</summary>
    <p>Više gradova i županija prijave prima preko vanjske aplikacije „SOM natječaji".
    Trebaš napraviti korisnički račun, pa se kroz njega prijaviti na natječaj.</p>
    <p>Račun napraviš jednom i koristiš ga za sve institucije koje taj sustav koriste.
    Nakon prijave u sustavu odabereš instituciju čiji natječaj tražiš.</p>
  </details>

  <details>
    <summary>Dokumentacija koju obično treba pripremiti</summary>
    <p>Razlikuje se po natječaju, ali ovo se traži najčešće:</p>
    <ul>
      <li>potvrda o upisu na studij</li>
      <li>prijepis ocjena ili potvrda o prosjeku</li>
      <li>uvjerenje o prebivalištu</li>
      <li>izjava da ne primaš drugu stipendiju</li>
      <li>dokazi o posebnim postignućima, ako se boduju</li>
      <li>za socijalne kategorije: potvrde o prihodima članova kućanstva</li>
    </ul>
    <p>Neke potvrde traju danima da ih dobiješ. Ako znaš da ti se natječaj otvara
    u listopadu, ima smisla pripremiti ih ranije.</p>
  </details>

  <details>
    <summary>Nepotpuna prijava = odbijena prijava</summary>
    <p>Gotovo svi natječaji izričito pišu da se nepotpune prijave i one predane
    nakon roka <strong>ne razmatraju</strong>. Nema dopunjavanja naknadno.</p>
    <p>Također provjeri <em>način</em> predaje — neki primaju samo elektronički,
    neki samo poštom ili osobno u pisarnici. Prijava poslana na pogrešan način
    tretira se kao da nije poslana.</p>
  </details>
</section>

<footer>
  <p><strong>Kontakt:</strong> <a href="mailto:{EMAIL}">{EMAIL}</a></p>
  <p>Nedostaje neka stipendija, ili si uočio netočan podatak? Piši nam — ispravljamo
     u najkraćem roku. Posebno nam je važno ako je <strong>rok prijave</strong> netočan.</p>
  <p>Ne dajemo osobne savjete o tome imaš li šanse za pojedinu stipendiju — za to se
     obrati instituciji koja je natječaj objavila.</p>
  <p class="meta">Zadnja provjera: {datetime.now().strftime('%d.%m.%Y. u %H:%M')} &middot;
     Pratimo {len(otvorene) + len(zatvorene)} izvora, popis se stalno dopunjuje.</p>
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
