# -*- coding: utf-8 -*-
"""
obavijesti.py — prijava na obavijesti o novim natjecajima mailom

Stranica je besmislena bez servisa koji prima prijave, pa se gradi tek kad
je BREVO_FORMA popunjena. Dok nije, web.py ju preskace i nigdje ne stoji
poveznica na nju — bolje da ne postoji nego da postoji i ne radi.

Sto Brevo mora imati prije nego se ovo ukljuci:
  1. obrazac (Contacts -> Forms) s poljima EMAIL, ZUPANIJA, TIP
  2. ukljucenu dvostruku potvrdu (double opt-in)
  3. stranicu zahvale koja vraca na stipendije.hr
Iz Brevovog ugradbenog koda treba samo adresa iz action="...", nista drugo.
"""
import os

from zajednicko import glava, navigacija, podnozje, WA_KANAL

# --- UKLJUCIVANJE --------------------------------------------------------
BREVO_FORMA = "https://b61131ba.sibforms.com/serve/MUIFAJWhHDPHDllmv3n8haYPynJiODYXR6hb0JSOer_RGjh48yZUwYNtHCLk5L80DDSOGD4DS2TREuM_ySiaPA28xfflYaPO38yiWwFBUQn-Pf4NJua26qCfiLBIHbq8Mx7qevm2akOP1dCoxNw1GXoMqyIghRmwbWxDpM18iflgc7dOFNkg11RkYzwLE4nwoXq8_y4v5iTa9A0Q4g=="
# -------------------------------------------------------------------------

ZUPANIJE = [
    "Bjelovarsko-bilogorska županija",
    "Brodsko-posavska županija",
    "Dubrovačko-neretvanska županija",
    "Grad Zagreb",
    "Istarska županija",
    "Karlovačka županija",
    "Koprivničko-križevačka županija",
    "Krapinsko-zagorska županija",
    "Ličko-senjska županija",
    "Međimurska županija",
    "Osječko-baranjska županija",
    "Požeško-slavonska županija",
    "Primorsko-goranska županija",
    "Sisačko-moslavačka županija",
    "Splitsko-dalmatinska županija",
    "Šibensko-kninska županija",
    "Varaždinska županija",
    "Virovitičko-podravska županija",
    "Vukovarsko-srijemska županija",
    "Zadarska županija",
    "Zagrebačka županija",
]

CSS = """
.ob{padding:2.6rem 0 0;max-width:46rem}
.ob h1{font-size:clamp(1.7rem,5vw,2.3rem);margin-bottom:.6rem}
.ob .lead{font-size:1.04rem;color:var(--tinta-2);max-width:52ch;margin:0 0 1.8rem}
.ob h2{font-size:1.16rem;margin:2.4rem 0 .5rem}
.ob p{font-size:.96rem;line-height:1.65}
.ob .sitno{font-size:.86rem;color:var(--tinta-2)}

.obr{border:1.5px solid var(--tinta);background:var(--karta);padding:1.4rem 1.3rem}
.obr label{display:block;font-size:.84rem;font-weight:600;color:var(--tinta);
  margin:0 0 .3rem}
.obr .red{margin-bottom:1rem}
.obr input[type=email],.obr select{width:100%;font-family:"Plex",sans-serif;
  font-size:.95rem;padding:.65rem .7rem;border:1px solid var(--linija);
  background:var(--papir);color:var(--tinta)}
.obr input[type=email]:focus,.obr select:focus{outline:2px solid var(--plava);
  outline-offset:-1px}
.obr button{width:100%;background:var(--plava);color:#fff;border:0;
  font-family:"Plex",sans-serif;font-weight:600;font-size:.98rem;
  padding:.8rem 1rem;cursor:pointer}
.obr button:hover{filter:brightness(1.12)}
.obr .pristanak{display:flex;gap:.6rem;align-items:flex-start;margin:0 0 1.1rem}
.obr .pristanak input{margin-top:.2rem;flex-shrink:0}
.obr .pristanak span{font-size:.84rem;color:var(--tinta-2);line-height:1.5}
.obr .pristanak a{color:var(--plava)}
.zamka{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}

.sto{display:grid;grid-template-columns:1fr 1fr;gap:.9rem;margin:.4rem 0 0}
.sto div{border:1px solid var(--linija);background:var(--karta);padding:.95rem 1rem}
.sto .ozn{font-family:"PlexMono",monospace;font-size:.68rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--plava);margin-bottom:.35rem}
.sto p{margin:0;font-size:.9rem;line-height:1.55}
@media(max-width:600px){.sto{grid-template-columns:1fr}}
"""


