"""Reakcje kinetyczne: metale, redoks, rozkłady termiczne, spalanie, chemia organiczna i reakcje pokazowe.

Każda reguła to generator przyjmujący kontekst naczynia (Ctx) i zwracający obiekty Rx – szybkość [mol/s],
stechiometrię na jednostkę postępu, entalpię i opis obserwacji. Silnik (sim.py) ogranicza postęp do dostępnych
ilości substratów, aplikuje zmiany i przelicza równowagi. Jony H+ i OH- są niejawne (bilans ładunku).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

from .data import ACIDS, METALS, REDUCIBLE, SOLIDS, IONS

FORM_AREA = {"granules": 1.0, "powder": 8.0, "ribbon": 4.0, "foil": 4.0, "nail": 0.5, "filings": 5.0,
             "wool": 14.0, "wire": 1.5, "lump": 1.3, "deposit": 3.0, "tree": 3.0, "chips": 1.0, "chunk": 1.2,
             "crystals": 2.0, "pellets": 1.5, "slice": 2.0, "candle": 1.0}

METAL_SOLIDS = {
    "Zn": ["Zn", "Zn_powder"], "Mg": ["Mg", "Mg_powder"], "Al": ["Al", "Al_powder"],
    "Fe": ["Fe", "Fe_filings", "Fe_wool"], "Cu": ["Cu", "Cu_foil", "Cu_dep"], "Ag": ["Ag"],
    "Pb": ["Pb", "Pb_dep"], "Sn": ["Sn"], "Ni": ["Ni"], "Na": ["Na"], "K": ["K"], "Li": ["Li"], "Ca": ["Ca"],
}
SOLID_METAL = {sid: m for m, ids in METAL_SOLIDS.items() for sid in ids}
DEPOSIT = {"Cu": "Cu_dep", "Ag": "Ag", "Pb": "Pb_dep", "Fe": "Fe_filings", "Sn": "Sn", "Ni": "Ni", "Zn": "Zn_powder"}
METAL_NAME = {"Zn": "cynk", "Mg": "magnez", "Al": "glin", "Fe": "żelazo", "Cu": "miedź", "Ag": "srebro",
              "Pb": "ołów", "Sn": "cyna", "Ni": "nikiel", "Na": "sód", "K": "potas", "Li": "lit", "Ca": "wapń"}
SUP = {1: "^+", 2: "^2+", 3: "^3+"}


@dataclass
class Rx:
    key: str
    rate: float
    st: dict
    dh: float = 0.0
    obs: str = ""
    eq: str = ""
    fx: dict = field(default_factory=dict)
    cap: float | None = None
    bubbles: bool = True


def arr(t: float, q10: float = 2.0, ref: float = 20.0) -> float:
    return q10 ** ((t - ref) / 10.0)


class Ctx:
    def __init__(self, v, e, sp, env_gas, env_cap, env_open, dt):
        self.v = v
        self.e = e
        self.sp = sp
        self.T = v["T"]
        self.ph = sp.ph
        self.h = sp.h
        self.oh = sp.oh
        self.vol = v["vol"]
        self.V = max(v["vol"], 0.05) / 1000.0
        self.wet = v["vol"] > 0.3
        self.stir = v.get("stir", 0) > 0
        self.env_gas = env_gas
        self.env_cap = env_cap
        self.env_open = env_open
        self.dt = dt
        self.prog = v.setdefault("prog", {})

    # --- stężenia i ilości ---
    def c(self, name):
        return self.sp.free.get(name, 0.0)

    def n(self, comp):
        return self.v["aq"].get(comp, 0.0)

    def ct(self, comp):
        return self.n(comp) / self.V

    def s(self, sid):
        st = self.v["solids"].get(sid)
        return st["n"] if st else 0.0

    def area(self, sid):
        n = self.s(sid)
        if n <= 0:
            return 0.0
        sd = SOLIDS[sid]
        mass = n * sd.mm
        return (mass ** (2.0 / 3.0)) * FORM_AREA.get(sd.style, 2.0)

    def org(self, sid):
        return self.v.get("org", {}).get(sid, 0.0)

    def xgas(self, gid):
        tot = sum(self.env_gas.values())
        if tot <= 0:
            return 0.0
        return self.env_gas.get(gid, 0.0) / tot

    def eth_frac(self):
        """Udział objętościowy etanolu w fazie ciekłej."""
        if self.vol <= 0:
            return 0.0
        return min(1.0, self.n("EtOH") * 46.07 / 0.789 / self.vol)

    def acid_cap(self, target_ph=7.0):
        """Ile moli H+ może zostać zużyte, zanim pH wzrośnie do target_ph."""
        from .equilibrium import _alphas
        cap = self.V * (self.h - 10 ** (-target_ph))
        for comp, n in self.v["aq"].items():
            sysd = ACIDS.get(comp)
            if not sysd or n <= 0:
                continue
            a_now = _alphas(sysd.pka, self.ph)
            a_t = _alphas(sysd.pka, target_ph)
            bound_now = sum((len(sysd.pka) - j) * a for j, a in enumerate(a_now))
            bound_t = sum((len(sysd.pka) - j) * a for j, a in enumerate(a_t))
            cap += n * (bound_now - bound_t)
        return max(cap, 0.0)

    def base_cap(self, target_ph=9.0):
        from .equilibrium import _alphas
        cap = self.V * (self.oh - 10 ** (target_ph - 14))
        for comp, n in self.v["aq"].items():
            sysd = ACIDS.get(comp)
            if not sysd or n <= 0:
                continue
            a_now = _alphas(sysd.pka, self.ph)
            a_t = _alphas(sysd.pka, target_ph)
            bound_now = sum((len(sysd.pka) - j) * a for j, a in enumerate(a_now))
            bound_t = sum((len(sysd.pka) - j) * a for j, a in enumerate(a_t))
            cap += n * (bound_t - bound_now)
        return max(cap, 0.0)

    def induction(self, key, active, delay):
        """Okres indukcji: zwraca True po 'delay' sekundach ciągłego spełniania warunku."""
        if active:
            self.prog[key] = self.prog.get(key, 0.0) + self.dt
        else:
            self.prog.pop(key, None)
        return self.prog.get(key, 0.0) >= delay


# ===============================================================================================================
# Metale
# ===============================================================================================================
def _passivation(c, metal):
    m = METALS[metal]
    f = 1.0
    if metal == "Al":
        f = 1.0 if c.ct("Cl-") > 0.05 or c.oh > 0.05 else 0.04
    if metal in ("Fe", "Al") and c.ct("NO3-") > 8 and c.h > 5:
        f = 0.0  # pasywacja w stężonym HNO3
    if metal in ("Fe", "Al") and c.ct("SO4") > 12:
        f = 0.01  # pasywacja w stężonym H2SO4
    if metal == "Pb" and (c.ct("Cl-") > 0.05 or c.ct("SO4") > 0.05):
        f = 0.05
    return f * (0.0 if not m else 1.0)


def r_metal_acid(c: Ctx):
    if not c.wet or (c.h < 1e-4 and c.ph > 6):
        return
    nitric = c.ct("NO3-") > 0.5 and c.h > 0.3
    for sid, st in list(c.v["solids"].items()):
        metal = SOLID_METAL.get(sid)
        if not metal or st["n"] <= 0:
            continue
        m = METALS[metal]
        if m.e0 >= 0 or m.k_acid <= 0:
            continue
        if nitric and metal not in ("Na", "K", "Li", "Ca"):
            continue
        weak = 0.03 * sum(c.c(ACIDS[k].forms[0]) for k in ("AcO", "Cit", "HCOO", "C2O4", "PO4", "Asc"))
        rate = m.k_acid * c.area(sid) * (min(c.h, 8.0) + weak) * arr(c.T) * _passivation(c, metal)
        if rate <= 0:
            continue
        ion = m.ion
        nm = METAL_NAME[metal]
        coef = {1: "2", 2: "", 3: "2"}[m.n]
        h_coef = {1: "2", 2: "2", 3: "6"}[m.n]
        ion_coef = {1: "2", 2: "", 3: "2"}[m.n]
        h2c = {1: "", 2: "", 3: "3"}[m.n]
        yield Rx(f"acid:{metal}", rate, {"s": {sid: -1}, "aq": {ion: 1}, "g": {"H2": m.n / 2}},
                 dh=-95.0 * m.n,
                 obs=f"{nm.capitalize()} roztwarza się w kwasie – wydzielają się pęcherzyki bezbarwnego gazu (wodór).",
                 eq=f"{coef}{metal} + {h_coef}H^+ → {ion_coef}{metal}{SUP[m.n]} + {h2c}H2↑",
                 cap=c.acid_cap(6.0) / m.n * 0.8)


def r_metal_water(c: Ctx):
    if not c.wet:
        return
    water = max(0.0, 1.0 - c.eth_frac())
    for metal in ("Na", "K", "Li", "Ca", "Mg"):
        for sid in METAL_SOLIDS[metal]:
            if c.s(sid) <= 0:
                continue
            m = METALS[metal]
            k = m.k_water + (m.k_hot_water * arr(c.T, 2.0, 70) if c.T > 55 else 0.0)
            eth = c.eth_frac()
            rate = k * c.area(sid) * (water + 0.08 * eth) * (arr(c.T, 1.6) if metal != "Mg" else 1.0)
            if rate <= 0:
                continue
            fx = {}
            obs = ""
            if metal == "Na":
                fx = {"float": 1, "melt": 1, "skate": 1, "hiss": 1}
                obs = ("Sód pływa po powierzchni, topi się w srebrzystą kulkę i szybko porusza się z sykiem; "
                       "wydziela się wodór, a roztwór staje się zasadowy.")
                if eth > 0.5:
                    obs = "Sód powoli reaguje z etanolem – wydzielają się pęcherzyki wodoru (etanolan sodu)."
            elif metal == "K":
                fx = {"float": 1, "melt": 1, "skate": 1, "flame": "#c58cf0", "hiss": 1, "pop": 1}
                obs = ("Potas reaguje gwałtownie – zapala się fioletowym płomieniem i biega po powierzchni wody, "
                       "na końcu słychać trzask.")
            elif metal == "Li":
                fx = {"float": 1}
                obs = "Lit pływa po wodzie i spokojnie reaguje, wydzielając pęcherzyki wodoru."
            elif metal == "Ca":
                fx = {"sink": 1}
                obs = "Wapń opada na dno i reaguje z wodą – wydziela się wodór, roztwór mętnieje (Ca(OH)₂)."
            elif metal == "Mg":
                obs = "Magnez powoli reaguje z gorącą wodą – na powierzchni pojawiają się drobne pęcherzyki gazu."
            n = m.n
            dh = {"Na": -184, "K": -196, "Li": -222, "Ca": -414, "Mg": -353}[metal]
            eq = {"Na": "2Na + 2H2O → 2NaOH + H2↑", "K": "2K + 2H2O → 2KOH + H2↑",
                  "Li": "2Li + 2H2O → 2LiOH + H2↑", "Ca": "Ca + 2H2O → Ca(OH)2 + H2↑",
                  "Mg": "Mg + 2H2O → Mg(OH)2 + H2↑"}[metal]
            if eth > 0.5 and metal == "Na":
                eq = "2Na + 2C2H5OH → 2C2H5ONa + H2↑"
            yield Rx(f"water:{metal}", rate, {"s": {sid: -1}, "aq": {m.ion: 1}, "g": {"H2": n / 2},
                                               "vol": -0.018 * n},
                     dh=dh, obs=obs, eq=eq, fx=fx)


def r_metal_base(c: Ctx):
    """Metale amfoteryczne (Al, Zn) w roztworach mocnych zasad."""
    if not c.wet or c.oh < 0.02:
        return
    for metal, k in (("Al", 4e-4), ("Zn", 3e-5)):
        for sid in METAL_SOLIDS[metal]:
            if c.s(sid) <= 0:
                continue
            m = METALS[metal]
            rate = k * c.area(sid) * min(c.oh, 5.0) * arr(c.T, 2.2)
            if metal == "Al":
                eq = "2Al + 2NaOH + 6H2O → 2Na[Al(OH)4] + 3H2↑"
                obs = "Glin roztwarza się w zasadzie – intensywnie wydziela się wodór, roztwór się ogrzewa."
            else:
                eq = "Zn + 2NaOH + 2H2O → Na2[Zn(OH)4] + H2↑"
                obs = "Cynk powoli roztwarza się w stężonej zasadzie, wydzielając wodór."
            yield Rx(f"base:{metal}", rate, {"s": {sid: -1}, "aq": {m.ion: 1}, "g": {"H2": m.n / 2},
                                              "vol": -0.018 * m.n},
                     dh=-140.0 * m.n, obs=obs, eq=eq, cap=c.base_cap(10.5) * 0.9)


def r_displacement(c: Ctx):
    if not c.wet:
        return
    for sid, st in list(c.v["solids"].items()):
        metal = SOLID_METAL.get(sid)
        if not metal or st["n"] <= 0 or metal in ("Na", "K", "Li", "Ca"):
            continue
        m = METALS[metal]
        area = c.area(sid)
        pas = _passivation(c, metal) if metal != "Al" else (1.0 if c.ct("Cl-") > 0.05 else 0.03)
        for ion, prod, nN, e0 in REDUCIBLE:
            if e0 <= m.e0 + 0.05:
                continue
            if prod == metal:
                continue
            conc = c.c(ion)
            if conc < 1e-7:
                continue
            rate = m.k_disp * area * conc * arr(c.T) * pas * 4.0
            ratio = m.n / nN
            st_ = {"s": {sid: -1}, "aq": {m.ion: 1, ion: -ratio}}
            if prod in METALS:
                dep = DEPOSIT[prod]
                st_["s"][dep] = st_["s"].get(dep, 0) + ratio
                pname = METAL_NAME[prod]
                colour = {"Cu": "czerwonobrunatny", "Ag": "srebrzysty, krystaliczny", "Pb": "szary, krystaliczny",
                          "Fe": "ciemnoszary", "Sn": "szary", "Ni": "szary", "Zn": "szary"}[prod]
                obs = f"Na powierzchni metalu ({METAL_NAME[metal]}) osadza się {colour} nalot – wydziela się {pname}."
                a = "" if ratio == 1 else (str(int(ratio)) if ratio == int(ratio) else "")
                if ratio == 0.5:
                    eq = f"2{metal} + {prod}{SUP[nN]} → 2{metal}{SUP[m.n]} + {prod}"
                elif ratio == int(ratio):
                    eq = f"{metal} + {a}{prod}{SUP[nN]} → {metal}{SUP[m.n]} + {a}{prod}"
                else:
                    eq = f"{int(nN)}{metal} + {int(m.n)}{prod}{SUP[nN]} → {int(nN)}{metal}{SUP[m.n]} + {int(m.n)}{prod}"
            else:
                st_["aq"][prod] = st_["aq"].get(prod, 0) + ratio
                obs = f"{METAL_NAME[metal].capitalize()} roztwarza się – jony Fe³⁺ redukują się do Fe²⁺."
                eq = f"{metal} + {int(ratio)}Fe^3+ → {metal}{SUP[m.n]} + {int(ratio)}Fe^2+"
            yield Rx(f"disp:{metal}:{ion}", rate, st_, dh=-80.0 * m.n * (e0 - m.e0), obs=obs, eq=eq,
                     bubbles=False)


def r_nitric(c: Ctx):
    hn = min(c.h, c.ct("NO3-"))
    if not c.wet or hn < 0.5:
        return
    for sid, st in list(c.v["solids"].items()):
        metal = SOLID_METAL.get(sid)
        if not metal or st["n"] <= 0 or metal in ("Na", "K", "Li", "Ca"):
            continue
        if metal in ("Fe", "Al") and hn > 8:
            continue  # pasywacja
        k = {"Cu": 6e-5, "Ag": 4e-5, "Zn": 2e-4, "Mg": 4e-4, "Pb": 2e-5, "Fe": 6e-5, "Sn": 2e-5, "Ni": 2e-5,
             "Al": 1e-6}.get(metal, 1e-5)
        m = METALS[metal]
        rate = k * c.area(sid) * hn * arr(c.T, 2.3)
        if hn > 6:
            yield Rx(f"nitric:{metal}:conc", rate, {"s": {sid: -1}, "aq": {m.ion: 1, "NO3-": -m.n},
                                                    "g": {"NO2": m.n}, "vol": 0.018 * m.n},
                     dh=-80.0 * m.n,
                     obs=f"{METAL_NAME[metal].capitalize()} gwałtownie reaguje ze stężonym kwasem azotowym(V) – "
                         "wydziela się brunatny, duszący gaz NO₂.",
                     eq=f"{metal} + 4HNO3 → {metal}(NO3)2 + 2NO2↑ + 2H2O" if m.n == 2 else
                     f"{metal} + 2HNO3 → {metal}NO3 + NO2↑ + H2O",
                     cap=c.acid_cap(2.0) / (2 * m.n) * 0.8)
        else:
            yield Rx(f"nitric:{metal}:dil", rate * 0.6,
                     {"s": {sid: -1}, "aq": {m.ion: 1, "NO3-": -m.n / 3}, "g": {"NO": m.n / 3},
                      "vol": 0.024 * m.n},
                     dh=-70.0 * m.n,
                     obs=f"{METAL_NAME[metal].capitalize()} roztwarza się w rozcieńczonym kwasie azotowym(V) – "
                         "wydziela się bezbarwny NO, który u wylotu naczynia brunatnieje (NO₂).",
                     eq=f"3{metal} + 8HNO3 → 3{metal}(NO3)2 + 2NO↑ + 4H2O" if m.n == 2 else
                     f"3{metal} + 4HNO3 → 3{metal}NO3 + NO↑ + 2H2O",
                     cap=c.acid_cap(2.0) / (8 / 3 * m.n / 2) * 0.8)


def r_conc_sulfuric(c: Ctx):
    if not c.wet or c.ct("SO4") < 11 or c.T < 90:
        return
    for sid in METAL_SOLIDS["Cu"]:
        if c.s(sid) > 0:
            yield Rx("h2so4:Cu", 4e-5 * c.area(sid) * arr(c.T, 2.0, 100),
                     {"s": {sid: -1}, "aq": {"Cu2+": 1, "SO4": -1}, "g": {"SO2": 1}, "vol": 0.036},
                     dh=-10, obs="Miedź roztwarza się w gorącym stężonym H₂SO₄ – wydziela się duszący SO₂, "
                                 "roztwór niebieszczeje.",
                     eq="Cu + 2H2SO4 → CuSO4 + SO2↑ + 2H2O")


# ===============================================================================================================
# Redoks w roztworze
# ===============================================================================================================
# reduktor: (składnik/gatunek, liczba elektronów, produkty na mol reduktora, stała k, nazwa, kluczowe)
REDUCTANTS = [
    ("Fe2+", 1, {"Fe3+": 1}, 2e3, "jony Fe²⁺"),
    ("H2O2", 2, {"g:O2": 1}, 60.0, "nadtlenek wodoru"),
    ("SO3", 2, {"SO4": 1}, 2e3, "siarczan(IV)"),
    ("I-", 1, {"I2": 0.5}, 150.0, "jodki"),
    ("C2O4", 2, {"g:CO2": 2}, 0.0, "szczawiany"),
    ("EtOH", 2, {"CH3CHO": 1}, 0.4, "etanol"),
    ("Glc", 2, {"Gluc-": 1}, 0.25, "glukoza"),
    ("Fru", 2, {"Gluc-": 1}, 0.25, "fruktoza"),
    ("HCHO", 2, {"HCOO": 1}, 2.0, "metanal"),
    ("S", 2, {"s:S_col": 1}, 50.0, "siarkowodór"),
    ("Asc", 2, {}, 500.0, "kwas askorbinowy"),
    ("Sn2+", 2, {"Sn4": 0}, 500.0, "jony Sn²⁺"),
]


def _red_conc(c, comp):
    if comp in ("SO3", "C2O4", "S", "Asc"):
        return c.ct(comp)
    if comp == "I-":
        return c.ct("I-")
    if comp in ("Fe2+", "Sn2+"):
        return c.ct(comp)
    return c.c(comp) if comp not in ("EtOH", "Glc", "Fru", "HCHO", "H2O2") else c.ct(comp)


def _apply_red_products(st, prods, factor):
    for k, v in prods.items():
        if k.startswith("g:"):
            st.setdefault("g", {})[k[2:]] = st.get("g", {}).get(k[2:], 0) + v * factor
        elif k.startswith("s:"):
            st.setdefault("s", {})[k[2:]] = st.get("s", {}).get(k[2:], 0) + v * factor
        elif k == "Sn4":
            continue
        else:
            st.setdefault("aq", {})[k] = st["aq"].get(k, 0) + v * factor


def r_permanganate(c: Ctx):
    mn = c.ct("MnO4-")
    if mn < 1e-7 or not c.wet:
        return
    if c.ph < 3.0:
        e_mn, prod, label = 5, ("aq", "Mn2+"), "acid"
    elif c.ph < 12.3:
        e_mn, prod, label = 3, ("s", "MnO2"), "neutral"
    else:
        e_mn, prod, label = 1, ("aq", "MnO4^2-"), "base"
    reds = list(REDUCTANTS)
    if c.org("C6H10") > 0:
        reds.append(("org:C6H10", 2, {"org:C6H10(OH)2": 1}, 30.0, "alken"))
    if c.ct("Cl-") > 4 and c.h > 4:
        reds.append(("Cl-", 1, {"Cl2": 0.5}, 0.03, "jony chlorkowe"))
    for comp, e_r, prods, k, rname in reds:
        if comp.startswith("org:"):
            cr = c.org(comp[4:]) / c.V
            k_eff = k * (1.0 if c.stir else 0.05)
        else:
            cr = _red_conc(c, comp)
            k_eff = k
        if cr <= 1e-8:
            continue
        if comp == "C2O4":
            k_eff = 120.0 * (c.ct("Mn2+") + 6e-5) * arr(c.T, 2.6, 25) if c.ph < 3 else 0.0
        elif comp in ("EtOH", "Glc", "Fru"):
            k_eff = k * arr(c.T, 2.2, 25) * (3.0 if label == "base" else 1.0)
        elif comp == "H2O2" and label != "acid":
            k_eff = k * 0.3
        if k_eff <= 0:
            continue
        rate = k_eff * mn * cr * c.V
        ratio = e_mn / e_r
        st = {"aq": {"MnO4-": -1}}
        if comp.startswith("org:"):
            st["org"] = {comp[4:]: -ratio}
        else:
            st["aq"][comp] = -ratio
        if prod[0] == "aq":
            st["aq"][prod[1]] = st["aq"].get(prod[1], 0) + 1
        else:
            st["s"] = {prod[1]: 1}
        for kk, vv in prods.items():
            if kk.startswith("org:"):
                st.setdefault("org", {})[kk[4:]] = vv * ratio
        _apply_red_products(st, {k2: v2 for k2, v2 in prods.items() if not k2.startswith("org:")}, ratio)
        if label == "acid":
            obs = f"Fioletowy roztwór manganianu(VII) odbarwia się – {rname} redukują Mn(VII) do Mn²⁺."
            if comp == "C2O4":
                obs = ("Roztwór KMnO₄ odbarwia się – początkowo powoli, potem coraz szybciej "
                       "(autokataliza jonami Mn²⁺).")
            if comp == "Cl-":
                obs = "Wydziela się żółtozielony, duszący chlor; fioletowa barwa zanika."
        elif label == "neutral":
            obs = f"Fioletowa barwa zanika, wytrąca się brunatny osad MnO₂ ({rname})."
        else:
            obs = f"Roztwór zmienia barwę z fioletowej na zieloną – powstają jony manganianowe(VI) ({rname})."
        eqs = {
            ("Fe2+", "acid"): "MnO4^- + 5Fe^2+ + 8H^+ → Mn^2+ + 5Fe^3+ + 4H2O",
            ("H2O2", "acid"): "2MnO4^- + 5H2O2 + 6H^+ → 2Mn^2+ + 5O2↑ + 8H2O",
            ("SO3", "acid"): "2MnO4^- + 5SO3^2- + 6H^+ → 2Mn^2+ + 5SO4^2- + 3H2O",
            ("SO3", "neutral"): "2MnO4^- + 3SO3^2- + H2O → 2MnO2↓ + 3SO4^2- + 2OH^-",
            ("SO3", "base"): "2MnO4^- + SO3^2- + 2OH^- → 2MnO4^2- + SO4^2- + H2O",
            ("I-", "acid"): "2MnO4^- + 10I^- + 16H^+ → 2Mn^2+ + 5I2 + 8H2O",
            ("C2O4", "acid"): "2MnO4^- + 5C2O4^2- + 16H^+ → 2Mn^2+ + 10CO2↑ + 8H2O",
            ("EtOH", "acid"): "2MnO4^- + 5C2H5OH + 6H^+ → 2Mn^2+ + 5CH3CHO + 8H2O",
            ("Glc", "base"): "MnO4^- + e^- → MnO4^2- (glukoza jako reduktor)",
            ("Cl-", "acid"): "2MnO4^- + 10Cl^- + 16H^+ → 2Mn^2+ + 5Cl2↑ + 8H2O",
            ("org:C6H10", "neutral"): "3C6H10 + 2MnO4^- + 4H2O → 3C6H10(OH)2 + 2MnO2↓ + 2OH^-",
        }
        eq = eqs.get((comp, label), {"acid": "MnO4^- + 8H^+ + 5e^- → Mn^2+ + 4H2O",
                                     "neutral": "MnO4^- + 2H2O + 3e^- → MnO2↓ + 4OH^-",
                                     "base": "MnO4^- + e^- → MnO4^2-"}[label])
        cap = None
        if label == "acid":
            cap = c.acid_cap(3.5) / 8.0
        yield Rx(f"mno4:{comp}:{label}", rate, st, dh=-150.0, obs=obs, eq=eq, cap=cap,
                 bubbles=comp in ("H2O2", "C2O4", "Cl-"))


def r_manganate(c: Ctx):
    mn = c.ct("MnO4^2-")
    if mn < 1e-7:
        return
    for comp, k in (("Glc", 0.08), ("Fru", 0.08), ("SO3", 500.0), ("EtOH", 0.05)):
        cr = c.ct(comp)
        if cr <= 0:
            continue
        rate = k * mn * cr * c.V * arr(c.T, 2.2, 25)
        st = {"aq": {"MnO4^2-": -1, comp: -1.0}, "s": {"MnO2": 1}}
        if comp == "SO3":
            st["aq"]["SO4"] = 1.0
        yield Rx(f"mno42:{comp}", rate, st, dh=-60,
                 obs="Zielony roztwór brunatnieje – manganian(VI) redukuje się do koloidalnego MnO₂ "
                     "(efekt „chemicznego kameleona”).",
                 eq="MnO4^2- + 2H2O + 2e^- → MnO2↓ + 4OH^-", bubbles=False)
    if c.ph < 10 and mn > 1e-6:
        # dysproporcjonowanie manganianu(VI) w środowisku obojętnym/kwasowym
        yield Rx("mno42:disp", 0.5 * mn * c.V, {"aq": {"MnO4^2-": -1, "MnO4-": 2 / 3}, "s": {"MnO2": 1 / 3}},
                 obs="Zielony manganian(VI) dysproporcjonuje – pojawia się fioletowa barwa i brunatny MnO₂.",
                 eq="3MnO4^2- + 4H^+ → 2MnO4^- + MnO2↓ + 2H2O", bubbles=False, cap=c.acid_cap(11) / 1.33)


def r_dichromate(c: Ctx):
    cr6 = c.ct("Cr6")
    if cr6 < 1e-7 or c.ph > 4 or not c.wet:
        return
    for comp, e_r, prods, k, rname in (("Fe2+", 1, {"Fe3+": 1}, 2e3, "jony Fe²⁺"),
                                        ("SO3", 2, {"SO4": 1}, 2e3, "siarczany(IV)"),
                                        ("EtOH", 2, {"CH3CHO": 1}, 0.8, "etanol"),
                                        ("I-", 1, {"I2": 0.5}, 20.0, "jodki"),
                                        ("H2O2", 2, {"g:O2": 1}, 5.0, "nadtlenek wodoru"),
                                        ("S", 2, {"s:S_col": 1}, 50.0, "siarkowodór")):
        cr = c.ct(comp)
        if cr <= 1e-8:
            continue
        kk = k * (arr(c.T, 2.2, 25) if comp == "EtOH" else 1.0) * min(1.0, c.h / 0.3)
        rate = kk * cr6 * cr * c.V
        ratio = 3 / e_r
        st = {"aq": {"Cr6": -1, comp: -ratio, "Cr3+": 1}}
        _apply_red_products(st, prods, ratio)
        eq = {"Fe2+": "Cr2O7^2- + 6Fe^2+ + 14H^+ → 2Cr^3+ + 6Fe^3+ + 7H2O",
              "SO3": "Cr2O7^2- + 3SO3^2- + 8H^+ → 2Cr^3+ + 3SO4^2- + 4H2O",
              "EtOH": "Cr2O7^2- + 3C2H5OH + 8H^+ → 2Cr^3+ + 3CH3CHO + 7H2O",
              "I-": "Cr2O7^2- + 6I^- + 14H^+ → 2Cr^3+ + 3I2 + 7H2O",
              "H2O2": "Cr2O7^2- + 3H2O2 + 8H^+ → 2Cr^3+ + 3O2↑ + 7H2O",
              "S": "Cr2O7^2- + 3H2S + 8H^+ → 2Cr^3+ + 3S↓ + 7H2O"}[comp]
        yield Rx(f"cr6:{comp}", rate, st, dh=-120.0,
                 obs=f"Pomarańczowy roztwór dichromianu(VI) zmienia barwę na zieloną – {rname} redukują Cr(VI) "
                     "do Cr³⁺.",
                 eq=eq, cap=c.acid_cap(3.5) / 5.0, bubbles=comp == "H2O2")


def r_halogens(c: Ctx):
    if not c.wet:
        return
    pairs = (("Cl2", "Br-", "Br2", "Cl-", "Woda chlorowa utlenia bromki – roztwór zabarwia się na pomarańczowo (Br₂).",
              "Cl2 + 2Br^- → 2Cl^- + Br2"),
             ("Cl2", "I-", "I2", "Cl-", "Woda chlorowa utlenia jodki – roztwór brunatnieje (wydziela się jod).",
              "Cl2 + 2I^- → 2Cl^- + I2"),
             ("Br2", "I-", "I2", "Br-", "Woda bromowa utlenia jodki – roztwór brunatnieje (jod).",
              "Br2 + 2I^- → 2Br^- + I2"))
    for ox, red, prod, side, obs, eq in pairs:
        n_ox, n_red = c.n(ox), c.n(red)
        if n_ox <= 1e-10 or n_red <= 1e-10:
            continue
        rate = 30.0 * min(n_ox, n_red / 2)
        yield Rx(f"hal:{ox}:{red}", rate, {"aq": {ox: -1, red: -2, prod: 1, side: 2}}, dh=-60, obs=obs, eq=eq,
                 bubbles=False)
    if c.n("Cl2") > 1e-10 and c.n("Fe2+") > 1e-10:
        yield Rx("hal:Cl2:Fe", 30.0 * min(c.n("Cl2"), c.n("Fe2+") / 2),
                 {"aq": {"Cl2": -1, "Fe2+": -2, "Fe3+": 2, "Cl-": 2}},
                 obs="Chlor utlenia jony Fe²⁺ do Fe³⁺ – roztwór żółknie.", eq="2Fe^2+ + Cl2 → 2Fe^3+ + 2Cl^-",
                 bubbles=False)
    for hal, prod_obs in (("Cl2", "chlorany(I)"), ("Br2", "bromiany")):
        if c.n(hal) > 1e-10 and c.oh > 1e-3:
            rate = 8.0 * c.n(hal) * min(1.0, c.oh / 0.02)
            st = {"aq": {hal: -1, "Cl-" if hal == "Cl2" else "Br-": 1}}
            if hal == "Cl2":
                st["aq"]["ClO"] = 1
            else:
                st["aq"]["Br-"] = 2  # uproszczenie (bromiany niebrane pod uwagę)
            yield Rx(f"hal:{hal}:OH", rate, st, dh=-100,
                     obs=f"Barwa {'chloru' if hal == 'Cl2' else 'bromu'} zanika w roztworze zasady – powstają "
                         f"{prod_obs}.",
                     eq="Cl2 + 2OH^- → Cl^- + ClO^- + H2O" if hal == "Cl2" else "3Br2 + 6OH^- → 5Br^- + BrO3^- + 3H2O",
                     cap=c.base_cap(9) / 2, bubbles=False)
    hclo = c.c("HClO")
    if hclo > 1e-6 and c.ct("Cl-") > 1e-3 and c.h > 1e-3:
        rate = 3.0 * hclo * c.ct("Cl-") * min(c.h, 5) * c.V
        yield Rx("bleach:acid", rate, {"aq": {"ClO": -1, "Cl-": -1, "Cl2": 1}}, dh=-20,
                 obs="Po zakwaszeniu wybielacza wydziela się żółtozielony, trujący chlor!",
                 eq="ClO^- + Cl^- + 2H^+ → Cl2↑ + H2O", cap=c.acid_cap(5) / 2)
    # jod i reduktory
    n_i2 = c.n("I2")
    if n_i2 > 1e-12:
        for red, obs, eq, prods in (
                ("S2O3^2-", "Brunatna barwa jodu zanika – tiosiarczan redukuje jod do jodków.",
                 "I2 + 2S2O3^2- → 2I^- + S4O6^2-", {"S4O6^2-": 0.5}),
                ("SO3", "Brunatna barwa jodu zanika – siarczany(IV) redukują jod.",
                 "I2 + SO3^2- + H2O → 2I^- + SO4^2- + 2H^+", {"SO4": 1}),
                ("Asc", "Barwa jodu zanika – witamina C (kwas askorbinowy) redukuje jod.",
                 "C6H8O6 + I2 → C6H6O6 + 2I^- + 2H^+", {})):
            nr = c.n(red)
            if nr <= 1e-12:
                continue
            per = 2 if red == "S2O3^2-" else 1
            rate = 200.0 * min(n_i2, nr / per)
            st = {"aq": {"I2": -1, red: -per, "I-": 2}}
            for k2, v2 in prods.items():
                st["aq"][k2] = st["aq"].get(k2, 0) + v2 * per
            yield Rx(f"i2:{red}", rate, st, obs=obs, eq=eq, bubbles=False)
    # Fe3+ + I-
    if c.ct("Fe3+") > 1e-6 and c.ct("I-") > 1e-6:
        rate = 0.6 * c.c("Fe3+") * c.ct("I-") * c.V * 50
        yield Rx("fe3:I", rate, {"aq": {"Fe3+": -2, "I-": -2, "Fe2+": 2, "I2": 1}},
                 obs="Jony Fe³⁺ utleniają jodki – roztwór brunatnieje od wydzielonego jodu.",
                 eq="2Fe^3+ + 2I^- → 2Fe^2+ + I2", bubbles=False)
    # Cu2+ + I-
    if c.ct("Cu2+") > 1e-5 and c.ct("I-") > 1e-5:
        rate = 5.0 * c.ct("Cu2+") * c.ct("I-") * c.V * 10
        yield Rx("cu:I", rate, {"aq": {"Cu2+": -2, "I-": -4, "I2": 1}, "s": {"CuI": 2}},
                 obs="Wytrąca się biały osad CuI zabarwiony na brunatno przez wydzielony jod.",
                 eq="2Cu^2+ + 4I^- → 2CuI↓ + I2", bubbles=False)


def r_peroxide(c: Ctx):
    n = c.n("H2O2")
    if n <= 1e-10:
        return
    k = 2e-6
    cat = []
    if c.s("MnO2") > 0:
        k += 0.25 * min(c.area("MnO2"), 3.0)
        cat.append("MnO₂")
    if c.c("I-") > 1e-4 and c.ph > 3:
        k += 2.5 * c.c("I-")
        cat.append("KI")
    if c.ct("Fe3+") > 1e-4:
        k += 0.08 * c.ct("Fe3+")
        cat.append("Fe³⁺")
    if c.ct("Catalase") > 0:
        k += 2.0e5 * c.ct("Catalase")
        cat.append("katalaza")
    for sid, kk in (("Yeast", 0.12), ("Potato", 0.03)):
        if c.s(sid) > 0:
            k += kk * min(c.area(sid), 4.0)
            cat.append("katalaza")
    if c.ct("Cu2+") > 1e-3:
        k += 0.004 * c.ct("Cu2+")
    rate = k * n * arr(c.T, 2.3)
    fx = {}
    if c.ct("Detergent") > 1e-4 and rate > 1e-5:
        fx = {"foam": "#f6e7a8" if "KI" in cat else "#f7f7f2"}
    obs = "Nadtlenek wodoru rozkłada się – wydziela się bezbarwny gaz (tlen)."
    if cat:
        obs = f"Pod wpływem katalizatora ({', '.join(sorted(set(cat)))}) nadtlenek wodoru gwałtownie się rozkłada – " \
              "wydziela się tlen."
    if fx:
        obs = "Gwałtownie powstaje gęsta piana wypełniona tlenem wypływająca z naczynia („pasta do zębów dla słonia”)."
    yield Rx("h2o2:dec", rate, {"aq": {"H2O2": -1}, "g": {"O2": 0.5}, "vol": 0.018}, dh=-98.0, obs=obs,
             eq="2H2O2 → 2H2O + O2↑", fx=fx)
    # utlenianie jodków (zegar jodowy)
    ni = c.ct("I-")
    if ni > 1e-6 and c.h > 1e-5:
        rate2 = (0.0115 + 0.17 * min(c.h, 3)) * c.ct("H2O2") * ni * c.V * arr(c.T, 2.0, 25)
        yield Rx("h2o2:I", rate2, {"aq": {"H2O2": -1, "I-": -2, "I2": 1}, "vol": 0.036}, dh=-130,
                 obs="Nadtlenek wodoru utlenia jodki w środowisku kwasowym – powstaje jod.",
                 eq="H2O2 + 2I^- + 2H^+ → I2 + 2H2O", cap=c.acid_cap(4) / 2, bubbles=False)
    # luminol – chemiluminescencja
    if c.ct("Luminol") > 0 and c.oh > 1e-3 and (c.ct("Fe3+") > 0 or c.ct("Cu2+") > 0 or c.s("Fe_filings") > 0):
        rate3 = 0.5 * c.ct("Luminol") * min(c.ct("H2O2"), 1) * c.V * 20
        yield Rx("luminol", rate3, {"aq": {"Luminol": -1, "H2O2": -2}, "g": {"N2": 1}},
                 obs="Roztwór świeci intensywnym niebieskim światłem – chemiluminescencja luminolu.",
                 eq="luminol + 2H2O2 + 2OH^- → 3-aminoftalan* + N2 + 4H2O → hν (λ ≈ 425 nm)",
                 fx={"lum": "#3fb8ff"}, bubbles=False)


def r_thiosulfate_acid(c: Ctx):
    n = c.ct("S2O3^2-")
    if n <= 1e-6 or c.h < 1e-4:
        return
    rate = 0.05 * n * (min(c.h, 3) ** 0.7) * arr(c.T, 2.0, 20) * c.V
    yield Rx("thio:acid", rate, {"aq": {"S2O3^2-": -1, "SO3": 1}, "s": {"S_col": 1}}, dh=-20,
             obs="Roztwór stopniowo mętnieje – wydziela się koloidalna siarka (żółtawy osad).",
             eq="S2O3^2- + 2H^+ → S↓ + SO2 + H2O", cap=c.acid_cap(4.5) / 2, bubbles=False)


def r_iron_oxidation(c: Ctx):
    x = c.xgas("O2")
    for sid, prod, k, obs, eq in (
            ("Fe(OH)2", "Fe(OH)3", 0.02, "Zielonkawy osad Fe(OH)₂ stopniowo brunatnieje na powierzchni – utlenia się "
                                         "tlenem z powietrza do Fe(OH)₃.", "4Fe(OH)2 + O2 + 2H2O → 4Fe(OH)3"),
            ("Mn(OH)2", "MnO2", 0.015, "Biały osad Mn(OH)₂ brunatnieje na powietrzu (utlenianie do MnO₂).",
             "2Mn(OH)2 + O2 → 2MnO2 + 2H2O")):
        n = c.s(sid)
        if n > 0 and x > 0.02:
            yield Rx(f"airox:{sid}", k * n * x / 0.21, {"s": {sid: -1, prod: 1}}, obs=obs, eq=eq, bubbles=False)


def r_complex_tests(c: Ctx):
    """Próby Fehlinga, Tollensa, Trommera, ksantoproteinowa, denaturacja, hydroliza, estryfikacja, zmydlanie."""
    if not c.wet:
        return
    reducers = [(r, c.ct(r)) for r in ("Glc", "Fru", "HCHO", "CH3CHO") if c.ct(r) > 1e-5]
    # --- Fehling / Trommer (Cu2+ w środowisku zasadowym, ogrzewanie) ---
    cu_tot = c.ct("Cu2+")
    cuoh = c.s("Cu(OH)2")
    if reducers and c.oh > 0.02 and c.T > 45 and (cu_tot > 1e-4 or cuoh > 0):
        for r, cr in reducers:
            k = 0.06 * 2 ** ((c.T - 70) / 6)
            prod = {"Glc": "Gluc-", "Fru": "Gluc-", "HCHO": "HCOO", "CH3CHO": "AcO"}[r]
            if cu_tot > 1e-4:
                rate = k * cu_tot * cr * c.V * 40
                st = {"aq": {"Cu2+": -2, r: -1, prod: 1}, "s": {"Cu2O": 1}, "vol": 0.054}
            else:
                rate = k * cuoh * cr * 400
                st = {"s": {"Cu(OH)2": -2, "Cu2O": 1}, "aq": {r: -1, prod: 1}, "vol": 0.054}
            yield Rx(f"fehling:{r}", rate, st, dh=-50,
                     obs="Po ogrzaniu niebieska barwa zanika i wytrąca się ceglastoczerwony osad tlenku miedzi(I) – "
                         "wynik pozytywny (grupa aldehydowa).",
                     eq="R-CHO + 2Cu(OH)2 + OH^- → R-COO^- + Cu2O↓ + 3H2O", bubbles=False)
    # --- Tollens ---
    ag = c.ct("Ag+")
    if reducers and ag > 1e-5 and c.ct("NH3") > 1e-4 and c.ph > 8:
        for r, cr in reducers:
            k = 0.08 * 2 ** ((c.T - 40) / 8)
            prod = {"Glc": "Gluc-", "Fru": "Gluc-", "HCHO": "HCOO", "CH3CHO": "AcO"}[r]
            rate = k * ag * cr * c.V * 30
            yield Rx(f"tollens:{r}", rate, {"aq": {"Ag+": -2, r: -1, prod: 1}, "s": {"Ag": 2}}, dh=-40,
                     obs="Na ściankach naczynia osadza się lśniące lustro srebrne – próba Tollensa pozytywna.",
                     eq="R-CHO + 2[Ag(NH3)2]^+ + 3OH^- → R-COO^- + 2Ag↓ + 4NH3 + 2H2O", fx={"mirror": 1},
                     bubbles=False)
    # --- białka ---
    prot = c.ct("Protein")
    if prot > 0:
        if c.ct("NO3-") > 4 and c.h > 4:
            yield Rx("xanto", 0.15 * c.n("Protein") * arr(c.T, 2.0),
                     {"aq": {"Protein": -1, "ProteinX": 1}},
                     obs="Białko ścina się i barwi na żółto – reakcja ksantoproteinowa (nitrowanie pierścieni "
                         "aromatycznych).", eq="białko + HNO3 → żółte nitropochodne", bubbles=False)
        coag = 0.0
        why = ""
        if c.T > 62:
            coag, why = 0.08 * arr(c.T, 2.5, 65), "pod wpływem wysokiej temperatury"
        for ion in ("Cu2+", "Pb2+", "Ag+"):
            if c.ct(ion) > 5e-3:
                coag, why = 0.4, "pod wpływem soli metali ciężkich"
        if c.ct("EtOH") > 3:
            coag, why = 0.2, "pod wpływem etanolu"
        if c.h > 0.5 and c.ct("NO3-") < 4:
            coag, why = 0.25, "pod wpływem stężonego kwasu"
        if coag > 0:
            yield Rx("denat", coag * c.n("Protein"), {"aq": {"Protein": -1}, "s": {"ProteinCoag": 1}},
                     obs=f"Białko ulega denaturacji {why} – wytrąca się biały, kłaczkowaty osad.",
                     eq="białko natywne → białko zdenaturowane (zmiana struktury II- i III-rzędowej)",
                     bubbles=False)
    px = c.ct("ProteinX")
    if px > 0 and c.T > 62:
        pass
    # --- hydroliza skrobi i sacharozy ---
    if c.h > 0.2 and c.T > 75:
        if c.n("Starch") > 0:
            yield Rx("hydro:starch", 0.02 * c.n("Starch") * arr(c.T, 2.0, 90),
                     {"aq": {"Starch": -1, "Glc": 1}},
                     obs="Skrobia hydrolizuje w gorącym kwasie do glukozy (zanika reakcja z jodem).",
                     eq="(C6H10O5)n + nH2O → nC6H12O6", bubbles=False)
        if c.n("Suc") > 0:
            yield Rx("hydro:suc", 0.012 * c.n("Suc") * arr(c.T, 2.0, 90), {"aq": {"Suc": -1, "Glc": 1, "Fru": 1}},
                     obs="Sacharoza ulega hydrolizie do glukozy i fruktozy (cukier inwertowany).",
                     eq="C12H22O11 + H2O → C6H12O6 + C6H12O6", bubbles=False)
    # --- estryfikacja (z katalizą kwasową) ---
    acid = c.c("CH3COOH")
    eth = c.ct("EtOH")
    if acid > 1e-3 and eth > 1e-3 and c.h > 0.05:
        cat = min(c.h, 6.0)
        kf = 0.0008 * cat * arr(c.T, 2.2, 25)
        water = max(1.0, 55.5 * (1.0 - c.eth_frac()))
        rate = kf * (acid * eth - c.ct("EtOAc") * water / 4.0) * c.V
        if rate > 0:
            yield Rx("ester", rate, {"aq": {"AcO": -1, "EtOH": -1, "EtOAc": 1}, "vol": 0.018 - 0.058}, dh=-3,
                     obs="Wyczuwalny jest przyjemny, owocowy zapach – powstaje octan etylu (ester).",
                     eq="CH3COOH + C2H5OH ⇌ CH3COOC2H5 + H2O (H2SO4, ogrzewanie)", bubbles=False)
    # --- zmydlanie tłuszczu ---
    oil = c.org("Oil")
    if oil > 0 and c.oh > 0.05:
        rate = 0.004 * oil * min(c.oh, 4) * arr(c.T, 2.3, 25) * (1.0 if c.stir else 0.4)
        yield Rx("sapon", rate, {"org": {"Oil": -1}, "aq": {"Glycerol": 1, "St-": 3}}, dh=-30,
                 obs="Tłuszcz stopniowo znika – zmydla się do glicerolu i mydła (stearynianu sodu).",
                 eq="tłuszcz + 3NaOH → glicerol + 3C17H35COONa", cap=c.base_cap(10.5) / 3, bubbles=False)
    # --- alkeny ---
    alk = c.org("C6H10")
    if alk > 0:
        br = c.n("Br2") + c.org("Br2")
        if br > 1e-10:
            k = 40.0 if c.stir or c.org("Br2") > 0 else 2.0
            rate = k * min(br, alk)
            src_aq = c.n("Br2") >= c.org("Br2")
            st = {"org": {"C6H10": -1, "C6H10Br2": 1}}
            if src_aq:
                st["aq"] = {"Br2": -1}
            else:
                st["org"]["Br2"] = -1
            yield Rx("alkene:Br2", rate, st, dh=-120,
                     obs="Pomarańczowa barwa bromu szybko zanika – addycja bromu do wiązania podwójnego.",
                     eq="C6H10 + Br2 → C6H10Br2", bubbles=False)
    # --- „niebieska butelka” (błękit metylenowy + glukoza + NaOH) ---
    if c.ct("MB") > 0 and c.ct("Glc") > 1e-3 and c.oh > 0.05:
        rate = 0.08 * c.n("MB") * min(c.oh, 2) * arr(c.T, 2.0, 25)
        yield Rx("bluebottle:red", rate, {"aq": {"MB": -1, "MBH": 1, "Glc": -1e-3}},
                 obs="Niebieski roztwór powoli odbarwia się – glukoza redukuje błękit metylenowy do formy leuko.",
                 eq="MB^+ (niebieski) + glukoza → MBH (bezbarwny)", bubbles=False)
    if c.ct("MBH") > 0:
        x = c.xgas("O2")
        rate = (2.0 if c.stir else 0.004) * c.n("MBH") * max(x, 0.0) / 0.21
        yield Rx("bluebottle:ox", rate, {"aq": {"MBH": -1, "MB": 1}},
                 obs="Po wstrząśnięciu tlen z powietrza ponownie utlenia barwnik – roztwór znów jest niebieski.",
                 eq="2MBH + O2 → 2MB^+ (niebieski) + 2OH^-", bubbles=False)


def r_hydrates(c: Ctx):
    """Bezwodny CuSO4 + kropla wody -> niebieski hydrat (test na wodę) oraz karbid, nadtlenek sodu."""
    n = c.s("CuSO4")
    if n > 0 and 0.01 < c.vol < 2.0 + 0.09 * n * 1000:
        yield Rx("cuso4:hyd", 0.5 * n, {"s": {"CuSO4": -1, "CuSO4·5H2O": 1}, "vol": -0.09}, dh=-78,
                 obs="Biały bezwodny siarczan(VI) miedzi(II) po zwilżeniu wodą zmienia barwę na niebieską i "
                     "ogrzewa się – wykryto wodę.", eq="CuSO4 (biały) + 5H2O → CuSO4·5H2O (niebieski)", bubbles=False)
    if c.wet and c.s("CaC2") > 0:
        yield Rx("carbide", 0.004 * c.area("CaC2") * arr(c.T), {"s": {"CaC2": -1}, "aq": {"Ca2+": 1},
                                                                  "g": {"C2H2": 1}, "vol": -0.036}, dh=-125,
                 obs="Karbid burzliwie reaguje z wodą – wydziela się etyn (acetylen), roztwór mętnieje od Ca(OH)₂.",
                 eq="CaC2 + 2H2O → C2H2↑ + Ca(OH)2")
    if c.wet and c.s("Na2O2") > 0:
        yield Rx("na2o2:w", 0.15 * c.s("Na2O2"), {"s": {"Na2O2": -1}, "aq": {"Na+": 2}, "g": {"O2": 0.5},
                                                   "vol": -0.018}, dh=-70,
                 obs="Nadtlenek sodu reaguje z wodą – wydziela się tlen, roztwór jest silnie zasadowy.",
                 eq="2Na2O2 + 2H2O → 4NaOH + O2↑")
    # dysocjacja tlenku fosforu i inne tlenki niemetali rozpuszczają się w ramach równowag (sole)


# ===============================================================================================================
# Reakcje ciał stałych i rozkłady termiczne
# ===============================================================================================================
def r_thermal(c: Ctx):
    T = c.T
    defs = [
        # (ciało, próg, k, stechiometria, dh, obs, eq, fx)
        ("KMnO4", 215, 0.03, {"s": {"KMnO4": -1, "K2MnO4": 0.5, "MnO2": 0.5}, "g": {"O2": 0.5}}, 20,
         "Kryształy KMnO₄ trzaskają i ciemnieją – wydziela się tlen (żarzące się łuczywo rozbłyska).",
         "2KMnO4 → K2MnO4 + MnO2 + O2↑", {"crackle": 1}),
        ("CaCO3", 640, 0.006, {"s": {"CaCO3": -1, "CaO": 1}, "g": {"CO2": 1}}, 178,
         "Węglan wapnia rozkłada się w wysokiej temperaturze – wydziela się CO₂, powstaje wapno palone (CaO).",
         "CaCO3 → CaO + CO2↑", {}),
        ("CaCO3_chips", 640, 0.004, {"s": {"CaCO3_chips": -1, "CaO": 1}, "g": {"CO2": 1}}, 178,
         "Marmur prażony w płomieniu rozkłada się – powstaje CaO i CO₂.", "CaCO3 → CaO + CO2↑", {}),
        ("CuCO3", 240, 0.05, {"s": {"CuCO3": -1, "CuO": 1}, "g": {"CO2": 1}}, 50,
         "Zielony węglan miedzi(II) czernieje – powstaje CuO, wydziela się CO₂ (mętnieje woda wapienna).",
         "CuCO3 → CuO + CO2↑", {}),
        ("NaHCO3", 90, 0.03, {"s": {"NaHCO3": -1, "Na2CO3": 0.5}, "g": {"CO2": 0.5, "H2O": 0.5}}, 65,
         "Soda oczyszczona rozkłada się – wydziela się CO₂ i para wodna (kropelki wody u wylotu).",
         "2NaHCO3 → Na2CO3 + H2O + CO2↑", {}),
        ("Cu(OH)2", 65, 0.03, {"s": {"Cu(OH)2": -1, "CuO": 1}, "vol": 0.018}, 10,
         "Niebieski osad Cu(OH)₂ podczas ogrzewania czernieje – powstaje tlenek miedzi(II).",
         "Cu(OH)2 → CuO + H2O", {}),
        ("CuSO4·5H2O", 105, 0.02, {"s": {"CuSO4·5H2O": -1, "CuSO4": 1}, "g": {"H2O": 5}}, 78,
         "Niebieskie kryształy tracą wodę krystalizacyjną i bieleją (bezwodny CuSO₄); u wylotu skrapla się woda.",
         "CuSO4·5H2O → CuSO4 + 5H2O", {}),
        ("NH4Cl", 300, 0.03, {"s": {"NH4Cl": -1}, "g": {"NH3": 1, "HCl": 1}}, 176,
         "Chlorek amonu „sublimuje” – rozkłada się na NH₃ i HCl, które w chłodniejszej części ponownie tworzą "
         "biały nalot.", "NH4Cl ⇌ NH3 + HCl", {}),
        ("I2_s", 85, 0.012, {"s": {"I2_s": -1}, "g": {"I2": 1}}, 62,
         "Jod sublimuje – naczynie wypełniają fioletowe pary.", "I2(s) → I2(g)", {}),
        ("Pb(NO3)2", 300, 0.02, {"s": {"Pb(NO3)2": -1, "PbO": 1}, "g": {"NO2": 2, "O2": 0.5}}, 300,
         "Kryształy trzaskają, wydziela się brunatny NO₂, pozostaje żółty PbO.", "2Pb(NO3)2 → 2PbO + 4NO2↑ + O2↑",
         {"crackle": 1}),
        ("Ag2O", 200, 0.02, {"s": {"Ag2O": -1, "Ag": 2}, "g": {"O2": 0.5}}, 31,
         "Brunatny tlenek srebra rozkłada się – pozostaje srebro, wydziela się tlen.", "2Ag2O → 4Ag + O2↑", {}),
        ("Suc_s", 190, 0.01, {"s": {"Suc_s": -1, "Caramel": 1}, "g": {"H2O": 2}}, 10,
         "Cukier topi się i brunatnieje – karmelizuje, pojawia się zapach karmelu.", "C12H22O11 → karmel + H2O", {}),
        ("Caramel", 300, 0.01, {"s": {"Caramel": -1, "C_char": 12}, "g": {"H2O": 9}}, 10,
         "Karmel czernieje i zwęgla się – pozostaje węgiel, wydziela się para wodna.", "karmel → C + H2O", {}),
        ("Glc_s", 200, 0.01, {"s": {"Glc_s": -1, "C_char": 6}, "g": {"H2O": 6}}, 10,
         "Glukoza topi się, brunatnieje i zwęgla.", "C6H12O6 → 6C + 6H2O", {}),
        ("KNO3", 420, 0.006, {"s": {"KNO3": -1, "KCl_from": 0}, "g": {"O2": 0.5}}, 120,
         "Saletra topi się i powoli wydziela tlen.", "2KNO3 → 2KNO2 + O2↑", {}),
    ]
    for sid, thr, k, st, dh, obs, eq, fx in defs:
        n = c.s(sid)
        if n <= 0 or T < thr:
            continue
        if sid in ("NaHCO3", "Cu(OH)2") and False:
            pass
        rate = k * n * math.exp(min((T - thr) / 40.0, 6.0))
        if sid == "Cu(OH)2":
            rate = k * n * math.exp(min((T - thr) / 10.0, 6.0))
        if sid == "CuSO4·5H2O" and c.vol > 0.5:
            continue  # w roztworze się rozpuszcza
        if sid in ("KMnO4", "NaHCO3", "NH4Cl", "Pb(NO3)2", "KNO3", "Suc_s", "Glc_s") and c.vol > 0.5:
            continue
        yield Rx(f"heat:{sid}", rate, st, dh=dh, obs=obs, eq=eq, fx=fx, bubbles=False)
    # chloran(V) potasu (z katalizatorem MnO2 lub bez)
    n = c.s("KClO3")
    if n > 0 and c.vol < 0.5:
        cat = c.s("MnO2") > 0
        thr = 200 if cat else 380
        if T > thr:
            rate = (0.05 if cat else 0.01) * n * math.exp(min((T - thr) / 40.0, 6.0))
            yield Rx("heat:KClO3", rate, {"s": {"KClO3": -1, "KCl_from": 1}, "g": {"O2": 1.5}}, dh=-39,
                     obs="Chloran(V) potasu rozkłada się – wydziela się tlen" + (
                         " (MnO₂ przyspiesza rozkład jako katalizator)." if cat else "."),
                     eq="2KClO3 → 2KCl + 3O2↑" + (" (MnO2)" if cat else ""))
    # dichromian amonu – „wulkan”
    n = c.s("(NH4)2Cr2O7")
    if n > 0 and (T > 185 or c.prog.get("volcano")):
        c.prog["volcano"] = 1.0
        yield Rx("volcano", 0.12 * n + 1e-5, {"s": {"(NH4)2Cr2O7": -1, "Cr2O3": 0.5}, "g": {"N2": 0.5, "H2O": 2}},
                 dh=-160, obs="Dichromian amonu rozkłada się jak „wulkan” – iskry i obfity, zielony, puszysty Cr₂O₃.",
                 eq="(NH4)2Cr2O7 → Cr2O3 + N2↑ + 4H2O", fx={"sparks": "#ffb347", "volcano": 1, "glow": 1})
    # żelazo + siarka
    nfe, ns = c.s("Fe_filings"), c.s("S")
    if nfe > 0 and ns > 0 and (T > 280 or c.prog.get("fes")):
        c.prog["fes"] = 1.0
        yield Rx("fes", 0.08 * min(nfe, ns) + 1e-6, {"s": {"Fe_filings": -1, "S": -1, "FeS": 1}}, dh=-100,
                 obs="Mieszanina żelaza i siarki rozżarza się i reaguje samorzutnie dalej – powstaje czarny FeS.",
                 eq="Fe + S → FeS", fx={"glow": 1})
    # termit
    nal, nfe2o3 = c.s("Al_powder"), c.s("Fe2O3")
    burning_mg = any(k.startswith("burn:Mg") for k in c.v.get("fx", {}).get("_active", []))
    if nal > 0 and nfe2o3 > 0 and (T > 900 or burning_mg or c.prog.get("thermite")):
        c.prog["thermite"] = 1.0
        yield Rx("thermite", 0.5 * min(nfe2o3, nal / 2) + 1e-6,
                 {"s": {"Fe2O3": -1, "Al_powder": -2, "Al2O3": 1, "Fe_molten": 2}}, dh=-850,
                 obs="Termit zapala się – oślepiający blask, snop iskier i wypływające ciekłe żelazo!",
                 eq="Fe2O3 + 2Al → Al2O3 + 2Fe", fx={"sparks": "#fff1b8", "bright": 1, "flame": "#fff3c4"})
    # glicerol + KMnO4 – samozapłon
    nk = c.s("KMnO4")
    gly = c.n("Glycerol")
    if nk > 0 and gly > 0:
        active = c.vol < 0.6 * gly * 92.09 / 1.26 * 1000 + 0.5
        if c.induction("glyc", active, 12.0):
            yield Rx("glycerol", 0.08 * min(nk, gly * 14 / 3) + 1e-6,
                     {"s": {"KMnO4": -1, "MnO2": 1}, "aq": {"Glycerol": -3 / 14, "K+": 1}, "g": {"CO2": 0.6,
                                                                                               "H2O": 0.8}},
                     dh=-180, obs="Po kilkunastu sekundach mieszanina zaczyna dymić i zapala się fioletowym "
                                  "płomieniem – samozapłon glicerolu z KMnO₄.",
                     eq="14KMnO4 + 4C3H5(OH)3 → 7K2CO3 + 7Mn2O3 + 5CO2 + 16H2O",
                     fx={"flame": "#c86cf0", "smoke": "#cfcfcf", "sparks": "#ffcf70"})
    # Ba(OH)2·8H2O + NH4SCN – reakcja silnie endotermiczna
    nb, nt = c.s("Ba(OH)2·8H2O"), c.s("NH4SCN")
    if nb > 0 and nt > 0 and (c.stir or c.prog.get("endo")):
        c.prog["endo"] = 1.0
        yield Rx("endo", 0.06 * min(nb, nt / 2) + 1e-6,
                 {"s": {"Ba(OH)2·8H2O": -1, "NH4SCN": -2}, "aq": {"Ba2+": 1, "SCN-": 2, "NH3": 2}, "vol": 0.18},
                 dh=164, obs="Kryształy mieszają się w mokrą masę, czuć amoniak, a naczynie silnie się oziębia – "
                             "reakcja endotermiczna (woda pod zlewką zamarza).",
                 eq="Ba(OH)2·8H2O + 2NH4SCN → Ba(SCN)2 + 2NH3↑ + 10H2O   ΔH > 0", bubbles=False)
    # cukier + stężony H2SO4
    nsuc = c.s("Suc_s") + c.n("Suc")
    if nsuc > 0 and c.ct("SO4") > 13:
        if c.induction("sugar", True, 6.0):
            src = {"s": {"Suc_s": -1}} if c.s("Suc_s") > 0 else {"aq": {"Suc": -1}}
            src.setdefault("s", {})["C_char"] = 12
            src["g"] = {"H2O": 6, "SO2": 0.3, "CO2": 0.3}
            src["vol"] = 0.09
            yield Rx("sugar:h2so4", 0.03 * nsuc + 2e-5, src, dh=-450,
                     obs="Cukier czernieje, a z naczynia wyrasta czarna, porowata kolumna węgla; wydziela się para "
                         "wodna i duszący SO₂ – stężony H₂SO₄ odwadnia sacharozę.",
                     eq="C12H22O11 → 12C + 11H2O (stęż. H2SO4)", fx={"blacksnake": 1, "steam": 1})


# ===============================================================================================================
# Spalanie
# ===============================================================================================================
def r_combustion(c: Ctx):
    x = c.xgas("O2")
    xcl = c.xgas("Cl2")
    xco2 = c.xgas("CO2")
    T = c.T
    if c.vol > 2.0:
        return  # w cieczy nic się nie pali
    fuels = [
        # (ciało, próg zapłonu, k, produkty, tlen na mol, dh, barwa płomienia, obs_powietrze, obs_tlen, eq, fx)
        ("Mg", 560, 0.0008, {"MgO": 1}, 0.5, -601, "#ffffff",
         "Magnez spala się oślepiająco jasnym, białym płomieniem; powstaje biały proszek MgO.",
         "Magnez spala się w tlenie jeszcze jaśniej, rozjarzając cały cylinder; powstaje biały dym MgO.",
         "2Mg + O2 → 2MgO", {"bright": 1, "smoke": "#f5f5f5"}),
        ("Mg_powder", 500, 0.002, {"MgO": 1}, 0.5, -601, "#ffffff",
         "Proszek magnezu spala się oślepiającym błyskiem.", "Proszek magnezu spala się błyskawicznie.",
         "2Mg + O2 → 2MgO", {"bright": 1, "smoke": "#f5f5f5"}),
        ("Fe_wool", 380, 0.00001, {"Fe3O4": 1 / 3}, 2 / 3, -373, None,
         "Wata stalowa żarzy się i sypie iskrami.",
         "Żelazo spala się w tlenie, rozsypując snopy jasnych iskier; powstaje czarny Fe₃O₄.",
         "3Fe + 2O2 → Fe3O4", {"sparks": "#ffcf5a"}),
        ("Fe_filings", 500, 0.00001, {"Fe3O4": 1 / 3}, 2 / 3, -373, None,
         "Opiłki żelaza wsypane w płomień spalają się iskrami.", "Opiłki żelaza spalają się w tlenie snopem iskier.",
         "3Fe + 2O2 → Fe3O4", {"sparks": "#ffcf5a"}),
        ("S", 250, 0.00003, {}, 1.0, -297, "#5a6cff",
         "Siarka topi się i spala małym, bladoniebieskim płomieniem; czuć duszący zapach SO₂.",
         "Siarka spala się w tlenie jasnym, niebiesko-fioletowym płomieniem; powstaje duszący SO₂.",
         "S + O2 → SO2", {}),
        ("C", 480, 0.00002, {}, 1.0, -394, None,
         "Węgiel drzewny żarzy się na czerwono.", "Węgiel drzewny spala się w tlenie jasnym, białym blaskiem bez płomienia.",
         "C + O2 → CO2", {"glow": 1}),
        ("P", 260, 0.00005, {"P4O10": 0.25}, 1.25, -746, "#fff2b0",
         "Fosfor spala się żółtym płomieniem, wydzielając gęsty biały dym (P₄O₁₀).",
         "Fosfor spala się w tlenie oślepiającym płomieniem i gęstym białym dymem.",
         "4P + 5O2 → P4O10", {"smoke": "#f7f7f7"}),
        ("Na", 120, 0.001, {"Na2O2": 0.5}, 0.5, -255, "#ffb21a",
         "Sód topi się i spala intensywnie żółtym płomieniem.", "Sód spala się w tlenie jaskrawożółtym płomieniem.",
         "2Na + O2 → Na2O2", {"smoke": "#f7f2d8"}),
        ("Cu", 280, 0.000002, {"CuO": 1}, 0.5, -157, None,
         "Miedź ogrzewana w płomieniu pokrywa się czarnym nalotem tlenku miedzi(II); płomień barwi się na zielono.",
         "Miedź czernieje – pokrywa się CuO.", "2Cu + O2 → 2CuO", {}),
        ("Cu_foil", 280, 0.000003, {"CuO": 1}, 0.5, -157, None,
         "Blaszka miedziana czernieje w płomieniu – powstaje CuO.", "Blaszka miedziana czernieje (CuO).",
         "2Cu + O2 → 2CuO", {}),
        ("Wax", 220, 2.2e-6, {}, 38.0, -15000, "#ffb347",
         "Świeca pali się jasnym, żółtym, kopcącym płomieniem.", "Świeca w tlenie pali się bardzo jasno.",
         "C25H52 + 38O2 → 25CO2 + 26H2O", {"candle": 1}),
    ]
    burning = []
    for sid, ign, k, prods, o2, dh, flame, obs_air, obs_o2, eq, fx in fuels:
        n = c.s(sid)
        if n <= 0:
            continue
        lit = T > ign or (c.prog.get(f"lit:{sid}") and T > ign * 0.6)
        if not lit:
            c.prog.pop(f"lit:{sid}", None)
            continue
        if sid == "Wax":
            factor = max(0.0, min(1.0, (x - 0.155) / 0.05))
            if x > 0.4:
                factor = 3.0
        else:
            factor = (x / 0.21) ** 1.2 if sid not in ("Fe_wool", "Fe_filings", "C") else (x / 0.21) ** 1.8
        if factor <= 1e-3:
            c.prog.pop(f"lit:{sid}", None)
            # Magnez pali się w CO2
            if sid in ("Mg", "Mg_powder") and xco2 > 0.5 and T > ign:
                rate = k * 0.5 * c.area(sid)
                yield Rx(f"burn:{sid}:CO2", rate, {"s": {sid: -1, "MgO": 1, "C_char": 0.5}, "env": {"CO2": -0.5}},
                         dh=-405, obs="Magnez pali się nawet w CO₂! Powstaje biały MgO z czarnymi drobinami węgla.",
                         eq="2Mg + CO2 → 2MgO + C", fx={"flame": "#ffffff", "bright": 1, "smoke": "#e8e8e8"},
                         bubbles=False)
            continue
        c.prog[f"lit:{sid}"] = 1.0
        rate = k * c.area(sid) * factor
        if sid == "Wax":
            rate = k * factor
        st = {"s": {sid: -1}, "env": {"O2": -o2}}
        for p, v in prods.items():
            st["s"][p] = v
        gas_prod = {"S": {"SO2": 1}, "C": {"CO2": 1}, "Wax": {"CO2": 25, "H2O": 26}}.get(sid, {})
        for gk, gv in gas_prod.items():
            st["env"][gk] = gv
        fxx = dict(fx)
        if flame:
            fxx["flame"] = flame
        if x > 0.5 and sid in ("S",):
            fxx["flame"] = "#7a5cff"
        burning.append(sid)
        yield Rx(f"burn:{sid}:{'o2' if x > 0.45 else 'air'}", rate, st, dh=dh, obs=obs_o2 if x > 0.45 else obs_air,
                 eq=eq, fx=fxx,
                 bubbles=False)
    # sód / żelazo w chlorze
    if xcl > 0.3:
        for sid, ign, k, prods, cl2, dh, obs, eq, fx in (
                ("Na", 100, 0.001, {"NaCl_smoke": 1}, 0.5, -411,
                 "Sód spala się w chlorze żółtym płomieniem, wydzielając biały dym chlorku sodu.", "2Na + Cl2 → 2NaCl",
                 {"flame": "#ffb21a", "smoke": "#f7f7f7"}),
                ("Fe_wool", 250, 0.00003, {"FeCl3_smoke": 1}, 1.5, -399,
                 "Rozgrzana wata stalowa spala się w chlorze, wydzielając brunatny dym FeCl₃.", "2Fe + 3Cl2 → 2FeCl3",
                 {"sparks": "#ff9a3a", "smoke": "#8e4a1a"}),
                ("Cu_foil", 250, 0.00002, {"CuCl2·2H2O": 1}, 1.0, -220,
                 "Rozgrzana miedź spala się w chlorze – powstaje brunatnożółty dym CuCl₂.", "Cu + Cl2 → CuCl2",
                 {"smoke": "#a88a3a"})):
            if c.s(sid) > 0 and T > ign:
                st = {"s": {sid: -1}, "env": {"Cl2": -cl2}}
                st["s"].update(prods)
                yield Rx(f"burnCl:{sid}", k * c.area(sid) * xcl, st, dh=dh, obs=obs, eq=eq, fx=fx, bubbles=False)


RULES = [r_metal_acid, r_metal_water, r_metal_base, r_displacement, r_nitric, r_conc_sulfuric, r_permanganate,
         r_manganate, r_dichromate, r_halogens, r_peroxide, r_thiosulfate_acid, r_iron_oxidation, r_complex_tests,
         r_hydrates, r_thermal, r_combustion]
