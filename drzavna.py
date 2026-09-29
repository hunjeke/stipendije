# -*- coding: utf-8 -*-
"""
Stranica o drzavnoj stipendiji — najveci natjecaj u godini.

Postoji zbog jednog dana: kad ministarstvo objavi natjecaj, desetci tisuca
studenata isti tjedan traze isto. Google tada ne stigne indeksirati novu
stranicu, pa ova mora stajati tjednima ranije i cekati ih spremna.

Dok natjecaja nema, stranica govori ono sto ljudi ionako traze u rujnu —
kad krecu prijave, koliko iznosi, sto pripremiti — i nudi im kanal da ih se
obavijesti. Kad natjecaj izade, mijenja se samo blok sa stanjem.

Svi podaci ovdje su prepisani s ministarstvovih stranica i iz proslogodisnjeg
natjecaja. Nijedan nije procijenjen. Sve sto se odnosi na prosli natjecaj je
tako i oznaceno, jer ove godine brojke mogu biti druge.
"""
import os

from zajednicko import glava, navigacija, podnozje

# --- provjereni podaci (izvori su na dnu stranice) -------------------------
IZNOS = "200 €"
RATA = 9
UKUPNO = "1.800 €"
BROJ_STIPENDIJA = "12.150"
STEM_NASTAVNICKI = "600 €"
STEM_OSTALI = "300 €"
SUSTAV = "https://vidra.srce.hr/"
MZO_SOCIO = ("https://mzom.gov.hr/istaknute-teme/odgoj-i-obrazovanje/"
             "visoko-obrazovanje/drzavne-stipendije/drzavne-stipendije-za-"
             "studente-nizega-socio-ekonomskoga-statusa/1563")
MZO_STEM = "https://mzom.gov.hr/drzavne-stipendije-za-studente-u-stem-podrucjima-znanosti/1562"
MZO_NATJECAJ = ("https://mzom.gov.hr/istaknute-teme/natjecaji-196/natjecaj-za-"
                "dodjelu-12-150-drzavnih-stipendija-za-akademsku-godinu-2025-"
                "2026-studentima-u-redovitom-statusu-koji-studiraju-na-visokim-"
                "ucilistima-u-republici-hrvatskoj/7289")