def _opcije():
    return "".join(f'<option value="{z}">{z}</option>' for z in ZUPANIJE)


# Ako je covjek dosao s naslovnice gdje je vec odabrao zupaniju, ne tjeraj
# ga da bira dvaput. U adresi stoji samo oznaka zupanije — nikad mail.
_PRESELEKT = """
<script>
(function(){
  var p = new URLSearchParams(location.search).get("z");
  if(!p) return;
  var s = document.getElementById("ZUPANIJA");
  if(!s) return;
  for(var i=0;i<s.options.length;i++){
    if(s.options[i].value === p){ s.selectedIndex = i; break; }
  }
})();
</script>"""


def obrazac():
    """Sam obrazac. Vraca prazno ako servis nije spojen."""
    if not BREVO_FORMA:
        return ""
    return f"""<form class="obr" method="POST" action="{BREVO_FORMA}">
  <div class="red">
    <label for="EMAIL">Tvoj mail</label>
    <input type="email" id="EMAIL" name="EMAIL" required
           placeholder="ime@primjer.com" autocomplete="email">
  </div>
  <div class="red">
    <label for="ZUPANIJA">Gdje živiš</label>
    <select id="ZUPANIJA" name="ZUPANIJA" required>
      <option value="">Odaberi županiju</option>
      {_opcije()}
    </select>
  </div>
  <div class="red">
    <label for="TIP">Tko si</label>
    <select id="TIP" name="TIP" required>
      <option value="">Odaberi</option>
      <option value="ucenik">Učenik srednje škole</option>
      <option value="student">Student</option>
      <option value="oba">I jedno i drugo me zanima</option>
    </select>
  </div>
  <div class="pristanak">
    <input type="checkbox" id="pristanak" required>
    <span><label for="pristanak" style="display:inline;font-weight:400">
      Slažem se da mi stipendije.hr šalje obavijesti o natječajima na mail.
      Odjaviti se mogu kad hoću, poveznicom u svakoj poruci. Imam 16 ili više
      godina, ili suglasnost roditelja.</label>
      <a href="privatnost.html">Što radimo s podacima</a></span>
  </div>
  <!-- Brevo ocekuje oba. email_address_check je zamka za robote i mora
       ostati prazno; covjek ga ne vidi, robot ga popuni i prijava otpada.
       locale je ono sto njihov obrazac salje, pa saljemo isto. -->
  <input type="text" name="email_address_check" value="" class="zamka"
         tabindex="-1" autocomplete="off" aria-hidden="true">
  <input type="hidden" name="locale" value="en">
  <button type="submit">Prijavi me na obavijesti</button>
</form>""" + _PRESELEKT


