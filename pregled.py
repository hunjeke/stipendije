# -*- coding: utf-8 -*-
"""
Gradi docs/pregled.png — sliku koju WhatsApp, Facebook i Viber pokazuju kad
netko zalijepi poveznicu na stranicu.

Na mobitelu se ta slika prikaze sirinom od tristotinjak piksela, pa sve sto je
na njoj sitno — nestane. Zato je iznos najveci element na slici: to je ono sto
covjeka natjera da klikne. Oznaka "PRIMJER" ostaje dovoljno vidljiva da slika
ne obecava iznos koji nitko ne jamci.

Pokretanje:  python pregled.py
"""
import os

from PIL import Image, ImageDraw, ImageFont
from fontTools.ttLib import TTFont

MAPA = "docs"
FONTOVI = os.path.join(MAPA, "f")
S, V = 1200, 630
NADRES = 2                                   # crtaj dvostruko pa smanji

POZADINA = (242, 244, 248)
TINTA = (20, 27, 45)
SIVA = (86, 95, 118)
PLAVA = (29, 78, 216)
BIJELA = (255, 255, 255)
TRAKA = (219, 224, 234)

# ono sto se mijenja — primjer iznosa i roka
IZNOS = "200 €"
RAZDOBLJE = "mjesečno"
ROK_DANA = 12
UDIO_TRAKE = 0.40                            # koliko je vremena za prijavu proslo


def ttf(ime):
    """woff2 sa stranice -> privremeni ttf koji PIL zna citati."""
    izlaz = f"_{ime}.ttf"
    if not os.path.exists(izlaz):
        f = TTFont(os.path.join(FONTOVI, f"{ime}.woff2"))
        f.flavor = None
        f.save(izlaz)
    return izlaz


def F(ime, vel):
    return ImageFont.truetype(ttf(ime), int(vel * NADRES))


def main():
    k = NADRES
    im = Image.new("RGB", (S * k, V * k), POZADINA)
    d = ImageDraw.Draw(im)

    def tekst(xy, t, font, boja, sidro="ls"):
        d.text((xy[0] * k, xy[1] * k), t, font=font, fill=boja, anchor=sidro)

    def pravokutnik(x0, y0, x1, y1, **kw):
        if "width" in kw:
            kw["width"] = int(kw["width"] * k)
        if "radius" in kw:
            kw["radius"] = int(kw["radius"] * k)
            d.rounded_rectangle((x0 * k, y0 * k, x1 * k, y1 * k), **kw)
        else:
            d.rectangle((x0 * k, y0 * k, x1 * k, y1 * k), **kw)

    L, D = 78, 1122                          # lijevi i desni rub sadrzaja

    # --- zaglavlje ---
    pravokutnik(L, 72, D, 75, fill=TINTA)
    tekst((L, 118), "PREGLED SVIH NATJEČAJA", F("plexmono-500", 20), SIVA)

    # znak + ime
    pravokutnik(L, 146, L + 96, 242, fill=PLAVA, radius=18)
    tekst((L + 48, 196), "S", F("bricolage-800", 62), BIJELA, "mm")
    naslov = F("bricolage-800", 84)
    tekst((L + 124, 226), "Stipendije", naslov, TINTA)
    sir = d.textlength("Stipendije", font=naslov) / k
    tekst((L + 124 + sir, 226), ".hr", naslov, PLAVA)

    tekst((L, 300), "Sve stipendije u Hrvatskoj na jednom mjestu.",
          F("plex-400", 32), TINTA)

    # --- kartica: iznos je glavni ---
    K0, K1 = 346, 556
    pravokutnik(L, K0, D, K1, fill=BIJELA, outline=TINTA, width=3)

    tekst((L + 34, K0 + 44), "IZNOS STIPENDIJE", F("plexmono-500", 19), SIVA)
    x = L + 30
    velik = F("bricolage-800", 118)
    tekst((x, K0 + 160), IZNOS, velik, PLAVA)
    x += d.textlength(IZNOS, font=velik) / k + 22
    tekst((x, K0 + 158), RAZDOBLJE, F("plexmono-500", 34), TINTA)

    # rok desno, manji — prati, ali ne otima pogled
    tekst((D - 34, K0 + 44), "ROK PRIJAVE", F("plexmono-500", 19), SIVA, "rs")
    tekst((D - 34, K0 + 112), f"još {ROK_DANA} dana", F("plex-500", 40), TINTA, "rs")

    # traka: koliko je roka proslo
    pravokutnik(L + 3, K1 - 14, D - 3, K1 - 3, fill=TRAKA)
    pravokutnik(L + 3, K1 - 14, L + 3 + (D - L - 6) * UDIO_TRAKE, K1 - 3, fill=PLAVA)

    # --- podnozje ---
    tekst((L, 600), "Iznosi · rokovi · upute za prijavu", F("plex-400", 26), SIVA)

    im = im.resize((S, V), Image.LANCZOS)
    put = os.path.join(MAPA, "pregled.png")
    im.save(put, optimize=True)
    print(f"Napisano {put} ({os.path.getsize(put)//1024} kB)")

    for ime in ("bricolage-800", "plex-400", "plex-500", "plexmono-500"):
        if os.path.exists(f"_{ime}.ttf"):
            os.remove(f"_{ime}.ttf")


if __name__ == "__main__":
    main()