CSS = """
.ds{padding:2.6rem 0 0}
.ds h1{font-size:clamp(1.7rem,5vw,2.4rem);margin-bottom:.6rem}
.ds .lead{font-size:1.04rem;color:var(--tinta-2);max-width:54ch;margin:0 0 1.6rem}
.ds h2{font-size:1.24rem;margin:2.8rem 0 .3rem}
.ds .pod{color:var(--tinta-2);font-size:.92rem;margin:0 0 1.1rem;max-width:56ch}
.ds p{font-size:.96rem;line-height:1.65}

/* stanje natjecaja — jedino sto se mijenja kad natjecaj izade */
.stanje{border:2px solid var(--plava);background:var(--karta);
  padding:1.15rem 1.2rem;display:flex;gap:1rem;align-items:center;
  flex-wrap:wrap;margin-bottom:2rem}
.stanje .txt{flex:1;min-width:16rem}
.stanje b{display:block;font-family:"Bricolage",sans-serif;font-weight:700;
  font-size:1.1rem;letter-spacing:-.012em;margin-bottom:.2rem}
.stanje span{font-size:.9rem;color:var(--tinta-2)}
.stanje a{display:inline-block;background:var(--plava);color:#fff;
  text-decoration:none;font-weight:600;font-size:.92rem;padding:.72rem 1.1rem;
  white-space:nowrap}
.stanje a:hover{filter:brightness(1.12)}

/* brojke */
.cifre{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;
  background:var(--linija);border:1px solid var(--linija);margin:0 0 .6rem}
.cifre div{background:var(--papir);padding:.95rem .9rem}
.cifre b{display:block;font-family:"PlexMono",monospace;font-size:1.32rem;
  font-weight:500;line-height:1.15;color:var(--tinta)}
.cifre span{font-size:.76rem;color:var(--tinta-2)}

/* tko ima pravo */
.tko{display:grid;grid-template-columns:repeat(3,1fr);gap:.8rem}
.tko div{border:1px solid var(--linija);background:var(--karta);padding:1rem}
.tko .ozn{font-family:"PlexMono",monospace;font-size:.68rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--plava);margin-bottom:.35rem}
.tko b{display:block;font-size:.98rem;margin-bottom:.3rem}
.tko p{margin:0;font-size:.88rem;color:var(--tinta-2);line-height:1.55}

/* koraci — okomita traka s brojevima */
.koraci{list-style:none;margin:0;padding:0;position:relative}
.koraci::before{content:"";position:absolute;left:19px;top:22px;bottom:22px;
  width:2px;background:var(--linija)}
.koraci li{position:relative;padding:0 0 1.5rem 3.4rem;min-height:2.6rem}
.koraci li:last-child{padding-bottom:0}
.kbroj{position:absolute;left:0;top:0;width:40px;height:40px;border-radius:50%;
  background:var(--plava);color:#fff;display:flex;align-items:center;
  justify-content:center;font-family:"PlexMono",monospace;font-size:1rem;
  font-weight:500;z-index:1}
.koraci h3{font-size:1.02rem;margin:.35rem 0 .3rem}
.koraci p{margin:0;font-size:.93rem;color:var(--tinta-2);line-height:1.6;
  max-width:56ch}
.koraci p + p{margin-top:.45rem}
.koraci em{font-style:normal;font-weight:500;color:var(--tinta)}
.koraci a{color:var(--tinta);text-decoration:none;
  border-bottom:1.5px solid var(--plava)}
.koraci a:hover{color:var(--plava)}
.upoz{display:inline-block;margin-top:.5rem;background:#FEF3C7;color:#92400E;
  font-size:.85rem;padding:.45rem .7rem;line-height:1.5;max-width:56ch}

/* popis za pripremu */
.spremi{list-style:none;margin:0;padding:0}
.spremi li{display:flex;gap:.7rem;align-items:flex-start;
  border-top:1px solid var(--linija);padding:.8rem 0;font-size:.95rem}
.spremi li:last-child{border-bottom:1px solid var(--linija)}
.spremi svg{flex-shrink:0;margin-top:.15rem}
.spremi small{display:block;color:var(--tinta-2);font-size:.86rem;margin-top:.15rem}

/* gdje se koji papir vadi */
.papiri{display:grid;grid-template-columns:repeat(2,1fr);gap:.8rem;margin-top:1rem}
.papir{border:1px solid var(--linija);background:var(--karta);padding:.95rem 1rem}
.papir h3{font-size:.98rem;margin:0 0 .35rem;line-height:1.35}
.papir .gdje{margin:0 0 .45rem;font-family:"PlexMono",monospace;font-size:.72rem;
  letter-spacing:.03em;color:var(--plava);line-height:1.5}
.papir p{margin:0;font-size:.88rem;color:var(--tinta-2);line-height:1.6}

/* vremenska crta proslogodisnjeg natjecaja */
.crta{display:grid;grid-template-columns:repeat(4,1fr);gap:1px;
  background:var(--linija);border:1px solid var(--linija)}
.crta div{background:var(--papir);padding:.9rem}
.crta b{display:block;font-family:"PlexMono",monospace;font-size:.95rem;
  color:var(--tinta)}
.crta span{font-size:.8rem;color:var(--tinta-2)}

/* izvori */
.izvori{list-style:none;margin:.4rem 0 0;padding:0;font-size:.92rem}
.izvori li{padding:.5rem 0;border-bottom:1px solid var(--linija)}
.izvori a{color:var(--tinta);text-decoration:none;
  border-bottom:1.5px solid var(--plava)}
.izvori a:hover{color:var(--plava)}
.napomena{margin-top:2.4rem;border:1px dashed var(--linija);padding:1rem 1.1rem;
  font-size:.9rem;color:var(--tinta-2);line-height:1.6}

@media(max-width:700px){
  .cifre{grid-template-columns:repeat(2,1fr)}
  .tko{grid-template-columns:1fr}
  .crta{grid-template-columns:1fr}
  .papiri{grid-template-columns:1fr}
}
@media(max-width:600px){
  .ds{padding:1.9rem 0 0}
  .ds h2{font-size:1.1rem;margin-top:2.2rem}
  .stanje{padding:1rem .9rem}
  .stanje a{width:100%;text-align:center}
  .koraci li{padding-left:3rem}
  .koraci::before{left:17px}
  .kbroj{width:36px;height:36px;font-size:.92rem}
}
"""


def _kvacica():
    return ('<svg width="17" height="17" viewBox="0 0 17 17" aria-hidden="true">'
            '<circle cx="8.5" cy="8.5" r="8.5" fill="#DCFCE7"/>'
            '<path d="M4.6 8.8l2.5 2.5 5-5.2" stroke="#15803D" stroke-width="2"'
            ' fill="none" stroke-linecap="round" stroke-linejoin="round"/></svg>')


