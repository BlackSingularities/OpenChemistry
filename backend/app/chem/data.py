"""Baza danych chemicznych: jony, układy kwasowo-zasadowe, kompleksy, ciała stałe, gazy, wskaźniki.

Konwencje:
- ilości w molach, objętości w mL, temperatura w °C, czas w s,
- jony H+ i OH- NIE są przechowywane – wynikają z bilansu ładunku (pH liczone przy każdym kroku),
- składniki roztworu to: jony proste ('Na+'), sumy układów kwasowo-zasadowych ('CO3', 'NH3'),
  cząsteczki obojętne ('H2O2') oraz wskaźniki ('ind:phph'),
- barwy podane jako (hex, stężenie odniesienia w mol/dm³) – na tej podstawie liczona jest absorbancja
  (prawo Lamberta-Beera), więc intensywność barwy zależy realistycznie od stężenia.
"""
from __future__ import annotations

from dataclasses import dataclass, field

F = 96485.0
R_GAS = 8.314
MOLAR_GAS_VOLUME = 24.0  # L/mol w 20 °C, 1 atm
T_AMBIENT = 20.0


# ---------------------------------------------------------------------------------------------------------------
# Jony proste (bez właściwości kwasowo-zasadowych)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Ion:
    id: str
    name: str
    charge: int
    mm: float
    color: tuple | None = None
    lam: float = 60.0  # przewodnictwo molowe jonu [S·cm²/mol]
    flame: str | None = None


_ION_ROWS = [
    # id, nazwa, ładunek, masa molowa, barwa, przewodnictwo, płomień
    ("Li+", "kation litu", 1, 6.94, None, 39, "Li"),
    ("Na+", "kation sodu", 1, 22.99, None, 50, "Na"),
    ("K+", "kation potasu", 1, 39.10, None, 74, "K"),
    ("Ag+", "kation srebra", 1, 107.87, None, 62, None),
    ("Mg2+", "kation magnezu", 2, 24.31, None, 106, None),
    ("Ca2+", "kation wapnia", 2, 40.08, None, 119, "Ca"),
    ("Sr2+", "kation strontu", 2, 87.62, None, 119, "Sr"),
    ("Ba2+", "kation baru", 2, 137.33, None, 127, "Ba"),
    ("Cu2+", "kation miedzi(II)", 2, 63.55, ("#5aaee8", 0.5), 107, "Cu"),
    ("Zn2+", "kation cynku", 2, 65.38, None, 106, None),
    ("Fe2+", "kation żelaza(II)", 2, 55.85, ("#b5d99a", 0.5), 108, None),
    ("Fe3+", "kation żelaza(III)", 3, 55.85, ("#e6d7a2", 0.3), 204, None),
    ("Al3+", "kation glinu", 3, 26.98, None, 183, None),
    ("Pb2+", "kation ołowiu(II)", 2, 207.2, None, 142, None),
    ("Sn2+", "kation cyny(II)", 2, 118.71, None, 110, None),
    ("Ni2+", "kation niklu(II)", 2, 58.69, ("#4fb36a", 0.5), 100, None),
    ("Co2+", "kation kobaltu(II)", 2, 58.93, ("#e8708f", 0.12), 110, None),
    ("Mn2+", "kation manganu(II)", 2, 54.94, ("#f0d4dc", 1.0), 107, None),
    ("Cr3+", "kation chromu(III)", 3, 52.00, ("#3d7b62", 0.2), 201, None),
    ("Cl-", "anion chlorkowy", -1, 35.45, None, 76, None),
    ("Br-", "anion bromkowy", -1, 79.90, None, 78, None),
    ("I-", "anion jodkowy", -1, 126.90, None, 77, None),
    ("NO3-", "anion azotanowy(V)", -1, 62.00, None, 71, None),
    ("ClO3-", "anion chloranowy(V)", -1, 83.45, None, 65, None),
    ("MnO4-", "anion manganianowy(VII)", -1, 118.94, ("#b23aa6", 0.002), 61, None),
    ("MnO4^2-", "anion manganianowy(VI)", -2, 118.94, ("#2e8b57", 0.01), 120, None),
    ("S2O3^2-", "anion tiosiarczanowy", -2, 112.13, None, 170, None),
    ("S4O6^2-", "anion tetrationianowy", -2, 224.26, None, 150, None),
    ("SCN-", "anion tiocyjanianowy", -1, 58.08, None, 66, None),
    ("St-", "anion stearynianowy (mydło)", -1, 283.5, None, 30, None),
    ("Tart^2-", "anion winianowy", -2, 148.07, None, 60, None),
    ("Gluc-", "anion glukonianowy", -1, 195.15, None, 30, None),
    ("FeCN6^4-", "anion heksacyjanożelazianowy(II)", -4, 211.95, ("#f2eaa0", 0.1), 440, None),
    ("FeCN6^3-", "anion heksacyjanożelazianowy(III)", -3, 211.95, ("#e8c62a", 0.05), 300, None),
]
IONS: dict[str, Ion] = {r[0]: Ion(*r) for r in _ION_ROWS}


# ---------------------------------------------------------------------------------------------------------------
# Układy kwasowo-zasadowe (formy od najbardziej sprotonowanej)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class AcidSystem:
    id: str
    name: str
    z0: int
    pka: tuple
    forms: tuple
    mm: float
    lam: tuple
    colors: tuple = ()
    volatile: tuple | None = None  # (indeks formy lotnej, gaz, stała Henry'ego 25 °C [M/atm], wsp. temperaturowy)


ACIDS: dict[str, AcidSystem] = {s.id: s for s in [
    AcidSystem("CO3", "węglany", 0, (6.35, 10.33), ("H2CO3", "HCO3-", "CO3^2-"), 60.01, (0, 44, 138),
               volatile=(0, "CO2", 0.034, 0.024)),
    AcidSystem("NH3", "amoniak / jon amonowy", 1, (9.25,), ("NH4+", "NH3"), 17.03, (73, 0),
               volatile=(1, "NH3", 57.0, 0.04)),
    AcidSystem("AcO", "kwas octowy / octany", 0, (4.76,), ("CH3COOH", "CH3COO-"), 60.05, (0, 41)),
    AcidSystem("SO4", "siarczany(VI)", -1, (1.99,), ("HSO4-", "SO4^2-"), 96.06, (50, 160)),
    AcidSystem("PO4", "fosforany(V)", 0, (2.15, 7.20, 12.35), ("H3PO4", "H2PO4-", "HPO4^2-", "PO4^3-"), 94.97,
               (0, 33, 114, 207)),
    AcidSystem("SO3", "siarczany(IV)", 0, (1.85, 7.2), ("H2SO3", "HSO3-", "SO3^2-"), 80.06, (0, 50, 144),
               volatile=(0, "SO2", 1.2, 0.03)),
    AcidSystem("S", "siarczki", 0, (7.0, 12.9), ("H2S", "HS-", "S^2-"), 32.06, (0, 65, 140),
               volatile=(0, "H2S", 0.10, 0.02)),
    AcidSystem("C2O4", "szczawiany", 0, (1.25, 4.27), ("H2C2O4", "HC2O4-", "C2O4^2-"), 88.02, (0, 40, 148)),
    AcidSystem("ClO", "chlorany(I)", 0, (7.53,), ("HClO", "ClO-"), 51.45, (0, 40)),
    AcidSystem("Cr6", "chromiany / dichromiany", -1, (6.5,), ("HCrO4-", "CrO4^2-"), 115.99, (50, 170),
               colors=(("#f08a24", 0.1), ("#f2d31b", 0.1))),
    AcidSystem("Cit", "kwas cytrynowy / cytryniany", 0, (3.13, 4.76, 6.40), ("H3Cit", "H2Cit-", "HCit^2-", "Cit^3-"),
               189.1, (0, 30, 60, 90)),
    AcidSystem("Asc", "kwas askorbinowy (wit. C)", 0, (4.1,), ("H2Asc", "HAsc-"), 175.1, (0, 30)),
    AcidSystem("HCOO", "kwas mrówkowy", 0, (3.75,), ("HCOOH", "HCOO-"), 45.02, (0, 55)),
]}


