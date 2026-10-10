# -*- coding: utf-8 -*-
"""
novosti.py — sto je novo od zadnje obavijesti, razvrstano po primateljima

Pokretanje:
    python novosti.py              pokazi sto bi islo van, ne mijenja nista
    python novosti.py --potvrdi    zabiljezi da je poslano

Zasto dva koraka: dok se obavijesti salju rukom, lako je pogledati popis,
poslati ga i tek onda ga oznaciti kao poslan. Da skripta sama oznacava,
jedno pokretanje bez slanja trajno bi pojelo natjecaj i nitko za njega ne
bi saznao.

Sto se smatra novim: natjecaj koji je u arhivi, jos je otvoren, i o kojem
jos nije javljeno. Ne gleda se datum prvog vidjenja nego popis poslanog —
jer pokretanje builda i slanje obavijesti nisu isti dogadaj.

Prvo pokretanje nikome nista ne salje. Samo zapamti sve sto je trenutno
otvoreno, da ljudi koji su se jucer prijavili ne dobiju trideset natjecaja
odjednom.
"""
import json
import os
import sys
from datetime import date

from web import za_koga

ARHIV = "natjecaji.json"
IZLAZ = "output.json"
POSLANO = "poslano.json"
IZVJESTAJ = "novosti.md"

SVIMA = "cijela hrvatska"   # podrucje koje ide svim pretplatnicima


