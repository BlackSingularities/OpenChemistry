"""Wygląd naczynia: barwa roztworu (prawo Lamberta-Beera), zmętnienie, osady, gazy, efekty wizualne."""
from __future__ import annotations

import math
from functools import lru_cache

from .data import ACIDS, COMPLEXES, GASES, INDICATORS, IONS, MOLECULES, SOLIDS, FLAME_COLORS

ORG_SPECIES = {
    "C6H14": ("heksan", 86.18, 0.655, None),
    "C6H10": ("cykloheksen", 82.14, 0.81, None),
    "Oil": ("olej roślinny", 885.0, 0.92, ("#f2d36b", 1.0)),
    "C6H10Br2": ("1,2-dibromocykloheksan", 241.95, 1.78, None),
    "C6H10(OH)2": ("cykloheksano-1,2-diol", 116.16, 1.0, None),
    "I2": ("jod (w fazie organicznej)", 253.8, None, ("#8b2fa0", 0.004)),
    "Br2": ("brom (w fazie organicznej)", 159.8, None, ("#e07a1c", 0.02)),
}

FORM_NAMES = {
    "H2CO3": "kwas węglowy (CO₂ aq)", "HCO3-": "wodorowęglan", "CO3^2-": "węglan",
    "NH4+": "jon amonowy", "NH3": "amoniak", "CH3COOH": "kwas octowy", "CH3COO-": "octan",
    "HSO4-": "wodorosiarczan(VI)", "SO4^2-": "siarczan(VI)", "H3PO4": "kwas fosforowy(V)",
    "H2PO4-": "diwodorofosforan(V)", "HPO4^2-": "wodorofosforan(V)", "PO4^3-": "fosforan(V)",
    "H2SO3": "kwas siarkowy(IV) (SO₂ aq)", "HSO3-": "wodorosiarczan(IV)", "SO3^2-": "siarczan(IV)",
    "H2S": "siarkowodór", "HS-": "wodorosiarczek", "S^2-": "siarczek", "H2C2O4": "kwas szczawiowy",
    "HC2O4-": "wodoroszczawian", "C2O4^2-": "szczawian", "HClO": "kwas chlorowy(I)", "ClO-": "chloran(I)",
    "HCrO4-": "dichromian(VI) / wodorochromian", "CrO4^2-": "chromian(VI)", "H3Cit": "kwas cytrynowy",
    "H2Cit-": "diwodorocytrynian", "HCit^2-": "wodorocytrynian", "Cit^3-": "cytrynian",
    "H2Asc": "kwas askorbinowy", "HAsc-": "askorbinian", "HCOOH": "kwas mrówkowy", "HCOO-": "mrówczan",
}

NAMED_COLORS = [
    ("bezbarwny", (250, 250, 250)), ("biały", (245, 245, 242)), ("jasnoniebieski", (150, 200, 240)),
    ("niebieski", (60, 130, 220)), ("granatowy", (30, 45, 150)), ("ciemnoniebieski", (25, 35, 90)),
    ("fioletowy", (120, 50, 160)), ("purpurowy", (150, 40, 130)), ("malinowy", (220, 50, 120)),
    ("różowy", (240, 140, 180)), ("jasnoróżowy", (248, 200, 220)), ("czerwony", (200, 30, 30)),
    ("krwistoczerwony", (150, 20, 20)), ("pomarańczowy", (240, 140, 30)), ("żółty", (240, 215, 50)),
    ("jasnożółty", (245, 235, 160)), ("żółtozielony", (180, 210, 60)), ("zielony", (60, 160, 80)),
    ("ciemnozielony", (30, 90, 50)), ("seledynowy", (190, 225, 170)), ("turkusowy", (40, 170, 170)),
    ("brunatny", (120, 60, 25)), ("brązowy", (140, 80, 40)), ("ceglasty", (170, 70, 40)),
    ("szary", (128, 128, 128)), ("czarny", (25, 25, 25)), ("brunatnożółty", (200, 140, 50)),
]


def hex2rgb(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def rgb2hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(x)))) for x in c)


@lru_cache(maxsize=512)
def eps(hexcol: str, ref: float):
    r = hex2rgb(hexcol)
    return tuple(-math.log10(max(ch, 3) / 255.0) / ref for ch in r)