# ---------------------------------------------------------------------------------------------------------------
# Cząsteczki obojętne w roztworze
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Molecule:
    id: str
    name: str
    mm: float
    color: tuple | None = None
    liquid_density: float | None = None  # g/mL dla cieczy dodawanych objętościowo
    smell: str | None = None
    volatile: tuple | None = None  # (gaz, Henry [M/atm], wsp. temp.)
    fluor: str | None = None


MOLECULES: dict[str, Molecule] = {m.id: m for m in [
    Molecule("H2O2", "nadtlenek wodoru", 34.01),
    Molecule("I2", "jod", 253.8, ("#c07a22", 0.002), volatile=("I2", 3.0, 0.04)),
    Molecule("Br2", "brom", 159.8, ("#e8902a", 0.02), smell="ostry, duszący zapach bromu", volatile=("Br2", 0.75, 0.04)),
    Molecule("Cl2", "chlor", 70.9, ("#e3eeb0", 0.06), smell="ostry, drażniący zapach chloru", volatile=("Cl2", 0.09, 0.03)),
    Molecule("Glc", "glukoza", 180.16),
    Molecule("Fru", "fruktoza", 180.16),
    Molecule("Suc", "sacharoza", 342.3),
    Molecule("Starch", "skrobia (jednostki glukozowe)", 162.1),
    Molecule("EtOH", "etanol", 46.07, liquid_density=0.789, smell="charakterystyczny zapach alkoholu"),
    Molecule("HCHO", "metanal (formaldehyd)", 30.03, smell="ostry, duszący zapach formaliny"),
    Molecule("CH3CHO", "etanal (aldehyd octowy)", 44.05, smell="zapach zielonych jabłek (etanal)"),
    Molecule("EtOAc", "octan etylu", 88.1, smell="przyjemny, owocowy zapach estru"),
    Molecule("Glycerol", "glicerol", 92.09, liquid_density=1.26),
    Molecule("Urea", "mocznik", 60.06),
    Molecule("Protein", "białko (albumina)", 66000.0),
    Molecule("ProteinX", "białko po reakcji ksantoproteinowej", 66000.0, ("#e8c21a", 0.0002)),
    Molecule("Pep", "wiązania peptydowe (jednostki)", 110.0),
    Molecule("Catalase", "katalaza (enzym)", 250000.0),
    Molecule("Detergent", "detergent (płyn do naczyń)", 300.0),
    Molecule("MB", "błękit metylenowy", 319.9, ("#1f5fd0", 2e-5)),
    Molecule("MBH", "leukobłękit metylenowy", 321.9),
    Molecule("Luminol", "luminol", 177.2, fluor="#3fb8ff"),
    Molecule("Fluorescein", "fluoresceina", 332.3, ("#9bd21f", 2e-4), fluor="#7dff4a"),
    Molecule("CuCl_aq", "chlorek miedzi(I) (kompleks)", 99.0),
]}


# ---------------------------------------------------------------------------------------------------------------
# Wskaźniki pH
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Indicator:
    id: str
    name: str
    pka: float | None
    acid: tuple | None  # barwa formy kwasowej (hex, stężenie odniesienia)
    base: tuple | None
    palette: tuple = ()  # dla wskaźników wielobarwnych: ((pH, hex), ...)
    ref: float = 1.5e-5


INDICATORS: dict[str, Indicator] = {i.id: i for i in [
    Indicator("phph", "fenoloftaleina", 9.4, None, ("#e0368f", 1.5e-5)),
    Indicator("mo", "oranż metylowy", 3.7, ("#d9301c", 1.5e-5), ("#f0b21a", 1.5e-5)),
    Indicator("mr", "czerwień metylowa", 5.0, ("#d8263a", 1.5e-5), ("#f2c21a", 1.5e-5)),
    Indicator("btb", "błękit bromotymolowy", 7.1, ("#ecd73a", 1.5e-5), ("#3b6ff0", 1.5e-5)),
    Indicator("litmus", "lakmus", 6.5, ("#e2404a", 1.5e-5), ("#5470e6", 1.5e-5)),
    Indicator("thymol", "błękit tymolowy (zasadowy zakres)", 8.9, ("#efd83a", 1.5e-5), ("#2c4fc0", 1.5e-5)),
    Indicator("univ", "wskaźnik uniwersalny", None, None, None, palette=(
        (0, "#c8102e"), (1, "#d8262a"), (2, "#e8412b"), (3, "#f07b2b"), (4, "#f5a623"), (5, "#f0cf35"),
        (6, "#c4d53b"), (7, "#5fb548"), (8, "#2e9e8f"), (9, "#2f6fc0"), (10, "#3b4ab0"), (11, "#4b3a9e"),
        (12, "#5a2c8c"), (14, "#4a1f73"))),
    Indicator("cabbage", "wyciąg z czerwonej kapusty", None, None, None, palette=(
        (1, "#d6205c"), (3, "#d84a8c"), (5, "#9c4ea8"), (7, "#6a5ab8"), (8, "#3f6fc4"), (9, "#2f9c9a"),
        (10, "#3fae5a"), (12, "#8bc43f"), (13.5, "#e2cf3a"))),
]}


# ---------------------------------------------------------------------------------------------------------------
# Kompleksy: [centrum + ligandy] = β·[centrum]·Π[L]^n
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Complex:
    id: str
    name: str
    center: str
    ligands: tuple  # ((ligand, n), ...)
    logb: float
    charge: int
    color: tuple | None = None
    dlogb_dT: float = 0.0
    lam: float = 60.0