def poziv(put=""):
    """Kratki blok s poveznicom na stranicu prijave. Ide na naslovnicu i
    zupanijske stranice. Nosi vlastiti stil jer te stranice imaju drugi CSS."""
    if not BREVO_FORMA:
        return ""
    return f"""<style>
.obp{{margin:1.6rem 0 .4rem;border:1.5px solid var(--tinta);background:var(--karta);
  padding:1.1rem 1.15rem}}
.obp b{{display:block;font-family:"Bricolage",sans-serif;font-weight:700;
  font-size:1.08rem;letter-spacing:-.012em;margin-bottom:.2rem}}
.obp span{{display:block;font-size:.88rem;color:var(--tinta-2);margin-bottom:.9rem}}
.obp form{{display:flex;gap:.6rem;flex-wrap:wrap}}
.obp select{{flex:1;min-width:13rem;font-family:"Plex",sans-serif;font-size:.92rem;
  padding:.6rem .7rem;border:1px solid var(--linija);background:var(--papir);
  color:var(--tinta)}}
.obp button{{background:var(--plava);color:#fff;border:0;font-family:"Plex",sans-serif;
  font-weight:600;font-size:.92rem;padding:.6rem 1.1rem;cursor:pointer;
  white-space:nowrap}}
.obp button:hover{{filter:brightness(1.12)}}
@media(max-width:600px){{.obp button{{width:100%}}}}
</style>
<aside class="obp">
  <b>Javi mi kad izađe natječaj za mene</b>
  <span>Odaberi županiju i dobivaš mail samo kad se otvori natječaj koji te
    se tiče. Ne šaljemo ništa drugo.</span>
  <form action="{put}prijava-obavijesti.html" method="GET">
    <select name="z" aria-label="Županija">
      <option value="">Odaberi županiju</option>
      {_opcije()}
    </select>
    <button type="submit">Dalje</button>
  </form>
</aside>"""


def stranica(mapa, broj_izvora, vrijeme):
    """Napise docs/prijava-obavijesti.html. Ne radi nista ako nije spojeno."""
    put_html = os.path.join(mapa, "prijava-obavijesti.html")
    if not BREVO_FORMA:
        # Ako je stranica ostala od ranije kad je servis bio spojen, makni ju —
        # inace bi na webu stajao obrazac koji nigdje ne salje.
        if os.path.exists(put_html):
            os.remove(put_html)
        return False

    html = glava(
        "Obavijesti o stipendijama na mail — stipendije.hr",
        "Ostavi mail i županiju pa ti javimo čim se otvori natječaj za "
        "stipendiju koji se odnosi na tebe. Bez reklama i bez drugih poruka.",
        dodatni_css=CSS,
    )
    html += navigacija("obavijesti")
    html += f"""<main class="w">
<div class="ob">
<h1>Javi mi kad izađe natječaj za mene</h1>
<p class="lead">Natječaji se otvaraju kroz cijelu jesen, svatko na svoj dan, i
  rokovi su kratki — često petnaest dana od objave. Umjesto da provjeravaš,
  ostavi mail i javimo ti.</p>

{obrazac()}

<h2>Što točno stiže</h2>
<div class="sto">
  <div><p class="ozn">Stiže</p>
    <p>Natječaj otvoren u tvojoj županiji, i onaj koji vrijedi za cijelu
       Hrvatsku. U poruci su rok, iznos i poveznica na službenu stranicu.</p></div>
  <div><p class="ozn">Ne stiže</p>
    <p>Natječaji iz drugih županija, podsjetnici, novosti o stranici,
       reklame. Tvoj mail ne dajemo nikome i ne koristimo ga ni za što
       drugo.</p></div>
</div>

<h2>Koliko često</h2>
<p>Onoliko koliko ima natječaja, a to je neravnomjerno. U rujnu i listopadu
  može biti nekoliko poruka mjesečno, a od veljače do ljeta najčešće nijedna.
  Provjera ide dvaput tjedno, pa poruka stigne najkasnije koji dan nakon
  objave.</p>

<h2>Odjava</h2>
<p>Poveznica za odjavu stoji u svakoj poruci i radi odmah, bez pitanja. Ako
  hoćeš da ti obrišemo mail iz evidencije, javi na
  <a href="mailto:erik.hunjek@gmail.com">erik.hunjek@gmail.com</a> i brišemo ga.</p>

<h2>Ako ti je draže WhatsApp</h2>
<p>Veće natječaje javljamo i na <a href="{WA_KANAL}" target="_blank"
  rel="noopener">WhatsApp kanalu</a>. Tamo ne biraš županiju, nego stiže
  sve — a mailom stiže samo tvoje.</p>
</div>
</main>
"""
    html += podnozje(broj_izvora, vrijeme)
    with open(put_html, "w", encoding="utf-8") as f:
        f.write(html)
    return True


