# -*- coding: utf-8 -*-
"""
Gradi javnu stranicu iz output.json:
  docs/index.html      natjecaji + filter
  docs/vodic.html      kako do stipendije
  docs/impressum.html  podaci o pruzatelju

Tehnicki statusi (GRESKA, PROVJERITI) se NE prikazuju javno.
"""
import json
import os
import re
from datetime import datetime

from zajednicko import glava, navigacija, podnozje, oblik, EMAIL, DOMENA, BAZA

ULAZ = "output.json"
IZVORI = "sources.json"
MAPA = "docs"
SVI = "Cijela Hrvatska"

# Kad je odabrana zupanija, sto s drzavnim izvorima u popisu pracenih?
#   True  = skupe se iza gumba (kraca stranica, manje suma)
#   False = svi ostaju vidljivi (duza stranica, vise sadrzaja odjednom)
# Otvoreni natjecaji su UVIJEK vidljivi, neovisno o ovoj postavci.
SKLOPI_DRZAVNE = True

# boja po vrsti izvora — i informacija i vizualni ritam
BOJE = {
    "Grad": "grad", "Općina": "grad", "Županija": "zup",
    "Sveučilište": "sve", "Zaklada": "zak", "Tvrtka": "tvr",
    "Ministarstvo": "drz", "Međunarodno": "med", "Agregator": "drz",
}


def esc(v):
    if v is None or str(v).strip() == "":
        return ""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def iso_rok(status):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", status or "")
    return m.group(1) if m else ""


def ucitaj_izvore():
    """URL -> (podrucje, zupanija, ocekivani mjesec, je li usko usmjeren)."""
    p, z, o, u = {}, {}, {}, {}
    if os.path.exists(IZVORI):
        for s in json.load(open(IZVORI, encoding="utf-8")):
            k = s["url"].rstrip("/")
            p[k] = s.get("podrucje") or SVI
            z[k] = s.get("zupanija") or ""
            o[k] = s.get("ocekivano") or ""
            u[k] = bool(s.get("usko"))
    return p, z, o, u


