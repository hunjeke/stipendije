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
import re
import sys
from datetime import date

# Namjerno se posuduje iz web.py: "isti natjecaj" mora znaciti isto na
# stranici i u mailu. Da novosti.py ima svoju usporedbu, jedno bi se
# popravljalo a drugo zaboravljalo.
from web import za_koga, _adrese, _bolji, _isti_natjecaj, _rijeci

IZVORI = "sources.json"
RUCNI = "rucni.json"
ARHIV = "natjecaji.json"
IZLAZ = "output.json"
POSLANO = "poslano.json"
IZVJESTAJ = "novosti.md"

SVIMA = "cijela hrvatska"   # podrucje koje ide svim pretplatnicima

# Natjecaj koji vrijedi za cijelu Hrvatsku i nema uvjet struke ide svima.
# Ako se jednom pokaze da je toga previse, dosta je prebaciti na False —
# tada nacionalni natjecaji ne idu nikome automatski, nego rukom.
SIROKI_SVIMA = True

# Naslovi koji sami po sebi znace usko usmjeren natjecaj. Sluze kao zastita
# za natjecaje koji dodu preko zajednicke popisne stranice, pa ih oznaka
# "usko" iz sources.json ne pokriva — izvor je sirok, natjecaj nije.
# Trazi se cijela rijec: "Roma" u naslovu da, "romanistiku" ne.
USKO_NASLOVI = (
    r"\brom[aieu]\b", r"\bromsk\w*\b",
    r"nacionaln\w+ manjin\w+",
)