def color_name(rgb, alpha_hint: float | None = None) -> str:
    """Polska nazwa barwy na podstawie odcienia (HSV)."""
    import colorsys
    r, g, b = (max(0.0, min(1.0, x / 255.0)) for x in rgb)
    h, sat, val = colorsys.rgb_to_hsv(r, g, b)
    h *= 360
    if sat < 0.07 and val > 0.86:
        return "bezbarwny"
    if val < 0.16:
        return "czarny"
    if sat < 0.14:
        return "szary" if val < 0.75 else "białawy"
    light = val > 0.82 and sat < 0.42
    dark = val < 0.45
    if h < 12 or h >= 345:
        return "różowy" if light else ("brunatnoczerwony" if dark else "czerwony")
    if h < 40:
        if dark:
            return "brunatny"
        return "jasnopomarańczowy" if light else ("ceglasty" if sat > 0.6 and val < 0.7 else "pomarańczowy")
    if h < 64:
        if dark:
            return "brunatnożółty"
        return "jasnożółty" if light else "żółty"
    if h < 88:
        return "żółtozielony" if not dark else "oliwkowy"
    if h < 160:
        return "seledynowy" if light else ("ciemnozielony" if dark else "zielony")
    if h < 195:
        return "jasnoniebieskozielony" if light else "niebieskozielony"
    if h < 250:
        if light:
            return "jasnoniebieski"
        return "granatowy" if (dark or (sat > 0.75 and val < 0.65)) else "niebieski"
    if h < 290:
        return "jasnofioletowy" if light else "fioletowy"
    if h < 322:
        return "różowofioletowy" if light else "purpurowy"
    return "różowy" if light else "malinowy"


def _interp_palette(pal, ph):
    if ph <= pal[0][0]:
        return pal[0][1]
    for (p0, c0), (p1, c1) in zip(pal, pal[1:]):
        if ph <= p1:
            t = (ph - p0) / (p1 - p0)
            a, b = hex2rgb(c0), hex2rgb(c1)
            return rgb2hex([a[i] + (b[i] - a[i]) * t for i in range(3)])
    return pal[-1][1]


_CX = {c.id: c for c in COMPLEXES}


def absorbance(sp, path: float):
    A = [0.0, 0.0, 0.0]

    def add(col, conc):
        if not col or conc <= 0:
            return
        e = eps(*col)
        for i in range(3):
            A[i] += e[i] * conc * path

    for name, conc in sp.free.items():
        if conc <= 1e-9:
            continue
        if name in IONS:
            add(IONS[name].color, conc)
        elif name in _CX:
            add(_CX[name].color, conc)
        elif name in MOLECULES:
            add(MOLECULES[name].color, conc)
        elif name.startswith("ind:"):
            ind = INDICATORS.get(name[4:])
            if not ind:
                continue
            if ind.palette:
                add((_interp_palette(ind.palette, sp.ph), ind.ref), conc)
            else:
                fb = 1.0 / (1.0 + 10 ** (ind.pka - sp.ph))
                add(ind.acid, conc * (1 - fb))
                add(ind.base, conc * fb)
    for sysd in ACIDS.values():
        if sysd.colors:
            for j, form in enumerate(sysd.forms):
                add(sysd.colors[j], sp.free.get(form, 0.0))
    return A


def liquid_rgb(sp, path):
    A = absorbance(sp, path)
    return tuple(255.0 * 10 ** (-min(a, 4.0)) for a in A), A


def org_rgb(v, path):
    vol = v.get("org_vol", 0.0)
    if vol <= 0:
        return None
    A = [0.0, 0.0, 0.0]
    for sid, n in v.get("org", {}).items():
        info = ORG_SPECIES.get(sid)
        if not info or not info[3] or n <= 0:
            continue
        conc = n / (vol / 1000.0)
        if sid == "Oil":
            conc = 1.0
        e = eps(*info[3])
        for i in range(3):
            A[i] += e[i] * conc * path
    return tuple(255.0 * 10 ** (-min(a, 4.0)) for a in A)


def species_label(name: str) -> str:
    if name in IONS:
        return IONS[name].name
    if name in _CX:
        return _CX[name].name
    if name in MOLECULES:
        return MOLECULES[name].name
    if name in FORM_NAMES:
        return FORM_NAMES[name]
    if name.startswith("ind:"):
        ind = INDICATORS.get(name[4:])
        return ind.name if ind else name
    return name


def formula_of(name: str) -> str:
    if name.startswith("ind:"):
        return ""
    return name


