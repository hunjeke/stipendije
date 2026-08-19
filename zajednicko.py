# -*- coding: utf-8 -*-
"""Zajednicki dijelovi svih stranica: tokeni, CSS, navigacija, podnozje."""

EMAIL = "erik.hunjek@gmail.com"
DOMENA = "stipendije.hr"

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?'
         'family=Bricolage+Grotesque:opsz,wght@12..96,500;12..96,700;12..96,800&'
         'family=IBM+Plex+Sans:wght@400;500;600&'
         'family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">')

CSS = """
:root{
  --papir:#EFF1EC;      /* hladan papir, ne krem */
  --karta:#FFFFFF;
  --tinta:#1E2230;      /* duboka tinta */
  --tinta-2:#5B6274;    /* prigusena */
  --linija:#D9DCD3;
  --otvoreno:#1B6B41;   /* borova zelena */
  --hitno:#A6331E;      /* pecatno crvena */
}
*{box-sizing:border-box}
html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--papir);color:var(--tinta);
  font-family:"IBM Plex Sans",system-ui,sans-serif;font-size:16px;line-height:1.6;
  -webkit-font-smoothing:antialiased}
.w{max-width:780px;margin:0 auto;padding:0 1.15rem}

/* --- navigacija --- */
.vrh{border-bottom:1px solid var(--linija);background:var(--papir);
  position:sticky;top:0;z-index:30}
.vrh .w{display:flex;align-items:center;justify-content:space-between;
  gap:1rem;padding-top:.85rem;padding-bottom:.85rem}
.logo{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;
  font-size:1.02rem;letter-spacing:-.02em;text-decoration:none;color:var(--tinta)}
.logo span{color:var(--otvoreno)}
.nav{display:flex;gap:1.15rem}
.nav a{font-size:.86rem;color:var(--tinta-2);text-decoration:none;
  padding-bottom:2px;border-bottom:1.5px solid transparent}
.nav a:hover{color:var(--tinta)}
.nav a.tu{color:var(--tinta);border-bottom-color:var(--tinta)}

/* --- tipografija --- */
h1{font-family:"Bricolage Grotesque",sans-serif;font-weight:800;
  font-size:clamp(1.9rem,5.5vw,2.7rem);line-height:1.08;letter-spacing:-.028em;
  margin:0 0 .5rem}
h2{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;
  font-size:1.18rem;letter-spacing:-.015em;margin:0}
h3{font-family:"Bricolage Grotesque",sans-serif;font-weight:700;
  font-size:1.04rem;letter-spacing:-.012em;margin:0 0 .15rem;line-height:1.28}
.meta{font-family:"IBM Plex Mono",monospace;font-size:.7rem;
  letter-spacing:.09em;text-transform:uppercase;color:var(--tinta-2)}

/* --- sekcije --- */
.sek{padding:2.6rem 0 0}
.sek-vrh{display:flex;align-items:baseline;gap:.7rem;
  padding-bottom:.7rem;border-bottom:1.5px solid var(--tinta);margin-bottom:1.1rem}
.sek-vrh .broj{font-family:"IBM Plex Mono",monospace;font-size:.78rem;
  color:var(--tinta-2);margin-left:auto}
.uvod{color:var(--tinta-2);font-size:.92rem;margin:-.5rem 0 1.2rem}

/* --- podnozje --- */
footer{margin-top:3.5rem;border-top:1px solid var(--linija);
  padding:1.8rem 0 3rem;font-size:.87rem;color:var(--tinta-2)}
footer p{margin:.55rem 0}
footer a{color:var(--otvoreno)}
footer .sitno{font-family:"IBM Plex Mono",monospace;font-size:.7rem;
  letter-spacing:.05em;margin-top:1.4rem;color:#8A909E}

/* --- upozorenje --- */
.upoz{border-left:3px solid var(--tinta);padding:.2rem 0 .2rem 1rem;
  margin:1.6rem 0 0;font-size:.87rem;color:var(--tinta-2)}
.upoz strong{color:var(--tinta)}

a:focus-visible,button:focus-visible,summary:focus-visible,
input:focus-visible{outline:2px solid var(--otvoreno);outline-offset:2px}
@media (prefers-reduced-motion:reduce){
  *{animation:none!important;transition:none!important}
}
"""


def oblik(n, jd, gjd, gmn):
    """Hrvatski broj + imenica: 1 izvor / 2-4 izvora / 5+ izvora.
    Pazi na 11-14 (uvijek mnozina) i na 21, 31... (jednina)."""
    z_, d = abs(n) % 10, abs(n) % 100
    if d in (11, 12, 13, 14):
        return gmn
    if z_ == 1:
        return jd
    if z_ in (2, 3, 4):
        return gjd
    return gmn


def glava(naslov, opis, dodatni_css="", dodatni_head=""):
    return f"""<!DOCTYPE html>
<html lang="hr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{naslov}</title>
<meta name="description" content="{opis}">
<meta property="og:title" content="{naslov}">
<meta property="og:description" content="{opis}">
<meta property="og:type" content="website">
{FONTS}
{dodatni_head}
<style>{CSS}{dodatni_css}</style>
</head>
<body>"""


def navigacija(tu):
    def k(s):
        return ' class="tu"' if s == tu else ""
    return f"""<header class="vrh"><div class="w">
  <a class="logo" href="./">stipendije<span>.hr</span></a>
  <nav class="nav">
    <a href="./"{k('natjecaji')}>Natječaji</a>
    <a href="vodic.html"{k('vodic')}>Vodič</a>
    <a href="impressum.html"{k('impressum')}>Impressum</a>
  </nav>
</div></header>"""


def podnozje(broj_izvora, vrijeme):
    imenica = oblik(broj_izvora, "izvor", "izvora", "izvora") + " "
    return f"""<footer><div class="w">
  <p><strong>Kontakt:</strong> <a href="mailto:{EMAIL}">{EMAIL}</a></p>
  <p>Nedostaje neka stipendija ili je podatak netočan? Javi nam — ispravljamo brzo.
     Posebno nam je važno ako je netočan <strong>rok prijave</strong>.</p>
  <p>Ne procjenjujemo tvoje šanse za pojedinu stipendiju. Za to pitaj instituciju
     koja je natječaj objavila.</p>
  <p class="sitno">Zadnja provjera {vrijeme} &nbsp;·&nbsp; {broj_izvora} {imenica}&nbsp;·&nbsp; podaci prikupljeni automatski</p>
</div></footer>
</body>
</html>"""
