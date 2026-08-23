# -*- coding: utf-8 -*-
"""Staticne podstranice: vodic, impressum, stranice po zupanijama, sitemap."""
import os
import re
import unicodedata
from datetime import datetime
from zajednicko import glava, navigacija, podnozje, oblik, EMAIL, DOMENA, BAZA


def lokativ(ime):
    """'Varaždinska županija' -> 'Varaždinskoj županiji'; 'Zagreb' -> 'Zagrebu'."""
    if ime.endswith("županija"):
        pridjev = ime[:-len("županija")].strip()
        if pridjev.endswith("a"):
            pridjev = pridjev[:-1] + "oj"
        return f"{pridjev} županiji"
    return ime + "u"


def slug(t):
    """Naziv zupanije -> dio adrese: 'Varazdinska zupanija' -> 'varazdinska'."""
    t = t.replace("županija", "").strip()
    zam = {"Ž":"Z","ž":"z","Š":"S","š":"s","Č":"C","č":"c",
           "Ć":"C","ć":"c","Đ":"D","đ":"d"}
    for a,b in zam.items():
        t = t.replace(a,b)
    t = unicodedata.normalize("NFKD", t).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9]+","-",t.lower()).strip("-")

CSS = """
.tekst{padding:2.6rem 0 0}
.tekst h1{margin-bottom:.6rem}
.lead{font-size:1.02rem;color:var(--tinta-2);max-width:52ch;margin:0 0 2rem}
.q{border-top:1px solid var(--linija);padding:1.15rem 0}
.q:last-of-type{border-bottom:1px solid var(--linija)}
.q h3{margin-bottom:.4rem}
.q p{margin:.5rem 0;font-size:.94rem;color:var(--tinta-2)}
.q ul{margin:.5rem 0;padding-left:1.2rem;font-size:.94rem;color:var(--tinta-2)}
.q li{margin-bottom:.3rem}
.q strong{color:var(--tinta)}
@media(max-width:600px){
  .tekst{padding:2rem 0 0}
  .lead{font-size:.97rem;margin-bottom:1.5rem}
  .q{padding:.9rem 0}
  .q h3{font-size:1rem;line-height:1.3}
  .q summary{padding:.3rem 0}
  .q p,.q ul{font-size:.91rem}
}

"""

PITANJA = [
 ("Kada se natječaji objavljuju",
  ["<p>Većina se otvara <strong>između rujna i prosinca</strong>, za akademsku godinu "
   "koja je već počela. Rokovi su kratki — nerijetko 15 dana od objave.</p>",
   "<p>Dio programa ide drugim ritmom: neki se objavljuju u svibnju i lipnju, "
   "a poneki i u siječnju. Zato provjeravaj i izvan jeseni.</p>"]),
 ("Ne možeš primati dvije javne stipendije odjednom",
  ["<p>Dok primaš državnu stipendiju, ne smiješ primati nijednu drugu koja se "
   "financira iz javnih izvora. Slično ograničenje traže i mnogi gradovi i "
   "županije — obično potpisuješ izjavu da ne primaš drugu stipendiju.</p>",
   "<p>Prijaviš li se na više natječaja, u svakome pročitaj što se smije kombinirati.</p>"]),
 ("Što znači „deficitarno zanimanje”",
  ["<p>Zanimanja za kojima postoji manjak kadra. Ako studiraš nešto s tog popisa, "
   "često imaš <strong>veće šanse i veći iznos</strong>, a ponegdje se traži i "
   "niži prosjek ocjena.</p>",
   "<p>Popis nije jedinstven — svaki grad i županija utvrđuje svoj prema lokalnom "
   "tržištu rada, i uvijek je priložen natječaju. Neki gradovi objavljuju i obrnut "
   "popis — zanimanja koja te godine <strong>neće</strong> stipendirati.</p>"]),
 ("Prebivalište je najčešći uvjet",
  ["<p>Gradske i županijske stipendije gotovo uvijek traže prijavljeno prebivalište "
   "na njihovu području, i to određeno vrijeme unaprijed — negdje šest mjeseci, "
   "negdje dvije godine prije objave natječaja.</p>",
   "<p>Mjesto <em>studiranja</em> i mjesto <em>prebivališta</em> nije isto. Možeš "
   "studirati u Zagrebu i primati stipendiju rodnog grada — kod mnogih gradova iznos "
   "je čak <strong>veći</strong> ako studiraš izvan njih.</p>"]),
 ("Ne mogu se svi prijaviti na sve",
  ["<p>Česta ograničenja koja se lako previde:</p>",
   "<ul><li>neki gradovi primaju samo studente <strong>druge i viših godina</strong></li>"
   "<li>negdje je uvjet minimalan broj ECTS bodova iz prethodne godine</li>"
   "<li>negdje postoji gornja dobna granica</li>"
   "<li>negdje se iz jedne obitelji stipendira samo jedna osoba</li></ul>"]),
 ("Što je SOM aplikacija",
  ["<p>Više gradova i županija prijave prima preko vanjske aplikacije "
   "„SOM natječaji”. Napraviš korisnički račun i kroz njega se prijaviš.</p>",
   "<p>Račun izrađuješ jednom i vrijedi za sve institucije koje taj sustav koriste. "
   "Nakon prijave u sustavu odabereš instituciju čiji natječaj tražiš.</p>"]),
 ("Dokumentacija koju treba pripremiti",
  ["<p>Razlikuje se po natječaju, ali ovo se traži najčešće:</p>",
   "<ul><li>potvrda o upisu na studij</li><li>prijepis ocjena ili potvrda o prosjeku</li>"
   "<li>uvjerenje o prebivalištu (često ne starije od tri mjeseca)</li>"
   "<li>izjava da ne primaš drugu stipendiju</li>"
   "<li>dokazi o postignućima, ako se boduju</li>"
   "<li>za socijalne kategorije: potvrde o prihodima kućanstva</li></ul>",
   "<p>Na neke potvrde čeka se danima. Ako znaš da ti se natječaj otvara u "
   "listopadu, pripremi ih ranije.</p>"]),
 ("Nepotpuna prijava je odbijena prijava",
  ["<p>Gotovo svi natječaji pišu da se nepotpune prijave i one predane nakon roka "
   "<strong>ne razmatraju</strong>. Nema naknadnog dopunjavanja.</p>",
   "<p>Provjeri i <em>način</em> predaje — neki primaju samo elektronički, neki samo "
   "poštom ili osobno u pisarnici. Prijava poslana krivim putem tretira se kao "
   "da nije poslana.</p>"]),
]


