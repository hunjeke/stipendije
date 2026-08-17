# -*- coding: utf-8 -*-
"""
Generira javnu stranicu iz output.json -> docs/index.html

Podrucje i zupaniju cita iz sources.json (povezuje po URL-u), pa scraper.py
ne treba mijenjati. Tehnicki statusi (GRESKA, PROVJERITI) se NE prikazuju javno.
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


def esc(v):
    if v is None or str(v).strip() == "":
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def ucitaj_izvore():
    """Vraca (URL -> podrucje, URL -> zupanija)."""
    p, z = {}, {}
    if os.path.exists(IZVORI):
        for s in json.load(open(IZVORI, encoding="utf-8")):
            k = s["url"].rstrip("/")
            p[k] = s.get("podrucje") or SVI
            z[k] = s.get("zupanija") or ""
    return p, z


def kartica(r, otvorena, podrucje, zupanija):
    naziv, url = esc(r.get("naziv")), esc(r.get("url"))
    iznos, rok = esc(r.get("iznos")), esc(r.get("rok_tekst"))
    uvjeti, kat = esc(r.get("uvjeti")), esc(r.get("kategorija"))

    upute = r.get("upute_za_prijavu") or ""
    koraci = "".join("<li>%s</li>" % esc(k.strip())
                     for k in upute.split("|") if k.strip())

    redovi = ""
    if iznos:
        redovi += '<div class="r"><span>Iznos</span><b>%s</b></div>' % iznos
    if rok and otvorena:
        redovi += '<div class="r"><span>Rok prijave</span><b>%s</b></div>' % rok
    if uvjeti:
        redovi += ('<div class="r"><span>Tko se može prijaviti</span>'
                   '<b>%s</b></div>' % uvjeti)

    upute_html = ""
    if koraci and otvorena:
        upute_html = ('<details><summary>Kako se prijaviti</summary>'
                      '<ol>%s</ol></details>' % koraci)

    if otvorena:
        oznaka = '<span class="o ok">Otvoreno za prijave</span>'
        klasa = "k ok"
    else:
        oznaka = '<span class="o zat">Trenutno zatvoreno</span>'
        klasa = "k zat"

    return ('<article class="%s" data-podrucje="%s" data-zupanija="%s">'
            '<div class="zag"><h3>%s</h3>%s</div>'
            '<div class="kat">%s &middot; %s</div>'
            '%s%s'
            '<a class="izv" href="%s" target="_blank" rel="noopener">'
            'Otvori službenu stranicu &rarr;</a></article>') % (
        klasa, esc(podrucje), esc(zupanija), naziv, oznaka,
        esc(podrucje), kat, redovi, upute_html, url)


def izbornik(zup_od):
    """Gradi stavke izbornika: gradovi grupirani pod svoje zupanije."""
    grupe, samostalne = {}, []
    for p, z in sorted(zup_od.items()):
        if "županija" in p:
            grupe.setdefault(p, [])
        elif z:
            grupe.setdefault(z, []).append(p)
        else:
            samostalne.append(p)

    def kv(vrijednost, tekst, uvuceno=False):
        kl = " uvuceno" if uvuceno else ""
        return ('<label class="stavka%s"><input type="checkbox" value="%s">'
                '<span>%s</span></label>' % (kl, esc(vrijednost), esc(tekst)))

    out = ""
    for p in samostalne:
        out += kv(p, p)
    for z in sorted(grupe):
        out += '<div class="grupa-nasl">%s</div>' % esc(z)
        if z in zup_od:
            out += kv(z, "Cijela županija", True)
        for g in sorted(grupe[z]):
            out += kv(g, g, True)
    return out


VODIC = """<section class="vodic">
  <h2>Kako do stipendije</h2>
  <p class="pod">Ako prvi put tražiš stipendiju, ovo je ono što ti nitko ne kaže unaprijed.</p>

  <details>
    <summary>Kada se natječaji objavljuju</summary>
    <p>Većina natječaja otvara se <strong>od rujna do prosinca</strong>, za akademsku
    godinu koja je već počela. Rokovi su često kratki &mdash; nerijetko 15 dana od objave.</p>
    <p>Manji dio programa ide drugim ritmom: neki se objavljuju u <strong>svibnju
    i lipnju</strong>, prema kraju ljetnog semestra. Zato vrijedi provjeravati
    i izvan jeseni.</p>
  </details>

  <details>
    <summary>Ne možeš primati dvije javne stipendije istovremeno</summary>
    <p>Kod državnih stipendija vrijedi pravilo da za vrijeme primanja državne stipendije
    student ne može primati drugu stipendiju financiranu iz javnih izvora. Slično
    ograničenje traže i mnogi gradovi i županije &mdash; obično moraš potpisati izjavu
    da ne primaš drugu stipendiju.</p>
    <p>Praktično: ako se prijavljuješ na više njih, provjeri u tekstu svakog natječaja
    što se smije kombinirati.</p>
  </details>

  <details>
    <summary>Što znači &bdquo;deficitarno zanimanje&ldquo;</summary>
    <p>Zanimanja za kojima postoji manjak kadra. Ako studiraš nešto s tog popisa,
    često imaš <strong>veće šanse i veći iznos</strong> &mdash; ponegdje su i pragovi
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
    stvari. Možeš studirati u Zagrebu i primati stipendiju svog rodnog grada &mdash; kod
    nekih gradova iznos je čak <strong>veći</strong> ako studiraš izvan njih.</p>
  </details>

  <details>
    <summary>Što je SOM aplikacija</summary>
    <p>Više gradova i županija prijave prima preko vanjske aplikacije
    &bdquo;SOM natječaji&ldquo;. Trebaš napraviti korisnički račun, pa se kroz njega
    prijaviti na natječaj.</p>
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
    <p>Također provjeri <em>način</em> predaje &mdash; neki primaju samo elektronički,
    neki samo poštom ili osobno u pisarnici. Prijava poslana na pogrešan način
    tretira se kao da nije poslana.</p>
  </details>