# --- skocni prozor -------------------------------------------------------
# Google kaznjava skocne prozore koji pokriju sadrzaj cim covjek dode s
# pretrazivanja. Zato okidac NIKAD nije ucitavanje stranice, nego scroll ili
# vrijeme — tek kad je covjek vec nesto radio na stranici.
#
# Ostala pravila, svako postoji zbog konkretnog nacina da se covjek naljuti:
#   - tko ga zatvori ne vidi ga 60 dana, tko se prijavi nikad vise
#   - na mobitelu je ploha pri dnu, ne prozor preko cijelog ekrana
#   - zatvara se s ×, tipkom Esc i klikom izvan njega
#   - ne postoji na stranici prijave ni na pravnim stranicama
# Postotak stranice je kriva mjera: 93 zatvorena natjecaja cine vecinu
# visine, pa bi 55% palo duboko u dio koji nitko ne cita. Zato se okida na
# kraju OTVORENIH natjecaja — to je trenutak kad je covjek prosao sve sto
# ga zanima i vidi da za njega mozda nema nista.
PRAG_PIKSELA = 900   # rezerva: stranice bez sekcije otvorenih
PRAG_SEKUNDI = 20
DANA_MIRA = 60       # koliko dugo se ne vraca onome tko ga je zatvorio


def skocni():
    """Skocni prozor s prijavom. Prazno dok servis nije spojen."""
    if not BREVO_FORMA:
        return ""
    return f"""<style>
.sk-sjena{{position:fixed;inset:0;z-index:90;background:rgba(10,12,16,.45);
  display:none;align-items:flex-end;justify-content:center}}
.sk-sjena.vidljiva{{display:flex}}
.sk{{background:var(--papir);width:100%;max-width:30rem;padding:1.3rem 1.2rem 1.2rem;
  border-top:3px solid var(--plava);position:relative;
  animation:sk-gore .22s ease-out}}
@keyframes sk-gore{{from{{transform:translateY(14px);opacity:0}}to{{transform:none;opacity:1}}}}
.sk b{{display:block;font-family:"Bricolage",sans-serif;font-weight:800;
  font-size:1.2rem;letter-spacing:-.015em;margin-bottom:.3rem;padding-right:1.6rem}}
.sk .sk-p{{font-size:.89rem;color:var(--tinta-2);line-height:1.5;margin:0 0 1rem}}
.sk input[type=email],.sk select{{width:100%;font-family:"Plex",sans-serif;
  font-size:.95rem;padding:.62rem .7rem;margin-bottom:.6rem;
  border:1px solid var(--linija);background:var(--karta);color:var(--tinta)}}
.sk button[type=submit]{{width:100%;background:var(--plava);color:#fff;border:0;
  font-family:"Plex",sans-serif;font-weight:600;font-size:.97rem;
  padding:.78rem 1rem;cursor:pointer;margin-top:.25rem}}
.sk button[type=submit]:hover{{filter:brightness(1.12)}}
.sk .sk-x{{position:absolute;top:.55rem;right:.6rem;background:none;border:0;
  font-size:1.5rem;line-height:1;color:var(--tinta-2);cursor:pointer;
  padding:.2rem .45rem}}
.sk .sk-x:hover{{color:var(--tinta)}}
.sk .sk-sitno{{font-size:.76rem;color:var(--tinta-2);margin:.7rem 0 0;line-height:1.45}}
.sk .sk-sitno a{{color:var(--plava)}}
.sk .zamka{{position:absolute;left:-9999px;width:1px;height:1px;opacity:0}}
@media(min-width:640px){{
  .sk-sjena{{align-items:center}}
  .sk{{border:1.5px solid var(--tinta);border-top:3px solid var(--plava)}}
}}
</style>
<div class="sk-sjena" id="sk-sjena" role="dialog" aria-modal="true"
     aria-labelledby="sk-naslov">
  <div class="sk">
    <button type="button" class="sk-x" id="sk-x" aria-label="Zatvori">&times;</button>
    <b id="sk-naslov">Javimo ti kad izađe natječaj za tebe</b>
    <p class="sk-p">Ostavi mail i županiju. Stiže samo natječaj koji se odnosi
      na tebe — ništa drugo ti ne šaljemo.</p>
    <form method="POST" action="{BREVO_FORMA}">
      <input type="email" name="EMAIL" required placeholder="ime@primjer.com"
             autocomplete="email" aria-label="Tvoj mail">
      <select name="ZUPANIJA" required aria-label="Županija">
        <option value="">Odaberi županiju</option>
        {_opcije()}
      </select>
      <select name="TIP" required aria-label="Tko si">
        <option value="">Učenik ili student?</option>
        <option value="ucenik">Učenik srednje škole</option>
        <option value="student">Student</option>
        <option value="oba">Oboje me zanima</option>
      </select>
      <!-- Brevo ocekuje oba. email_address_check je zamka za robote i mora
           ostati prazno; covjek ga ne vidi, robot ga popuni i prijava otpada.
           locale je ono sto njihov obrazac salje, pa saljemo isto. -->
      <input type="text" name="email_address_check" value="" class="zamka"
             tabindex="-1" autocomplete="off" aria-hidden="true">
      <input type="hidden" name="locale" value="en">
      <button type="submit" id="sk-salji">Javi mi</button>
    </form>
    <p class="sk-sitno">Prijavom pristaješ na obavijesti o natječajima.
      Odjava je u svakoj poruci. <a href="privatnost.html">Što radimo s podacima</a></p>
  </div>
</div>
""" + _SKOCNI_JS.replace(
        "__DANA__", str(DANA_MIRA)).replace(
        "__PIKS__", str(PRAG_PIKSELA)).replace(
        "__SEK__", str(PRAG_SEKUNDI))


