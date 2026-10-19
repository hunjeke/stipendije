# -*- coding: utf-8 -*-
"""
stem.py — stranica o drzavnim STEM stipendijama

Zasto zasebna stranica, a ne odlomak unutar drzavne:

Search Console za 22.8.–17.10.2026. pokazuje 3.332 pojavljivanja na upitima
oko "stem stipendije", a samo 240 klikova i prosjecnu poziciju 6,7 do 9,2.
Razlog je jednostavan: STEM je dosad bio odlomak na stranici o
socio-ekonomskoj drzavnoj stipendiji, pa Google na upit o STEM-u mora
ponuditi stranicu koja je o necem drugom. Odlomak ne moze pobijediti
stranicu.

Podaci su provjereni 19.10.2026. na mzom.gov.hr. Tog dana javni poziv za
2026./2027. jos nije bio raspisan — na stranici ministarstva stoji samo
poziv za 2025./2026. i recenica da ga ministar raspisuje do 25. listopada.
Zato je ovo stranica o cekanju, ne popis s rokom: tko sada trazi "stem
stipendije 2026" upravo ceka taj poziv.

VAZNO: "do 25. listopada" je rok DA MINISTAR RASPISE POZIV, a ne rok za
prijavu studenata. Ta se recenica vec jednom procitala kao rok prijave i
na stranici se pojavila stipendija koja ne postoji. Ako ikada budes mijenjao
ovaj tekst, ta razlika mora ostati jasna.

Kad poziv izade: postavi OTVOREN = True, upisi ROK, POVEZNICA i BROJ, pa
pokreni build. Tekst se sam prebaci.
"""
import os

from zajednicko import glava, navigacija, podnozje
from drzavna import (CSS, STEM_NASTAVNICKI, STEM_OSTALI, STEM_BROJ,
                     STEM_IZVADAK, STEM_ODLUKA, SUSTAV, MZO_STEM, _kvacica,
                     izbor)

# --- stanje natjecaja ------------------------------------------------------
# OTVOREN = False -> poziv jos nije raspisan (provjereno 19.10.2026.)
# OTVOREN = True  -> poziv je vani; tada popuni ROK, POVEZNICA i BROJ
OTVOREN = False
ROK = ""
POVEZNICA = ""

RATA = 9
ROK_OBJAVE = "25. listopada"
PROVJERENO = "19. listopada 2026"

# Postoci po kojima se dijeli ono sto ostane nakon nastavnickih studija.
# Iz pravilnika; prepisano, ne procitano strojno.
KVOTE = [
    ("30 %", "prva godina prijediplomskog, integriranog i stručnog kratkog studija"),
    ("40 %", "više godine prijediplomskog i druga godina stručnog kratkog studija"),
    ("10 %", "više godine integriranog prijediplomskog i diplomskog studija"),
    ("10 %", "prva godina diplomskog studija"),
    ("10 %", "druga godina diplomskog studija"),
]

# Sto se moze napraviti dok poziv jos nije vani. Namjerno nije popis
# obaveznih dokumenata — poziv jos nije objavljen, pa bi takav popis bio
# izmisljen. Ovo su provjere koje vrijede bez obzira na tekst poziva.
DOK_CEKAS = [
    ("Provjeri je li tvoj studij na popisu",
     "Odluci sve. „STEM” ovdje nije isto što i tehnički fakultet — vrijedi "
     "službeni Izvadak studijskih programa koji ministarstvo objavljuje uz "
     "poziv. Ako tvog programa nema na popisu, prijava ne prolazi bez obzira "
     "na ocjene."),
    ("Provjeri radi li ti AAI@EduHr",
     "Prijava se predaje kroz Sustav državnih stipendija, a u njega se ulazi "
     "AAI@EduHr korisničkim računom. Ako ti lozinka ne radi, to se rješava na "
     "matičnom fakultetu i zna potrajati — bolje sada nego na dan roka."),
    ("Pripremi prijepis ocjena",
     "Rang-liste se slažu po uspjehu, pa je prijepis ocjena ono što ti u "
     "svakom slučaju treba. Studentska referada ga ne izdaje isti dan."),
]


def _blok_stanja():
    if OTVOREN:
        rok = f" Rok prijave je <strong>{ROK}</strong>." if ROK else ""
        gumb = (f'<a href="{POVEZNICA}" target="_blank" rel="noopener">'
                f'Otvori poziv &rarr;</a>') if POVEZNICA else ""
        return f"""<div class="stanje">
  <div class="txt">
    <b>Javni poziv je raspisan — prijave su otvorene</b>
    <span>Prijavljuje se elektronički, kroz Sustav državnih stipendija.{rok}</span>
  </div>
  {gumb}
</div>"""
    return f"""<div class="stanje">
  <div class="txt">
    <b>Javni poziv za 2026./2027. još nije raspisan</b>
    <span>Ministarstvo navodi da ga ministar raspisuje do {ROK_OBJAVE} za
      tekuću akademsku godinu. Provjereno {PROVJERENO}. Javimo ti na
      WhatsAppu istoga dana kad izađe.</span>
  </div>
  <a href="https://whatsapp.com/channel/0029Vb8yRo75Ui2aMzBAjv1a"
     target="_blank" rel="noopener">Obavijesti me &rarr;</a>
</div>"""