CSS_INDEX = """
/* --- hero --- */
.hero{padding:3.2rem 0 .4rem}
.hero .oznaka{display:inline-block;margin-bottom:1rem}

/* prazno stanje */
.prazno{margin-top:1.8rem;border:1.5px solid var(--tinta);background:var(--karta);
  padding:1.3rem 1.15rem}
.prazno .kad{font-family:"Bricolage",sans-serif;font-weight:700;
  font-size:1.35rem;letter-spacing:-.02em;margin:0 0 .35rem}
.prazno p{margin:.35rem 0;font-size:.92rem;color:var(--tinta-2)}

/* --- filter --- */
.filteri{margin:2.2rem 0 0;background:var(--karta);border:2px solid var(--plava);
  padding:1.15rem 1.2rem 1.25rem}
.oznaka-f{display:block;font-family:"Bricolage",sans-serif;
  font-weight:700;font-size:1.06rem;letter-spacing:-.012em;
  color:var(--tinta);margin-bottom:.65rem}
#zupanija{width:100%;max-width:460px;background:var(--papir);
  border:1.5px solid var(--tinta);border-radius:0;padding:.78rem 2.6rem .78rem .9rem;
  font-family:"Plex",sans-serif;font-size:1rem;font-weight:500;
  color:var(--tinta);cursor:pointer;appearance:none;-webkit-appearance:none;
  background-image:url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='13' height='8'%3E%3Cpath d='M1 1l5.5 5.5L12 1' stroke='%231D4ED8' stroke-width='2' fill='none'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 1rem center}
#zupanija:hover,#zupanija:focus{border-color:var(--plava);background-color:#fff}
.pojasnjenje{margin:.7rem 0 0;font-size:.85rem;color:var(--tinta-2);max-width:48ch}

/* --- kartice --- */
.k{background:var(--karta);border:1px solid var(--linija);
  padding:1.05rem 1.15rem;margin-bottom:.75rem}
.k.otv{border-left:3px solid var(--otvoreno)}
.k.skriveno{display:none}
.k .zag{display:flex;justify-content:flex-start;gap:.7rem;
  align-items:baseline;flex-wrap:wrap}
.status{font-family:"PlexMono",monospace;font-size:.66rem;letter-spacing:.09em;
  text-transform:uppercase;padding:.2rem .5rem;white-space:nowrap;
  flex-shrink:0;align-self:flex-start;max-width:100%}
.status.otv{background:#DCFCE7;color:var(--otvoreno)}
.status.zat{background:var(--papir);color:var(--tinta-2)}
.status.hitno{background:#FEE2E2;color:var(--hitno)}
.k .izvor{font-family:"PlexMono",monospace;font-size:.68rem;
  letter-spacing:.06em;text-transform:uppercase;color:var(--tinta-2);
  margin-bottom:.55rem}
.polja{display:grid;grid-template-columns:8.5rem 1fr;gap:.28rem .9rem;
  font-size:.9rem;margin:.5rem 0 0}
.polja dt{color:var(--tinta-2)}
.polja dd{margin:0}
.polja dd.iznos{font-family:"PlexMono",monospace;font-weight:500}
.k details{margin-top:.75rem;font-size:.88rem}
.k summary{cursor:pointer;color:var(--plava);font-weight:500}
.k details ol{margin:.55rem 0 0;padding-left:1.25rem;color:var(--tinta-2)}
.k details li{margin-bottom:.3rem}
.veza{display:inline-block;margin-top:.8rem;font-size:.88rem;font-weight:500;
  color:var(--tinta);text-decoration:none;border-bottom:1.5px solid var(--plava);
  padding-bottom:1px}
.veza:hover{color:var(--plava)}
.nema-rez{display:none;border:1px dashed var(--linija);padding:1.05rem 1.15rem;
  color:var(--tinta-2);font-size:.9rem;margin:0}
.nema-rez.vidljivo{display:block}
.zatvoreni-omot{margin-top:.4rem}

/* --- zbijeni popis zatvorenih izvora --- */
.rd{display:flex;align-items:center;gap:.75rem;padding:.62rem .3rem;
  border-bottom:1px solid var(--linija);text-decoration:none;color:var(--tinta);
  font-size:.92rem}
.rd:first-of-type{border-top:1px solid var(--linija)}
.rd:hover{background:var(--karta)}
.rd-naziv{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.rd-pod{font-family:"PlexMono",monospace;font-size:.68rem;letter-spacing:.06em;
  text-transform:uppercase;color:var(--tinta-2);white-space:nowrap;flex-shrink:0}
.rd-str{color:var(--tinta-2);font-size:.85rem;flex-shrink:0}
.rd:hover .rd-str{color:var(--otvoreno)}
.tocka,i.tocka{width:8px;height:8px;flex-shrink:0;border-radius:50%;display:inline-block}
.tocka.grad{background:#15803D}
.tocka.zup{background:#1D4ED8}
.tocka.sve{background:#7A4E9E}
.tocka.zak{background:#B8860B}
.tocka.tvr{background:#B91C1C}
.tocka.drz{background:#141B2D}
.tocka.med{background:#0F8A8A}
.legenda{display:flex;flex-wrap:wrap;gap:.5rem 1.1rem;margin:.2rem 0 1.1rem;
  font-size:.74rem;color:var(--tinta-2)}
.legenda span{display:flex;align-items:center;gap:.35rem}
@media(max-width:600px){
  .rd{font-size:.88rem;gap:.55rem;padding:.6rem .2rem}
  .rd-pod{display:none}
}
.popis-zup{display:flex;flex-wrap:wrap;gap:.45rem}
.popis-zup a{font-size:.88rem;color:var(--tinta);text-decoration:none;
  border:1px solid var(--linija);background:var(--karta);padding:.42rem .75rem}
.popis-zup a:hover{border-color:var(--plava);color:var(--plava)}
/* kad je odabrana zupanija, lokalne stipendije idu prve */
.grupa{display:flex;flex-direction:column}
.grupa .k{order:0}
.grupa .k.drzavna{order:1}
.grupa .nema-rez{order:2}
.medja{order:1;display:none;margin:.5rem 0 .9rem;
  font-family:"PlexMono",monospace;font-size:.7rem;letter-spacing:.09em;
  text-transform:uppercase;color:var(--tinta-2);
  border-top:1px solid var(--linija);padding-top:.85rem}
.medja.vidljiva{display:block}
/* sklapanje drzavnih izvora kad je odabrana zupanija */
.k.drzavna.sklopljena{display:none}
.prekidac{order:1;display:none;background:var(--karta);
  border:1px dashed var(--linija);width:100%;padding:.75rem 1rem;
  font-family:"Plex",sans-serif;font-size:.88rem;color:var(--tinta-2);
  cursor:pointer;text-align:left;margin-bottom:.9rem}
.prekidac:hover{border-color:var(--plava);color:var(--tinta)}
.prekidac.vidljiv{display:block}
@media(max-width:600px){
  /* hero */
  .hero{padding:2rem 0 .4rem}

  .prazno{padding:1.05rem .95rem}
  .prazno .kad{font-size:1.2rem}

  /* filter */
  .filteri{margin:1.7rem 0 0;padding:1rem .9rem 1.05rem}
  .oznaka-f{font-size:1rem}
  #zupanija{max-width:100%;font-size:1rem;padding:.8rem 2.4rem .8rem .8rem}
  .pojasnjenje{font-size:.8rem}
  .medja{font-size:.66rem;margin:.35rem 0 .8rem}

  /* sekcije */
  .sek{padding:2rem 0 0}
  h2{font-size:1.06rem}
  .sek-vrh{gap:.5rem}
  .sek-vrh .broj{font-size:.86rem}

  /* kartice */
  .k{padding:.95rem .9rem}
  /* oznaka uvijek iznad naslova, da ne skace i ne izlazi van */
  .k .zag{flex-direction:column-reverse;align-items:flex-start;gap:.45rem}
  .k .zag h3{min-width:0;width:100%}
  h3{font-size:.97rem}
  .status{font-size:.62rem;padding:.18rem .45rem}
  .polja{grid-template-columns:1fr;gap:.05rem}
  .polja dt{font-size:.76rem;margin-top:.45rem;color:#8A909E}
  .polja dd{font-size:.92rem}
  /* veca povrsina za prst */
  .k summary{padding:.35rem 0}
  .veza{padding:.4rem 0 .3rem}
}
@media(max-width:380px){
}
"""