KORACI = [
    ("Provjeri kako se prijavljuješ — prije nego natječaj izađe",
     ['Na državnim stranicama to zovu <em>vjerodajnicom</em>; to su samo '
      'korisničko ime i lozinka kojima dokazuješ da si to ti.',
      f'Prijava se ne otvara imenom koje sam izmisliš. U sustav se '
      f'ulazi <strong>AAI@EduHr</strong> elektroničkim identitetom (onaj koji '
      f'dobiješ na fakultetu) ili prijavom preko sustava <strong>e-Građani</strong> — onom istom kojom otvaraš e-Poreznu ili e-Zdravstveno.',
      'Ako ti AAI lozinka ne radi ili je nikad nisi aktivirao, to se rješava na '
      'matičnom fakultetu i zna potrajati koji dan.'],
     'Ovo je najčešći razlog zbog kojeg ljudi propuste rok — ne sam natječaj, '
     'nego to što na zadnji dan otkriju da se ne mogu prijaviti u sustav.'),

    ("Otvori sustav VIDRA",
     [f'Prijave idu isključivo preko <a href="{SUSTAV}" target="_blank" '
      f'rel="noopener">vidra.srce.hr</a> — nacionalnog sustava za studentske '
      f'natječaje. Isti sustav vodi i natječaje za smještaj i prijevoz.',
      'Nema papirnate prijave i ništa se ne šalje poštom.'], None),

    ("Ispuni elektronički obrazac",
     ['Velik dio podataka sustav sam dohvaća iz državnih registara čim se '
      'prijaviš, pa ne prepisuješ ono što država već zna o tebi.',
      'Tvoje je da provjeriš je li dohvaćeno točno i dopuniš ostalo.'], None),

    ("Priloži samo ono što sustav nije sam dohvatio",
     ['Prilozi moraju biti <strong>na hrvatskome jeziku</strong> i predaju se '
      'samo elektronički — ništa se ne šalje poštom.',
      'Koji dokumenti trebaju ovisi o tvojim okolnostima, a ne o tome tko si. '
      'Većina studenata ne prilaže gotovo ništa. Popis i gdje se što vadi je '
      '<a href="#papiri">niže na ovoj stranici</a>.'], None),

    ("Rezultati, rang-lista i prihvaćanje",
     ['Bodovi i mjesto na rang-listi vide se u samom sustavu. Kod socio-ekonomske '
      'kategorije na bodove utječu prihodi kućanstva, braća i sestre u školovanju, '
      'život u domu i upis deficitarnog zanimanja.',
      'Ako prođeš, imaš rok da stipendiju prihvatiš i potpišeš ugovor. '
      'Isplata ide mjesečno, do 15. u mjesecu.'],
     'Prihvaćanje ima svoj rok, odvojen od roka prijave. Tko ga prespava, '
     'gubi stipendiju koju je već dobio.'),
]

# Sto sustav dohvaca sam. Ovo je najkorisniji podatak na stranici: ljudi
# krenu skupljati papire koje nitko ne trazi.
SAM_DOHVACA = [
    ("Prihodi kućanstva", "iz EDIP registra Porezne uprave"),
    ("Invaliditet", "iz Registra osoba s invaliditetom"),
    ("Roditeljstvo i razvod", "iz državnih matica"),
    ("Status hrvatskog branitelja", "iz Registra hrvatskih branitelja"),
    ("Školovanje i upis", "iz e-Matica i Informacijskog sustava studentskih prava"),
    ("Mirovinski podaci", "iz registra mirovinskog osiguranja"),
]