def vodic(mapa, broj, vrijeme):
    q = "".join(f'<div class="q"><h3>{n}</h3>{"".join(t)}</div>' for n, t in PITANJA)
    html = glava("Kako do stipendije — stipendije.hr",
                 "Rokovi, uvjeti i dokumentacija: što treba znati prije prijave "
                 "na natječaj za stipendiju u Hrvatskoj.", CSS)
    html += navigacija("vodic")
    html += f"""<main class="w"><section class="tekst">
<h1>Kako do stipendije</h1>
<p class="lead">Prijavljuješ li se prvi put, ovdje je ono što u natječajima piše
sitno, a odlučuje hoće li tvoja prijava proći.</p>
{q}
</section></main>"""
    html += podnozje(broj, vrijeme)
    open(os.path.join(mapa, "vodic.html"), "w", encoding="utf-8").write(html)


def impressum(mapa, broj, vrijeme):
    html = glava("Impressum — stipendije.hr",
                 "Podaci o pružatelju usluge i uvjeti korištenja stranice "
                 "stipendije.hr.", CSS)
    html += navigacija("")
    html += f"""<main class="w"><section class="tekst">
<h1>Impressum</h1>
<p class="lead">Podaci o pružatelju usluge i uvjetima pod kojima se
podaci na ovoj stranici objavljuju.</p>

<div class="q"><h3>O stranici</h3>
<p>stipendije.hr je privatan i nekomercijalan projekt. Stranica je besplatna,
nema oglasa i ne naplaćuje ništa.</p>
<p>Za sva pitanja, prijave grešaka i prijedloge javi se na adresu
u podnožju stranice.</p></div>

<div class="q"><h3>Odakle podaci</h3>
<p>Podatke o natječajima automatski prikupljamo sa službenih stranica institucija
koje stipendije dodjeljuju — gradova, županija, ministarstava, sveučilišta,
zaklada i tvrtki. Uz svaki unos stoji poveznica na izvorni natječaj.</p>
<p>Provjera se pokreće automatski dvaput tjedno. Prikazani podaci odgovaraju
onome što je u trenutku provjere pisalo na izvornoj stranici.</p></div>

<div class="q"><h3>Ograničenje odgovornosti</h3>
<p>Podaci su informativni. Rokovi, iznosi i uvjeti mogu se promijeniti nakon naše
zadnje provjere, a moguće su i greške u automatskom prikupljanju.</p>
<p><strong>Mjerodavan je isključivo tekst natječaja na stranici institucije koja ga
je objavila.</strong> Ne odgovaramo za propuštene rokove, odbijene prijave ni druge
posljedice odluka donesenih na temelju podataka s ove stranice.</p></div>

<div class="q"><h3>Prijava greške</h3>
<p>Uočiš li netočan podatak, javi nam. Netočne rokove ispravljamo prve, jer
su jedina greška koja nekome može oduzeti priliku.</p></div>

<div class="q"><h3>Autorska prava</h3>
<p>Tekstovi natječaja pripadaju institucijama koje su ih objavile. Ova stranica
prikazuje sažetke i poveznice na izvore.</p></div>
</section></main>"""
    html += podnozje(broj, vrijeme)
    open(os.path.join(mapa, "impressum.html"), "w", encoding="utf-8").write(html)