COMPLEXES: list[Complex] = [
    # hydroliza kationów (odpowiada za kwasowy odczyn roztworów soli Fe3+, Al3+, Cu2+...)
    Complex("[Fe(OH)]2+", "hydroksożelazo(III)", "Fe3+", (("OH-", 1),), 11.81, 2, ("#d08a28", 0.05)),
    Complex("[Fe(OH)2]+", "dihydroksożelazo(III)", "Fe3+", (("OH-", 2),), 22.3, 1, ("#b8661c", 0.05)),
    Complex("[Al(OH)]2+", "hydroksoglin", "Al3+", (("OH-", 1),), 9.0, 2),
    Complex("[Cr(OH)]2+", "hydroksochrom(III)", "Cr3+", (("OH-", 1),), 10.1, 2, ("#3d7b62", 0.2)),
    Complex("[Cu(OH)]+", "hydroksomiedź(II)", "Cu2+", (("OH-", 1),), 6.5, 1, ("#5aaee8", 0.5)),
    Complex("[Pb(OH)]+", "hydroksoołów(II)", "Pb2+", (("OH-", 1),), 6.3, 1),
    Complex("[Zn(OH)]+", "hydroksocynk", "Zn2+", (("OH-", 1),), 5.0, 1),
    Complex("[Sn(OH)]+", "hydroksocyna(II)", "Sn2+", (("OH-", 1),), 10.4, 1),
    Complex("[Ni(OH)]+", "hydroksonikiel(II)", "Ni2+", (("OH-", 1),), 4.1, 1, ("#4fb36a", 0.5)),
    Complex("[Co(OH)]+", "hydroksokobalt(II)", "Co2+", (("OH-", 1),), 4.3, 1, ("#e8708f", 0.12)),
    Complex("[Mn(OH)]+", "hydroksomangan(II)", "Mn2+", (("OH-", 1),), 3.4, 1),
    Complex("[Fe(OH)]+", "hydroksożelazo(II)", "Fe2+", (("OH-", 1),), 4.5, 1, ("#b5d99a", 0.5)),
    Complex("[Mg(OH)]+", "hydroksomagnez", "Mg2+", (("OH-", 1),), 2.6, 1),
    Complex("[Cu(NH3)2]2+", "diaminamiedź(II)", "Cu2+", (("NH3", 2),), 7.6, 2, ("#3f7fd8", 0.1)),
    Complex("[Cu(NH3)4]2+", "tetraaminamiedź(II)", "Cu2+", (("NH3", 4),), 12.6, 2, ("#3f63ee", 0.012)),
    Complex("[CuCl4]2-", "tetrachloromiedzian(II)", "Cu2+", (("Cl-", 4),), -1.0, -2, ("#86b52e", 0.2)),
    Complex("[Ag(NH3)2]+", "diaminasrebro(I)", "Ag+", (("NH3", 2),), 7.2, 1),
    Complex("[Zn(NH3)4]2+", "tetraaminacynk", "Zn2+", (("NH3", 4),), 9.5, 2),
    Complex("[Ni(NH3)6]2+", "heksaaminanikiel(II)", "Ni2+", (("NH3", 6),), 8.6, 2, ("#6a5fd6", 0.2)),
    Complex("[Zn(OH)4]2-", "tetrahydroksocynkan", "Zn2+", (("OH-", 4),), 15.5, -2),
    Complex("[Al(OH)4]-", "tetrahydroksoglinian", "Al3+", (("OH-", 4),), 33.0, -1),
    Complex("[Pb(OH)3]-", "trihydroksoołowian(II)", "Pb2+", (("OH-", 3),), 14.5, -1),
    Complex("[Cr(OH)4]-", "tetrahydroksochromian(III)", "Cr3+", (("OH-", 4),), 29.9, -1, ("#3c8c3c", 0.1)),
    Complex("[Fe(SCN)]2+", "tiocyjanianożelazo(III)", "Fe3+", (("SCN-", 1),), 3.0, 2, ("#ee3a2a", 1.5e-4)),
    Complex("[Fe(SCN)2]+", "ditiocyjanianożelazo(III)", "Fe3+", (("SCN-", 2),), 4.6, 1, ("#e8342a", 1.5e-4)),
    Complex("[Ag(S2O3)2]3-", "ditiosiarczanosrebrzan(I)", "Ag+", (("S2O3^2-", 2),), 13.5, -3),
    Complex("[CoCl4]2-", "tetrachlorokobaltan(II)", "Co2+", (("Cl-", 4),), -2.9, -2, ("#2f55d8", 0.05), 0.045),
    Complex("[Cu(Tart)2]2-", "winianowy kompleks miedzi(II) (płyn Fehlinga)", "Cu2+", (("Tart^2-", 2),), 19.0, -2,
            ("#1e4fc4", 0.05)),
    Complex("[Cu(Pep)2(OH)2]", "kompleks biuretowy", "Cu2+", (("Pep", 2), ("OH-", 2)), 22.0, 0, ("#7a3fa8", 0.004)),
    Complex("I3-", "anion trijodkowy", "I2", (("I-", 1),), 2.85, -1, ("#8a4512", 0.004)),
    Complex("I2·skrobia", "kompleks jod-skrobia", "I2", (("I-", 1), ("Starch", 1)), 7.6, -1, ("#151a52", 4e-4)),
]


# ---------------------------------------------------------------------------------------------------------------
# Gazy
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Gas:
    id: str
    name: str
    mm: float
    color: str | None = None  # barwa przy czystym gazie
    smell: str | None = None
    acidity: int = 0  # wilgotny papierek: -1 kwasowy, +1 zasadowy, 2 odbarwia
    density: float = 1.0  # względem powietrza


GASES: dict[str, Gas] = {g.id: g for g in [
    Gas("O2", "tlen", 32.0, density=1.1),
    Gas("N2", "azot", 28.0, density=0.97),
    Gas("H2", "wodór", 2.02, density=0.07),
    Gas("CO2", "tlenek węgla(IV)", 44.0, acidity=-1, density=1.52),
    Gas("CO", "tlenek węgla(II)", 28.0, density=0.97),
    Gas("NH3", "amoniak", 17.03, smell="ostry, duszący zapach amoniaku", acidity=1, density=0.59),
    Gas("HCl", "chlorowodór", 36.46, smell="ostry, drażniący zapach chlorowodoru", acidity=-1, density=1.27),
    Gas("Cl2", "chlor", 70.9, "#bcd34a", "ostry, drażniący zapach chloru", acidity=2, density=2.45),
    Gas("SO2", "tlenek siarki(IV)", 64.07, None, "ostry zapach palonej siarki", acidity=-1, density=2.26),
    Gas("NO2", "tlenek azotu(IV)", 46.0, "#a0471d", "ostry, duszący zapach", acidity=-1, density=1.58),
    Gas("NO", "tlenek azotu(II)", 30.0, density=1.04),
    Gas("H2S", "siarkowodór", 34.08, None, "zapach zgniłych jaj", acidity=-1, density=1.19),
    Gas("C2H2", "etyn (acetylen)", 26.04, None, "charakterystyczny zapach (zanieczyszczenia fosfiną)", density=0.9),
    Gas("C2H4", "eten (etylen)", 28.05, None, "słodkawy zapach", density=0.97),
    Gas("CH4", "metan", 16.04, density=0.55),
    Gas("Br2", "pary bromu", 159.8, "#b5541f", "ostry, duszący zapach bromu", acidity=2, density=5.5),
    Gas("I2", "pary jodu", 253.8, "#8a3fb5", "charakterystyczny zapach jodu", density=8.8),
    Gas("H2O", "para wodna", 18.0, density=0.62),
]}

AIR = {"N2": 0.78, "O2": 0.21, "CO2": 0.0004}


# ---------------------------------------------------------------------------------------------------------------
# Metale (do reakcji wypierania, z kwasami i wodą)
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Metal:
    id: str
    ion: str
    n: int  # liczba elektronów
    e0: float
    k_acid: float  # stała szybkości z H+
    k_water: float = 0.0  # stała szybkości z wodą (zimną)
    k_hot_water: float = 0.0
    k_disp: float = 5e-4
    passivating: bool = False
    amphoteric: bool = False


METALS: dict[str, Metal] = {m.id: m for m in [
    Metal("K", "K+", 1, -2.93, 0.02, k_water=5e-3),
    Metal("Na", "Na+", 1, -2.71, 0.01, k_water=1.7e-3),
    Metal("Li", "Li+", 1, -3.04, 0.004, k_water=4e-4),
    Metal("Ca", "Ca2+", 2, -2.87, 0.003, k_water=2e-4),
    Metal("Mg", "Mg2+", 2, -2.37, 4e-4, k_water=2e-10, k_hot_water=4e-6),
    Metal("Al", "Al3+", 3, -1.66, 6e-5, passivating=True, amphoteric=True),
    Metal("Zn", "Zn2+", 2, -0.76, 1.2e-4, amphoteric=True),
    Metal("Fe", "Fe2+", 2, -0.44, 6e-6),
    Metal("Ni", "Ni2+", 2, -0.25, 1.5e-6),
    Metal("Sn", "Sn2+", 2, -0.14, 1.5e-6),
    Metal("Pb", "Pb2+", 2, -0.13, 1e-7),
    Metal("Cu", "Cu2+", 2, 0.34, 0.0),
    Metal("Ag", "Ag+", 1, 0.80, 0.0),
]}

# pary utleniacz/reduktor (jon -> produkt redukcji) do reakcji wypierania i ogniw
REDUCIBLE = [
    # jon, produkt (metal lub jon), liczba elektronów, E°
    ("Ag+", "Ag", 1, 0.80),
    ("Fe3+", "Fe2+", 1, 0.77),
    ("Cu2+", "Cu", 2, 0.34),
    ("Pb2+", "Pb", 2, -0.13),
    ("Sn2+", "Sn", 2, -0.14),
    ("Ni2+", "Ni", 2, -0.25),
    ("Fe2+", "Fe", 2, -0.44),
    ("Zn2+", "Zn", 2, -0.76),
]