# Sto se ipak vadi rukom — i tocno gdje. (naslov, gdje, kako)
PAPIRI = [
    ("Korisničko ime i lozinka za AAI@EduHr",
     "Tvoj fakultet, administrator informacijskog sustava",
     "Ne izdaje se centralno nego na matičnom učilištu — referada zna uputiti "
     "kome. Preuzima se osobno, uz OIB i indeks, a i zaboravljena lozinka se "
     "mijenja osobno. Zato ovo rješavaj tjednima prije, ne na dan prijave."),

    ("Ili prijava preko e-Građana",
     "gov.hr/e-gradjani",
     "Ako se već prijavljuješ mobilnim bankarstvom ili osobnom iskaznicom s "
     "čipom, pristup imaš. To je brži put od AAI-ja ako ti on ne radi."),

    ("Rodni list brata ili sestre",
     "e-Građani, usluga e-Matične knjige",
     "Zatražiš elektronički zapis i stigne ti u korisnički pretinac. Dovoljna je "
     "i najjednostavnija razina prijave. Treba samo ako prijavljuješ "
     "braću ili sestre u školovanju, jer oni nose bodove."),

    ("Potvrda o školovanju brata ili sestre",
     "Škola ili fakultet koji pohađaju",
     "Vadi je osoba na koju glasi, u svojoj referadi ili tajništvu škole. "
     "Traje nekoliko minuta, ali netko mora otići."),

    ("Smrtni list roditelja",
     "Matični ured",
     "Preko e-Građana dostupni su rodni i vjenčani list; smrtni se i dalje vadi "
     "u matičnom uredu, u bilo kojem, ne nužno mjestu rođenja."),

    ("Sudska odluka o razvodu roditelja",
     "Presuda koju roditelji već imaju",
     "Ako je primjerak izgubljen, preslika se traži na sudu koji je donio "
     "presudu. Razvod nosi bodove u socio-ekonomskoj kategoriji."),

    ("Potvrda o skrbništvu ili smještaju",
     "Hrvatski zavod za socijalni rad, područni ured prema prebivalištu",
     "To je ustanova koja je naslijedila centre za socijalnu skrb. Popis "
     "područnih ureda je na socskrb.hr."),

    ("Rješenje o priznatom statusu iz Domovinskog rata",
     "Upravno tijelo koje je status priznalo",
     "Za kategoriju D-1. Traži se ondje gdje je rješenje izvorno izdano — "
     "najčešće u županijskom upravnom odjelu nadležnom za branitelje."),

    ("Potvrda o kategorizaciji sportaša",
     "Hrvatski olimpijski odbor",
     "HOO vodi Registar kategoriziranih sportaša. Ako si u njemu, potvrda nosi "
     "dodatne bodove."),

    ("Potvrda o upisu na doktorski studij",
     "Referada matičnog učilišta",
     "Samo za kategoriju P. Za preddiplomski i diplomski studij upis se dohvaća "
     "automatski, pa potvrdu ne trebaš."),

    ("Potvrda o prihodima ostvarenima u inozemstvu",
     "Porezna uprava te države",
     "Hrvatski registri vide samo prihode u Hrvatskoj. Ako je netko iz kućanstva "
     "radio u inozemstvu, taj se dio dokazuje sam."),
]

VREMENSKA = [
    ("14.10.", "objavljen natječaj, u 12:00"),
    ("4.11.", "istekao rok prijave, u 12:00"),
    ("do 25.10.", "javni poziv za STEM stipendije"),
    ("do 15.", "isplata svakog mjeseca"),
]