CSS_ZUP = """
.zag-zup{padding:2.4rem 0 0}
.natrag{display:inline-block;font-size:.85rem;color:var(--tinta-2);
  text-decoration:none;margin-bottom:1rem}
.natrag:hover{color:var(--otvoreno)}
.zag-zup h1{font-size:clamp(1.6rem,4.6vw,2.2rem);margin-bottom:.5rem}
.sazetak{font-size:1rem;color:var(--tinta-2);max-width:52ch;margin:0 0 1.6rem}
.brojke{display:flex;gap:1.6rem;flex-wrap:wrap;padding:.9rem 0 0;
  border-top:1px solid var(--linija);margin-bottom:2rem}
.brojka b{display:block;font-family:"IBM Plex Mono",monospace;
  font-size:1.5rem;line-height:1.1}
.brojka span{font-size:.78rem;color:var(--tinta-2)}
.druge{margin-top:3rem;padding-top:1.4rem;border-top:1px solid var(--linija)}
.druge h2{font-size:1rem;margin-bottom:.7rem}
.popis-zup{display:flex;flex-wrap:wrap;gap:.4rem}
.popis-zup a{font-size:.85rem;color:var(--tinta);text-decoration:none;
  border:1px solid var(--linija);background:var(--karta);padding:.35rem .7rem}
.popis-zup a:hover{border-color:var(--otvoreno);color:var(--otvoreno)}
@media(max-width:600px){.zag-zup{padding:1.8rem 0 0}.sazetak{font-size:.95rem}}
"""


def stranica_zupanije(mapa, ime, kartice_html, br_otv, br_uk,
                      sve_zupanije, broj_izvora, vrijeme,
                      popis_za_json=()):
    """Zasebna stranica po zupaniji — da Google ima sto indeksirati."""
    sl = slug(ime)
    os.makedirs(os.path.join(mapa, "zupanija"), exist_ok=True)

    lok = lokativ(ime)
    god = datetime.now().year
    naslov = f"Stipendije u {lok} {god}. — otvoreni natječaji | stipendije.hr"
    opis = (f"Svi natječaji za stipendije u {lok}: iznosi, rokovi prijave "
            f"i upute za prijavu. Izvore provjeravamo dvaput tjedno.")

    if br_otv:
        uvod = (f"Trenutno {oblik(br_otv,'je otvoren','su otvorena','je otvoreno')} "
                f"{br_otv} {oblik(br_otv,'natječaj','natječaja','natječaja')} "
                f"za stipendije u {lok}.")
    else:
        uvod = (f"Trenutno nema otvorenih natječaja u {lok}. "
                f"Većina se objavljuje između rujna i prosinca — pratimo ih "
                f"automatski i pojavit će se ovdje čim se otvore.")

    druge = "".join(
        f'<a href="{slug(z)}.html">{z.replace(" županija","")}</a>'
        for z in sorted(sve_zupanije) if z != ime)

    # strukturirani podaci: Googleu govore da je ovo popis natjecaja
    import json as _json
    stavke = []
    for i, (n, u) in enumerate(popis_za_json, 1):
        stavke.append({"@type": "ListItem", "position": i,
                       "name": n, "url": u})
    ld = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": naslov.split(" |")[0],
        "description": opis,
        "inLanguage": "hr-HR",
        "url": f"{BAZA}/zupanija/{sl}.html",
        "isPartOf": {"@type": "WebSite", "name": "stipendije.hr",
                     "url": f"{BAZA}/"},
        "mainEntity": {"@type": "ItemList", "numberOfItems": len(stavke),
                       "itemListElement": stavke},
    }
    glava_extra = ('<script type="application/ld+json">'
                   + _json.dumps(ld, ensure_ascii=False) + '</script>')

    html = glava(naslov, opis, CSS_ZUP, glava_extra, put="../")
    html += navigacija("natjecaji", put="../")
    html += f"""<main class="w"><section class="zag-zup">
  <a class="natrag" href="../">&larr; Sve stipendije u Hrvatskoj</a>
  <h1>Stipendije u {lok}</h1>
  <p class="sazetak">{uvod}</p>
  <div class="brojke">
    <div class="brojka"><b>{br_otv}</b><span>otvoreno sada</span></div>
    <div class="brojka"><b>{br_uk}</b><span>{oblik(br_uk,'izvor','izvora','izvora')} koje pratimo</span></div>
  </div>
  {kartice_html}
  <div class="druge">
    <h2>Ostale županije</h2>
    <div class="popis-zup">{druge}</div>
  </div>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme, put="../")
    open(os.path.join(mapa, "zupanija", f"{sl}.html"), "w",
         encoding="utf-8").write(html)
    return f"zupanija/{sl}.html"


def sitemap(mapa, putevi):
    """sitemap.xml + robots.txt"""
    danas = datetime.now().strftime("%Y-%m-%d")
    unosi = ""
    for p, prio in putevi:
        adresa = f"{BAZA}/{p}" if p else f"{BAZA}/"
        unosi += (f"  <url><loc>{adresa}</loc><lastmod>{danas}</lastmod>"
                  f"<changefreq>weekly</changefreq>"
                  f"<priority>{prio}</priority></url>\n")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           f"{unosi}</urlset>\n")
    open(os.path.join(mapa, "sitemap.xml"), "w", encoding="utf-8").write(xml)

    open(os.path.join(mapa, "robots.txt"), "w", encoding="utf-8").write(
        f"User-agent: *\nAllow: /\n\nSitemap: {BAZA}/sitemap.xml\n")


def privatnost(mapa, broj, vrijeme):
    from zajednicko import GA_ID
    ga_dio = ""
    if GA_ID:
        ga_dio = """
