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
from web import (za_koga, _bolji, _isti_natjecaj, _rijeci,
                 opisna_stranica)
from scraper import bez_kvacica

IZVORI = "sources.json"
RUCNI = "rucni.json"
ARHIV = "natjecaji.json"
IZLAZ = "output.json"
POSLANO = "poslano.json"
# Slugovi iz zadnjeg ispisa — `--potvrdi` oznacava tocno njih.
PRIKAZANO = "novosti-prikazano.json"
IZVJESTAJ = "novosti.md"

SVIMA = "cijela hrvatska"   # podrucje koje ide svim pretplatnicima

# Natjecaj koji vrijedi za cijelu Hrvatsku i nema uvjet struke ide svima.
# Ako se jednom pokaze da je toga previse, dosta je prebaciti na False —
# tada nacionalni natjecaji ne idu nikome automatski, nego rukom.
SIROKI_SVIMA = True

# Idu li gradski natjecaji samo onima koji su upisali grad.
#
# Polje GRAD postoji na obrascu tek od 12.10.2026., pa ga vecina
# pretplatnika nema. Dok je tako, dijeljenje po gradu znaci da gradski
# natjecaji ne stignu gotovo nikome: skupina "s upisanim gradom" ima nula
# ljudi, a natjecaj tise propadne nego da je poslan svima u zupaniji.
#
# Dok je False: jedan mail po zupaniji, s gradskim natjecajima unutra,
# svima u toj zupaniji. Kad dovoljno ljudi upise grad, vrati na True i
# podjela se vraca bez ikakve druge izmjene.
DIJELI_PO_GRADU = False

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
    """Adresa za usporedivanje: bez upitnika, sa sidrom.

    Upitnik se brise jer FER u poveznicu stavlja promjenjiv token
    (`?@=33rxj`), pa bi isti natjecaj svaki tjedan izgledao kao novi.
    Sidro se NE brise: na istoj rubrici bas ono razlikuje jedan natjecaj od
    drugog (`#news_93995`). Bez njega su tri FER-ove stipendije ista adresa
    i dvije nestanu."""
    u, _, sidro = (u or "").strip().partition("#")
    u = u.split("?")[0].rstrip("/").lower()
    return u + ("#" + sidro.lower() if sidro else "")


def _adresa_natjecaja(z):
    """Adresa po kojoj se zapis iz arhive prepoznaje kao odredeni natjecaj.

    U arhivi `url` nije natjecaj nego stranica s koje je procitan — za
    procitane zapise to je rubrika, a jedna rubrika nosi vise razlicitih
    natjecaja. Sam natjecaj je u `poveznica`. Usporedba po `url` zato spaja
    sve sto dolazi s iste rubrike: CEEPUS i slovacki program oba vise na
    ampeu.hr/natjecaji, a to su dvije razlicite stipendije.

    Kod rucnog upisa je obrnuto: `url` je sam natjecaj, a `poveznica` zna
    biti naslovnica izvora — tri Privrednikova fonda imaju tri PDF-a kao
    `url` i zajednicki privrednik.hr kao `poveznica`."""
    if z.get("rucni"):
        return _adresa(z.get("url"))
    return _adresa(z.get("poveznica") or z.get("url"))


def _ista_prijava(a, b):
    """Vode li dva zapisa na isti natjecaj.

    Osim izravnog poklapanja hvata se i slucaj kad rucni upis vodi ravno na
    natjecaj, a procitani zapis na rubriku koja na njega pokazuje."""
    ka, kb = _adresa_natjecaja(a), _adresa_natjecaja(b)
    if ka and ka == kb:
        return True
    return bool(ka and ka == _adresa(b.get("url"))) or \
           bool(kb and kb == _adresa(a.get("url")))


