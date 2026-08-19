# -*- coding: utf-8 -*-
"""Staticne podstranice: vodic i impressum."""
import os
from zajednicko import glava, navigacija, podnozje, EMAIL, DOMENA

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
.redak{display:grid;grid-template-columns:11rem 1fr;gap:.3rem 1rem;
  padding:.65rem 0;border-top:1px solid var(--linija);font-size:.93rem}
.redak dt{color:var(--tinta-2)}
.redak dd{margin:0}
.popuni{background:#FBF3D8;padding:.1rem .35rem;
  font-family:"IBM Plex Mono",monospace;font-size:.85rem}
@media(max-width:560px){.redak{grid-template-columns:1fr;gap:.1rem}}
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
    html += navigacija("impressum")
    html += f"""<main class="w"><section class="tekst">
<h1>Impressum</h1>
<p class="lead">Podaci o pružatelju usluge i uvjetima pod kojima se
podaci na ovoj stranici objavljuju.</p>

<h3>Pružatelj usluge</h3>
<dl class="redak">
  <dt>Naziv</dt><dd><span class="popuni">popuniti</span></dd>
  <dt>Sjedište</dt><dd><span class="popuni">popuniti</span></dd>
  <dt>OIB</dt><dd><span class="popuni">popuniti</span></dd>
  <dt>Odgovorna osoba</dt><dd><span class="popuni">popuniti</span></dd>
  <dt>E-pošta</dt><dd><a href="mailto:{EMAIL}">{EMAIL}</a></dd>
</dl>

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
<p>Uočiš li netočan podatak, javi na <a href="mailto:{EMAIL}">{EMAIL}</a>.
Netočne rokove ispravljamo prve.</p></div>

<div class="q"><h3>Autorska prava</h3>
<p>Tekstovi natječaja pripadaju institucijama koje su ih objavile. Ova stranica
prikazuje sažetke i poveznice na izvore.</p></div>
</section></main>"""
    html += podnozje(broj, vrijeme)
    open(os.path.join(mapa, "impressum.html"), "w", encoding="utf-8").write(html)
