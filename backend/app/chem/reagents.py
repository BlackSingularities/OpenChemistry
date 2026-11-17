"""Katalog odczynników na półce laboratoryjnej."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Reagent:
    id: str
    name: str
    group: str
    kind: str  # solution, solid, liquid (organiczna, osobna faza), gas, indicator
    comp: dict = field(default_factory=dict)  # mol/L składników (solution/indicator) lub {solid_id: 1}
    formula: str = ""
    hazards: tuple = ()
    unit: str = "mL"
    presets: tuple = ()
    org: dict = field(default_factory=dict)  # dla cieczy organicznych: mol/mL
    note: str = ""
    piece: float | None = None  # masa „kawałka” [g]


def sol(id, name, group, comp, formula="", hazards=(), presets=(1, 2, 5, 10, 20), note=""):
    return Reagent(id, name, group, "solution", comp, formula, hazards, "mL", presets, note=note)


def solid(id, name, group, sid, formula="", hazards=(), presets=(0.1, 0.5, 1, 2, 5), piece=None, note=""):
    return Reagent(id, name, group, "solid", {sid: 1}, formula, hazards, "g", presets, piece=piece, note=note)


def ind(id, name, comp, formula=""):
    return Reagent(id, name, "Wskaźniki", "indicator", comp, formula, (), "krople", (1, 2, 3, 5))


def gas(id, name, formula, hazards=()):
    return Reagent(id, name, "Gazy (butle)", "gas", {formula: 1}, formula, hazards, "cylinder", (1,))


A, B, S = "Kwasy", "Zasady", "Sole – roztwory"
R = [
    # ---------------- kwasy ----------------
    sol("HCl_01", "Kwas solny 0,1 mol/dm³", A, {"Cl-": 0.1}, "HCl", ("corr",)),
    sol("HCl_1", "Kwas solny 1 mol/dm³", A, {"Cl-": 1.0}, "HCl", ("corr",)),
    sol("HCl_2", "Kwas solny 2 mol/dm³", A, {"Cl-": 2.0}, "HCl", ("corr",)),
    sol("HCl_6", "Kwas solny 6 mol/dm³", A, {"Cl-": 6.0}, "HCl", ("corr",)),
    sol("HCl_conc", "Kwas solny stężony 36%", A, {"Cl-": 11.6}, "HCl", ("corr", "tox")),
    sol("H2SO4_05", "Kwas siarkowy(VI) 0,5 mol/dm³", A, {"SO4": 0.5}, "H2SO4", ("corr",)),
    sol("H2SO4_1", "Kwas siarkowy(VI) 1 mol/dm³", A, {"SO4": 1.0}, "H2SO4", ("corr",)),
    sol("H2SO4_conc", "Kwas siarkowy(VI) stężony 96%", A, {"SO4": 18.0}, "H2SO4", ("corr",)),
    sol("HNO3_2", "Kwas azotowy(V) 2 mol/dm³", A, {"NO3-": 2.0}, "HNO3", ("corr", "ox")),
    sol("HNO3_conc", "Kwas azotowy(V) stężony 65%", A, {"NO3-": 14.4}, "HNO3", ("corr", "ox", "tox")),
    sol("AcOH_1", "Kwas octowy 1 mol/dm³", A, {"AcO": 1.0}, "CH3COOH", ("irr",)),
    sol("AcOH_conc", "Kwas octowy lodowaty 99%", A, {"AcO": 17.4}, "CH3COOH", ("corr", "flam")),
    sol("H3PO4_1", "Kwas fosforowy(V) 1 mol/dm³", A, {"PO4": 1.0}, "H3PO4", ("corr",)),
    sol("H2C2O4_025", "Kwas szczawiowy 0,25 mol/dm³", A, {"C2O4": 0.25}, "H2C2O4", ("tox",)),
    sol("Citric_05", "Kwas cytrynowy 0,5 mol/dm³", A, {"Cit": 0.5}, "C6H8O7", ("irr",)),
    sol("Vinegar", "Ocet spirytusowy 10%", A, {"AcO": 1.7}, "CH3COOH"),
    sol("Lemon", "Sok z cytryny", A, {"Cit": 0.3}, "C6H8O7", note="Zawiera kwas cytrynowy."),
    sol("HCOOH_1", "Kwas mrówkowy 1 mol/dm³", A, {"HCOO": 1.0}, "HCOOH", ("corr",)),
    # ---------------- zasady ----------------
    sol("NaOH_01", "Wodorotlenek sodu 0,1 mol/dm³", B, {"Na+": 0.1}, "NaOH", ("corr",)),
    sol("NaOH_1", "Wodorotlenek sodu 1 mol/dm³", B, {"Na+": 1.0}, "NaOH", ("corr",)),
    sol("NaOH_2", "Wodorotlenek sodu 2 mol/dm³", B, {"Na+": 2.0}, "NaOH", ("corr",)),
    sol("NaOH_6", "Wodorotlenek sodu 6 mol/dm³", B, {"Na+": 6.0}, "NaOH", ("corr",)),
    sol("KOH_1", "Wodorotlenek potasu 1 mol/dm³", B, {"K+": 1.0}, "KOH", ("corr",)),
    sol("LimeWater", "Woda wapienna (nasycony Ca(OH)₂)", B, {"Ca2+": 0.02}, "Ca(OH)2", ("irr",)),
    sol("BaOH2_01", "Wodorotlenek baru 0,1 mol/dm³", B, {"Ba2+": 0.1}, "Ba(OH)2", ("corr", "tox")),
    sol("NH3_2", "Woda amoniakalna 2 mol/dm³", B, {"NH3": 2.0}, "NH3·H2O", ("irr",)),
    sol("NH3_conc", "Woda amoniakalna stężona 25%", B, {"NH3": 13.3}, "NH3·H2O", ("corr", "env")),
    # ---------------- sole ----------------
    sol("NaCl_1", "Chlorek sodu 1 mol/dm³", S, {"Na+": 1.0, "Cl-": 1.0}, "NaCl"),
    sol("NaCl_sat", "Solanka (nasycony NaCl)", S, {"Na+": 6.1, "Cl-": 6.1}, "NaCl"),
    sol("KCl_05", "Chlorek potasu 0,5 mol/dm³", S, {"K+": 0.5, "Cl-": 0.5}, "KCl"),
    sol("LiCl_05", "Chlorek litu 0,5 mol/dm³", S, {"Li+": 0.5, "Cl-": 0.5}, "LiCl", ("irr",)),
    sol("SrCl2_05", "Chlorek strontu 0,5 mol/dm³", S, {"Sr2+": 0.5, "Cl-": 1.0}, "SrCl2", ("irr",)),
    sol("NaNO3_05", "Azotan(V) sodu 0,5 mol/dm³", S, {"Na+": 0.5, "NO3-": 0.5}, "NaNO3"),
    sol("KNO3_05", "Azotan(V) potasu 0,5 mol/dm³", S, {"K+": 0.5, "NO3-": 0.5}, "KNO3"),
    sol("KBr_05", "Bromek potasu 0,5 mol/dm³", S, {"K+": 0.5, "Br-": 0.5}, "KBr"),
    sol("KI_05", "Jodek potasu 0,5 mol/dm³", S, {"K+": 0.5, "I-": 0.5}, "KI"),
    sol("KI_01", "Jodek potasu 0,1 mol/dm³", S, {"K+": 0.1, "I-": 0.1}, "KI"),
    sol("Na2SO4_05", "Siarczan(VI) sodu 0,5 mol/dm³", S, {"Na+": 1.0, "SO4": 0.5}, "Na2SO4"),
    sol("Na2CO3_1", "Węglan sodu 1 mol/dm³", S, {"Na+": 2.0, "CO3": 1.0}, "Na2CO3", ("irr",)),
    sol("NaHCO3_05", "Wodorowęglan sodu 0,5 mol/dm³", S, {"Na+": 0.5, "CO3": 0.5}, "NaHCO3"),
    sol("CuSO4_05", "Siarczan(VI) miedzi(II) 0,5 mol/dm³", S, {"Cu2+": 0.5, "SO4": 0.5}, "CuSO4", ("irr", "env")),
    sol("CuSO4_01", "Siarczan(VI) miedzi(II) 0,1 mol/dm³", S, {"Cu2+": 0.1, "SO4": 0.1}, "CuSO4", ("irr", "env")),
    sol("CuCl2_05", "Chlorek miedzi(II) 0,5 mol/dm³", S, {"Cu2+": 0.5, "Cl-": 1.0}, "CuCl2", ("irr", "env")),
    sol("FeCl3_01", "Chlorek żelaza(III) 0,1 mol/dm³", S, {"Fe3+": 0.1, "Cl-": 0.35}, "FeCl3", ("corr",),
        note="Zakwaszony HCl, aby zapobiec hydrolizie."),
    sol("FeSO4_02", "Siarczan(VI) żelaza(II) 0,2 mol/dm³", S, {"Fe2+": 0.2, "SO4": 0.25}, "FeSO4", ("irr",),
        note="Zakwaszony H2SO4."),
    sol("AgNO3_01", "Azotan(V) srebra 0,1 mol/dm³", S, {"Ag+": 0.1, "NO3-": 0.1}, "AgNO3", ("corr", "env")),
    sol("PbNO3_01", "Azotan(V) ołowiu(II) 0,1 mol/dm³", S, {"Pb2+": 0.1, "NO3-": 0.2}, "Pb(NO3)2", ("tox", "env")),
    sol("BaCl2_01", "Chlorek baru 0,1 mol/dm³", S, {"Ba2+": 0.1, "Cl-": 0.2}, "BaCl2", ("tox",)),
    sol("CaCl2_05", "Chlorek wapnia 0,5 mol/dm³", S, {"Ca2+": 0.5, "Cl-": 1.0}, "CaCl2", ("irr",)),
    sol("MgSO4_05", "Siarczan(VI) magnezu 0,5 mol/dm³", S, {"Mg2+": 0.5, "SO4": 0.5}, "MgSO4"),
    sol("ZnSO4_05", "Siarczan(VI) cynku 0,5 mol/dm³", S, {"Zn2+": 0.5, "SO4": 0.5}, "ZnSO4", ("irr", "env")),
    sol("AlCl3_02", "Chlorek glinu 0,2 mol/dm³", S, {"Al3+": 0.2, "Cl-": 0.6}, "AlCl3", ("irr",)),
    sol("NiSO4_05", "Siarczan(VI) niklu(II) 0,5 mol/dm³", S, {"Ni2+": 0.5, "SO4": 0.5}, "NiSO4", ("tox", "env")),
    sol("CoCl2_05", "Chlorek kobaltu(II) 0,5 mol/dm³", S, {"Co2+": 0.5, "Cl-": 1.0}, "CoCl2", ("tox",)),
    sol("MnSO4_05", "Siarczan(VI) manganu(II) 0,5 mol/dm³", S, {"Mn2+": 0.5, "SO4": 0.5}, "MnSO4", ("irr",)),
    sol("SnCl2_05", "Chlorek cyny(II) 0,5 mol/dm³", S, {"Sn2+": 0.5, "Cl-": 1.3}, "SnCl2", ("corr",),
        note="Zakwaszony HCl."),
    sol("KMnO4_002", "Manganian(VII) potasu 0,02 mol/dm³", S, {"K+": 0.02, "MnO4-": 0.02}, "KMnO4", ("ox", "env")),
    sol("KMnO4_0002", "Manganian(VII) potasu 0,002 mol/dm³", S, {"K+": 0.002, "MnO4-": 0.002}, "KMnO4", ("ox",)),
    sol("K2Cr2O7_01", "Dichromian(VI) potasu 0,1 mol/dm³", S, {"K+": 0.2, "Cr6": 0.2}, "K2Cr2O7",
        ("tox", "ox", "env")),
    sol("K2CrO4_01", "Chromian(VI) potasu 0,1 mol/dm³", S, {"K+": 0.2, "Cr6": 0.1}, "K2CrO4", ("tox", "env")),
    sol("KSCN_01", "Tiocyjanian potasu 0,1 mol/dm³", S, {"K+": 0.1, "SCN-": 0.1}, "KSCN", ("irr",)),
    sol("NH4Cl_1", "Chlorek amonu 1 mol/dm³", S, {"NH3": 1.0, "Cl-": 1.0}, "NH4Cl", ("irr",)),
    sol("NH4NO3_1", "Azotan(V) amonu 1 mol/dm³", S, {"NH3": 1.0, "NO3-": 1.0}, "NH4NO3"),
    sol("Na2S2O3_01", "Tiosiarczan sodu 0,1 mol/dm³", S, {"Na+": 0.2, "S2O3^2-": 0.1}, "Na2S2O3"),
    sol("Na2S2O3_02", "Tiosiarczan sodu 0,2 mol/dm³", S, {"Na+": 0.4, "S2O3^2-": 0.2}, "Na2S2O3"),
    sol("Na2SO3_05", "Siarczan(IV) sodu 0,5 mol/dm³", S, {"Na+": 1.0, "SO3": 0.5}, "Na2SO3"),
    sol("Na2S_01", "Siarczek sodu 0,1 mol/dm³", S, {"Na+": 0.2, "S": 0.1}, "Na2S", ("corr", "tox")),
    sol("Na3PO4_01", "Fosforan(V) sodu 0,1 mol/dm³", S, {"Na+": 0.3, "PO4": 0.1}, "Na3PO4", ("irr",)),
    sol("Na2HPO4_01", "Wodorofosforan(V) sodu 0,1 mol/dm³", S, {"Na+": 0.2, "PO4": 0.1}, "Na2HPO4"),
    sol("NaAc_1", "Octan sodu 1 mol/dm³", S, {"Na+": 1.0, "AcO": 1.0}, "CH3COONa"),
    sol("Na2C2O4_005", "Szczawian sodu 0,05 mol/dm³", S, {"Na+": 0.1, "C2O4": 0.05}, "Na2C2O4", ("tox",)),
    sol("K4FeCN6_01", "Heksacyjanożelazian(II) potasu 0,1 mol/dm³", S, {"K+": 0.4, "FeCN6^4-": 0.1},
        "K4[Fe(CN)6]"),
    sol("K3FeCN6_01", "Heksacyjanożelazian(III) potasu 0,1 mol/dm³", S, {"K+": 0.3, "FeCN6^3-": 0.1},
        "K3[Fe(CN)6]", ("irr",)),
    sol("H2O2_3", "Woda utleniona 3%", "Utleniacze i reduktory", {"H2O2": 0.88}, "H2O2"),
    sol("H2O2_30", "Perhydrol 30%", "Utleniacze i reduktory", {"H2O2": 9.8}, "H2O2", ("corr", "ox")),
    sol("ClWater", "Woda chlorowa", "Utleniacze i reduktory", {"Cl2": 0.05}, "Cl2(aq)", ("tox",)),
    sol("BrWater", "Woda bromowa", "Utleniacze i reduktory", {"Br2": 0.02}, "Br2(aq)", ("tox", "corr")),
    sol("Lugol", "Płyn Lugola (jod w KI)", "Utleniacze i reduktory", {"I2": 0.04, "K+": 0.12, "I-": 0.12}, "I2 + KI"),
    sol("Bleach", "Wybielacz (podchloryn sodu)", "Utleniacze i reduktory", {"Na+": 0.75, "ClO": 0.7}, "NaClO",
        ("corr", "env")),
    sol("VitC_01", "Witamina C 0,1 mol/dm³", "Utleniacze i reduktory", {"Asc": 0.1}, "C6H8O6"),
    # ---------------- związki organiczne i biologiczne ----------------
    sol("Glc_05", "Glukoza 0,5 mol/dm³", "Organiczne", {"Glc": 0.5}, "C6H12O6"),
    sol("Suc_05", "Sacharoza 0,5 mol/dm³", "Organiczne", {"Suc": 0.5}, "C12H22O11"),
    sol("Starch_1", "Kleik skrobiowy 1%", "Organiczne", {"Starch": 0.06}, "(C6H10O5)n"),
    sol("EtOH", "Etanol 96%", "Organiczne", {"EtOH": 16.4}, "C2H5OH", ("flam",)),
    sol("Glycerol", "Glicerol", "Organiczne", {"Glycerol": 13.7}, "C3H5(OH)3"),
    sol("Formalin", "Formalina (metanal 4%)", "Organiczne", {"HCHO": 1.3}, "HCHO", ("tox",)),
    sol("Acetaldehyde", "Etanal 1 mol/dm³", "Organiczne", {"CH3CHO": 1.0}, "CH3CHO", ("flam", "irr")),
    sol("EggWhite", "Roztwór białka jaja kurzego", "Organiczne", {"Protein": 2e-4, "Pep": 0.08}, "białko"),
    sol("Urea_1", "Mocznik 1 mol/dm³", "Organiczne", {"Urea": 1.0}, "CO(NH2)2"),
    sol("Soap", "Roztwór mydła", "Organiczne", {"Na+": 0.02, "St-": 0.02}, "C17H35COONa"),
    sol("Detergent", "Płyn do mycia naczyń", "Organiczne", {"Detergent": 0.05}, "detergent"),
    sol("Catalase", "Ekstrakt z wątroby (katalaza)", "Organiczne", {"Catalase": 1e-5}, "enzym"),
    sol("MB_sol", "Błękit metylenowy 0,05%", "Organiczne", {"MB": 0.0016}, "C16H18N3SCl"),
    sol("Luminol_sol", "Roztwór luminolu (zasadowy)", "Organiczne", {"Luminol": 0.006, "Na+": 0.2},
        "C8H7N3O2"),
    sol("FehlingA", "Płyn Fehlinga I (CuSO₄)", "Odczynniki do prób", {"Cu2+": 0.28, "SO4": 0.28}, "CuSO4"),
    sol("FehlingB", "Płyn Fehlinga II (winian, NaOH)", "Odczynniki do prób", {"Na+": 3.7, "K+": 1.2, "Tart^2-": 1.2},
        "KNaC4H4O6 + NaOH", ("corr",)),
    sol("Tollens", "Odczynnik Tollensa (świeży)", "Odczynniki do prób",
        {"Ag+": 0.05, "NH3": 0.35, "NO3-": 0.05, "Na+": 0.05}, "[Ag(NH3)2]OH", ("corr",)),
    sol("Water", "Woda destylowana", "Woda", {}, "H2O", presets=(1, 5, 10, 20, 50, 100)),
    sol("TapWater", "Woda twarda (wodociągowa)", "Woda", {"Ca2+": 0.004, "Mg2+": 0.0015, "CO3": 0.014,
                                                         "Cl-": 0.003}, "H2O + Ca²⁺, Mg²⁺"),
    sol("Seltzer", "Woda gazowana", "Woda", {"CO3": 0.12}, "H2O + CO2"),
    # ---------------- ciecze organiczne (osobna faza) ----------------
    Reagent("Hexane", "Heksan", "Organiczne", "liquid", formula="C6H14", hazards=("flam", "irr", "env"),
            org={"C6H14": 0.655 / 86.18}, presets=(1, 2, 5, 10)),
    Reagent("Cyclohexene", "Cykloheksen (alken)", "Organiczne", "liquid", formula="C6H10", hazards=("flam", "irr"),
            org={"C6H10": 0.81 / 82.14}, presets=(1, 2, 5)),
    Reagent("Oil", "Olej roślinny", "Organiczne", "liquid", formula="tłuszcz", org={"Oil": 0.92 / 885.0},
            presets=(1, 2, 5, 10)),
    # ---------------- wskaźniki ----------------
    ind("ind_phph", "Fenoloftaleina", {"ind:phph": 1.5e-3}),
    ind("ind_mo", "Oranż metylowy", {"ind:mo": 1.5e-3}),
    ind("ind_mr", "Czerwień metylowa", {"ind:mr": 1.5e-3}),
    ind("ind_btb", "Błękit bromotymolowy", {"ind:btb": 1.5e-3}),
    ind("ind_litmus", "Lakmus", {"ind:litmus": 1.5e-3}),
    ind("ind_thymol", "Błękit tymolowy", {"ind:thymol": 1.5e-3}),
    ind("ind_univ", "Wskaźnik uniwersalny", {"ind:univ": 1.5e-3}),
    ind("ind_cabbage", "Wyciąg z czerwonej kapusty", {"ind:cabbage": 1.5e-3}),
    ind("ind_starch", "Skrobia (wskaźnik, krople)", {"Starch": 0.06}),
    # ---------------- ciała stałe: metale ----------------
    solid("Na", "Sód (kawałek)", "Metale", "Na", "Na", ("flam", "corr"), (0.05, 0.1, 0.2), piece=0.1),
    solid("K", "Potas (kawałek)", "Metale", "K", "K", ("flam", "corr"), (0.05, 0.1), piece=0.08),
    solid("Li", "Lit (kawałek)", "Metale", "Li", "Li", ("flam", "corr"), (0.05, 0.1), piece=0.05),
    solid("Ca", "Wapń (granulki)", "Metale", "Ca", "Ca", ("flam",), (0.1, 0.2, 0.5), piece=0.2),
    solid("Mg", "Magnez (wstążka)", "Metale", "Mg", "Mg", ("flam",), (0.03, 0.05, 0.1, 0.2), piece=0.05),
    solid("Mg_powder", "Magnez (proszek)", "Metale", "Mg_powder", "Mg", ("flam",), (0.05, 0.1, 0.5)),
    solid("Al", "Glin (folia)", "Metale", "Al", "Al", (), (0.05, 0.1, 0.2), piece=0.1),
    solid("Al_powder", "Glin (proszek)", "Metale", "Al_powder", "Al", ("flam",), (0.1, 0.5, 1)),
    solid("Zn", "Cynk (granulki)", "Metale", "Zn", "Zn", (), (0.3, 0.6, 1, 2), piece=0.6),
    solid("Zn_powder", "Pył cynkowy", "Metale", "Zn_powder", "Zn", ("flam", "env"), (0.1, 0.5, 1)),
    solid("Fe", "Żelazo (gwóźdź)", "Metale", "Fe", "Fe", (), (3,), piece=3.0),
    solid("Fe_filings", "Opiłki żelaza", "Metale", "Fe_filings", "Fe", (), (0.2, 0.5, 1, 2)),
    solid("Fe_wool", "Wata stalowa", "Metale", "Fe_wool", "Fe", (), (0.1, 0.3, 0.5)),
    solid("Cu", "Miedź (drut)", "Metale", "Cu", "Cu", (), (0.5, 1, 2), piece=1.0),
    solid("Cu_foil", "Miedź (blaszka)", "Metale", "Cu_foil", "Cu", (), (0.3, 0.5, 1), piece=0.5),
    solid("Pb", "Ołów (granulki)", "Metale", "Pb", "Pb", ("tox", "env"), (1, 2)),
    solid("Sn", "Cyna (granulki)", "Metale", "Sn", "Sn", (), (1, 2)),
    solid("Ni", "Nikiel (granulki)", "Metale", "Ni", "Ni", ("irr",), (1, 2)),
    # ---------------- ciała stałe: niemetale i tlenki ----------------
    solid("S", "Siarka (proszek)", "Niemetale i tlenki", "S", "S", (), (0.1, 0.5, 1)),
    solid("C", "Węgiel drzewny", "Niemetale i tlenki", "C", "C", (), (0.1, 0.3, 0.5)),
    solid("P", "Fosfor czerwony", "Niemetale i tlenki", "P", "P", ("flam",), (0.05, 0.1)),
    solid("I2_s", "Jod (kryształy)", "Niemetale i tlenki", "I2_s", "I2", ("tox", "env"), (0.05, 0.1, 0.5)),
    solid("MnO2", "Tlenek manganu(IV)", "Niemetale i tlenki", "MnO2", "MnO2", ("tox",), (0.1, 0.5, 1)),
    solid("CuO", "Tlenek miedzi(II)", "Niemetale i tlenki", "CuO", "CuO", ("env",), (0.2, 0.5, 1)),
    solid("CaO", "Tlenek wapnia (wapno palone)", "Niemetale i tlenki", "CaO", "CaO", ("corr",), (0.5, 1, 2)),
    solid("MgO", "Tlenek magnezu", "Niemetale i tlenki", "MgO", "MgO", (), (0.2, 0.5, 1)),
    solid("ZnO", "Tlenek cynku", "Niemetale i tlenki", "ZnO", "ZnO", ("env",), (0.2, 0.5, 1)),
    solid("Fe2O3", "Tlenek żelaza(III)", "Niemetale i tlenki", "Fe2O3", "Fe2O3", (), (0.5, 1, 2)),
    solid("Na2O2", "Nadtlenek sodu", "Niemetale i tlenki", "Na2O2", "Na2O2", ("ox", "corr"), (0.1, 0.5)),
    solid("CaC2", "Karbid (węglik wapnia)", "Niemetale i tlenki", "CaC2", "CaC2", ("flam",), (0.5, 1, 2)),
    solid("SiO2", "Piasek", "Niemetale i tlenki", "SiO2", "SiO2", (), (1, 5, 10)),
    # ---------------- ciała stałe: sole ----------------
    solid("NaCl_s", "Chlorek sodu (sól kuchenna)", "Sole – kryształy", "NaCl", "NaCl", (), (0.5, 1, 2, 5, 10)),
    solid("KNO3_s", "Azotan(V) potasu (saletra)", "Sole – kryształy", "KNO3", "KNO3", ("ox",), (1, 5, 10, 20)),
    solid("NH4Cl_s", "Chlorek amonu", "Sole – kryształy", "NH4Cl", "NH4Cl", ("irr",), (0.5, 1, 2, 5)),
    solid("NH4NO3_s", "Azotan(V) amonu", "Sole – kryształy", "NH4NO3", "NH4NO3", ("ox",), (2, 5, 10)),
    solid("NH4SCN_s", "Tiocyjanian amonu", "Sole – kryształy", "NH4SCN", "NH4SCN", ("irr",), (5, 10)),
    solid("BaOH2_s", "Wodorotlenek baru ·8H₂O", "Sole – kryształy", "Ba(OH)2·8H2O", "Ba(OH)2·8H2O",
          ("corr", "tox"), (10, 20)),
    solid("NaOH_s", "Wodorotlenek sodu (granulki)", "Sole – kryształy", "NaOH", "NaOH", ("corr",), (0.5, 1, 2, 4)),
    solid("NaHCO3_s", "Wodorowęglan sodu (soda oczyszczona)", "Sole – kryształy", "NaHCO3", "NaHCO3", (),
          (0.5, 1, 2, 5)),
    solid("Na2CO3_s", "Węglan sodu (soda)", "Sole – kryształy", "Na2CO3", "Na2CO3", ("irr",), (0.5, 1, 2)),
    solid("CaCO3_s", "Węglan wapnia (proszek)", "Sole – kryształy", "CaCO3", "CaCO3", (), (0.5, 1, 2)),
    solid("Marble", "Marmur (kawałki CaCO₃)", "Sole – kryształy", "CaCO3_chips", "CaCO3", (), (1, 2, 5, 10)),
    solid("CuCO3_s", "Zasadowy węglan miedzi(II) (malachit)", "Sole – kryształy", "CuCO3", "CuCO3·Cu(OH)2",
          ("env",), (0.5, 1)),
    solid("CuSO4_5H2O", "Siarczan(VI) miedzi(II) ·5H₂O", "Sole – kryształy", "CuSO4·5H2O", "CuSO4·5H2O",
          ("irr", "env"), (0.5, 1, 2, 5, 10)),
    solid("CuSO4_anh", "Siarczan(VI) miedzi(II) bezwodny", "Sole – kryształy", "CuSO4", "CuSO4", ("irr", "env"),
          (0.5, 1, 2)),
    solid("KMnO4_s", "Manganian(VII) potasu (kryształy)", "Sole – kryształy", "KMnO4", "KMnO4", ("ox", "env"),
          (0.05, 0.1, 0.5, 1, 2)),
    solid("K2Cr2O7_s", "Dichromian(VI) potasu", "Sole – kryształy", "K2Cr2O7", "K2Cr2O7", ("tox", "ox"), (0.5, 1)),
    solid("NH4Cr2O7_s", "Dichromian(VI) amonu", "Sole – kryształy", "(NH4)2Cr2O7", "(NH4)2Cr2O7", ("tox", "ox"),
          (1, 2, 5)),
    solid("KClO3_s", "Chloran(V) potasu", "Sole – kryształy", "KClO3", "KClO3", ("ox", "tox"), (0.5, 1, 2)),
    solid("KI_s", "Jodek potasu", "Sole – kryształy", "KI", "KI", (), (0.1, 0.5, 1)),
    solid("PbNO3_s", "Azotan(V) ołowiu(II)", "Sole – kryształy", "Pb(NO3)2", "Pb(NO3)2", ("tox", "ox"), (0.5, 1)),
    solid("Alum_s", "Ałun glinowo-potasowy", "Sole – kryształy", "Alum", "KAl(SO4)2·12H2O", (), (1, 5, 10, 20)),
    solid("FeSO4_s", "Siarczan(VI) żelaza(II) ·7H₂O", "Sole – kryształy", "FeSO4·7H2O", "FeSO4·7H2O", ("irr",),
          (0.5, 1, 2)),
    solid("FeCl3_s", "Chlorek żelaza(III)", "Sole – kryształy", "FeCl3", "FeCl3·6H2O", ("corr",), (0.5, 1)),
    solid("CaCl2_s", "Chlorek wapnia (bezwodny)", "Sole – kryształy", "CaCl2", "CaCl2", ("irr",), (1, 2, 5)),
    solid("CoCl2_s", "Chlorek kobaltu(II) ·6H₂O", "Sole – kryształy", "CoCl2", "CoCl2·6H2O", ("tox",), (0.5, 1)),
    solid("NaAc_s", "Octan sodu ·3H₂O", "Sole – kryształy", "NaAc", "CH3COONa·3H2O", (), (5, 10, 20)),
    solid("Na2S2O3_s", "Tiosiarczan sodu ·5H₂O", "Sole – kryształy", "Na2S2O3", "Na2S2O3·5H2O", (), (1, 5)),
    # ---------------- ciała stałe: organiczne ----------------
    solid("Sugar", "Cukier (sacharoza)", "Organiczne", "Suc_s", "C12H22O11", (), (1, 2, 5, 10)),
    solid("Glucose", "Glukoza", "Organiczne", "Glc_s", "C6H12O6", (), (0.5, 1, 2)),
    solid("Starch_s", "Skrobia (mąka ziemniaczana)", "Organiczne", "Starch_s", "(C6H10O5)n", (), (0.5, 1)),
    solid("Urea_s", "Mocznik", "Organiczne", "Urea_s", "CO(NH2)2", (), (1, 5, 10)),
    solid("CitricAcid_s", "Kwas cytrynowy", "Organiczne", "CitricAcid", "C6H8O7", ("irr",), (1, 2, 5)),
    solid("VitC_s", "Kwas askorbinowy (witamina C)", "Organiczne", "AscAcid", "C6H8O6", (), (0.1, 0.5, 1)),
    solid("Soap_s", "Mydło (płatki)", "Organiczne", "Na_St", "C17H35COONa", (), (0.2, 0.5, 1)),
    solid("Yeast", "Drożdże", "Organiczne", "Yeast", "katalaza", (), (0.5, 1, 2)),
    solid("Potato", "Plaster ziemniaka", "Organiczne", "Potato", "katalaza", (), (2,), piece=2.0),
    solid("Wax", "Świeca parafinowa", "Organiczne", "Wax", "C25H52", (), (5,), piece=5.0),
    # ---------------- gazy z butli ----------------
    gas("gas_O2", "Tlen", "O2", ("ox",)),
    gas("gas_H2", "Wodór", "H2", ("flam",)),
    gas("gas_CO2", "Tlenek węgla(IV)", "CO2"),
    gas("gas_N2", "Azot", "N2"),
    gas("gas_Cl2", "Chlor", "Cl2", ("tox", "ox")),
    gas("gas_NH3", "Amoniak", "NH3", ("tox", "corr")),
    gas("gas_HCl", "Chlorowodór", "HCl", ("tox", "corr")),
    gas("gas_SO2", "Tlenek siarki(IV)", "SO2", ("tox",)),
]
REAGENTS: dict[str, Reagent] = {r.id: r for r in R}