def _bez_sidra(u):
    """Adresa stranice, bez sidra. Oznake `usko` u sources.json stoje na
    razini stranice, a zapis sa sidrom (`...stipendije#news_93995`) po punoj
    se adresi s njom ne bi poklopio — pa bi FER-ove stipendije, koje su
    oznacene kao uske, ipak otisle mailom svima."""
    return _adresa(u).split("#")[0]


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
    for u in (z.get("url"), z.get("poveznica")):
        if u and (_adresa(u) in USKO or _bez_sidra(u) in USKO):
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


def _drzavna(z):
    """Je li ovo drzavna stipendija — socio-ekonomska ili STEM.

    Samo te dvije idu mailom svim pretplatnicima. Ostalo sto vrijedi za
    cijelu Hrvatsku (zaklade, Bavarska, Slovacka, CEEPUS, kadrovske
    stipendije tvrtki) stoji na stranici, ali se ne salje: tice se malog
    dijela ljudi, a svaki takav mail trosi paznju koju treba sacuvati za
    natjecaj na koji se prijavljuje pola zemlje.
    """
    from drzavna import MZO_SOCIO, POVEZNICA
    adrese = {a.rstrip("/").lower() for a in (MZO_SOCIO, POVEZNICA) if a}
    spoj = ""
    for k in ("url", "poveznica"):
        v = (z.get(k) or "").strip().rstrip("/").lower()
        if v in adrese:
            return True
        spoj += v
    if "mzom.gov.hr" not in spoj:
        return False
    n = bez_kvacica(z.get("naslov") or "")
    if "rome" in n or "romsk" in n:      # romska drzavna je uza skupina
        return False
    return ("drzavne stipendije" in n or "drzavnih stipendija" in n
            or "stem" in n)


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
        return ("svi",) if (SIROKI_SVIMA and _drzavna(z)) else None

    # Grad Zagreb nema nadredenu zupaniju; podrucje mu je ujedno i odabir
    # u obrascu, pa ide kao zupanija.
    if not zup:
        return ("zupanija", pod) if pod else None

    if pod == zup or pod.endswith("županija"):
        return ("zupanija", zup)

    return ("grad", pod, zup)


def _ime_skupine(k):
    """Naslov odsjecka u izvjestaju."""
    if k[0] == "drzavna":
        return "Svi pretplatnici — državna stipendija"
    if k[2] is None:
        return k[1]
    return k[1] + (" — s upisanim gradom" if k[2] else " — bez upisanog grada")


def _rok(z):
    """Rok u mailu, isti oblik kao na stranici: 18.10.2026. do 23:59.

    Izvori rok pisu recenicom — "od 1. listopada 2026. godine od 7,00 sati do
    zakljucno 18. listopada 2026. godine do 23:59". Stranica to vec ispisuje
    iz isparsiranog datuma, a mail je dosad prepisivao recenicu doslovno, pa
    je isti natjecaj na dva mjesta izgledao kao dva razlicita podatka.

    Sat se zadrzava kad ga izvor navodi: kod roka u 12:00 to je razlika
    izmedu predane i propustene prijave. Kad datum nije isparsiran, ostaje
    izvorni tekst — bolje nesto nego nista."""
    iso = z.get("rok_iso") or ""
    izvorni = (z.get("rok_tekst") or "").strip()
    if len(iso) != 10:
        return izvorni
    g, m, d = iso.split("-")
    out = f"{d}.{m}.{g}."
    # sat se uzima samo ako stoji uz zadnji datum u recenici, da se ne pokupi
    # vrijeme pocetka prijava ("od 7,00 sati do ...")
    rep = izvorni[izvorni.rfind(d) if d in izvorni else 0:]
    sat = re.search(r"\b(\d{1,2}):(\d{2})\b", rep)
    if sat:
        out += f" do {int(sat.group(1))}:{sat.group(2)}"
    return out


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
        # _bolji iz web.py cita "_rucni", ne "rucni" — s krivim
        # imenom prednost rucnog upisa kod izjednacenja nikad ne proradi.
        "_rucni": z.get("rucni"),
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
            # Dva rucna upisa se NIKAD ne spajaju, ni po adresi. Covjek ih
            # je upisao jedan po jedan i svaki je drugi natjecaj; Rovinj ima
            # tri potpore s istim rokom i gotovo istim naslovom, a dva MZO-ova
            # romska upisa kao `url` nose istu rubriku ministarstva.
            if z.get("rucni") and z2.get("rucni"):
                continue
            # Uz adresu se uvijek trazi i isti rok. Sama adresa nije dovoljna
            # jer jedna rubrika zna nositi vise natjecaja pod istim sidrom:
            # FER na istoj stranici ima stipendiju za elektrotehniku, Zavarsar
            # D&ST i Hrvatsku Lutriju, sve tri s adresom koja se ne razlikuje.
            # Razlicit rok zato znaci razlicit natjecaj. Pogrijesimo li tu,
            # posljedica je jedan mail viska — a ne natjecaj koji nestane.
            if rok != (z2.get("rok_iso") or ""):
                continue
            isti = _ista_prijava(z, z2) or _isti_natjecaj(
                par["naslov_natjecaja"], par2["naslov_natjecaja"], bez=bez)
            if isti:
                if _bolji(par, par2):
                    ishod[i] = (z, par)
                break
        else:
            ishod.append((z, par))
    return [z for z, _ in ishod]