def stranica(mapa, broj_izvora, vrijeme):
    """Napise docs/stem-stipendije.html."""
    kvote = "".join(f'<li><b>{p}</b> — {o}</li>' for p, o in KVOTE)
    cekanje = "".join(
        f'<li>{_kvacica()}<div><strong>{n}</strong><small>{o}</small></div></li>'
        for n, o in DOK_CEKAS)

    try:
        from obavijesti import poziv as _poziv_obavijesti
        prijava = _poziv_obavijesti()
    except Exception:
        prijava = ""

    html = glava(
        "STEM stipendije 2026./2027. — iznos, uvjeti i kad izlazi poziv",
        f"Državne STEM stipendije: {STEM_NASTAVNICKI} mjesečno za nastavničke "
        f"i {STEM_OSTALI} za ostale STEM studije, {STEM_BROJ} stipendija. "
        f"Javni poziv se raspisuje do {ROK_OBJAVE}. Provjereno na stranicama "
        "Ministarstva znanosti, obrazovanja i mladih.",
        CSS)
    html += navigacija("drzavna")

    html += f"""<main class="w"><section class="ds">
<h1>STEM stipendije</h1>
<p class="lead">Državna stipendija za studente u STEM područjima znanosti.
Odvojen je natječaj od one za niži socio-ekonomski status, s većim iznosom i
vlastitim rang-listama. Ove godine dodjeljuje se {STEM_BROJ} stipendija.</p>

{izbor("stem")}

{_blok_stanja()}

<div class="cifre">
  <div><b>{STEM_NASTAVNICKI}</b><span>mjesečno, nastavnički STEM studiji</span></div>
  <div><b>{STEM_OSTALI}</b><span>mjesečno, ostali STEM studiji</span></div>
  <div><b>{STEM_BROJ}</b><span>stipendija za 2026./2027.</span></div>
  <div><b>{RATA}</b><span>rata, listopad 2026. – lipanj 2027.</span></div>
</div>

<h2>Što „do {ROK_OBJAVE}” zapravo znači</h2>
<p class="pod">Na stranicama ministarstva stoji da javni poziv raspisuje
ministar do {ROK_OBJAVE} za tekuću akademsku godinu. To je rok
<strong>ministarstvu da poziv objavi</strong> — nije rok tebi da se
prijaviš. Rok za prijavu piše u samom pozivu i počinje teći tek kad poziv
izađe. Ako negdje pročitaš da se STEM stipendije prijavljuju „do
{ROK_OBJAVE}”, to je ta dva roka pomiješana.</p>

<h2>Nastavnički studiji se ne natječu</h2>
<p class="pod">Studentima nastavničkih STEM studija stipendija pripada ako
zadovolje uvjete iz pravilnika — ne ovisi o rang-listi. Tek se ostatak
stipendija dijeli po rang-listama, po unaprijed određenim postocima:</p>
<ul class="spremi">{kvote}</ul>

<h2>Što možeš napraviti dok poziv ne izađe</h2>
<p class="pod">Rokovi za prijavu su kratki, a ovo troje ne ovisi o tekstu
poziva i rješava se unaprijed.</p>
<ul class="sam">{cekanje}</ul>

<h2>Prijava ide kroz Sustav državnih stipendija</h2>
<p class="pod">Prijave se ne šalju mailom ni poštom nego se predaju
elektronički, u Sustavu državnih stipendija na
<a href="{SUSTAV}" target="_blank" rel="noopener">vidra.srce.hr</a>.
Prijavljuješ se AAI@EduHr računom, istim kojim ulaziš u studomat. Isti sustav
koristi se i za državnu stipendiju za niži socio-ekonomski status, ali su to
dvije odvojene prijave na dva odvojena poziva.</p>

<h2>Službeni izvori</h2>
<ul class="izvori">
  <li><a href="{MZO_STEM}" target="_blank" rel="noopener">Ministarstvo —
      državne stipendije za studente u STEM područjima znanosti</a></li>
  <li><a href="{STEM_ODLUKA}" target="_blank" rel="noopener">Odluka o broju
      STEM stipendija za 2026./2027. (PDF)</a></li>
  <li><a href="{STEM_IZVADAK}" target="_blank" rel="noopener">Izvadak
      studijskih programa koji se priznaju kao STEM (XLSX)</a></li>
  <li><a href="{SUSTAV}" target="_blank" rel="noopener">VIDRA — sustav u kojem
      se predaje prijava</a></li>
</ul>

<p class="napomena">Ovu stranicu održavamo ručno, a podatke provjeravamo na
stranicama ministarstva; zadnji put {PROVJERENO}. Dok javni poziv ne izađe,
rok za prijavu nije poznat. Ako uočiš da je nešto zastarjelo, javi nam i
ispravit ćemo.</p>
</section>
{prijava}
</main>"""
    html += podnozje(broj_izvora, vrijeme)
    open(os.path.join(mapa, "stem-stipendije.html"), "w",
         encoding="utf-8").write(html)
    return "stem-stipendije.html"
