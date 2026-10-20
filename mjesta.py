# -*- coding: utf-8 -*-
"""
mjesta.py — sve jedinice lokalne samouprave u Hrvatskoj, po zupanijama

Sluzbeni popis Ministarstva pravosuda i uprave ("Popis zupanija, gradova i
opcina"): 556 jedinica — 128 gradova i 428 opcina. Grad Zagreb nema
podmjesta pa ga ovdje nema; u obrascu je on sam po sebi izbor zupanije.

Zasto cijeli popis, a ne samo mjesta koja pratimo: polje GRAD sluzi i da
saznamo odakle su ljudi. Covjek iz mjesta koje jos ne pratimo mora ga moci
odabrati — inace preskoci polje i ne znamo da je trebao bas to mjesto.
Sto se bira, to je ujedno i popis izvora koje vrijedi dodati sljedece.

Popis se ne mijenja cesto. Kad se promijeni (spajanje opcina, novi grad),
zamijeni cijeli recnik novim izvozom sa sluzbenog popisa.
"""

MJESTA = {
    "Bjelovarsko-bilogorska županija": [
        "Berek", "Bjelovar", "Čazma", "Daruvar", "Dežanovac", "Đulovac",
        "Garešnica", "Grubišno Polje", "Hercegovac", "Ivanska", "Kapela",
        "Končanica", "Nova Rača", "Rovišće", "Šandrovac", "Severin",
        "Sirač", "Štefanje", "Velika Pisanica", "Velika Trnovitica",
        "Veliki Grđevac", "Veliko Trojstvo", "Zrinski Topolovac"
    ],
    "Brodsko-posavska županija": [
        "Bebrina", "Brodski Stupnik", "Bukovlje", "Cernik", "Davor",
        "Donji Andrijevci", "Dragalić", "Garčin", "Gornja Vrba",
        "Gornji Bogićevci", "Gundinci", "Klakar", "Nova Gradiška",
        "Nova Kapela", "Okučani", "Oprisavci", "Oriovac", "Podcrkavlje",
        "Rešetari", "Sibinj", "Sikirevci", "Slavonski Brod",
        "Slavonski Šamac", "Stara Gradiška", "Staro Petrovo Selo",
        "Velika Kopanica", "Vrbje", "Vrpolje"
    ],
    "Dubrovačko-neretvanska županija": [
        "Blato", "Dubrovačko primorje", "Dubrovnik", "Janjina", "Konavle",
        "Korčula", "Kula Norinska", "Lastovo", "Lumbarda", "Metković",
        "Mljet", "Opuzen", "Orebić", "Ploče", "Pojezerje", "Slivno",
        "Smokvica", "Ston", "Trpanj", "Vela Luka", "Zažablje",
        "Župa dubrovačka"
    ],
    "Istarska županija": [
        "Bale-Valle", "Barban", "Brtonigla-Verteneglio", "Buje-Buie",
        "Buzet", "Cerovlje", "Fažana-Fasana", "Funtana-Fontane",
        "Gračišće", "Grožnjan-Grisignana", "Kanfanar", "Karojba",
        "Kaštelir-Labinci-Castelliere-S. Domenica", "Kršan", "Labin",
        "Lanišće", "Ližnjan-Lisignano", "Lupoglav", "Marčana", "Medulin",
        "Motovun-Montona", "Novigrad-Cittanova", "Oprtalj-Portole",
        "Pazin", "Pićan", "Poreč-Parenzo", "Pula-Pola", "Raša",
        "Rovinj-Rovigno", "Sveta Nedelja", "Sveti Lovreč",
        "Sveti Petar u Šumi", "Svetvinčenat", "Tar-Vabriga-Torre Abrega",
        "Tinjan", "Umag-Umago", "Višnjan-Visignano", "Vižinada-Visinada",
        "Vodnjan-Dignano", "Vrsar-Orsera", "Žminj"
    ],
    "Karlovačka županija": [
        "Barilović", "Bosiljevo", "Cetingrad", "Draganić", "Duga Resa",
        "Generalski Stol", "Josipdol", "Kamanje", "Karlovac", "Krnjak",
        "Lasinja", "Netretić", "Ogulin", "Ozalj", "Plaški", "Rakovica",
        "Ribnik", "Saborsko", "Slunj", "Tounj", "Vojnić", "Žakanje"
    ],
    "Koprivničko-križevačka županija": [
        "Đelekovec", "Drnje", "Đurđevac", "Ferdinandovac", "Gola",
        "Gornja Rijeka", "Hlebine", "Kalinovac", "Kalnik",
        "Kloštar Podravski", "Koprivnica", "Koprivnički Bregi",
        "Koprivnički Ivanec", "Križevci", "Legrad", "Molve",
        "Novigrad Podravski", "Novo Virje", "Peteranec",
        "Podravske Sesvete", "Rasinja", "Sokolovac", "Sveti Ivan Žabno",
        "Sveti Petar Orehovec", "Virje"
    ],
    "Krapinsko-zagorska županija": [
        "Bedekovčina", "Budinščina", "Desinić", "Donja Stubica",
        "Đurmanec", "Gornja Stubica", "Hrašćina", "Hum na Sutli",
        "Jesenje", "Klanjec", "Konjščina", "Kraljevec na Sutli", "Krapina",
        "Krapinske Toplice", "Kumrovec", "Lobor", "Mače",
        "Marija Bistrica", "Mihovljan", "Novi Golubovec", "Oroslavje",
        "Petrovsko", "Pregrada", "Radoboj", "Stubičke Toplice",
        "Sveti Križ Začretje", "Tuhelj", "Veliko Trgovišće", "Zabok",
        "Zagorska Sela", "Zlatar", "Zlatar Bistrica"
    ],
    "Ličko-senjska županija": [
        "Brinje", "Donji Lapac", "Gospić", "Karlobag", "Lovinac",
        "Novalja", "Otočac", "Perušić", "Plitvička Jezera", "Senj",
        "Udbina", "Vrhovine"
    ],
    "Međimurska županija": [
        "Belica", "Čakovec", "Dekanovec", "Domašinec", "Donja Dubrava",
        "Donji Kraljevec", "Donji Vidovec", "Goričan", "Gornji Mihaljevec",
        "Kotoriba", "Mala Subotica", "Mursko Središće", "Nedelišće",
        "Orehovica", "Podturen", "Prelog", "Pribislavec", "Selnica",
        "Šenkovec", "Strahoninec", "Štrigova", "Sveta Marija",
        "Sveti Juraj na Bregu", "Sveti Martin na Muri", "Vratišinec"
    ],
    "Osječko-baranjska županija": [
        "Antunovac", "Beli Manastir", "Belišće", "Bilje", "Bizovac",
        "Čeminac", "Čepin", "Đakovo", "Darda", "Donja Motičina",
        "Donji Miholjac", "Draž", "Drenje", "Đurđenovac", "Erdut",
        "Ernestinovo", "Feričanci", "Gorjani", "Jagodnjak",
        "Kneževi Vinogradi", "Koška", "Levanjska Varoš", "Magadenovac",
        "Marijanci", "Našice", "Osijek", "Petlovac", "Petrijevci",
        "Podgorač", "Podravska Moslavina", "Popovac", "Punitovci",
        "Satnica Đakovačka", "Semeljci", "Šodolovci", "Strizivojna",
        "Trnava", "Valpovo", "Viljevo", "Viškovci", "Vladislavci", "Vuka"
    ],
    "Požeško-slavonska županija": [
        "Brestovac", "Čaglin", "Jakšić", "Kaptol", "Kutjevo", "Lipik",
        "Pakrac", "Pleternica", "Požega", "Velika"
    ],
    "Primorsko-goranska županija": [
        "Bakar", "Baška", "Brod Moravice", "Čabar", "Čavle", "Cres",
        "Crikvenica", "Delnice", "Dobrinj", "Fužine", "Jelenje", "Kastav",
        "Klana", "Kostrena", "Kraljevica", "Krk", "Lokve", "Lopar",
        "Lovran", "Mali Lošinj", "Malinska-Dubašnica", "Matulji",
        "Mošćenička Draga", "Mrkopalj", "Novi Vinodolski", "Omišalj",
        "Opatija", "Punat", "Rab", "Ravna Gora", "Rijeka", "Skrad",
        "Vinodolska općina", "Viškovo", "Vrbnik", "Vrbovsko"
    ],
    "Sisačko-moslavačka županija": [
        "Donji Kukuruzari", "Dvor", "Glina", "Gvozd", "Hrvatska Dubica",
        "Hrvatska Kostajnica", "Jasenovac", "Kutina", "Lekenik",
        "Lipovljani", "Majur", "Martinska Ves", "Novska", "Petrinja",
        "Popovača", "Sisak", "Sunja", "Topusko", "Velika Ludina"
    ],
    "Splitsko-dalmatinska županija": [
        "Baška Voda", "Bol", "Brela", "Cista Provo", "Dicmo", "Dugi Rat",
        "Dugopolje", "Gradac", "Hrvace", "Hvar", "Imotski", "Jelsa",
        "Kaštela", "Klis", "Komiža", "Lećevica", "Lokvičići", "Lovreć",
        "Makarska", "Marina", "Milna", "Muć", "Nerežišća", "Okrug", "Omiš",
        "Otok", "Podbablje", "Podgora", "Podstrana", "Postira", "Prgomet",
        "Primorski Dolac", "Proložac", "Pučišća", "Runovići", "Seget",
        "Selca", "Šestanovac", "Sinj", "Solin", "Šolta", "Split",
        "Stari Grad", "Sućuraj", "Supetar", "Sutivan", "Trilj", "Trogir",
        "Tučepi", "Vis", "Vrgorac", "Vrlika", "Zadvarje", "Zagvozd",
        "Zmijavci"
    ],
    "Varaždinska županija": [
        "Bednja", "Beretinec", "Breznica", "Breznički Hum", "Cestica",
        "Donja Voća", "Gornji Kneginec", "Ivanec", "Jalžabet", "Klenovnik",
        "Lepoglava", "Ljubešćica", "Ludbreg", "Mali Bukovec", "Martijanec",
        "Maruševec", "Novi Marof", "Petrijanec", "Sračinec", "Sveti Đurđ",
        "Sveti Ilija", "Trnovec Bartolovečki", "Varaždin",
        "Varaždinske Toplice", "Veliki Bukovec", "Vidovec", "Vinica",
        "Visoko"
    ],
    "Virovitičko-podravska županija": [
        "Čačinci", "Čađavica", "Crnac", "Gradina", "Lukač", "Mikleuš",
        "Nova Bukovica", "Orahovica", "Pitomača", "Slatina", "Sopje",
        "Špišić Bukovica", "Suhopolje", "Virovitica", "Voćin", "Zdenci"
    ],
    "Vukovarsko-srijemska županija": [
        "Andrijaševci", "Babina Greda", "Bogdanovci", "Borovo", "Bošnjaci",
        "Cerna", "Drenovci", "Gradište", "Gunja", "Ilok", "Ivankovo",
        "Jarmina", "Lovas", "Markušica", "Negoslavci", "Nijemci", "Nuštar",
        "Otok", "Privlaka", "Stari Jankovci", "Stari Mikanovci", "Štitar",
        "Tompojevci", "Tordinci", "Tovarnik", "Trpinja", "Vinkovci",
        "Vođinci", "Vrbanja", "Vukovar", "Županja"
    ],
    "Zadarska županija": [
        "Benkovac", "Bibinje", "Biograd na Moru", "Galovac", "Gračac",
        "Jasenice", "Kali", "Kolan", "Kukljica", "Lišane Ostrovičke",
        "Nin", "Novigrad", "Obrovac", "Pag", "Pakoštane", "Pašman",
        "Polača", "Poličnik", "Posedarje", "Povljana", "Preko", "Privlaka",
        "Ražanac", "Sali", "Škabrnja", "Stankovci", "Starigrad", "Sukošan",
        "Sveti Filip i Jakov", "Tkon", "Vir", "Vrsi", "Zadar",
        "Zemunik Donji"
    ],
    "Zagrebačka županija": [
        "Bedenica", "Bistra", "Brckovljani", "Brdovec", "Dubrava",
        "Dubravica", "Dugo Selo", "Farkaševac", "Gradec", "Ivanić-Grad",
        "Jakovlje", "Jastrebarsko", "Klinča Sela", "Kloštar Ivanić",
        "Krašić", "Kravarsko", "Križ", "Luka", "Marija Gorica", "Orle",
        "Pisarovina", "Pokupsko", "Preseka", "Pušća", "Rakovec", "Rugvica",
        "Samobor", "Stupnik", "Sveta Nedelja", "Sveti Ivan Zelina",
        "Velika Gorica", "Vrbovec", "Zaprešić", "Žumberak"
    ],
    "Šibensko-kninska županija": [
        "Bilice", "Biskupija", "Civljane", "Drniš", "Ervenik", "Kijevo",
        "Kistanje", "Knin", "Murter-Kornati", "Pirovac", "Primošten",
        "Promina", "Rogoznica", "Ružić", "Šibenik", "Skradin", "Tisno",
        "Tribunj", "Unešić", "Vodice"
    ],
}