def novi_natjecaji():
    # Arhiva je od sada kljucana adresom i rokom, a poslano.json pamti
    # slugove. Ovdje se gleda po slugu, pa oznake poslanog i dalje vrijede.
    sirovo = _ucitaj(ARHIV, {})
    arhiv = {(z.get("slug") or k): z for k, z in sirovo.items()}
    poslano = set(_ucitaj(POSLANO, {}).get("slugovi", []))
    # Opisne stranice ministarstva nisu natjecaji — bez ovoga bi STEM
    # stipendija s nepostojecim rokom otisla na mail svim studentima.
    otvoreni = {s: z for s, z in arhiv.items()
                if _otvoren(z) and not opisna_stranica(z)}
    novi = {s: z for s, z in otvoreni.items() if s not in poslano}
    return arhiv, poslano, otvoreni, novi


def vec_javljeno(novi, arhiv, poslano):
    """Novi zapisi koji su zapravo natjecaj o kojem je vec javljeno.

    Arhiva je kljucana slugom koji nastaje iz naslova sto ga model procita.
    Procita li ga sljedeci tjedan drugim rijecima, nastane novi slug i novi
    "novi natjecaj" — a rijec je o istom natjecaju. Spajanje unutar jednog
    pokretanja to ne hvata jer se stari zapis vise ne nalazi medu novima.

    Bez ove provjere isti bi natjecaj otisao istom covjeku dvaput. Na dan
    pisanja ovoga takvih je bilo jedanaest."""
    stari = [arhiv[s] for s in poslano if s in arhiv]
    pogodak = {}
    for slug, z in novi.items():
        par = _kao_zapis(z)
        pod = (z.get("podrucje") or "").strip()
        rok = z.get("rok_iso") or ""
        bez = tuple(_rijeci(pod)) if pod else ()
        for z2 in stari:
            if (z2.get("podrucje") or "").strip() != pod:
                continue
            par2 = _kao_zapis(z2)
            if z.get("rucni") and z2.get("rucni"):
                continue
            if rok != (z2.get("rok_iso") or ""):
                continue
            if _ista_prijava(z, z2) or _isti_natjecaj(
                    par["naslov_natjecaja"], par2["naslov_natjecaja"], bez=bez):
                pogodak[slug] = (z, z2)
                break
    return pogodak