# ---------------------------------------------------------------------------------------------------------------
# Ciała stałe
# ---------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Solid:
    id: str
    name: str
    formula: str
    mm: float
    color: str
    kind: str  # 'ppt' trudno rozpuszczalny (Ksp), 'salt' rozpuszczalny (rozpuszczalność), 'metal', 'inert', 'organic'
    comp: tuple = ()  # skład jonowy: ((gatunek wolny, ν), ...) – gatunki: jony proste, formy układów, 'OH-'
    logksp: float | None = None
    dlogksp_dT: float = 0.0
    solub: tuple = ()  # rozpuszczalność g/100 g wody: ((T, s), ...) liczona na sól bezwodną
    anh_mm: float | None = None  # masa molowa soli bezwodnej (dla hydratów)
    dh_sol: float = 0.0  # entalpia rozpuszczania kJ/mol
    k_dis: float = 0.2  # stała szybkości rozpuszczania 1/s
    settle: float = 20.0  # czas sedymentacji [s]
    scatter: float = 1.0  # zdolność mętnienia
    style: str = "powder"  # wygląd: powder, crystals, granules, ribbon, nail, foil, wire, curdy, gel, deposit, ...
    density: float = 2.5
    flame: str | None = None
    mp: float | None = None
    melt_color: str | None = None
    note: str | None = None
    nucleation: float = 0.02  # przesycenie potrzebne do zarodkowania (log)


def _s(*a, **k):
    return Solid(*a, **k)