_SKOCNI_JS = """<script>
(function(){
  var K = "obavijesti-skocni";
  var sjena = document.getElementById("sk-sjena");
  if(!sjena) return;

  function procitaj(){
    try{
      var v = localStorage.getItem(K);
      if(!v) return null;
      if(v === "prijavljen") return "nikad";
      return Number(v) > Date.now() ? "cekaj" : null;
    }catch(e){ return null; }
  }
  if(procitaj()) return;

  function zapamti(trajno){
    try{
      localStorage.setItem(K, trajno ? "prijavljen"
        : String(Date.now() + __DANA__*24*60*60*1000));
    }catch(e){}
  }

  var prikazan = false, oko = null;
  function prikazi(){
    if(prikazan) return;
    prikazan = true;
    sjena.classList.add("vidljiva");
    document.removeEventListener("scroll", naScroll);
    clearTimeout(sat);
    if(oko) oko.disconnect();
  }
  function zatvori(){
    sjena.classList.remove("vidljiva");
    zapamti(false);
  }

  // Glavni okidac: kraj sekcije s otvorenim natjecajima. Tko je dosao dotle
  // vidio je sve sto se danas moze prijaviti — i to je trenutak kad mu
  // obavijest o buducim natjecajima stvarno nesto znaci.
  var otv = document.getElementById("sek-otv");
  var kartice = otv ? otv.querySelectorAll(".k") : [];
  var naOtvorenima = false;

  if(kartice.length && window.IntersectionObserver){
    // Ne na samom kraju sekcije — tko ima 12 otvorenih natjecaja skrolao bi
    // pet ekrana prije nego ga vidi. Dovoljno je da je prosao vecinu.
    var i = Math.max(1, Math.ceil(kartice.length * 0.6) - 1);
    oko = new IntersectionObserver(function(z){
      if(z[0].isIntersecting) prikazi();
    }, {threshold: 0.5});
    oko.observe(kartice[i]);
    naOtvorenima = true;
  }

  // Rezerva samo za stranice bez otvorenih natjecaja (izvan sezone). Kad
  // sekcija postoji, piksela nema — inace se okine prije opazaca.
  function naScroll(){
    if(window.scrollY >= __PIKS__) prikazi();
  }
  if(!naOtvorenima){
    document.addEventListener("scroll", naScroll, {passive:true});
  }
  var sat = setTimeout(prikazi, __SEK__*1000);

  document.getElementById("sk-x").addEventListener("click", zatvori);
  sjena.addEventListener("click", function(e){ if(e.target === sjena) zatvori(); });
  document.addEventListener("keydown", function(e){
    if(e.key === "Escape" && sjena.classList.contains("vidljiva")) zatvori();
  });
  document.getElementById("sk-salji").addEventListener("click", function(){
    zapamti(true);
  });
})();
</script>"""