def _ucitaj(put, zadano):
    try:
        with open(put, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return zadano


def _adresa(u):
    """Adresa bez upitnika i sidra, za usporedivanje."""
    u = (u or "").strip().split("?")[0].split("#")[0]
    return u.rstrip("/").lower()


def _usko_adrese():
    """Adrese oznacene kao usko usmjerene, iz oba popisa.

    "Usko" znaci: uvjeti su takvi da natjecaj vrijedi za vrlo mali dio
    ljudi na listi — odredena struka, vojna obveza, pripadnost manjini.
    Takav natjecaj stoji na stranici kao i svaki drugi, ali ne ide mailom
    svima u zupaniji. Posalje li se takav natjecaj na 120 adresa, 118
    ljudi dobije poruku koja im ne znaci nista, i sljedecu vise ne otvore.
    """
    a = set()
    for put in (IZVORI, RUCNI):
        for r in _ucitaj(put, []):
            if r.get("usko"):
                a.add(_adresa(r.get("url")))
    a.discard("")
    return a


USKO = _usko_adrese()


def _usko(z):
    """Je li natjecaj usko usmjeren."""
    if _adresa(z.get("url")) in USKO:
        return True
    n = (z.get("naslov") or "").lower()
    return any(re.search(k, n) for k in USKO_NASLOVI)


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
    """Kome natjecaj ide. None znaci: nikome na mail, samo na stranicu.

    Vraca:
      ("svi",)                    svim pretplatnicima
      ("zupanija", ime)           onima koji su odabrali tu zupaniju
      ("grad", mjesto, zupanija)  onima koji su uz zupaniju upisali i mjesto
    """
    if _usko(z):
        return None

    pod = (z.get("podrucje") or "").strip()
    zup = (z.get("zupanija") or "").strip()

    if pod.lower() == SVIMA:
        return ("svi",) if SIROKI_SVIMA else None

    # Grad Zagreb nema nadredenu zupaniju; podrucje mu je ujedno i odabir
    # u obrascu, pa ide kao zupanija.
    if not zup:
        return ("zupanija", pod) if pod else None

    if pod == zup or pod.endswith("županija"):
        return ("zupanija", zup)

    return ("grad", pod, zup)


def _ime_skupine(k):
    """Naslov odsjecka u izvjestaju."""
    if k[0] == "svi":
        return "Svi pretplatnici"
    if k[0] == "zupanija":
        return k[1]
    return f"{k[1]} ({k[2]})"


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


def _kao_zapis(z):
    """Zapis iz arhive u obliku koji usporedbe iz web.py ocekuju."""
    return {
        "naslov_natjecaja": z.get("naslov"),
        "url": z.get("url"),
        "poveznica_natjecaj": z.get("poveznica"),
        "iznos": z.get("iznos"),
        "rok_tekst": z.get("rok_tekst"),
        "uvjeti": z.get("uvjeti"),
        "upute_za_prijavu": z.get("upute_za_prijavu"),
        "rucni": z.get("rucni"),
        "iznosi": z.get("iznosi"),
    }


def _spoji_iste(zapisi):
    """Isti natjecaj pod vise naslova spoji u jedan.

    Arhiva je dodavajuca i kljucana slugom, a slug nastaje iz naslova koji
    model procita. Procita li ga sljedeci put drugim rijecima — "Stipendije
    za vojne studente IT" umjesto "Stipendije za studente IKT tehnologija" —
    u arhivi nastaje jos jedan zapis o istom natjecaju. Stranica to spaja
    prije prikaza, pa se ne vidi; mail bi bez ovoga istu stipendiju poslao
    tri puta istom covjeku.

    Spaja se samo unutar istog podrucja, i to kad vode na istu adresu ili
    kad im je rok isti a naslovi govore o istome drugim rijecima."""
    ishod = []
    for z in zapisi:
        par = _kao_zapis(z)
        pod = (z.get("podrucje") or "").strip()
        bez = tuple(_rijeci(pod)) if pod else ()
        rok = z.get("rok_iso") or ""
        for i, (z2, par2) in enumerate(ishod):
            if (z2.get("podrucje") or "").strip() != pod:
                continue
            isti = bool(_adrese(par) & _adrese(par2))
            # Dva rucna upisa se po naslovu ne spajaju: covjek ih je upisao
            # jedan po jedan i svaki je drugi natjecaj. Rovinj ima tri
            # potpore s istim rokom i gotovo istim naslovom, i to su tri
            # razlicita novca.
            if not isti and z.get("rucni") and z2.get("rucni"):
                continue
            if not isti and rok and rok == (z2.get("rok_iso") or ""):
                isti = _isti_natjecaj(par["naslov_natjecaja"],
                                      par2["naslov_natjecaja"], bez=bez)
            if isti:
                if _bolji(par, par2):
                    ishod[i] = (z, par)
                break
        else:
            ishod.append((z, par))
    return [z for z, _ in ishod]


def novi_natjecaji():
    arhiv = _ucitaj(ARHIV, {})
    poslano = set(_ucitaj(POSLANO, {}).get("slugovi", []))
    otvoreni = {s: z for s, z in arhiv.items() if _otvoren(z)}
    novi = {s: z for s, z in otvoreni.items() if s not in poslano}
    return arhiv, poslano, otvoreni, novi


def razvrstaj(novi):
    """({(kome, skupina): [zapisi]}, [preskoceni]).

    Preskoceni su natjecaji koji ne idu nikome na mail. Ne nestaju tiho —
    ispisuju se u izvjestaju da se vidi sto je ostalo samo na stranici i
    da se oznaka moze ispraviti ako je kriva."""
    grupe, preskoceni = {}, []
    for z in _spoji_iste(list(novi.values())):
        k = _kome(z)
        if k is None:
            preskoceni.append(z)
            continue
        grupe.setdefault((k, _skupina(z)), []).append(z)
    for v in grupe.values():
        v.sort(key=lambda z: z.get("rok_iso") or "9999")
    preskoceni.sort(key=lambda z: (z.get("podrucje") or "", z.get("naslov") or ""))
    return grupe, preskoceni


def _poruka(zapisi, kome, skupina):
    """Tekst maila za jednu skupinu primatelja."""
    jedan = len(zapisi) == 1
    if jedan:
        z = zapisi[0]
        predmet = f"Otvoren natječaj: {z['naslov']}"
    else:
        gdje = "cijela Hrvatska" if kome[0] == "svi" else kome[1]
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

    if kome[0] == "grad":
        zasto = ("Ovo dobivaš jer si u postavkama upisao "
                 f"{kome[1]} kao svoje mjesto.")
    elif kome[0] == "zupanija":
        zasto = "Ovo dobivaš jer si se prijavio na obavijesti za svoju županiju."
    else:
        zasto = ("Ovo dobivaš jer si se prijavio na obavijesti. Ovaj natječaj "
                 "vrijedi za cijelu Hrvatsku.")

    return predmet, (
        f"{uvod}\n\n" + "\n\n".join(redci) +
        "\n\nSve otvorene stipendije: https://stipendije.hr"
        f"\n\n{zasto}"
    )


def _filtar(kome, skupina):
    """Kako to podesiti u Brevu, recenicom koja se moze prepisati."""
    if kome[0] == "svi":
        a = "svi u listi (natječaj vrijedi za cijelu Hrvatsku)"
    elif kome[0] == "zupanija":
        a = f'ZUPANIJA jednako "{kome[1]}"'
    else:
        a = f'GRAD jednako "{kome[1]}" I ZUPANIJA jednako "{kome[2]}"'
    if skupina == "oba":
        return a
    return f'{a} I TIP jednako "{skupina}" ili "oba"'


def _blok_preskoceni(preskoceni):
    """Sto je ostalo samo na stranici i zasto."""
    if not preskoceni:
        return []
    L = ["---", "", "## Ne ide na mail", "",
         f"**{len(preskoceni)}** natječaj(a) je označen kao usko usmjeren pa "
         "ne ide nikome mailom. Na stranici stoji normalno. Ako je koja "
         "oznaka kriva, makni `\"usko\": true` iz `sources.json` ili "
         "`rucni.json` i pokreni ponovno.", "",
         "| Natječaj | Područje | Rok |", "|---|---|---|"]
    for z in preskoceni:
        L.append(f"| {(z.get('naslov') or '')[:52].replace('|', '/')} "
                 f"| {(z.get('podrucje') or '—')} "
                 f"| {(z.get('rok_tekst') or '—')[:22]} |")
    L.append("")
    return L


def izvjestaj(grupe, otvoreni, novi, preskoceni=()):
    L = [f"# Nove obavijesti — {date.today().strftime('%d.%m.%Y.')}", ""]
    sumnjivi, greske = zapelo()
    if not novi:
        L += ["Nema novih natječaja od zadnje obavijesti.", "",
              f"Otvorenih ukupno: {len(otvoreni)}. O svima je već javljeno.", ""]
        L += _blok_preskoceni(preskoceni)
        L += _blok_zapelo(sumnjivi, greske)
        return "\n".join(L) + "\n"

    L += [f"Novih natječaja: **{len(novi)}**", "",
          f"Skupina primatelja: **{len(grupe)}**", "",
          "Pošalji svaku skupinu zasebno, pa pokreni "
          "`python novosti.py --potvrdi` da se zabilježi.", ""]

    for (kome, sk), zapisi in sorted(grupe.items()):
        L += ["---", "",
              f"## {_ime_skupine(kome)} — {sk}", "",
              f"**Filtar u Brevu:** {_filtar(kome, sk)}", ""]
        predmet, tijelo = _poruka(zapisi, kome, sk)
        L += [f"**Predmet:** {predmet}", "", "```", tijelo, "```", ""]
    L += _blok_preskoceni(preskoceni)
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

    grupe, preskoceni = razvrstaj(novi)
    open(IZVJESTAJ, "w", encoding="utf-8").write(
        izvjestaj(grupe, otvoreni, novi, preskoceni))

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
    for (kome, sk), zapisi in sorted(grupe.items()):
        print(f"  {_ime_skupine(kome):32} {sk:8} {len(zapisi)}")
    if preskoceni:
        print(f"\n  Ne ide na mail (usko usmjereno): {len(preskoceni)}")
        for z in preskoceni:
            print(f"    - {(z.get('naslov') or '')[:60]}")
    if zapinje:
        print(f"\nZa ručnu provjeru: {len(sumnjivi)} s nepročitanim rokom, "
              f"{len(greske)} nedohvatljivih")
    print(f"\nTekstovi poruka: {IZVJESTAJ}")
    print("Kad pošalješ, pokreni: python novosti.py --potvrdi")


if __name__ == "__main__":
    main()