_SOLIDS = [
    # ---------------- osady trudno rozpuszczalne ----------------
    _s("AgCl", "chlorek srebra", "AgCl", 143.32, "#f4f4ef", "ppt", (("Ag+", 1), ("Cl-", 1)), -9.75, 0.03,
       settle=14, style="curdy", density=5.6),
    _s("AgBr", "bromek srebra", "AgBr", 187.77, "#efe3b2", "ppt", (("Ag+", 1), ("Br-", 1)), -12.3, settle=16,
       style="curdy", density=6.5),
    _s("AgI", "jodek srebra", "AgI", 234.77, "#efda6a", "ppt", (("Ag+", 1), ("I-", 1)), -16.07, settle=18,
       style="curdy", density=5.7),
    _s("Ag2CrO4", "chromian(VI) srebra", "Ag2CrO4", 331.73, "#a8331f", "ppt", (("Ag+", 2), ("CrO4^2-", 1)), -11.95,
       settle=20, density=5.6),
    _s("Ag2CO3", "węglan srebra", "Ag2CO3", 275.75, "#efe8cf", "ppt", (("Ag+", 2), ("CO3^2-", 1)), -11.07, settle=20),
    _s("Ag3PO4", "fosforan(V) srebra", "Ag3PO4", 418.58, "#e8cf3b", "ppt", (("Ag+", 3), ("PO4^3-", 1)), -16.05,
       settle=20),
    _s("Ag2O", "tlenek srebra", "Ag2O", 231.74, "#4f3d2c", "ppt", (("Ag+", 2), ("OH-", 2)), -15.4, settle=25),
    _s("Ag2S", "siarczek srebra", "Ag2S", 247.8, "#1b1b1b", "ppt", (("Ag+", 2), ("S^2-", 1)), -49.2, settle=25),
    _s("Ag2SO4", "siarczan(VI) srebra", "Ag2SO4", 311.8, "#f5f5f0", "ppt", (("Ag+", 2), ("SO4^2-", 1)), -4.92,
       settle=12, style="crystals"),
    _s("BaSO4", "siarczan(VI) baru", "BaSO4", 233.39, "#f7f7f5", "ppt", (("Ba2+", 1), ("SO4^2-", 1)), -9.96,
       settle=40, scatter=1.4, density=4.5),
    _s("BaCO3", "węglan baru", "BaCO3", 197.34, "#f5f5f2", "ppt", (("Ba2+", 1), ("CO3^2-", 1)), -8.59, settle=30),
    _s("BaCrO4", "chromian(VI) baru", "BaCrO4", 253.37, "#f2df5a", "ppt", (("Ba2+", 1), ("CrO4^2-", 1)), -9.93,
       settle=30),
    _s("BaC2O4", "szczawian baru", "BaC2O4", 225.3, "#f5f5f2", "ppt", (("Ba2+", 1), ("C2O4^2-", 1)), -6.8, settle=25),
    _s("CaCO3", "węglan wapnia", "CaCO3", 100.09, "#f4f4f0", "ppt", (("Ca2+", 1), ("CO3^2-", 1)), -8.48,
       settle=30, density=2.7, nucleation=0.8),
    _s("CaCO3_chips", "marmur (węglan wapnia)", "CaCO3", 100.09, "#ece8df", "ppt", (("Ca2+", 1), ("CO3^2-", 1)),
       -8.48, k_dis=0.004, settle=0.5, style="chips", density=2.7),
    _s("CaSO4", "siarczan(VI) wapnia", "CaSO4", 136.14, "#f4f4f0", "ppt", (("Ca2+", 1), ("SO4^2-", 1)), -4.31,
       settle=20),
    _s("Ca(OH)2", "wodorotlenek wapnia", "Ca(OH)2", 74.09, "#f4f4f2", "ppt", (("Ca2+", 1), ("OH-", 2)), -4.35, -0.008,
       settle=40),
    _s("Ca3(PO4)2", "fosforan(V) wapnia", "Ca3(PO4)2", 310.18, "#f4f4f0", "ppt", (("Ca2+", 3), ("PO4^3-", 2)), -28.7,
       settle=40, style="gel"),
    _s("CaC2O4", "szczawian wapnia", "CaC2O4", 128.1, "#f4f4f0", "ppt", (("Ca2+", 1), ("C2O4^2-", 1)), -8.64,
       settle=30),
    _s("Ca(St)2", "stearynian wapnia (kłaczki)", "Ca(C17H35COO)2", 607.0, "#efede4", "ppt", (("Ca2+", 1), ("St-", 2)),
       -12.0, settle=60, style="curdy", density=1.0),
    _s("Mg(St)2", "stearynian magnezu", "Mg(C17H35COO)2", 591.2, "#efede4", "ppt", (("Mg2+", 1), ("St-", 2)), -10.5,
       settle=60, style="curdy", density=1.0),
    _s("SrSO4", "siarczan(VI) strontu", "SrSO4", 183.68, "#f4f4f0", "ppt", (("Sr2+", 1), ("SO4^2-", 1)), -6.46,
       settle=25),
    _s("SrCO3", "węglan strontu", "SrCO3", 147.63, "#f4f4f0", "ppt", (("Sr2+", 1), ("CO3^2-", 1)), -9.03, settle=30),
    _s("MgCO3", "węglan magnezu", "MgCO3", 84.31, "#f4f4f0", "ppt", (("Mg2+", 1), ("CO3^2-", 1)), -5.17, settle=30, nucleation=0.8),
    _s("Mg(OH)2", "wodorotlenek magnezu", "Mg(OH)2", 58.32, "#f2f2f0", "ppt", (("Mg2+", 1), ("OH-", 2)), -11.25,
       settle=60, style="gel"),
    _s("PbCl2", "chlorek ołowiu(II)", "PbCl2", 278.1, "#f4f4f2", "ppt", (("Pb2+", 1), ("Cl-", 2)), -4.77, 0.012,
       settle=15, style="crystals"),
    _s("PbI2", "jodek ołowiu(II)", "PbI2", 461.0, "#f2c21b", "ppt", (("Pb2+", 1), ("I-", 2)), -8.01, 0.036,
       settle=25, style="spangles", density=6.2),
    _s("PbSO4", "siarczan(VI) ołowiu(II)", "PbSO4", 303.26, "#f6f6f4", "ppt", (("Pb2+", 1), ("SO4^2-", 1)), -7.6,
       settle=30),
    _s("PbCrO4", "chromian(VI) ołowiu(II)", "PbCrO4", 323.2, "#f1c40f", "ppt", (("Pb2+", 1), ("CrO4^2-", 1)), -12.55,
       settle=30),
    _s("PbS", "siarczek ołowiu(II)", "PbS", 239.3, "#161616", "ppt", (("Pb2+", 1), ("S^2-", 1)), -27.5, settle=30),
    _s("Pb(OH)2", "wodorotlenek ołowiu(II)", "Pb(OH)2", 241.2, "#f4f4f2", "ppt", (("Pb2+", 1), ("OH-", 2)), -14.9,
       settle=40, style="gel"),
    _s("PbCO3", "węglan ołowiu(II)", "PbCO3", 267.2, "#f4f4f2", "ppt", (("Pb2+", 1), ("CO3^2-", 1)), -13.13,
       settle=30),
    _s("Cu(OH)2", "wodorotlenek miedzi(II)", "Cu(OH)2", 97.56, "#5e9fd8", "ppt", (("Cu2+", 1), ("OH-", 2)), -18.6,
       settle=45, style="gel", density=3.4),
    _s("CuCO3", "zasadowy węglan miedzi(II)", "CuCO3·Cu(OH)2", 110.6, "#4fa58c", "ppt", (("Cu2+", 1), ("CO3^2-", 1)),
       -9.86, settle=40),
    _s("CuS", "siarczek miedzi(II)", "CuS", 95.61, "#141414", "ppt", (("Cu2+", 1), ("S^2-", 1)), -36.1, settle=35),
    _s("CuI", "jodek miedzi(I)", "CuI", 190.45, "#efe7d6", "inert", settle=25),
    _s("Cu2O", "tlenek miedzi(I)", "Cu2O", 143.09, "#b0402a", "inert", settle=20, density=6.0),
    _s("CuO", "tlenek miedzi(II)", "CuO", 79.55, "#1d1b1a", "ppt", (("Cu2+", 1), ("OH-", 2)), -20.4, k_dis=0.02,
       settle=8, density=6.3),
    _s("Fe(OH)3", "wodorotlenek żelaza(III)", "Fe(OH)3", 106.87, "#9c4a1c", "ppt", (("Fe3+", 1), ("OH-", 3)), -37.2,
       settle=60, style="gel"),
    _s("Fe(OH)2", "wodorotlenek żelaza(II)", "Fe(OH)2", 89.86, "#6b7d47", "ppt", (("Fe2+", 1), ("OH-", 2)), -16.31,
       settle=50, style="gel"),
    _s("FeS", "siarczek żelaza(II)", "FeS", 87.91, "#1a1a1a", "ppt", (("Fe2+", 1), ("S^2-", 1)), -18.2, settle=30),
    _s("FePO4", "fosforan(V) żelaza(III)", "FePO4", 150.8, "#efe4c4", "ppt", (("Fe3+", 1), ("PO4^3-", 1)), -21.9,
       settle=40),
    _s("Al(OH)3", "wodorotlenek glinu", "Al(OH)3", 78.0, "#f1f1ef", "ppt", (("Al3+", 1), ("OH-", 3)), -33.5,
       settle=70, style="gel"),
    _s("AlPO4", "fosforan(V) glinu", "AlPO4", 121.95, "#f4f4f0", "ppt", (("Al3+", 1), ("PO4^3-", 1)), -20.0,
       settle=40),
    _s("Zn(OH)2", "wodorotlenek cynku", "Zn(OH)2", 99.4, "#f3f3f1", "ppt", (("Zn2+", 1), ("OH-", 2)), -16.5,
       settle=60, style="gel"),
    _s("ZnS", "siarczek cynku", "ZnS", 97.45, "#f4f4f0", "ppt", (("Zn2+", 1), ("S^2-", 1)), -24.7, settle=30),
    _s("ZnCO3", "węglan cynku", "ZnCO3", 125.4, "#f4f4f0", "ppt", (("Zn2+", 1), ("CO3^2-", 1)), -9.94, settle=30),
    _s("Ni(OH)2", "wodorotlenek niklu(II)", "Ni(OH)2", 92.7, "#7fc08a", "ppt", (("Ni2+", 1), ("OH-", 2)), -15.26,
       settle=50, style="gel"),
    _s("Co(OH)2", "wodorotlenek kobaltu(II)", "Co(OH)2", 92.95, "#c77a95", "ppt", (("Co2+", 1), ("OH-", 2)), -14.23,
       settle=50, style="gel"),
    _s("Mn(OH)2", "wodorotlenek manganu(II)", "Mn(OH)2", 88.95, "#ede3d6", "ppt", (("Mn2+", 1), ("OH-", 2)), -12.7,
       settle=50, style="gel"),
    _s("Cr(OH)3", "wodorotlenek chromu(III)", "Cr(OH)3", 103.0, "#5c7f6a", "ppt", (("Cr3+", 1), ("OH-", 3)), -30.2,
       settle=60, style="gel"),
    _s("MgNH4PO4", "fosforan(V) amonu i magnezu", "MgNH4PO4", 137.3, "#f4f4f0", "ppt",
       (("Mg2+", 1), ("NH4+", 1), ("PO4^3-", 1)), -12.6, settle=30, style="crystals"),
    _s("ZnO", "tlenek cynku", "ZnO", 81.38, "#f6f6f2", "ppt", (("Zn2+", 1), ("OH-", 2)), -16.7, k_dis=0.03, settle=10),
    _s("MgO", "tlenek magnezu", "MgO", 40.3, "#f6f6f4", "ppt", (("Mg2+", 1), ("OH-", 2)), -9.0, k_dis=0.01,
       settle=10, dh_sol=-37),
    _s("CaO", "tlenek wapnia (wapno palone)", "CaO", 56.08, "#f2f0ea", "ppt", (("Ca2+", 1), ("OH-", 2)), 2.0,
       k_dis=0.05, settle=10, dh_sol=-82, style="chips"),
    _s("Fe2O3", "tlenek żelaza(III)", "Fe2O3", 159.7, "#8e2f16", "ppt", (("Fe3+", 2), ("OH-", 6)), -78.0, k_dis=0.002,
       settle=10, density=5.2),
    _s("P4O10", "tlenek fosforu(V)", "P4O10", 283.9, "#f5f5f5", "salt", (("H3PO4", 4),), solub=((0, 1000),),
       k_dis=1.0, dh_sol=-300),
    _s("Na2O2", "nadtlenek sodu", "Na2O2", 77.98, "#f2e6a8", "inert", settle=5),
    _s("CaC2", "karbid (węglik wapnia)", "CaC2", 64.1, "#5d5a55", "inert", settle=1, style="chips"),
    _s("ProteinCoag", "ścięte białko", "białko", 66000.0, "#f3f1e8", "inert", settle=80, style="curdy", density=1.1),
    _s("Starch_s", "skrobia", "(C6H10O5)n", 162.1, "#f7f6f1", "organic", settle=15),
    # ---------------- sole rozpuszczalne ----------------
    _s("NaCl", "chlorek sodu", "NaCl", 58.44, "#f7f7f7", "salt", (("Na+", 1), ("Cl-", 1)),
       solub=((0, 35.7), (20, 35.9), (100, 39.2)), dh_sol=3.9, style="crystals", density=2.16),
    _s("KCl", "chlorek potasu", "KCl", 74.55, "#f7f7f7", "salt", (("K+", 1), ("Cl-", 1)),
       solub=((0, 28.0), (20, 34.2), (100, 56.3)), dh_sol=17.2, style="crystals"),
    _s("KNO3", "azotan(V) potasu (saletra)", "KNO3", 101.1, "#f7f7f7", "salt", (("K+", 1), ("NO3-", 1)),
       solub=((0, 13.3), (20, 31.6), (40, 63.9), (60, 110), (80, 169), (100, 246)), dh_sol=34.9, style="needles",
       k_dis=0.15),
    _s("NaNO3", "azotan(V) sodu", "NaNO3", 85.0, "#f7f7f7", "salt", (("Na+", 1), ("NO3-", 1)),
       solub=((0, 73), (20, 88), (100, 180)), dh_sol=20.5, style="crystals"),
    _s("NH4Cl", "chlorek amonu (salmiak)", "NH4Cl", 53.49, "#f7f7f7", "salt", (("NH4+", 1), ("Cl-", 1)),
       solub=((0, 29.4), (20, 37.2), (100, 77.3)), dh_sol=14.8, style="crystals"),
    _s("NH4NO3", "azotan(V) amonu", "NH4NO3", 80.04, "#f7f7f7", "salt", (("NH4+", 1), ("NO3-", 1)),
       solub=((0, 118), (20, 192), (100, 871)), dh_sol=25.7, style="crystals"),
    _s("(NH4)2SO4", "siarczan(VI) amonu", "(NH4)2SO4", 132.14, "#f7f7f7", "salt", (("NH4+", 2), ("SO4^2-", 1)),
       solub=((0, 70.6), (20, 75.4), (100, 103.8)), dh_sol=6.6, style="crystals"),
    _s("NH4SCN", "tiocyjanian amonu", "NH4SCN", 76.12, "#f7f7f7", "salt", (("NH4+", 1), ("SCN-", 1)),
       solub=((0, 120), (20, 163),), dh_sol=22.6, style="crystals"),
    _s("KSCN", "tiocyjanian potasu", "KSCN", 97.18, "#f7f7f7", "salt", (("K+", 1), ("SCN-", 1)),
       solub=((0, 177), (20, 217),), dh_sol=24.2, style="crystals"),
    _s("NaOH", "wodorotlenek sodu", "NaOH", 40.0, "#f7f7f5", "salt", (("Na+", 1), ("OH-", 1)),
       solub=((0, 42), (20, 109), (100, 347)), dh_sol=-44.5, style="pellets", k_dis=0.08),
    _s("KOH", "wodorotlenek potasu", "KOH", 56.11, "#f7f7f5", "salt", (("K+", 1), ("OH-", 1)),
       solub=((0, 97), (20, 112), (100, 178)), dh_sol=-57.6, style="pellets", k_dis=0.08),
    _s("Na2CO3", "węglan sodu (soda)", "Na2CO3", 105.99, "#f7f7f7", "salt", (("Na+", 2), ("CO3^2-", 1)),
       solub=((0, 7), (20, 21.5), (35, 49), (100, 45)), dh_sol=-26.7),
    _s("NaHCO3", "wodorowęglan sodu (soda oczyszczona)", "NaHCO3", 84.01, "#f7f7f7", "salt",
       (("Na+", 1), ("HCO3-", 1)), solub=((0, 6.9), (20, 9.6), (60, 16.4), (100, 23.6)), dh_sol=16.7),
    _s("CaCl2", "chlorek wapnia", "CaCl2", 110.98, "#f7f7f7", "salt", (("Ca2+", 1), ("Cl-", 2)),
       solub=((0, 59.5), (20, 74.5), (100, 159)), dh_sol=-82.8, style="crystals"),
    _s("BaCl2", "chlorek baru", "BaCl2", 208.23, "#f7f7f7", "salt", (("Ba2+", 1), ("Cl-", 2)),
       solub=((0, 31.2), (20, 35.8), (100, 59.4)), dh_sol=-13.2, style="crystals"),
    _s("Ba(OH)2·8H2O", "wodorotlenek baru (oktahydrat)", "Ba(OH)2·8H2O", 315.46, "#f7f7f7", "salt",
       (("Ba2+", 1), ("OH-", 2)), solub=((0, 1.67), (20, 3.89), (50, 13.1), (80, 101)), anh_mm=171.34, dh_sol=63.0,
       style="crystals"),
    _s("CuSO4·5H2O", "siarczan(VI) miedzi(II) – pięciowodny", "CuSO4·5H2O", 249.69, "#2f7ad6", "salt",
       (("Cu2+", 1), ("SO4^2-", 1)), solub=((0, 14.3), (20, 20.7), (40, 28.5), (60, 40), (80, 55), (100, 75.4)),
       anh_mm=159.6, dh_sol=11.5, style="crystals", k_dis=0.12),
    _s("CuSO4", "bezwodny siarczan(VI) miedzi(II)", "CuSO4", 159.6, "#efeee6", "salt", (("Cu2+", 1), ("SO4^2-", 1)),
       solub=((0, 14.3), (20, 20.7), (100, 75.4)), dh_sol=-66.5, k_dis=0.2),
    _s("CuCl2·2H2O", "chlorek miedzi(II)", "CuCl2·2H2O", 170.48, "#3fb07a", "salt", (("Cu2+", 1), ("Cl-", 2)),
       solub=((0, 68.6), (20, 73), (100, 120)), anh_mm=134.45, dh_sol=-17, style="crystals"),
    _s("Cu(NO3)2", "azotan(V) miedzi(II)", "Cu(NO3)2·3H2O", 241.6, "#2f6fd0", "salt", (("Cu2+", 1), ("NO3-", 2)),
       solub=((0, 83), (20, 125), (100, 247)), anh_mm=187.56, style="crystals"),
    _s("FeSO4·7H2O", "siarczan(VI) żelaza(II)", "FeSO4·7H2O", 278.0, "#9fd49a", "salt", (("Fe2+", 1), ("SO4^2-", 1)),
       solub=((0, 15.6), (20, 26.6), (60, 55), (100, 50)), anh_mm=151.9, style="crystals"),
    _s("FeCl3", "chlorek żelaza(III)", "FeCl3·6H2O", 270.3, "#c8862a", "salt", (("Fe3+", 1), ("Cl-", 3)),
       solub=((0, 74), (20, 92), (100, 535)), anh_mm=162.2, dh_sol=-60, style="crystals"),
    _s("ZnSO4", "siarczan(VI) cynku", "ZnSO4·7H2O", 287.6, "#f7f7f7", "salt", (("Zn2+", 1), ("SO4^2-", 1)),
       solub=((0, 41.6), (20, 53.8), (100, 60.5)), anh_mm=161.47, style="crystals"),
    _s("MgSO4", "siarczan(VI) magnezu (sól gorzka)", "MgSO4·7H2O", 246.5, "#f7f7f7", "salt",
       (("Mg2+", 1), ("SO4^2-", 1)), solub=((0, 22), (20, 33.7), (100, 50)), anh_mm=120.37, dh_sol=16, style="needles"),
    _s("Na2SO4", "siarczan(VI) sodu", "Na2SO4", 142.04, "#f7f7f7", "salt", (("Na+", 2), ("SO4^2-", 1)),
       solub=((0, 4.9), (20, 19.5), (32, 49.7), (100, 42.5)), style="crystals"),
    _s("K2SO4", "siarczan(VI) potasu", "K2SO4", 174.26, "#f7f7f7", "salt", (("K+", 2), ("SO4^2-", 1)),
       solub=((0, 7.4), (20, 11.1), (100, 24)), style="crystals"),
    _s("Alum", "ałun glinowo-potasowy", "KAl(SO4)2·12H2O", 474.4, "#f5f5f7", "salt",
       (("K+", 1), ("Al3+", 1), ("SO4^2-", 2)), solub=((0, 3), (20, 5.9), (40, 11.7), (60, 24.8), (80, 71), (100, 154)),
       anh_mm=258.2, dh_sol=42, style="octahedra", k_dis=0.08),
    _s("Al2(SO4)3", "siarczan(VI) glinu", "Al2(SO4)3·18H2O", 666.4, "#f7f7f7", "salt", (("Al3+", 2), ("SO4^2-", 3)),
       solub=((0, 31.2), (20, 36.4), (100, 89)), anh_mm=342.15, style="crystals"),
    _s("AlCl3", "chlorek glinu", "AlCl3·6H2O", 241.4, "#f7f7f7", "salt", (("Al3+", 1), ("Cl-", 3)),
       solub=((20, 45.8),), anh_mm=133.34, dh_sol=-50, style="crystals"),
    _s("KMnO4", "manganian(VII) potasu", "KMnO4", 158.03, "#3a1240", "salt", (("K+", 1), ("MnO4-", 1)),
       solub=((0, 2.8), (20, 6.4), (40, 12.6), (65, 25)), dh_sol=43.6, style="crystals", k_dis=0.06),
    _s("K2MnO4", "manganian(VI) potasu", "K2MnO4", 197.13, "#16402a", "salt", (("K+", 2), ("MnO4^2-", 1)),
       solub=((20, 30),), style="powder"),
    _s("K2Cr2O7", "dichromian(VI) potasu", "K2Cr2O7", 147.09, "#e86a12", "salt", (("K+", 1), ("HCrO4-", 1)),
       solub=((0, 4.9), (20, 12.3), (40, 26.3), (60, 45.6), (80, 73), (100, 102)), dh_sol=35,
       style="crystals"),
    _s("K2CrO4", "chromian(VI) potasu", "K2CrO4", 194.19, "#f2d31b", "salt", (("K+", 2), ("CrO4^2-", 1)),
       solub=((0, 58.2), (20, 62.9), (100, 79.2)), style="crystals"),
    _s("(NH4)2Cr2O7", "dichromian(VI) amonu", "(NH4)2Cr2O7", 126.04, "#e9620f", "salt", (("NH4+", 1), ("HCrO4-", 1)),
       solub=((20, 35.6),), style="crystals"),
    _s("Cr2O3", "tlenek chromu(III)", "Cr2O3", 151.99, "#3f6e2e", "inert", settle=20, style="fluffy"),
    _s("AgNO3", "azotan(V) srebra", "AgNO3", 169.87, "#f7f7f7", "salt", (("Ag+", 1), ("NO3-", 1)),
       solub=((0, 122), (20, 216), (100, 733)), dh_sol=22.6, style="crystals"),
    _s("Pb(NO3)2", "azotan(V) ołowiu(II)", "Pb(NO3)2", 331.2, "#f7f7f7", "salt", (("Pb2+", 1), ("NO3-", 2)),
       solub=((0, 37.5), (20, 54.3), (100, 127)), dh_sol=33.6, style="crystals"),
    _s("KI", "jodek potasu", "KI", 166.0, "#f7f7f7", "salt", (("K+", 1), ("I-", 1)),
       solub=((0, 128), (20, 144), (100, 206)), dh_sol=20.3, style="crystals"),
    _s("KBr", "bromek potasu", "KBr", 119.0, "#f7f7f7", "salt", (("K+", 1), ("Br-", 1)),
       solub=((0, 53.6), (20, 65.3), (100, 102)), dh_sol=19.9, style="crystals"),
    _s("NaBr", "bromek sodu", "NaBr", 102.9, "#f7f7f7", "salt", (("Na+", 1), ("Br-", 1)), solub=((20, 90.8),),
       style="crystals"),
    _s("NaI", "jodek sodu", "NaI", 149.9, "#f7f7f7", "salt", (("Na+", 1), ("I-", 1)), solub=((20, 178),),
       style="crystals"),
    _s("KClO3", "chloran(V) potasu", "KClO3", 122.55, "#f7f7f7", "salt", (("K+", 1), ("ClO3-", 1)),
       solub=((0, 3.3), (20, 7.3), (60, 23.8), (100, 56.3)), dh_sol=41.4, style="crystals"),
    _s("KCl_from", "chlorek potasu", "KCl", 74.55, "#f7f7f7", "salt", (("K+", 1), ("Cl-", 1)),
       solub=((20, 34.2),), style="powder"),
    _s("Na2S2O3", "tiosiarczan sodu", "Na2S2O3·5H2O", 248.2, "#f7f7f7", "salt", (("Na+", 2), ("S2O3^2-", 1)),
       solub=((0, 52.5), (20, 70.1), (100, 245)), anh_mm=158.1, dh_sol=47.4, style="crystals"),
    _s("Na2SO3", "siarczan(IV) sodu", "Na2SO3", 126.04, "#f7f7f7", "salt", (("Na+", 2), ("SO3^2-", 1)),
       solub=((20, 27),), style="powder"),
    _s("Na2S", "siarczek sodu", "Na2S·9H2O", 240.2, "#f0edd8", "salt", (("Na+", 2), ("S^2-", 1)), solub=((20, 18.6),),
       anh_mm=78.04, style="crystals"),
    _s("Na3PO4", "fosforan(V) sodu", "Na3PO4·12H2O", 380.1, "#f7f7f7", "salt", (("Na+", 3), ("PO4^3-", 1)),
       solub=((20, 14.5),), anh_mm=163.94, style="crystals"),
    _s("Na2HPO4", "wodorofosforan(V) sodu", "Na2HPO4", 141.96, "#f7f7f7", "salt", (("Na+", 2), ("HPO4^2-", 1)),
       solub=((20, 7.7),), style="powder"),
    _s("NaAc", "octan sodu", "CH3COONa·3H2O", 136.08, "#f7f7f7", "salt", (("Na+", 1), ("CH3COO-", 1)),
       solub=((0, 36.2), (20, 46.4), (100, 170)), anh_mm=82.03, dh_sol=19.7, style="crystals"),
    _s("H2C2O4", "kwas szczawiowy", "H2C2O4·2H2O", 126.07, "#f7f7f7", "salt", (("H2C2O4", 1),),
       solub=((20, 9.5), (80, 84)), anh_mm=90.03, style="crystals"),
    _s("Na2C2O4", "szczawian sodu", "Na2C2O4", 134.0, "#f7f7f7", "salt", (("Na+", 2), ("C2O4^2-", 1)),
       solub=((20, 3.7),), style="powder"),
    _s("CitricAcid", "kwas cytrynowy", "C6H8O7", 192.12, "#f7f7f7", "salt", (("H3Cit", 1),), solub=((20, 147),),
       dh_sol=22, style="crystals"),
    _s("AscAcid", "kwas askorbinowy (witamina C)", "C6H8O6", 176.12, "#f6f3e6", "salt", (("H2Asc", 1),),
       solub=((20, 33),), style="powder"),
    _s("CoCl2", "chlorek kobaltu(II)", "CoCl2·6H2O", 237.9, "#c2365d", "salt", (("Co2+", 1), ("Cl-", 2)),
       solub=((20, 52.9),), anh_mm=129.84, style="crystals"),
    _s("NiSO4", "siarczan(VI) niklu(II)", "NiSO4·6H2O", 262.85, "#3fa35c", "salt", (("Ni2+", 1), ("SO4^2-", 1)),
       solub=((20, 44.4),), anh_mm=154.75, style="crystals"),
    _s("MnSO4", "siarczan(VI) manganu(II)", "MnSO4·H2O", 169.0, "#f0d8de", "salt", (("Mn2+", 1), ("SO4^2-", 1)),
       solub=((20, 62.9),), anh_mm=151.0, style="powder"),
    _s("Glc_s", "glukoza", "C6H12O6", 180.16, "#f7f7f5", "salt", (("Glc", 1),), solub=((20, 91), (100, 500)),
       dh_sol=11, style="powder"),
    _s("Suc_s", "sacharoza (cukier)", "C12H22O11", 342.3, "#f8f8f6", "salt", (("Suc", 1),),
       solub=((0, 179), (20, 204), (100, 487)), dh_sol=5.4, style="crystals", mp=186, melt_color="#c98a2b"),
    _s("Urea_s", "mocznik", "CO(NH2)2", 60.06, "#f7f7f7", "salt", (("Urea", 1),), solub=((20, 108),), dh_sol=15.1,
       style="crystals"),
    _s("Na_St", "mydło (stearynian sodu)", "C17H35COONa", 306.5, "#f3efe2", "salt", (("Na+", 1), ("St-", 1)),
       solub=((20, 10),), style="flakes"),
    # ---------------- metale ----------------
    _s("Na", "sód", "Na", 22.99, "#c9cdd2", "metal", style="lump", density=0.97, mp=98, flame="Na"),
    _s("K", "potas", "K", 39.10, "#c3c7cf", "metal", style="lump", density=0.89, mp=63, flame="K"),
    _s("Li", "lit", "Li", 6.94, "#b8bcc2", "metal", style="lump", density=0.53, flame="Li"),
    _s("Ca", "wapń", "Ca", 40.08, "#c9c9c4", "metal", style="granules", density=1.55, flame="Ca"),
    _s("Mg", "magnez (wstążka)", "Mg", 24.31, "#b8bec5", "metal", style="ribbon", density=1.74, mp=650),
    _s("Mg_powder", "magnez (proszek)", "Mg", 24.31, "#9aa0a6", "metal", style="powder", density=1.74),
    _s("Al", "glin (folia)", "Al", 26.98, "#cfd5dc", "metal", style="foil", density=2.70, mp=660),
    _s("Al_powder", "glin (proszek)", "Al", 26.98, "#aab0b6", "metal", style="powder", density=2.70),
    _s("Zn", "cynk (granulki)", "Zn", 65.38, "#a9b0b4", "metal", style="granules", density=7.14, mp=420),
    _s("Zn_powder", "pył cynkowy", "Zn", 65.38, "#8a9095", "metal", style="powder", density=7.14),
    _s("Fe", "żelazo (gwóźdź)", "Fe", 55.85, "#7d8287", "metal", style="nail", density=7.87),
    _s("Fe_filings", "opiłki żelaza", "Fe", 55.85, "#5e6366", "metal", style="filings", density=7.87),
    _s("Fe_wool", "wata stalowa", "Fe", 55.85, "#8c9196", "metal", style="wool", density=7.87),
    _s("Cu", "miedź (drut)", "Cu", 63.55, "#c27a45", "metal", style="wire", density=8.96),
    _s("Cu_foil", "miedź (blaszka)", "Cu", 63.55, "#c9824c", "metal", style="foil", density=8.96),
    _s("Cu_dep", "miedź (osad)", "Cu", 63.55, "#b2602f", "metal", style="deposit", density=8.96),
    _s("Ag", "srebro (osad)", "Ag", 107.87, "#c8cbd2", "metal", style="tree", density=10.5),
    _s("Pb", "ołów", "Pb", 207.2, "#6f747a", "metal", style="granules", density=11.3),
    _s("Pb_dep", "ołów (osad – drzewko)", "Pb", 207.2, "#5d6268", "metal", style="tree", density=11.3),
    _s("Sn", "cyna", "Sn", 118.71, "#c3c6c9", "metal", style="granules", density=7.3),
    _s("Ni", "nikiel", "Ni", 58.69, "#a7a9a3", "metal", style="granules", density=8.9),
    # ---------------- substancje proste i inne ----------------
    _s("S", "siarka", "S", 32.06, "#f2db3a", "inert", style="powder", density=2.0, mp=115, melt_color="#b8611c"),
    _s("S_col", "siarka koloidalna", "S", 32.06, "#f0e6a0", "inert", settle=900, scatter=2.5),
    _s("C", "węgiel drzewny", "C", 12.01, "#1c1c1c", "inert", style="chunk", density=0.5),
    _s("C_char", "zwęglona masa (węgiel)", "C", 12.01, "#141210", "inert", style="char", density=0.3),
    _s("P", "fosfor czerwony", "P", 30.97, "#8c2b1e", "inert", style="powder", density=2.3),
    _s("I2_s", "jod (kryształy)", "I2", 253.8, "#2b2236", "inert", style="crystals", density=4.9),
    _s("MnO2", "tlenek manganu(IV)", "MnO2", 86.94, "#2b211b", "inert", settle=12, density=5.0),
    _s("SiO2", "piasek (krzemionka)", "SiO2", 60.08, "#e3d3a6", "inert", settle=2, style="sand"),
    _s("Wax", "parafina (świeca)", "C25H52", 352.7, "#f3eedd", "organic", style="candle", density=0.9, mp=55),
    _s("PrussianBlue", "błękit pruski", "Fe4[Fe(CN)6]3", 859.2, "#1d3b8f", "ppt", (("Fe3+", 4), ("FeCN6^4-", 3)),
       -40.5, settle=80, scatter=1.6),
    _s("TurnbullBlue", "błękit Turnbulla", "Fe3[Fe(CN)6]2", 591.4, "#1f3a92", "ppt", (("Fe2+", 3), ("FeCN6^3-", 2)),
       -30.0, settle=80, scatter=1.6),
    _s("Cu2FeCN6", "heksacyjanożelazian(II) miedzi(II)", "Cu2[Fe(CN)6]", 339.0, "#8a3420", "ppt",
       (("Cu2+", 2), ("FeCN6^4-", 1)), -15.9, settle=60),
    _s("PbO", "tlenek ołowiu(II)", "PbO", 223.2, "#f0c53a", "inert", settle=10),
    _s("Fe3O4", "tlenek żelaza(II,III)", "Fe3O4", 231.5, "#1d1d1f", "inert", settle=8),
    _s("Al2O3", "tlenek glinu", "Al2O3", 101.96, "#f4f2ec", "inert", settle=8),
    _s("Fe_molten", "stopione żelazo", "Fe", 55.85, "#ffb347", "metal", style="molten", density=7.0),
    _s("NaCl_smoke", "chlorek sodu (dym)", "NaCl", 58.44, "#f7f7f7", "salt", (("Na+", 1), ("Cl-", 1)),
       solub=((20, 35.9),), style="powder"),
    _s("FeCl3_smoke", "chlorek żelaza(III) (dym)", "FeCl3", 162.2, "#8e4a1a", "salt", (("Fe3+", 1), ("Cl-", 3)),
       solub=((20, 92),), style="powder"),
    _s("Caramel", "karmel", "—", 300.0, "#7a3f12", "organic", style="melt"),
    _s("Yeast", "drożdże (katalaza)", "—", 1000.0, "#d9c39a", "organic", style="powder"),
    _s("Potato", "plaster ziemniaka (katalaza)", "—", 1000.0, "#efe1b0", "organic", style="slice"),
]
SOLIDS: dict[str, Solid] = {s.id: s for s in _SOLIDS}