def hvala(mapa, broj_izvora, vrijeme):
    """Stranica na koju Brevo vrati covjeka nakon slanja obrasca.

    Bez nje Brevo prikaze goli JSON odgovor, sto izgleda kao da je nesto
    puklo. Stranica postoji samo zato da covjek zna da treba otici u mail —
    kod dvostruke potvrde tu otpadne najvise ljudi.
    """
    put_html = os.path.join(mapa, "hvala.html")
    if not BREVO_FORMA:
        if os.path.exists(put_html):
            os.remove(put_html)
        return False

    html = glava(
        "Provjeri mail — stipendije.hr",
        "Prijava je zaprimljena. Ostao je jos jedan korak: potvrda poveznicom "
        "u mailu koji smo upravo poslali.",
        dodatni_css=CSS + """
.hv{text-align:center;padding:4rem 0 3rem;max-width:34rem;margin:0 auto}
.hv .kvaka{width:3.2rem;height:3.2rem;margin:0 auto 1.2rem;border-radius:50%;
  background:var(--plava);display:flex;align-items:center;justify-content:center}
.hv .kvaka svg{width:1.6rem;height:1.6rem;stroke:#fff;stroke-width:2.6;fill:none;
  stroke-linecap:round;stroke-linejoin:round}
.hv h1{font-size:clamp(1.5rem,4.5vw,2rem);margin-bottom:.7rem}
.hv p{color:var(--tinta-2);line-height:1.65}
.hv .koraci{text-align:left;border:1px solid var(--linija);background:var(--karta);
  padding:1.1rem 1.2rem;margin:1.8rem 0}
.hv .koraci p{margin:.45rem 0;font-size:.93rem;color:var(--tinta)}
.hv .natrag{display:inline-block;margin-top:.6rem;color:var(--plava);
  font-weight:600;text-decoration:none}
.hv .natrag:hover{text-decoration:underline}
""",
        dodatni_head='<meta name="robots" content="noindex">',
    )
    html += navigacija("")
    html += """<main class="w">
<div class="hv">
  <div class="kvaka"><svg viewBox="0 0 24 24" aria-hidden="true">
    <path d="M4 12.5l5.5 5.5L20 7"/></svg></div>
  <h1>Skoro gotovo — provjeri mail</h1>
  <p>Poslali smo ti poruku s poveznicom za potvrdu. Dok ne klikneš na nju,
     nisi upisan i nećemo ti ništa slati.</p>
  <div class="koraci">
    <p>Otvori mail koji si upisao.</p>
    <p>Klikni na poveznicu u poruci.</p>
    <p>Ako poruke nema za koju minutu, pogledaj u neželjenu poštu.</p>
  </div>
  <a class="natrag" href="./">&larr; Natrag na natječaje</a>
</div>
</main>
"""
    html += podnozje(broj_izvora, vrijeme)
    with open(put_html, "w", encoding="utf-8") as f:
        f.write(html)
    return True