<div class="q"><h3>Google Analytics</h3>
<p>Ako pristaneš, koristimo Google Analytics kako bismo vidjeli koliko ljudi
posjećuje stranicu, s kojih uređaja dolaze i koje stranice gledaju. To nam
pomaže da znamo koje županije treba bolje pokriti.</p>
<p>Google Analytics postavlja kolačiće na tvoj uređaj i podatke obrađuje Google.
Postavili smo ga tako da se <strong>IP adresa skraćuje</strong>, pa se ne bilježi
u punom obliku.</p>
<p><strong>Ako odbiješ, ne postavlja se nijedan kolačić</strong> i mjerenje se
ne pokreće. Stranica radi jednako u oba slučaja.</p></div>

<div class="q"><h3>Kako promijeniti odluku</h3>
<p>Tvoj odabir sprema se lokalno u pregledniku. Ako ga želiš promijeniti,
obriši podatke stranice u postavkama preglednika — traka s pitanjem
pojavit će se ponovno pri sljedećem posjetu.</p></div>
"""

    html = glava("Privatnost — stipendije.hr",
                 "Koje podatke prikuplja stipendije.hr i kako se koriste.", CSS)
    html += navigacija("")
    html += f"""<main class="w"><section class="tekst">
<h1>Privatnost</h1>
<p class="lead">Kratko i bez pravničkog jezika: što se bilježi kad posjetiš
ovu stranicu.</p>

<div class="q"><h3>Ne tražimo nikakve podatke</h3>
<p>Stranica nema registraciju, prijavu ni obrasce. Ne tražimo ime, e-poštu
ni bilo što drugo. Ako nam pišeš na e-poštu, tvoju poruku vidimo samo mi
i ne koristimo je ni za što drugo osim odgovora.</p></div>
{ga_dio}
<div class="q"><h3>Poslužitelj</h3>
<p>Stranicu poslužuje GitHub Pages. Kao i svaki poslužitelj na internetu,
GitHub bilježi tehničke podatke o zahtjevima. Na to nemamo utjecaja i te
podatke ne vidimo.</p></div>

<div class="q"><h3>Vanjske poveznice</h3>
<p>Svaki natječaj vodi na stranicu institucije koja ga je objavila. Kad
klikneš takvu poveznicu, vrijede pravila privatnosti te stranice, ne naša.</p></div>

<div class="q"><h3>Fontovi</h3>
<p>Stranica učitava pisma s Google Fontsa, pri čemu se tvoja IP adresa
prosljeđuje Googleu. To je tehnički nužno za prikaz pisama.</p></div>

<div class="q"><h3>Pitanja</h3>
<p>Za sve o privatnosti javi se na adresu u podnožju stranice.</p></div>
</section></main>"""
    html += podnozje(broj, vrijeme)
    open(os.path.join(mapa, "privatnost.html"), "w", encoding="utf-8").write(html)