def kartica(r, otvorena, podrucje, zupanija):
    naziv = esc(r.get("naziv"))
    # ako je scraper nasao izravnu poveznicu na natjecaj, koristi nju
    izravna = r.get("poveznica_natjecaj")
    url = esc(izravna or r.get("url"))
    tekst_veze = ("Otvori natječaj" if izravna and otvorena
                  else "Službena stranica")
    iznos, rok = esc(r.get("iznos")), esc(r.get("rok_tekst"))
    uvjeti = esc(r.get("uvjeti"))
    iso = iso_rok(r.get("status") or "")

    polja = ""
    if iznos:
        # monospace samo za kratke iznose ("200 EUR"); duge recenice
        # se u mono citaju tesko, pa idu obicnim pismom
        kl = "iznos" if len(iznos) <= 32 else ""
        polja += f'<dt>Iznos</dt><dd class="{kl}">{iznos}</dd>'
    if rok and otvorena:
        polja += f'<dt>Rok prijave</dt><dd>{rok}</dd>'
    if uvjeti:
        polja += f'<dt>Tko se prijavljuje</dt><dd>{uvjeti}</dd>'
    polja = f'<dl class="polja">{polja}</dl>' if polja else ""

    upute = r.get("upute_za_prijavu") or ""
    koraci = "".join(f"<li>{esc(k.strip())}</li>"
                     for k in upute.split("|") if k.strip())
    upute_html = (f'<details><summary>Kako se prijaviti</summary><ol>{koraci}</ol></details>'
                  if koraci and otvorena else "")

    if otvorena:
        znak = '<span class="status otv" data-znak>Otvoreno</span>'
        klasa = "k otv"
    else:
        znak = '<span class="status zat">Zatvoreno</span>'
        klasa = "k"

    return (f'<article class="{klasa}" data-podrucje="{esc(podrucje)}" '
            f'data-zupanija="{esc(zupanija)}" data-rok="{iso}">'
            f'<div class="zag"><h3>{naziv}</h3>{znak}</div>'
            f'<div class="izvor">{esc(podrucje)}</div>'
            f'{polja}{upute_html}'
            f'<a class="veza" href="{url}" target="_blank" rel="noopener">'
            f'{tekst_veze} &rarr;</a></article>')


# hrvatski abecedni red: ... S, Š, T, U, V, Z, Ž
_ABC = "aábcčćdđefghijklmnoprsštuvzž"
_RANG = {z: i for i, z in enumerate(_ABC)}