def razvrstaj(novi):
    """({kljuc: [zapisi]}, [preskoceni]) — jedan mail po osobi, ne po natjecaju.

    Prije je svaki natjecaj isao svojom porukom, pa je covjek iz Rovinja u
    jednom tjednu mogao dobiti cetiri maila. Sada se slaze tjedni pregled:
    svaki pretplatnik dobije najvise jednu poruku sa svime sto ga se tice.

    Kljucevi:
      ("drzavna",)            drzavna stipendija — svima, zasebnom porukom
      ("zup", zupanija, False)  ZUPANIJA = X, bez upisanog grada
      ("zup", zupanija, True)   ZUPANIJA = X, s upisanim gradom

    Dvije skupine po zupaniji postoje zato sto gradski natjecaji idu samo
    onima koji su upisali grad. Tko nije, dobiva isti mail bez gradskog
    dijela. TIP (ucenik/student) se vise ne dijeli u zasebne poruke — kad bi
    se dijelio, covjek s oznakom "oba" dobio bi dvije — nego svaki natjecaj
    u popisu nosi oznaku za koga je.

    Preskoceni su natjecaji koji ne idu nikome na mail. Ne nestaju tiho —
    ispisuju se u izvjestaju da se vidi sto je ostalo samo na stranici."""
    grupe, preskoceni = {}, []
    zupanijski, gradski = {}, {}
    for z in _spoji_iste(list(novi.values())):
        k = _kome(z)
        if k is None:
            preskoceni.append(z)
        elif k[0] == "svi":
            grupe.setdefault(("drzavna",), []).append(z)
        elif k[0] == "zupanija":
            zupanijski.setdefault(k[1], []).append(z)
        else:
            gradski.setdefault(k[2], []).append(z)

    for zup in set(zupanijski) | set(gradski):
        samo_zup = zupanijski.get(zup, [])
        if not DIJELI_PO_GRADU:
            grupe[("zup", zup, None)] = samo_zup + gradski.get(zup, [])
            continue
        if samo_zup:
            grupe[("zup", zup, False)] = list(samo_zup)
        grupe[("zup", zup, True)] = samo_zup + gradski.get(zup, [])

    for v in grupe.values():
        v.sort(key=lambda z: (z.get("rok_iso") or "9999", z.get("naslov") or ""))
    preskoceni.sort(key=lambda z: (z.get("podrucje") or "", z.get("naslov") or ""))
    return grupe, preskoceni


_ZA_KOGA = {"ucenik": " — samo za učenike",
            "student": " — samo za studente",
            "oba": ""}


def _redak(z):
    """Jedan natjecaj u popisu."""
    dio = [f"**{z['naslov']}**"]
    if z.get("podrucje"):
        dio.append(z["podrucje"])
    iz = _iznos(z)
    if iz:
        dio.append(iz)
    rok = _rok(z)
    if rok:
        dio.append(f"rok {rok}")
    veza = z.get("poveznica") or z.get("url") or ""
    return (" · ".join(dio) + _ZA_KOGA.get(_skupina(z), "")
            + (f"\n{veza}" if veza else ""))