def flame_color_for(v) -> tuple[str, str] | None:
    """Barwa płomienia od kationów w naczyniu (test płomieniowy)."""
    weights = {}
    for comp, n in v.get("aq", {}).items():
        ion = IONS.get(comp)
        if ion and ion.flame and n > 1e-7:
            weights[ion.flame] = weights.get(ion.flame, 0.0) + n
    for sid, st in v.get("solids", {}).items():
        s = SOLIDS.get(sid)
        if not s or st.get("n", 0) <= 0:
            continue
        for sp, _nu in s.comp:
            ion = IONS.get(sp)
            if ion and ion.flame:
                weights[ion.flame] = weights.get(ion.flame, 0.0) + st["n"]
        if s.flame:
            weights[s.flame] = weights.get(s.flame, 0.0) + st["n"]
    if not weights:
        return None
    if "Na" in weights:
        weights["Na"] *= 8.0  # sód dominuje barwę płomienia
    key = max(weights, key=weights.get)
    return FLAME_COLORS[key]


def view(v: dict, sp, e) -> dict:
    path = max(0.5, min(2.0, e.diam / 4.0))
    out = {"id": v["id"], "type": v["type"], "vol": round(v["vol"], 3), "org_vol": round(v.get("org_vol", 0.0), 3),
           "T": round(v["T"], 1), "heat": v.get("heat"), "stopper": v.get("stopper", False),
           "outlet": v.get("outlet"), "mirror": v.get("mirror"), "fx": {k: val for k, val in v.get("fx", {}).items() if not k.startswith("_")}}
    if v["vol"] > 0.01 and sp is not None:
        rgb, A = liquid_rgb(sp, path)
        out["pH"] = round(sp.ph, 2)
        out["liquid"] = rgb2hex(rgb)
        out["absorb"] = round(min(1.0, sum(A) / 3.0), 3)
        out["color_name"] = color_name(rgb)
    else:
        out["pH"] = None
        out["liquid"] = None
    orgc = org_rgb(v, path)
    if orgc:
        out["org_color"] = rgb2hex(orgc)
    # zmętnienie i osady
    vol_l = max(v["vol"], 0.2) / 1000.0
    od, tcol = 0.0, [0.0, 0.0, 0.0]
    solids = []
    for sid, st in v.get("solids", {}).items():
        s = SOLIDS.get(sid)
        n = st.get("n", 0.0)
        if not s or n <= 1e-9:
            continue
        mass = n * s.mm
        susp = st.get("susp", 0.0) if v["vol"] > 0.3 else 0.0
        if susp > 0:
            o = (mass * susp / vol_l) * s.scatter * 0.7
            od += o
            rgb = hex2rgb(s.color)
            for i in range(3):
                tcol[i] += rgb[i] * o
        color = s.color
        style = s.style
        if s.mp and v["T"] > s.mp and s.melt_color:
            color, style = s.melt_color, "melt"
        if sid == "ZnO" and v["T"] > 300:
            color = "#f2df6a"
        if sid == "CoCl2" and v["T"] > 110 and v["vol"] < 0.3:
            color = "#2a49b8"
        solids.append({"id": sid, "name": s.name, "formula": s.formula, "color": color, "style": style,
                       "mass": round(mass, 4), "vol": round(mass / max(s.density, 0.3) * (2.0 if style in (
                           "gel", "curdy", "fluffy", "char") else 1.3), 4), "settled": round(1 - susp, 3)})
    if od > 0:
        out["turbid"] = round(1 - math.exp(-od), 3)
        out["turbid_color"] = rgb2hex([x / od for x in tcol])
    out["solids"] = solids
    # gazy w przestrzeni nad cieczą
    gas = v.get("gas", {})
    tot = sum(gas.values())
    gcol = None
    if tot > 0:
        A = [0.0, 0.0, 0.0]
        for gid, n in gas.items():
            g = GASES.get(gid)
            if g and g.color and n > 0:
                frac = n / tot
                e2 = eps(g.color, 0.6)
                for i in range(3):
                    A[i] += e2[i] * frac
        if sum(A) > 0.02:
            gcol = rgb2hex([255 * 10 ** (-min(a, 3)) for a in A])
            out["gas_alpha"] = round(min(0.9, sum(A) / 2.2), 3)
    out["gas_color"] = gcol
    out["gas"] = {k: round(n / tot, 4) for k, n in gas.items() if tot > 0 and n / tot > 0.002}
    out["gas_ml"] = round(tot * 24000, 2)
    return out