def hr_kljuc(s):
    """Sortiranje po hrvatskoj abecedi umjesto po kodovima znakova."""
    out = []
    for z in s.lower():
        out.append(_RANG.get(z, 99 + ord(z) % 50))
    return out


def legenda_html():
    stavke = [("grad", "Grad ili općina"), ("zup", "Županija"),
              ("sve", "Sveučilište"), ("zak", "Zaklada"),
              ("tvr", "Tvrtka"), ("drz", "Država"), ("med", "Međunarodno")]
    return ('<div class="legenda">'
            + "".join(f'<span><i class="tocka {k}"></i>{t}</span>'
                      for k, t in stavke) + '</div>')


def redak(r, podrucje, zupanija):
    """Zatvoreni izvor: jedan zbijen redak umjesto pune kartice."""
    kat = r.get("kategorija") or ""
    boja = BOJE.get(kat, "drz")
    return (f'<a class="rd k" href="{esc(r.get("url"))}" target="_blank" '
            f'rel="noopener" data-podrucje="{esc(podrucje)}" '
            f'data-zupanija="{esc(zupanija)}">'
            f'<span class="tocka {boja}" title="{esc(kat)}"></span>'
            f'<span class="rd-naziv">{esc(r.get("naziv"))}</span>'
            f'<span class="rd-pod">{esc(podrucje)}</span>'
            f'<span class="rd-str">&rarr;</span></a>')


def izbornik(podrucja):
    """Padajuci izbornik zupanija. Podrucje koje ne pripada nijednoj zupaniji
    (Grad Zagreb) stoji samo, s jasnom oznakom da je grad."""
    opcije = '<option value="">Sve stipendije u Hrvatskoj</option>'
    for p in sorted(podrucja, key=hr_kljuc):
        naziv = p if "županija" in p else f"Grad {p}"
        opcije += f'<option value="{esc(p)}">{esc(naziv)}</option>'
    return opcije


# --- rokovi se racunaju u pregledniku, a ne pri gradnji stranice ---
# Stranica se gradi dvaput tjedno, a rok moze isteci bilo kojeg dana. Zato
# svaki posjetitelj iznova racuna dane iz data-rok: istekli natjecaji nestaju
# iz "Otvoreno za prijave" i prije nego skripta idući put prođe kroz izvore.
# Ovaj blok ide na naslovnicu I na stranice zupanija.
JS_ROKOVI = """
(function(){
  // 1 dan / 2-4 dana / 5+ dana; pazi na 11-14 i na 21, 31...
  function oblik(n,jd,gjd,gmn){
    var z=Math.abs(n)%10, d=Math.abs(n)%100;
    if(d>=11&&d<=14) return gmn;
    if(z===1) return jd;
    if(z>=2&&z<=4) return gjd;
    return gmn;
  }

  // Cijeli dani do roka po lokalnom kalendaru:
  //   n > 0  jos ima dana,  n === 0  danas je zadnji dan,  n < 0  rok je prosao.
  // Usporeduju se ponoci, pa doba dana i ljetno/zimsko vrijeme ne pomicu racun.
  function dana(iso){
    if(!iso) return null;
    var d=/^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(iso);
    if(!d) return null;
    var rok=new Date(+d[1], +d[2]-1, +d[3]);
    var s=new Date(), danas=new Date(s.getFullYear(), s.getMonth(), s.getDate());
    return Math.round((rok-danas)/86400000);
  }

  var istekle=0;
  document.querySelectorAll(".k.otv[data-rok]").forEach(function(k){
    var n=dana(k.getAttribute("data-rok"));
    if(n===null) return;
    if(n<0){                       // rok je prosao — van iz otvorenih
      k.classList.add("isteklo");
      k.style.display="none";
      istekle++;
      return;
    }
    var z=k.querySelector("[data-znak]");
    if(!z) return;
    if(n===0){ z.className="status hitno"; z.textContent="Zadnji dan"; }
    else if(n<=7){ z.className="status hitno";
      z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
    else if(n<=21){ z.textContent="Još "+n+" "+oblik(n,"dan","dana","dana"); }
  });

  if(!istekle) return;

  // brojke i naslovi moraju pratiti ono sto se stvarno vidi
  var ziv=document.querySelectorAll(".k.otv:not(.isteklo)").length;
  document.querySelectorAll("[data-broj-otv]").forEach(function(b){
    b.textContent = ziv+" "+oblik(ziv,"natječaj","natječaja","natječaja");
  });
  document.querySelectorAll("[data-broj-otv-n]").forEach(function(b){
    b.textContent = ziv;
  });
  if(ziv>0) return;

  var sek=document.getElementById("sek-otv");
  if(sek) sek.style.display="none";
  var prazno=document.getElementById("nema-otvorenih");
  if(prazno) prazno.style.display="";
  var sazetak=document.getElementById("sazetak-zup");
  if(sazetak && sazetak.getAttribute("data-nema"))
    sazetak.textContent=sazetak.getAttribute("data-nema");
})();
"""