def stranica(mapa, broj_izvora, vrijeme):
    """Napise docs/drzavna-stipendija.html."""
    koraci = ""
    for i, (naslov, odlomci, upozorenje) in enumerate(KORACI, 1):
        tijelo = "".join(f"<p>{o}</p>" for o in odlomci)
        if upozorenje:
            tijelo += f'<div class="upoz">{upozorenje}</div>'
        koraci += (f'<li><span class="kbroj">{i}</span>'
                   f'<h3>{naslov}</h3>{tijelo}</li>')

    sam = "".join(
        f'<li>{_kvacica()}<div><strong>{n}</strong><small>{o}</small></div></li>'
        for n, o in SAM_DOHVACA)

    papiri = "".join(
        f'<div class="papir"><h3>{n}</h3>'
        f'<p class="gdje">{g}</p><p>{k}</p></div>'
        for n, g, k in PAPIRI)

    crta = "".join(f'<div><b>{d}</b><span>{o}</span></div>' for d, o in VREMENSKA)

    html = glava(
        "Državna stipendija 2026./2027. — kad kreću prijave, uvjeti i iznos",
        "Kako se prijaviti na državnu stipendiju: korak po korak, što pripremiti, "
        "koliko iznosi i kad se očekuje natječaj. Provjereno na stranicama "
        "Ministarstva znanosti, obrazovanja i mladih.",
        CSS)
    html += navigacija("drzavna")
    html += f"""<main class="w"><section class="ds">
<h1>Državna stipendija</h1>
<p class="lead">Najveći natječaj za stipendije u Hrvatskoj. Prošle akademske
godine dodijeljeno je {BROJ_STIPENDIJA} stipendija po {IZNOS} mjesečno. Ovdje je
kako se prijaviti, korak po korak.</p>

<div class="stanje">
  <div class="txt">
    <b>Natječaj za 2026./2027. još nije objavljen</b>
    <span>Ministar ga po pravilu raspisuje do 15. listopada. Prošle je godine
      izašao 14. listopada. Javimo ti na WhatsAppu istoga dana.</span>
  </div>
  <a href="https://whatsapp.com/channel/0029Vb8yRo75Ui2aMzBAjv1a"
     target="_blank" rel="noopener">Obavijesti me &rarr;</a>
</div>

<div class="cifre">
  <div><b>{IZNOS}</b><span>mjesečno</span></div>
  <div><b>{RATA}</b><span>mjesečnih rata</span></div>
  <div><b>{UKUPNO}</b><span>ukupno po godini</span></div>
  <div><b>{BROJ_STIPENDIJA}</b><span>stipendija lani</span></div>
</div>

<h2>Tko se može prijaviti</h2>
<p class="pod">Redoviti studenti na visokim učilištima u Hrvatskoj. Natječaj ima
tri odvojene kategorije, sa zasebnim rang-listama.</p>
<div class="tko">
  <div>
    <div class="ozn">Kategorija E</div>
    <b>Slabiji socio-ekonomski status</b>
    <p>Prosječni mjesečni prihodi po članu kućanstva ne prelaze 160 %
       proračunske osnovice. Najveća kategorija.</p>
  </div>
  <div>
    <div class="ozn">Kategorija D-1</div>
    <b>Djeca iz Domovinskog rata</b>
    <p>Djeca poginulih, umrlih ili nestalih osoba, te vojni i civilni invalidi
       rata i civilni invalidi iz Domovinskog rata.</p>
  </div>
  <div>
    <div class="ozn">Kategorija P</div>
    <b>Invaliditet i skrbništvo</b>
    <p>Studenti s invaliditetom i oni koji su bili pod skrbništvom ili imaju
       pravo na smještaj — na doktorskim studijima.</p>
  </div>
</div>

<h2>Kako se prijaviti</h2>
<p class="pod">Cijela prijava je elektronička. Ovih pet koraka vrijedi za sve
kategorije.</p>
<ol class="koraci">{koraci}</ol>

<h2 id="papiri">Koje papire trebaš i gdje se vade</h2>
<p class="pod">Prvo dobra vijest: većinu toga ne moraš nigdje vaditi. Čim se
prijaviš, sustav sam povuče podatke iz državnih registara.</p>
<ul class="spremi">{sam}</ul>

<p class="pod" style="margin-top:1.6rem">Rukom se prilaže samo ono što u
registrima ne piše. Za većinu studenata to je malo ili ništa — popis ispod je
redom po tome koliko se često traži.</p>
<div class="papiri">{papiri}</div>

<h2>STEM stipendije su odvojen natječaj</h2>
<p class="pod">Ako studiraš u STEM području, postoji drugi javni poziv, s većim
iznosom i vlastitim rang-listama.</p>
<div class="cifre">
  <div><b>{STEM_NASTAVNICKI}</b><span>mjesečno, nastavnički STEM studiji</span></div>
  <div><b>{STEM_OSTALI}</b><span>mjesečno, ostali STEM studiji</span></div>
  <div><b>{RATA}</b><span>mjesečnih rata</span></div>
  <div><b>do 25.10.</b><span>rok da ministar raspiše poziv</span></div>
</div>

<h2>Kako je išlo prošle godine</h2>
<p class="pod">Datumi iz natječaja za 2025./2026. Ovogodišnji mogu biti drugi,
ali razmaci su obično slični.</p>
<div class="crta">{crta}</div>

<h2>Gdje to piše</h2>
<p class="pod">Sve na ovoj stranici prepisano je s ovih adresa. Prije prijave
provjeri ih sam — vrijedi ono što piše u natječaju, ne ovdje.</p>
<ul class="izvori">
  <li><a href="{MZO_SOCIO}" target="_blank" rel="noopener">Ministarstvo — državne
      stipendije za studente nižega socio-ekonomskog statusa</a></li>
  <li><a href="{MZO_STEM}" target="_blank" rel="noopener">Ministarstvo — državne
      stipendije u STEM područjima</a></li>
  <li><a href="{MZO_NATJECAJ}" target="_blank" rel="noopener">Natječaj za
      2025./2026. — prošlogodišnji tekst s rokovima</a></li>
  <li><a href="{SUSTAV}" target="_blank" rel="noopener">VIDRA — sustav u kojem
      se predaje prijava</a></li>
</ul>

<p class="napomena">Ovu stranicu održavamo ručno, a podatke provjeravamo na
stranicama ministarstva. Dok novi natječaj ne izađe, sve brojke odnose se na
akademsku godinu 2025./2026. i mogu se promijeniti. Ako uočiš da je nešto
zastarjelo, javi nam i ispravit ćemo.</p>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme)
    put = os.path.join(mapa, "drzavna-stipendija.html")
    open(put, "w", encoding="utf-8").write(html)
    return "drzavna-stipendija.html"