</section>"""


CSS = """*{box-sizing:border-box}
body{margin:0;font-family:-apple-system,"Segoe UI",Roboto,sans-serif;
background:#f5f6f8;color:#1a1d21;line-height:1.55}
.w{max-width:820px;margin:0 auto;padding:2rem 1rem 4rem}
header h1{font-size:1.9rem;margin:0 0 .3rem}
header p{margin:0;color:#5a6270}
.upoz{background:#fff8e6;border:1px solid #f0d99b;border-radius:8px;
padding:.9rem 1rem;margin:1.5rem 0;font-size:.88rem;color:#5c4a1a}
.filteri{margin:1.5rem 0 .5rem;position:relative;display:flex;
gap:.5rem;align-items:center;flex-wrap:wrap}
.otvori{background:#fff;border:1px solid #d5dae0;border-radius:8px;
padding:.6rem .9rem;font-size:.92rem;font-family:inherit;color:#1a1d21;
cursor:pointer;display:flex;align-items:center;gap:.6rem;min-width:240px;
justify-content:space-between;text-align:left}
.otvori:hover{border-color:#9aa4b0}
.otvori[aria-expanded="true"]{border-color:#1a1d21}
.strelica{color:#8a919c;font-size:.8rem}
.ocisti{background:none;border:none;color:#1558d6;font-size:.85rem;
cursor:pointer;font-family:inherit;padding:.4rem}
.ocisti:hover{text-decoration:underline}
.panel{position:absolute;top:100%;left:0;z-index:20;margin-top:.4rem;
background:#fff;border:1px solid #d5dae0;border-radius:10px;
box-shadow:0 8px 24px rgba(0,0,0,.12);width:min(430px,100%);
max-height:min(60vh,430px);overflow-y:auto}
.napomena{margin:0;padding:.85rem 1rem;font-size:.8rem;color:#6b7280;
border-bottom:1px solid #eef0f3;line-height:1.45}
.stavke{padding:.4rem 0 .6rem}
.grupa-nasl{font-size:.74rem;color:#8a919c;text-transform:uppercase;
letter-spacing:.04em;padding:.7rem 1rem .25rem;font-weight:600}
.stavka{display:flex;align-items:center;gap:.6rem;padding:.42rem 1rem;
font-size:.9rem;cursor:pointer}
.stavka:hover{background:#f5f6f8}
.stavka.uvuceno{padding-left:1.6rem}
.stavka input{width:16px;height:16px;accent-color:#1a1d21;cursor:pointer;
flex-shrink:0;margin:0}
h2{font-size:1.15rem;margin:2.5rem 0 .3rem;display:flex;align-items:center;gap:.6rem}
.br{background:#e3e6ea;color:#4a5260;font-size:.8rem;padding:.1rem .55rem;
border-radius:20px;font-weight:600}
.pod{margin:.2rem 0 1.2rem;color:#6b7280;font-size:.88rem}
.prazno{background:#fff;border:1px solid #e3e6ea;border-radius:10px;
padding:1.3rem;margin-top:1rem}
.prazno p{margin:.4rem 0;font-size:.93rem}
.k{background:#fff;border:1px solid #e3e6ea;border-radius:10px;
padding:1.1rem 1.2rem;margin-bottom:.9rem;border-left:4px solid #cbd2d9}
.k.ok{border-left-color:#1a9c4a}
.k.zat{opacity:.72}
.k.skriveno{display:none}
.nema-rez{display:none;background:#fff;border:1px solid #e3e6ea;
border-radius:10px;padding:1.1rem 1.2rem;color:#6b7280;font-size:.9rem;margin:0}
.nema-rez.vidljivo{display:block}
.zag{display:flex;justify-content:space-between;align-items:flex-start;
gap:.8rem;flex-wrap:wrap}
h3{font-size:1rem;margin:0 0 .2rem;flex:1;min-width:200px}
.o{font-size:.72rem;padding:.22rem .6rem;border-radius:20px;
font-weight:600;white-space:nowrap}
.o.ok{background:#d8f3e2;color:#0d6b32}
.o.zat{background:#eceef1;color:#5a6270}
.kat{font-size:.75rem;color:#8a919c;margin-bottom:.6rem}
.r{display:grid;grid-template-columns:150px 1fr;gap:.3rem .8rem;
font-size:.89rem;padding:.22rem 0}
.r span{color:#6b7280}
.r b{font-weight:500}
details{margin-top:.7rem;font-size:.88rem}
summary{cursor:pointer;color:#1558d6;font-weight:500}
details ol{margin:.6rem 0 0;padding-left:1.3rem;color:#3d4450}
details li{margin-bottom:.35rem}
.izv{display:inline-block;margin-top:.8rem;color:#1558d6;
text-decoration:none;font-size:.88rem;font-weight:500}
.izv:hover{text-decoration:underline}
.vodic{margin-top:3.5rem;background:#fff;border:1px solid #e3e6ea;
border-radius:10px;padding:1.4rem}
.vodic h2{margin:0 0 .2rem}
.vodic details{border-top:1px solid #eef0f3;padding:.75rem 0 .3rem;margin:0}
.vodic details:first-of-type{border-top:none}
.vodic summary{color:#1a1d21;font-weight:600;font-size:.94rem}
.vodic details p{font-size:.89rem;color:#3d4450;margin:.6rem 0}
.vodic details ul{font-size:.89rem;color:#3d4450;padding-left:1.3rem;margin:.6rem 0}
.vodic details li{margin-bottom:.3rem}
footer{margin-top:3rem;padding-top:1.5rem;border-top:1px solid #e3e6ea;
font-size:.86rem;color:#4a5260}
footer p{margin:.6rem 0}
footer a{color:#1558d6}
footer .meta{font-size:.78rem;color:#8a919c;margin-top:1.2rem}
@media(max-width:520px){.r{grid-template-columns:1fr}.r span{font-size:.8rem}
.otvori{min-width:100%}.panel{width:100%}}"""


JS = """(function () {
  var SVI = "Cijela Hrvatska";
  var ZUP_OD = __ZUP_OD__;   // grad -> zupanija kojoj pripada
  var panel = document.getElementById("panel");
  var otvori = document.getElementById("otvori");
  var oznaka = document.getElementById("oznaka");
  var ocisti = document.getElementById("ocisti");
  var polja = panel.querySelectorAll("input[type=checkbox]");
  var kartice = document.querySelectorAll(".k");

  function odabrano() {
    var v = [];
    polja.forEach(function (p) { if (p.checked) v.push(p.value); });
    return v;
  }

  function prosiri(sel) {
    // ako je odabran grad, ukljuci i njegovu zupaniju
    var out = sel.slice();
    sel.forEach(function (s) {
      var z = ZUP_OD[s];
      if (z && out.indexOf(z) === -1) out.push(z);
    });
    return out;
  }

  function osvjezi() {
    var izvorni = odabrano();
    var sel = prosiri(izvorni);

    if (izvorni.length === 0) {
      oznaka.textContent = "Sva podru\\u010dja";
      ocisti.hidden = true;
    } else if (izvorni.length === 1) {
      oznaka.textContent = izvorni[0];
      ocisti.hidden = false;
    } else {
      oznaka.textContent = izvorni.length + " odabrano";
      ocisti.hidden = false;
    }

    kartice.forEach(function (k) {
      var p = k.getAttribute("data-podrucje");
      var z = k.getAttribute("data-zupanija") || "";
      var pokazi;
      if (izvorni.length === 0) {
        pokazi = true;
      } else {
        pokazi = (p === SVI) || sel.indexOf(p) !== -1 ||
                 (z !== "" && sel.indexOf(z) !== -1);
      }
      k.classList.toggle("skriveno", !pokazi);
    });

    document.querySelectorAll(".grupa").forEach(function (g) {
      var ima = g.querySelectorAll(".k:not(.skriveno)").length > 0;
      var poruka = g.querySelector(".nema-rez");
      if (poruka) poruka.classList.toggle("vidljivo", !ima);
    });
  }

  otvori.addEventListener("click", function (e) {
    e.stopPropagation();
    var otv = panel.hidden;
    panel.hidden = !otv;
    otvori.setAttribute("aria-expanded", otv ? "true" : "false");
  });

  panel.addEventListener("click", function (e) { e.stopPropagation(); });

  document.addEventListener("click", function () {
    panel.hidden = true;
    otvori.setAttribute("aria-expanded", "false");
  });

  polja.forEach(function (p) { p.addEventListener("change", osvjezi); });

  ocisti.addEventListener("click", function (e) {
    e.stopPropagation();
    polja.forEach(function (p) { p.checked = false; });
    osvjezi();
  });

  osvjezi();
})();"""


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

    otvorene.sort(key=lambda t: t[0].get("naziv") or "")
    zatvorene.sort(key=lambda t: t[0].get("naziv") or "")

    zup_od = {}
    for _, p, z in otvorene + zatvorene:
        if p != SVI:
            zup_od.setdefault(p, z)
    stavke = izbornik(zup_od)

    # mapa grad -> zupanija za JS (samo gradovi, ne same zupanije)
    mapa = {p: z for p, z in zup_od.items() if z and z != p}
    js = JS.replace("__ZUP_OD__", json.dumps(mapa, ensure_ascii=False))

    if otvorene:
        sek_otv = ('<h2>Trenutno otvoreno <span class="br">%d</span></h2>'
                   '<div class="grupa">%s'
                   '<p class="nema-rez">Nema otvorenih natječaja za odabrano '
                   'područje.</p></div>') % (
            len(otvorene), "".join(kartica(r, True, p, z) for r, p, z in otvorene))
    else:
        sek_otv = """<h2>Trenutno otvoreno</h2>
<div class="prazno">
  <p><strong>Trenutno nema otvorenih natječaja.</strong></p>
  <p>Većina natječaja objavljuje se od rujna do prosinca. Ispod su izvori koje
     pratimo &mdash; kad se neki otvori, pojavit će se ovdje.</p>
</div>"""

    sek_zat = ""
    if zatvorene:
        sek_zat = ('<h2>Izvori koje pratimo <span class="br">%d</span></h2>'
                   '<p class="pod">Ovi natječaji trenutno nisu otvoreni. '
                   'Provjeravamo ih automatski dvaput tjedno.</p>'
                   '<div class="grupa">%s'
                   '<p class="nema-rez">Nema izvora za odabrano područje.</p>'
                   '</div>') % (
            len(zatvorene), "".join(kartica(r, False, p, z) for r, p, z in zatvorene))

    html = """<!DOCTYPE html>
<html lang="hr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>stipendije.hr &mdash; stipendije u Hrvatskoj na jednom mjestu</title>
<meta name="description" content="Pregled aktivnih natječaja za stipendije u Hrvatskoj — iznosi, rokovi i upute za prijavu.">
<meta property="og:title" content="stipendije.hr">
<meta property="og:description" content="Aktivni natječaji za stipendije u Hrvatskoj na jednom mjestu.">
<meta property="og:type" content="website">
<style>
%s
</style>
</head>
<body>
<div class="w">
<header>
  <h1>stipendije.hr</h1>
  <p>Stipendije u Hrvatskoj na jednom mjestu &mdash; iznosi, rokovi i upute za prijavu.</p>
</header>

<div class="upoz">
  <strong>Važno:</strong> podaci se prikupljaju automatski i služe isključivo
  kao informacija. Rokovi i uvjeti mogu se promijeniti, a moguće su i greške u
  prikupljanju. <strong>Prije prijave uvijek provjerite službenu stranicu</strong>
  koja je linkana uz svaki natječaj. Ne odgovaramo za propuštene rokove ni za
  odluke donesene na temelju ovih podataka.
</div>

<div class="filteri">
  <button class="otvori" id="otvori" aria-expanded="false">
    <span id="oznaka">Sva područja</span>
    <span class="strelica">&#9662;</span>
  </button>
  <button class="ocisti" id="ocisti" hidden>Očisti</button>
  <div class="panel" id="panel" hidden>
    <p class="napomena">Odaberi svoj grad ili županiju &mdash; možeš označiti više njih.
       Državne stipendije prikazuju se uvijek, a uz grad automatski dobivaš
       i stipendije njegove županije.</p>
    <div class="stavke">%s</div>
  </div>
</div>

%s
%s
%s

<footer>
  <p><strong>Kontakt:</strong> <a href="mailto:%s">%s</a></p>
  <p>Nedostaje neka stipendija, ili si uočio netočan podatak? Piši nam &mdash;
     ispravljamo u najkraćem roku. Posebno nam je važno ako je
     <strong>rok prijave</strong> netočan.</p>
  <p>Ne dajemo osobne savjete o tome imaš li šanse za pojedinu stipendiju &mdash;
     za to se obrati instituciji koja je natječaj objavila.</p>
  <p class="meta">Zadnja provjera: %s &middot; Pratimo %d izvora,
     popis se stalno dopunjuje.</p>
</footer>
</div>

<script>
%s
</script>
</body>
</html>""" % (CSS, stavke, sek_otv, sek_zat, VODIC, EMAIL, EMAIL,
              datetime.now().strftime("%d.%m.%Y. u %H:%M"),
              len(otvorene) + len(zatvorene), js)

    os.makedirs(IZLAZ_MAPA, exist_ok=True)
    open(IZLAZ, "w", encoding="utf-8").write(html)

    print("Napisano %s" % IZLAZ)
    print("  otvorenih: %d  zatvorenih: %d" % (len(otvorene), len(zatvorene)))
    print("  sakriveno: %d" % (len(d) - len(otvorene) - len(zatvorene)))
    print("  izbornik: %d podrucja" % len(zup_od))


if __name__ == "__main__":
    main()