JS = """
(function(){
  var SVI="Cijela Hrvatska";

  // 1 dan / 2-4 dana / 5+ dana; pazi na 11-14 i na 21, 31...
  function oblik(n,jd,gjd,gmn){
    var z=Math.abs(n)%10, d=Math.abs(n)%100;
    if(d>=11&&d<=14) return gmn;
    if(z===1) return jd;
    if(z>=2&&z<=4) return gjd;
    return gmn;
  }

  var izbor=document.getElementById("zupanija");
  if(!izbor) return;
  var kartice=document.querySelectorAll(".k");

  function osvjezi(){
    var z=izbor.value;
    kartice.forEach(function(k){
      var p=k.getAttribute("data-podrucje"),
          zk=k.getAttribute("data-zupanija")||"";
      // bez odabira sve; inace: drzavne uvijek + sve iz odabrane zupanije
      var ok = !z || p===SVI || zk===z || p===z;
      k.classList.toggle("skriveno",!ok);
    });
    document.querySelectorAll(".grupa").forEach(function(g){
      var ima=g.querySelectorAll(".k:not(.skriveno):not(.isteklo)").length>0;
      var por=g.querySelector(".nema-rez");
      if(por)por.classList.toggle("vidljivo",!ima);
    });
    sklopiDrzavne(!!z);
  }

  // Kad je odabrana zupanija, ZATVORENE drzavne se skupe iza gumba.
  // Otvorene ostaju vidljive uvijek: ako se mozes prijaviti danas,
  // nebitno je je li stipendija lokalna ili drzavna.
  var prekidac=document.getElementById("prekidac");
  var razmotano=__RAZMOTANO__;

  function sklopiDrzavne(aktivno){
    if(!prekidac) return;
    var omot=prekidac.parentNode;
    var drz=omot.querySelectorAll(".k.drzavna:not(.skriveno):not(.isteklo)");
    if(!aktivno || drz.length===0){
      prekidac.classList.remove("vidljiv");
      omot.querySelectorAll(".k.drzavna").forEach(function(k){
        k.classList.remove("sklopljena");
      });
      razmotano=false;
      return;
    }
    prekidac.classList.add("vidljiv");
    drz.forEach(function(k){ k.classList.toggle("sklopljena", !razmotano); });
    prekidac.textContent = razmotano
      ? "Sakrij dr\u017eavne izvore"
      : "Prika\u017ei jo\u0161 " + drz.length + " " +
        oblik(drz.length,"dr\u017eavni izvor","dr\u017eavna izvora","dr\u017eavnih izvora") +
        " koji vrijede za sve";
  }

  if(prekidac){
    prekidac.addEventListener("click", function(){
      razmotano=!razmotano;
      sklopiDrzavne(true);
    });
  }
  izbor.addEventListener("change",osvjezi);
  osvjezi();
})();
"""