# gatunek wolny -> składnik bilansu (do zdejmowania przy strącaniu)
SPECIES_COMPONENT: dict[str, str] = {}
for _sys in ACIDS.values():
    for _f in _sys.forms:
        SPECIES_COMPONENT[_f] = _sys.id
for _ion in IONS:
    SPECIES_COMPONENT[_ion] = _ion
for _m in MOLECULES:
    SPECIES_COMPONENT[_m] = _m

# Barwy płomienia w teście płomieniowym
FLAME_COLORS = {
    "Na": ("#ffb21a", "intensywnie żółta"),
    "K": ("#c58cf0", "fioletowa (różowofioletowa)"),
    "Li": ("#e8203c", "karminowa"),
    "Ca": ("#ff6a1f", "ceglastoczerwona"),
    "Sr": ("#ff1a2e", "czerwona (karminowa)"),
    "Ba": ("#9be04a", "żółtozielona"),
    "Cu": ("#2fd6a0", "zielononiebieska"),
    "B": ("#3fe06a", "zielona"),
}

# Gatunki charakterystyczne dla zapachu w roztworze
SMELL_SPECIES = {
    "CH3COOH": (0.05, "zapach octu"),
    "NH3": (0.02, "ostry zapach amoniaku"),
    "H2S": (1e-4, "zapach zgniłych jaj"),
    "H2SO3": (0.002, "duszący zapach tlenku siarki(IV)"),
    "HClO": (0.01, "zapach chloru (wybielacza)"),
    "HCOOH": (0.1, "ostry zapach kwasu mrówkowego"),
}