def _poruka(zapisi, kljuc):
    """Tekst maila za jednu skupinu primatelja."""
    if kljuc[0] == "drzavna":
        jedan = len(zapisi) == 1
        predmet = (f"Otvoren natječaj: {zapisi[0]['naslov']}" if jedan
                   else f"{len(zapisi)} nova natječaja za državnu stipendiju")
        uvod = ("Otvorio se natječaj za državnu stipendiju:" if jedan
                else "Otvorili su se natječaji za državne stipendije:")
        zasto = ("Ovo dobivaš jer si se prijavio na obavijesti. Državna "
                 "stipendija vrijedi za cijelu Hrvatsku, pa je dobivaju svi.")
        return predmet, (f"{uvod}\n\n"
                         + "\n\n".join(_redak(z) for z in zapisi)
                         + "\n\nCijeli postupak prijave i bodovanje: "
                           "https://stipendije.hr/drzavna-stipendija.html"
                         f"\n\n{zasto}")

    _, zup, s_gradom = kljuc
    # 2-4 "nova natječaja", 5+ "novih natječaja" — "3 novih" bode u oko
    n = len(zapisi)
    koliko = ("Jedan novi natječaj" if n == 1
              else f"{n} nova natječaja" if n <= 4
              else f"{n} novih natječaja")
    predmet = f"{koliko} — {zup}"

    zup_zapisi = [z for z in zapisi if (_kome(z) or ("",))[0] == "zupanija"]
    grad_zapisi = [z for z in zapisi if (_kome(z) or ("",))[0] == "grad"]

    dijelovi = ["Ovo se otvorilo otkad smo se zadnji put javili."]
    if zup_zapisi:
        dijelovi.append(f"**{zup}**\n\n"
                        + "\n\n".join(_redak(z) for z in zup_zapisi))
    if grad_zapisi:
        po_gradu = {}
        for z in grad_zapisi:
            po_gradu.setdefault(z.get("podrucje") or "", []).append(z)
        redci = []
        for grad in sorted(po_gradu):
            redci.append("\n\n".join(_redak(z) for z in po_gradu[grad]))
        dijelovi.append("**Gradovi i općine u tvojoj županiji**\n\n"
                        + "\n\n".join(redci))

    zasto = "Ovo dobivaš jer si se prijavio na obavijesti za svoju županiju."

    # Kad gradski natjecaji idu cijeloj zupaniji, vecini primatelja nijedan
    # nije iz njihovog mjesta. Umjesto da to ispadne promaseni mail, ista
    # poruka pita za mjesto — tako se polje GRAD puni samo od sebe i
    # podjela po gradu jednom postane moguca.
    if grad_zapisi and not DIJELI_PO_GRADU:
        dijelovi.append(
            "Gornji natječaji su iz cijele županije, pa možda nijedan nije iz "
            "tvog mjesta — uvjet je gotovo uvijek prebivalište. Upiši svoje "
            "mjesto u postavkama i ubuduće ti šaljemo samo natječaje koji "
            "vrijede za tebe: {{ update_profile }}")
    elif grad_zapisi:
        zasto = ("Ovo dobivaš jer si se prijavio na obavijesti i upisao svoje "
                 "mjesto.")

    return predmet, ("\n\n".join(dijelovi)
                     + "\n\nSve otvorene stipendije: https://stipendije.hr"
                     f"\n\n{zasto}")


def _filtar(kljuc):
    """Kako to podesiti u Brevu, recenicom koja se moze prepisati."""
    if kljuc[0] == "drzavna":
        return "svi u listi (državna stipendija vrijedi za cijelu Hrvatsku)"
    _, zup, s_gradom = kljuc
    if s_gradom is None:
        return f'ZUPANIJA jednako "{zup}"  — i ništa drugo'
    return (f'ZUPANIJA jednako "{zup}" I GRAD '
            + ("nije prazan" if s_gradom else "je prazan"))


def _blok_vec_javljeno(ponovljeni):
    """Sto je arhiva primila pod novim imenom, a vec je javljeno."""
    if not ponovljeni:
        return []
    L = ["---", "", "## Već javljeno, ne šalje se ponovno", "",
         f"**{len(ponovljeni)}** zapis(a) je u arhivu ušlo pod novim naslovom, "
         "ali je o tom natječaju već javljeno. Označeni su kao poslani i "
         "nigdje ne idu.", "",
         "| novi zapis | već javljeno kao |", "|---|---|"]
    for z, z2 in ponovljeni:
        L.append(f"| {(z.get('naslov') or '')[:46].replace('|', '/')} "
                 f"| {(z2.get('naslov') or '')[:46].replace('|', '/')} |")
    L.append("")
    return L


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