def main():
    if not os.path.exists(ULAZ):
        print("GRESKA: nema %s" % ULAZ)
        return

    d = json.load(open(ULAZ, encoding="utf-8"))
    pod_map, zup_map, _, usko_map = ucitaj_izvore()

    otvorene, zatvorene = [], []
    for r in d:
        s = r.get("status") or ""
        k = (r.get("url") or "").rstrip("/")
        par = (r, pod_map.get(k, SVI), zup_map.get(k, ""))
        if s.startswith("OTVORENO"):
            otvorene.append(par)
        elif s.startswith("ROK ISTEKAO") or s.startswith("NEMA AKTIVNOG"):
            zatvorene.append(par)

    # najhitniji prvi
    otvorene.sort(key=lambda t: (iso_rok(t[0].get("status") or "") or "9999",
                                 t[0].get("naziv") or ""))
    zatvorene.sort(key=lambda t: t[0].get("naziv") or "")

    # popis za izbornik: zupanije + podrucja koja ne pripadaju nijednoj (npr. Grad Zagreb)
    podrucja = set()
    for _, p, z in otvorene + zatvorene:
        if p == SVI:
            continue
        podrucja.add(z if z else p)

    vrijeme = datetime.now().strftime("%d.%m.%Y.")
    ukupno = len(otvorene) + len(zatvorene)

    # ---------- hero ----------
    # Uski natjecaji (npr. samo za jedan studij) ostaju u popisu, ali ne idu
    # na vrh stranice — ondje ide nesto sto se tice vise ljudi. Ako su otvoreni
    # SAMO uski, na vrhu stoji opca poruka, a oni se vide u popisu ispod.
    siroke = [t for t in otvorene
              if not usko_map.get((t[0].get("url") or "").rstrip("/"), False)]

    # Poruka "nema otvorenih" uvijek postoji u HTML-u, samo je skrivena dok ima
    # otvorenih. Ako posjetitelju u pregledniku istekne zadnji rok, JS je otkrije
    # — bez toga bi stranica ostala prazna i bez objasnjenja.
    # Bez isticanja pojedinacnog natjecaja na vrhu: sto Zagrepcaninu znaci
    # rok u Sibeniku? Ide ravno na filter i popis.
    skrij = ' style="display:none"' if siroke else ''
    hero = f"""<div class="prazno" id="nema-otvorenih"{skrij}>
  <p class="kad">Sezona kreće u rujnu.</p>
  <p>Većina gradova, županija i sveučilišta natječaje objavljuje između rujna
     i prosinca. Rokovi su kratki, često 15 dana od objave.</p>
  <p>Izvore provjeravamo automatski dvaput tjedno. Čim se neki natječaj otvori,
     pojavit će se ovdje.</p>
</div>"""

    # ---------- sekcije ----------
    sek_otv = ""
    if otvorene:
        sek_otv = (f'<section class="sek" id="sek-otv">'
                   f'<div class="sek-vrh"><h2>Otvoreno za prijave</h2>'
                   f'<span class="broj" data-broj-otv>{len(otvorene)} '
                   f'{oblik(len(otvorene), "natječaj", "natječaja", "natječaja")}'
                   f'</span></div>'
                   f'<div class="grupa">'
                   + "".join(kartica(r, True, p, z) for r, p, z in otvorene)
                   + '<div class="medja">Otvoreno svima u Hrvatskoj</div>'
                   + '<p class="nema-rez">Za odabrano područje nema otvorenih natječaja. '
                     'Pogledaj popis izvora ispod.</p></div></section>')

    sek_zat = ""
    if zatvorene:
        sek_zat = (f'<section class="sek"><div class="sek-vrh"><h2>Izvori koje pratimo</h2>'
                   f'<span class="broj">{len(zatvorene)} '
                   f'{oblik(len(zatvorene), "izvor", "izvora", "izvora")}'
                   f'</span></div>'
                   f'<p class="uvod">Ovdje natječaj trenutno nije otvoren. '
                   f'Provjeravamo ih automatski svaki ponedjeljak i četvrtak.</p>'
                   f'<div class="grupa zatvoreni-omot">'
                   + "".join(kartica(r, False, p, z) for r, p, z in zatvorene)
                   + '<button type="button" class="prekidac" id="prekidac"></button>' 
                   + '<div class="medja">Otvoreno svima u Hrvatskoj</div>'
                   + '<p class="nema-rez">Za odabrano područje nemamo izvora. '
                     'Ako znaš neki, javi nam.</p></div></section>')

    # veze na stranice po zupanijama (i za korisnike i za trazilice)
    from stranice import slug as _slug
    _zup = sorted({z if z else p for _, p, z in otvorene + zatvorene if p != SVI})
    sek_zup = ('<section class="sek"><div class="sek-vrh">'
               '<h2>Pregled po županijama</h2></div>'
               '<p class="uvod">Svaka županija ima svoju stranicu s popisom '
               'natječaja i rokovima.</p><div class="popis-zup">'
               + "".join(f'<a href="zupanija/{_slug(z)}.html">'
                         f'{z.replace(" županija","")}</a>' for z in _zup)
               + '</div></section>')

    js = JS_ROKOVI + JS.replace("__RAZMOTANO__",
                                "false" if SKLOPI_DRZAVNE else "true")

    ld = json.dumps({
        "@context": "https://schema.org",
        "@type": "WebSite",
        "name": "Stipendije.hr",
        "alternateName": "Stipendije u Hrvatskoj",
        "url": BAZA + "/",
        "inLanguage": "hr-HR",
        "description": ("Pregled otvorenih natječaja za stipendije u Hrvatskoj "
                        "— iznosi, rokovi prijave i upute."),
    }, ensure_ascii=False)

    html = glava(
        "Stipendije u Hrvatskoj — otvoreni natječaji, iznosi i rokovi",
        "Svi otvoreni natječaji za stipendije u Hrvatskoj na jednom mjestu. "
        "Iznosi, rokovi prijave i upute — provjereno dvaput tjedno.",
        CSS_INDEX,
        '<script type="application/ld+json">' + ld + '</script>')
    html += navigacija("natjecaji")
    html += f"""<main>
<section class="hero"><div class="w">
  <span class="meta oznaka">Ažurirano {vrijeme}</span>
  <h1>Sve stipendije u Hrvatskoj<br>na jednom mjestu.</h1>
  {hero}
  <div class="filteri">
    <label class="oznaka-f" for="zupanija">Odaberi županiju</label>
    <select id="zupanija">{izbornik(podrucja)}</select>
    <p class="pojasnjenje">Prikazuju se stipendije te županije, svih njezinih
      gradova i one državne, na koje imaju pravo svi.</p>
  </div>
</div></section>
<div class="w">{sek_otv}{sek_zat}{sek_zup}</div>
</main>
<script>{js}</script>"""
    html += podnozje(ukupno, vrijeme)

    os.makedirs(MAPA, exist_ok=True)
    open(os.path.join(MAPA, "index.html"), "w", encoding="utf-8").write(html)

    from stranice import (vodic, impressum, privatnost,
                          stranica_zupanije, sitemap, slug)
    vodic(MAPA, ukupno, vrijeme)
    impressum(MAPA, ukupno, vrijeme)
    privatnost(MAPA, ukupno, vrijeme)

    # --- zasebna stranica po zupaniji (za trazilice) ---
    sve_zup = sorted({z if z else p for _, p, z in otvorene + zatvorene
                      if p != SVI})
    putevi = [("", "1.0"), ("vodic.html", "0.7"),
              ("impressum.html", "0.3"), ("privatnost.html", "0.3")]

    for zup in sve_zup:
        otv_z = [(r, p, z) for r, p, z in otvorene
                 if z == zup or p == zup]
        zat_z = [(r, p, z) for r, p, z in zatvorene
                 if z == zup or p == zup]
        dio = ""
        if otv_z:
            dio += ('<div class="sek-vrh" id="sek-otv"><h2>Otvoreno za prijave</h2>'
                    f'<span class="broj" data-broj-otv-n>{len(otv_z)}</span></div>'
                    + "".join(kartica(r, True, p, z) for r, p, z in otv_z))
        if zat_z:
            dio += ('<div class="sek-vrh" style="margin-top:2.2rem">'
                    '<h2>Izvori koje pratimo</h2>'
                    f'<span class="broj">{len(zat_z)}</span></div>'
                    + "".join(kartica(r, False, p, z) for r, p, z in zat_z))
        # i zupanijska stranica sama izbacuje istekle rokove
        dio += "<script>" + JS_ROKOVI + "</script>"
        popis = [(r.get("naziv") or "", r.get("url") or "")
                 for r, _, _ in otv_z + zat_z]
        put = stranica_zupanije(MAPA, zup, dio, len(otv_z),
                                len(otv_z) + len(zat_z), sve_zup,
                                ukupno, vrijeme, popis)
        putevi.append((put, "0.8"))

    sitemap(MAPA, putevi)
    print("  stranica po zupanijama: %d" % len(sve_zup))

    print("Napisano %s/index.html, vodic.html, impressum.html" % MAPA)
    print("  otvorenih: %d  zatvorenih: %d  sakriveno: %d"
          % (len(otvorene), len(zatvorene), len(d) - ukupno))
    print("  izbornik: %d zupanija" % len(podrucja))


if __name__ == "__main__":
    main()