def _ucitaj(put, zadano):
    try:
        with open(put, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return zadano


def _otvoren(z):
    """Rok jos nije prosao. Zapis bez roka racunamo kao otvoren jer ga je
    arhiva upisala samo dok je bio otvoren."""
    r = z.get("rok_iso") or ""
    return (not r) or r >= date.today().isoformat()


def _skupina(z):
    """'ucenik' | 'student' | 'oba' — ista logika kao na stranici."""
    return za_koga({
        "naslov_natjecaja": z.get("naslov"),
        "uvjeti": z.get("uvjeti"),
        "naziv": z.get("izvor_naziv"),
        "iznosi": z.get("iznosi"),
    })


def _kome(z):
    """Kojoj zupaniji pripada. Prazno znaci: svima."""
    pod = (z.get("podrucje") or "").strip()
    if pod.lower() == SVIMA:
        return ""
    return (z.get("zupanija") or pod).strip()


def _iznos(z):
    """Kratki iznos za poruku. Radije nista nego pogresno."""
    mj = [i for i in (z.get("iznosi") or [])
          if i.get("razdoblje") == "mjesecno" and i.get("eur")]
    if not mj:
        return ""
    naj = max(int(i["eur"]) for i in mj)
    return f"{naj} € mjesečno" + (" (najviši iznos)" if len(mj) > 1 else "")


def zapelo():
    """Izvori koji nesto imaju, ali se javno ne prikazuju.

    Dvije vrste. Prvi su oni gdje je natjecaj prepoznat ali mu rok nije
    procitan — takav zapis nikad ne izade na stranicu, pa se o njemu ne
    sazna nista dok ga netko ne pogleda rucno. Drugi su izvori koji se
    uopce ne daju dohvatiti.

    Ovo stoji uz obavijesti namjerno: to je jedini trenutak u tjednu kad
    covjek ionako gleda sto je novo, pa je najmanja sansa da promakne.
    """
    sumnjivi, greske = [], []
    for r in _ucitaj(IZLAZ, []):
        s = r.get("status") or ""
        if s.startswith("PROVJERITI"):
            sumnjivi.append(r)
        elif s.startswith("GREŠKA"):
            greske.append(r)
    kljuc = lambda r: (r.get("naziv") or "").lower()
    return sorted(sumnjivi, key=kljuc), sorted(greske, key=kljuc)


def _blok_zapelo(sumnjivi, greske):
    if not sumnjivi and not greske:
        return ["---", "", "Nijedan izvor ne zapinje. ", ""]
    L = ["---", "", "## Za ručnu provjeru", ""]
    if sumnjivi:
        L += [f"**{len(sumnjivi)} izvora je prepoznalo natječaj, ali mu nije "
              "pročitalo rok.** Takvi se javno ne prikazuju — ako je koji "
              "otvoren, nitko ga ne vidi.", "",
              "| Izvor | Što je pročitano kao rok | Stranica |",
              "|---|---|---|"]
        for r in sumnjivi:
            rok = (r.get("rok_tekst") or "—").replace("|", "/")[:46]
            L.append(f"| {(r.get('naziv') or '')[:40]} | {rok} | {r.get('url') or ''} |")
        L.append("")
    if greske:
        L += [f"**{len(greske)} izvora se ne da dohvatiti.** Ako neki od njih "
              "ima otvoren natječaj, treba ga upisati u `rucni.json`.", "",
              "| Izvor | Problem |", "|---|---|"]
        for r in greske:
            st = (r.get("status") or "").replace("|", "/")[:60]
            L.append(f"| {(r.get('naziv') or '')[:40]} | {st} |")
        L.append("")
    return L


def novi_natjecaji():
    arhiv = _ucitaj(ARHIV, {})
    poslano = set(_ucitaj(POSLANO, {}).get("slugovi", []))
    otvoreni = {s: z for s, z in arhiv.items() if _otvoren(z)}
    novi = {s: z for s, z in otvoreni.items() if s not in poslano}
    return arhiv, poslano, otvoreni, novi


def razvrstaj(novi):
    """{(zupanija, skupina): [zapisi]} — zupanija "" znaci svima."""
    grupe = {}
    for z in novi.values():
        grupe.setdefault((_kome(z), _skupina(z)), []).append(z)
    for v in grupe.values():
        v.sort(key=lambda z: z.get("rok_iso") or "9999")
    return grupe


def _poruka(zapisi, zupanija, skupina):
    """Tekst maila za jednu skupinu primatelja."""
    jedan = len(zapisi) == 1
    if jedan:
        z = zapisi[0]
        predmet = f"Otvoren natječaj: {z['naslov']}"
    else:
        gdje = zupanija or "cijela Hrvatska"
        koliko = ("2 nova natječaja" if len(zapisi) == 2
                  else f"{len(zapisi)} novih natječaja" if len(zapisi) > 4
                  else f"{len(zapisi)} nova natječaja")
        predmet = f"{koliko} — {gdje}"

    redci = []
    for z in zapisi:
        dio = [f"**{z['naslov']}**"]
        if z.get("podrucje"):
            dio.append(z["podrucje"])
        iz = _iznos(z)
        if iz:
            dio.append(iz)
        if z.get("rok_tekst"):
            dio.append(f"rok {z['rok_tekst']}")
        veza = z.get("poveznica") or z.get("url") or ""
        redci.append(" · ".join(dio) + (f"\n{veza}" if veza else ""))

    uvod = ("Otvorio se natječaj koji te se tiče:" if jedan
            else "Otvorili su se novi natječaji koji te se tiču:")
    return predmet, (
        f"{uvod}\n\n" + "\n\n".join(redci) +
        "\n\nSve otvorene stipendije: https://stipendije.hr"
        "\n\nOvo dobivaš jer si se prijavio na obavijesti za svoju županiju."
    )


def _filtar(zupanija, skupina):
    """Kako to podesiti u Brevu, recenicom koja se moze prepisati."""
    if zupanija:
        a = f'ZUPANIJA jednako "{zupanija}"'
    else:
        a = "svi u listi (natječaj vrijedi za cijelu Hrvatsku)"
    if skupina == "oba":
        return a
    return f'{a} I TIP jednako "{skupina}" ili "oba"'


def izvjestaj(grupe, otvoreni, novi):
    L = [f"# Nove obavijesti — {date.today().strftime('%d.%m.%Y.')}", ""]
    sumnjivi, greske = zapelo()
    if not novi:
        L += ["Nema novih natječaja od zadnje obavijesti.", "",
              f"Otvorenih ukupno: {len(otvoreni)}. O svima je već javljeno.", ""]
        L += _blok_zapelo(sumnjivi, greske)
        return "\n".join(L) + "\n"

    L += [f"Novih natječaja: **{len(novi)}**", "",
          f"Skupina primatelja: **{len(grupe)}**", "",
          "Pošalji svaku skupinu zasebno, pa pokreni "
          "`python novosti.py --potvrdi` da se zabilježi.", ""]

    for (zup, sk), zapisi in sorted(grupe.items()):
        L += ["---", "",
              f"## {zup or 'Svi pretplatnici'} — {sk}", "",
              f"**Filtar u Brevu:** {_filtar(zup, sk)}", ""]
        predmet, tijelo = _poruka(zapisi, zup, sk)
        L += [f"**Predmet:** {predmet}", "", "```", tijelo, "```", ""]
    L += _blok_zapelo(sumnjivi, greske)
    return "\n".join(L) + "\n"


def main():
    potvrdi = "--potvrdi" in sys.argv
    arhiv, poslano, otvoreni, novi = novi_natjecaji()

    if not os.path.exists(POSLANO):
        # Prvo pokretanje: zapamti zateceno stanje i ne salji nista.
        json.dump({"slugovi": sorted(otvoreni)}, open(POSLANO, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
        print(f"Prvo pokretanje. Zapamćeno {len(otvoreni)} otvorenih natječaja, "
              f"ništa se ne šalje.\nOd sljedećeg puta javlja samo ono što se "
              f"otvori poslije ovoga.")
        return

    grupe = razvrstaj(novi)
    open(IZVJESTAJ, "w", encoding="utf-8").write(izvjestaj(grupe, otvoreni, novi))

    if potvrdi:
        if not novi:
            print("Nema ničega za označiti.")
            return
        json.dump({"slugovi": sorted(poslano | set(novi))},
                  open(POSLANO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        print(f"Označeno kao poslano: {len(novi)} natječaja.")
        return

    sumnjivi, greske = zapelo()
    zapinje = len(sumnjivi) + len(greske)

    if not novi:
        print(f"Nema novih natječaja. Otvorenih ukupno: {len(otvoreni)}.")
        if zapinje:
            print(f"ALI: {len(sumnjivi)} izvora s nepročitanim rokom i "
                  f"{len(greske)} nedohvatljivih — popis je u {IZVJESTAJ}.")
        return

    print(f"\nNovih natječaja: {len(novi)}   ·   skupina primatelja: {len(grupe)}\n")
    for (zup, sk), zapisi in sorted(grupe.items()):
        print(f"  {zup or 'SVI':32} {sk:8} {len(zapisi)}")
    if zapinje:
        print(f"\nZa ručnu provjeru: {len(sumnjivi)} s nepročitanim rokom, "
              f"{len(greske)} nedohvatljivih")
    print(f"\nTekstovi poruka: {IZVJESTAJ}")
    print("Kad pošalješ, pokreni: python novosti.py --potvrdi")


if __name__ == "__main__":
    main()