def izvjestaj(grupe, otvoreni, novi, preskoceni=(), ponovljeni=()):
    L = [f"# Nove obavijesti — {date.today().strftime('%d.%m.%Y.')}", ""]
    sumnjivi, greske = zapelo()
    if not novi:
        L += ["Nema novih natječaja od zadnje obavijesti.", "",
              f"Otvorenih ukupno: {len(otvoreni)}. O svima je već javljeno.", ""]
        L += _blok_vec_javljeno(ponovljeni)
        L += _blok_preskoceni(preskoceni)
        L += _blok_zapelo(sumnjivi, greske)
        return "\n".join(L) + "\n"

    ide = sum(len(v) for v in grupe.values())
    L += [f"Ide mailom: **{ide}**" + (
              f"  ·  ne ide: {len(preskoceni)}" if preskoceni else "")
          + (f"  ·  već javljeno: {len(ponovljeni)}" if ponovljeni else ""), "",
          f"Skupina primatelja: **{len(grupe)}**", "",
          "Svaki pretplatnik je u najviše jednoj skupini, pa dobiva jedan "
          "mail. Pošalji svaku skupinu zasebno, pa pokreni "
          "`python novosti.py --potvrdi` da se zabilježi.", ""]

    for kljuc, zapisi in sorted(grupe.items()):
        L += ["---", "",
              f"## {_ime_skupine(kljuc)}", "",
              f"**Filtar u Brevu:** {_filtar(kljuc)}", ""]
        predmet, tijelo = _poruka(zapisi, kljuc)
        L += [f"**Predmet:** {predmet}", "", "```", tijelo, "```", ""]
    L += _blok_vec_javljeno(ponovljeni)
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

    # Zapisi koji su samo novo ime za vec javljeni natjecaj ispadaju prije
    # razvrstavanja. Oznace se kao poslani da se ne vracaju svaki tjedan.
    ponovljeni = vec_javljeno(novi, arhiv, poslano)
    za_slanje = {s: z for s, z in novi.items() if s not in ponovljeni}

    if potvrdi:
        # Oznacava se tocno ono sto je zadnji ispis prikazao, a ne ono sto je
        # novo u ovom trenutku. Bez toga bi natjecaj koji je build dodao
        # izmedu ispisa i potvrde bio oznacen kao poslan, a nikome poslan.
        prikazano = set(_ucitaj(PRIKAZANO, {}).get("slugovi", []))
        if not prikazano:
            print("Nema zabilježenog ispisa. Pokreni prvo `python novosti.py` "
                  "bez --potvrdi, pošalji, pa onda potvrdi.")
            return
        json.dump({"slugovi": sorted(poslano | prikazano)},
                  open(POSLANO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        os.remove(PRIKAZANO)
        print(f"Označeno kao poslano: {len(prikazano - poslano)} natječaja.")
        return

    grupe, preskoceni = razvrstaj(za_slanje)
    open(IZVJESTAJ, "w", encoding="utf-8").write(
        izvjestaj(grupe, otvoreni, za_slanje, preskoceni,
                  list(ponovljeni.values())))

    # Preskoceni (usko) se NE biljeze kao poslani: ako se oznaka pokaze
    # krivom, maknes `"usko": true` i natjecaj se vrati u sljedeci ispis.
    # Ponovljeni se biljeze odmah — o njima je vec javljeno.
    posl_odmah = sorted(poslano | set(ponovljeni))
    if posl_odmah != sorted(poslano):
        json.dump({"slugovi": posl_odmah}, open(POSLANO, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1)
    json.dump({"slugovi": sorted(z["slug"] for v in grupe.values() for z in v
                                 if z.get("slug"))},
              open(PRIKAZANO, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    sumnjivi, greske = zapelo()
    zapinje = len(sumnjivi) + len(greske)

    if ponovljeni:
        print(f"  Već javljeno pod drugim naslovom, preskočeno: {len(ponovljeni)}")
    if not za_slanje:
        print(f"Nema novih natječaja. Otvorenih ukupno: {len(otvoreni)}.")
        if zapinje:
            print(f"ALI: {len(sumnjivi)} izvora s nepročitanim rokom i "
                  f"{len(greske)} nedohvatljivih — popis je u {IZVJESTAJ}.")
        return

    ide = sum(len(v) for v in grupe.values())
    print(f"\nIde mailom: {ide}   ·   skupina primatelja: {len(grupe)}\n")
    for kljuc, zapisi in sorted(grupe.items()):
        print(f"  {_ime_skupine(kljuc):46} {len(zapisi)}")
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
