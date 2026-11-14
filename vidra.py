# -*- coding: utf-8 -*-
"""
Stranica o sustavu VIDRA.

Zasto postoji (Search Console, 28 dana do 14.11.2026.): upiti s rijecju
"vidra" ("vidra srce", "vidra stipendije"...) imali su oko 11.000 prikaza i
samo 105 klikova, jer je Google nudio stranicu o drzavnoj stipendiji, a
covjek je trazio sustav za prijavu. Ovdje je odgovor na to pitanje: gdje se
ulazi, cime se prijavljuje i sto se u sustavu trenutno moze predati.

Sve tvrdnje vec stoje na stranicama o drzavnoj i STEM stipendiji, gdje su
provjerene na natjecajima; stanje poziva cita se iz istih modula.
"""
import os
from datetime import date

import drzavna
import stem

DATOTEKA = "vidra.html"
PRIJEVOZ_SLUG = "potpora-prijevoz-studenata-invaliditetom-2027"


def _red(naziv, veza, stanje, otvoreno):
    boja = "var(--plava)" if otvoreno else "var(--tinta-2)"
    return (f'<tr><td><a href="{veza}">{naziv}</a></td>'
            f'<td style="color:{boja}">{stanje}</td></tr>')


def stranica(mapa, arhiv, glava, navigacija, podnozje, broj_izvora, vrijeme):
    danas = date.today().isoformat()
    redci = []

    if drzavna.OTVOREN and drzavna.ROK_ISO and danas > drzavna.ROK_ISO:
        s, o = f"zatvoreno, rok je bio {drzavna.ROK.split(' do ')[0]}", False
    elif drzavna.OTVOREN:
        s, o = f"otvoreno do {drzavna.ROK}", True
    else:
        s, o = "natječaj još nije raspisan", False
    redci.append(_red("Državna stipendija (socio-ekonomski status)",
                      "drzavna-stipendija.html", s, o))

    if stem.zatvoren():
        s, o = f"zatvoreno, rok je bio {stem.ROK.split(' do ')[0]}", False
    elif stem.OTVOREN:
        s, o = f"otvoreno do {stem.ROK}", True
    else:
        s, o = "poziv još nije raspisan", False
    redci.append(_red("Državna STEM stipendija", "stem-stipendije.html", s, o))

    pr = next((z for z in arhiv.values()
               if (z.get("slug") or "") == PRIJEVOZ_SLUG), None)
    if pr and (pr.get("rok_iso") or "") >= danas:
        redci.append(_red("Potpora za prijevoz studenata s invaliditetom",
                          f"natjecaj/{PRIJEVOZ_SLUG}.html",
                          f"otvoreno do {pr.get('rok_tekst')}", True))

    html = glava(
        "VIDRA stipendije — prijava na vidra.srce.hr i što je sada otvoreno",
        "VIDRA je sustav u kojem se predaju prijave za državnu i STEM "
        "stipendiju. Gdje se ulazi, čime se prijavljuješ (AAI@EduHr ili "
        "e-Građani) i koji su natječaji u sustavu trenutno otvoreni.",
        drzavna.CSS)
    html += navigacija("drzavna")
    html += f"""<main class="w"><section class="ds">
<h1>VIDRA: prijava na državne stipendije</h1>
<p class="lead">VIDRA je sustav Srca u kojem se elektronički predaju prijave
za državnu stipendiju, STEM stipendiju i druge studentske natječaje
Ministarstva. Nema papirnate prijave i ništa se ne šalje poštom.</p>

<div class="stanje">
  <div class="txt">
    <b>Tražiš sam sustav?</b>
    <span>Ovo je stipendije.hr, neovisna stranica s uputama. U sustav se
      ulazi na adresi vidra.srce.hr.</span>
  </div>
  <a href="{drzavna.SUSTAV}" target="_blank" rel="noopener">Otvori VIDRU &rarr;</a>
</div>

<h2>Što je u VIDRI sada otvoreno</h2>
<table class="bod"><tbody>{''.join(redci)}</tbody></table>
<p class="pod">Stanje se osvježava sa stranicom; rok i uvjete uvijek provjeri
u samom natječaju.</p>

<h2>Čime se prijavljuješ</h2>
<p class="pod">U sustav se ne ulazi imenom koje sam izmisliš. Prijavljuješ se
<strong>AAI@EduHr</strong> elektroničkim identitetom, onim koji dobiješ na
fakultetu i kojim ulaziš u studomat, ili preko sustava
<strong>e-Građani</strong>.</p>
<p class="pod">Ako ti AAI lozinka ne radi ili je nikad nisi aktivirao, to se
rješava na matičnom fakultetu, kod administratora informacijskog sustava;
referada zna uputiti kome. Zna potrajati koji dan, pa to ne ostavljaj za
zadnji dan roka.</p>

<h2>Kako izgleda prijava</h2>
<p class="pod">Velik dio podataka sustav sam dohvaća iz državnih registara
čim se prijaviš. Tvoje je da provjeriš je li dohvaćeno točno, dopuniš ostalo
i priložiš samo ono što sustav nije sam dohvatio. Cijeli postupak, korak po
korak, s popisom dokumenata: <a href="drzavna-stipendija.html"><b>državna
stipendija &rarr;</b></a> i <a href="stem-stipendije.html"><b>STEM
stipendija &rarr;</b></a></p>

<h2>Nakon prijave</h2>
<p class="pod">Bodovi i mjesto na rang-listi državne stipendije vide se u
samom sustavu. Ako prođeš, stipendiju treba u roku prihvatiti; tko taj rok
propusti, gubi stipendiju koju je već dobio.</p>

<p class="napomena">stipendije.hr nije povezan sa Srcem ni s Ministarstvom.
Za tehničke probleme s prijavom obrati se podršci sustava VIDRA ili svom
fakultetu.</p>
</section></main>"""
    html += podnozje(broj_izvora, vrijeme)
    with open(os.path.join(mapa, DATOTEKA), "w", encoding="utf-8") as f:
        f.write(html)
    return DATOTEKA
