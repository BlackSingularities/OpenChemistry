"""Równowagi w roztworze wodnym: pH z bilansu ładunku, formy kwasowo-zasadowe, kompleksy, strącanie (Ksp)."""
from __future__ import annotations

import math
from functools import lru_cache

from .data import ACIDS, COMPLEXES, IONS, MOLECULES, SOLIDS, SPECIES_COMPONENT, Solid

LN10 = math.log(10)


def pkw(t: float) -> float:
    d = t - 25.0
    return 14.0 - 0.033 * d + 0.00009 * d * d


def _alphas(pka: tuple, ph: float) -> list[float]:
    """Udziały form układu kwasowo-zasadowego (indeks = liczba oddanych protonów)."""
    logs = [0.0]
    acc = 0.0
    for j, p in enumerate(pka, start=1):
        acc += ph - p
        logs.append(acc)
    m = max(logs)
    ex = [math.exp((v - m) * LN10) for v in logs]
    s = sum(ex)
    return [e / s for e in ex]


class Speciation:
    __slots__ = ("ph", "h", "oh", "free", "vol_l", "t", "ionic", "tot")

    def __init__(self, ph, h, oh, free, vol_l, t, ionic=0.0):
        self.ionic = ionic
        self.ph = ph
        self.h = h
        self.oh = oh
        self.free = free
        self.vol_l = vol_l
        self.t = t

    def c(self, name: str) -> float:
        return self.free.get(name, 0.0)


_COMPLEX_BY_CENTER: dict[str, list] = {}
_CX_BY_ID = {c.id: c for c in COMPLEXES}
# ligand będący formą układu kwasowo-zasadowego -> (układ, indeks formy)
LIG_SYS: dict[str, tuple[str, int]] = {}
for _sid, _sysd in ACIDS.items():
    for _j, _f in enumerate(_sysd.forms):
        LIG_SYS[_f] = (_sid, _j)
for _cx in COMPLEXES:
    _COMPLEX_BY_CENTER.setdefault(_cx.center, []).append(_cx)


def _charge_of_component(cid: str) -> int | None:
    ion = IONS.get(cid)
    return ion.charge if ion else None


def speciate(aq: dict, vol_ml: float, t: float) -> Speciation:
    vol_l = max(vol_ml, 0.05) / 1000.0
    tot = {k: v / vol_l for k, v in aq.items() if v > 1e-15}
    kw = 10 ** (-pkw(t))
    systems = [(ACIDS[k], c) for k, c in tot.items() if k in ACIDS]
    simple = [(k, c, IONS[k].charge) for k, c in tot.items() if k in IONS]
    # centra kompleksów obecne w roztworze
    centers = []
    for cen, cxs in _COMPLEX_BY_CENTER.items():
        ct = tot.get(cen, 0.0)
        if ct <= 0:
            continue
        usable = []
        for cx in cxs:
            ok = True
            for lig, _n in cx.ligands:
                if lig == "OH-":
                    continue
                comp = LIG_SYS[lig][0] if lig in LIG_SYS else lig
                if tot.get(comp, 0) <= 0:
                    ok = False
            if ok:
                logb = cx.logb + cx.dlogb_dT * (t - 25.0)
                usable.append((cx, logb))
        if usable:
            centers.append((cen, ct, usable))
    center_ids = {c[0] for c in centers}

    lig_ids = sorted({lig for _c, _t, us in centers for cx, _lb in us for lig, _n in cx.ligands if lig != "OH-"})
    L_state: dict[str, float] = {}

    def evaluate(ph: float, full: bool = False):
        h = 10 ** (-ph)
        oh = kw / h
        bound: dict[str, float] = {}
        cx_conc: dict[str, float] = {}
        free_center: dict[str, float] = {}
        bound_sys: dict[str, float] = {}
        if centers:
            # dostępne ligandy (dla form układów kwasowych – udział danej formy przy tym pH)
            avail = {}
            lig_alpha = {}
            for lig in lig_ids:
                if lig in LIG_SYS:
                    sid, j = LIG_SYS[lig]
                    al = _alphas(ACIDS[sid].pka, ph)[j]
                    lig_alpha[lig] = (sid, al)
                    avail[lig] = tot.get(sid, 0.0) * al
                else:
                    avail[lig] = tot.get(lig, 0.0)
            L = {lig: L_state.get(lig, avail[lig]) for lig in lig_ids}
            for lig in lig_ids:
                L[lig] = min(max(L[lig], avail[lig] * 1e-30, 1e-300), max(avail[lig], 1e-300))
            iters = 60 if not L_state else 25
            log_oh = math.log10(oh)
            for _it in range(iters):
                logL = {k: math.log10(max(v, 1e-300)) for k, v in L.items()}
                logL["OH-"] = log_oh
                cx_terms = []
                for cen, ct, usable in centers:
                    terms = []
                    for cx, logb in usable:
                        lg = logb
                        for lig, n in cx.ligands:
                            lg += n * logL[lig]
                        terms.append((cx, lg))
                    mx = 0.0
                    for _cx, lgv in terms:
                        if lgv > mx:
                            mx = lgv
                    weights = [math.exp((float(lgv) - mx) * LN10) for _cx, lgv in terms]
                    denom = math.exp(-mx * LN10) + sum(weights)
                    free_center[cen] = ct * math.exp(-mx * LN10) / denom
                    for (cx, _lgv), wgt in zip(terms, weights):
                        cx_conc[cx.id] = ct * wgt / denom
                # suma związanych ligandów / wolny ligand
                svals = {lig: 0.0 for lig in lig_ids}
                for cxid, conc in cx_conc.items():
                    cx = _CX_BY_ID[cxid]
                    for lig, n in cx.ligands:
                        if lig != "OH-":
                            svals[lig] += n * conc / max(L[lig], 1e-300)
                change = 0.0
                for lig in lig_ids:
                    if lig in lig_alpha:
                        sid, al = lig_alpha[lig]
                        new = tot.get(sid, 0.0) * al / (1.0 + al * svals[lig])
                    else:
                        new = avail[lig] / (1.0 + svals[lig])
                    new = max(new, 1e-300)
                    damp = math.sqrt(L[lig] * new)
                    change = max(change, abs(math.log10(damp) - math.log10(L[lig])))
                    L[lig] = damp
                if change < 1e-6:
                    break
            L_state.update(L)
            for cxid, conc in cx_conc.items():
                for lig, n in _CX_BY_ID[cxid].ligands:
                    if lig != "OH-":
                        bound[lig] = bound.get(lig, 0.0) + n * conc
            for k in list(bound):
                if k in LIG_SYS:
                    sid = LIG_SYS[k][0]
                    bound_sys[sid] = bound_sys.get(sid, 0.0) + bound.pop(k)
            for k in bound:
                lt = tot.get(k, 0.0)
                if bound[k] > lt:
                    bound[k] = lt
            for k in bound_sys:
                bound_sys[k] = min(bound_sys[k], tot.get(k, 0.0))
        charge = h - oh
        free = {} if full else None
        for k, c, z in simple:
            if k in center_ids:
                c = free_center.get(k, c)
            elif k in bound:
                c = max(c - bound[k], 0.0)
            charge += z * c
            if full:
                free[k] = c
        for sysd, c in systems:
            if sysd.id in bound_sys:
                c = max(c - bound_sys[sysd.id], 0.0)
            al = _alphas(sysd.pka, ph)
            for j, a in enumerate(al):
                charge += (sysd.z0 - j) * c * a
                if full:
                    free[sysd.forms[j]] = c * a
        for cxid, conc in cx_conc.items():
            charge += _CX_BY_ID[cxid].charge * conc
            if full:
                free[cxid] = conc
        if full:
            for k, c in tot.items():
                if k in MOLECULES or k.startswith("ind:"):
                    if k in center_ids:
                        free[k] = free_center.get(k, c)
                    elif k in bound:
                        free[k] = max(c - bound[k], 0.0)
                    else:
                        free[k] = c
            free["H+"] = h
            free["OH-"] = oh
            return free
        return charge

    lo, hi = -2.0, 16.5
    for _ in range(46):
        mid = 0.5 * (lo + hi)
        if evaluate(mid) > 0:
            lo = mid
        else:
            hi = mid
    ph = 0.5 * (lo + hi)
    free = evaluate(ph, full=True)
    sp = Speciation(ph, 10 ** (-ph), kw / 10 ** (-ph), free, vol_l, t)
    ionic = 0.0
    for name, c in free.items():
        z = species_charge(name)
        if z:
            ionic += c * z * z
    sp.ionic = 0.5 * ionic
    sp.tot = tot
    return sp


_CHARGE_CACHE: dict[str, int] = {}


def species_charge(name: str) -> int:
    z = _CHARGE_CACHE.get(name)
    if z is not None:
        return z
    z = 0
    if name in ("H+",):
        z = 1
    elif name == "OH-":
        z = -1
    elif name in IONS:
        z = IONS[name].charge
    elif name in _CX_BY_ID:
        z = _CX_BY_ID[name].charge
    else:
        for sysd in ACIDS.values():
            if name in sysd.forms:
                z = sysd.z0 - sysd.forms.index(name)
                break
    _CHARGE_CACHE[name] = z
    return z


def log_gamma(z: int, ionic: float) -> float:
    """Równanie Daviesa (siła jonowa ograniczona do 1 mol/dm³)."""
    if not z or ionic <= 0:
        return 0.0
    i = min(ionic, 1.0)
    si = math.sqrt(i)
    return -0.51 * z * z * (si / (1 + si) - 0.3 * i)


# ---------------------------------------------------------------------------------------------------------------
# Iloczyn rozpuszczalności
# ---------------------------------------------------------------------------------------------------------------
def _interp(points, t):
    if len(points) == 1:
        return points[0][1]
    if t <= points[0][0]:
        return points[0][1]
    for (t0, s0), (t1, s1) in zip(points, points[1:]):
        if t <= t1:
            return s0 + (s1 - s0) * (t - t0) / (t1 - t0)
    return points[-1][1]


@lru_cache(maxsize=4096)
def _log_ksp_cached(sid: str, t_round: int) -> float:
    s = SOLIDS[sid]
    t = float(t_round)
    if s.logksp is not None:
        return s.logksp + s.dlogksp_dT * (t - 25.0)
    sol = _interp(s.solub, t)  # g / 100 g wody
    mm = s.anh_mm or s.mm
    m = max(sol, 1e-6) * 10.0 / mm  # mol/kg ~ mol/L
    lk = 0.0
    for _sp, nu in s.comp:
        lk += nu * math.log10(nu * m)
    return lk


def log_ksp(s: Solid, t: float) -> float:
    return _log_ksp_cached(s.id, int(round(t)))


def saturation_index(s: Solid, sp: Speciation) -> float:
    lq = 0.0
    act = s.kind == "ppt" and sp.ionic > 1e-4
    salt = s.kind == "salt" and getattr(sp, "tot", None) is not None
    for name, nu in s.comp:
        if salt and name != "OH-":
            # rozpuszczalność soli z tablic dotyczy całkowitej ilości rozpuszczonej soli
            c = sp.tot.get(component_of(name) or name, 0.0)
        else:
            c = sp.free.get(name, 0.0)
        if c <= 0:
            return -99.0
        lq += nu * math.log10(c)
        if act:
            lq += nu * log_gamma(species_charge(name), sp.ionic)
    return lq - log_ksp(s, sp.t)


def component_of(species: str) -> str | None:
    if species == "OH-":
        return None
    return SPECIES_COMPONENT.get(species)


def apply_solid_delta(aq: dict, s: Solid, x: float) -> dict:
    """Zwraca nowy słownik składników po wytrąceniu x moli ciała stałego (x<0 – rozpuszczenie)."""
    out = dict(aq)
    for name, nu in s.comp:
        comp = component_of(name)
        if comp is None:
            continue
        out[comp] = max(out.get(comp, 0.0) - nu * x, 0.0)
    return out


def max_precipitable(aq: dict, s: Solid) -> float:
    m = math.inf
    for name, nu in s.comp:
        comp = component_of(name)
        if comp is None:
            continue
        m = min(m, aq.get(comp, 0.0) / nu)
    return 0.0 if m is math.inf else m


PPT_KINDS = ("ppt", "salt")

# ciała stałe, które mogą się samorzutnie wytrącić (bez form „handlowych” jak marmur czy dym)
_NOT_SPONTANEOUS = {"CaCO3_chips", "CaO", "MgO", "ZnO", "Fe2O3", "CuO", "NaCl_smoke", "FeCl3_smoke", "CuSO4",
                    "P4O10", "KCl_from", "Na_St", "Glc_s", "Suc_s", "Urea_s", "CitricAcid", "AscAcid", "H2C2O4",
                    "NaOH", "KOH", "Ba(OH)2·8H2O", "Na2S", "Na2SO3", "NaAc", "K2MnO4", "CaCl2", "AlCl3",
                    "FeCl3", "Al2(SO4)3", "NH4SCN", "KSCN", "NH4NO3", "NaI", "NaBr", "Na3PO4", "Na2HPO4",
                    "Na2C2O4", "MnSO4", "CoCl2", "Cu(NO3)2", "AgNO3", "Pb(NO3)2", "KI", "KBr", "(NH4)2Cr2O7",
                    "K2CrO4", "Na2S2O3", "ZnSO4", "NiSO4", "FeSO4·7H2O", "CuCl2·2H2O", "MgCO3", "Mg(St)2"}

CANDIDATES: list[Solid] = [s for s in SOLIDS.values()
                           if s.kind in PPT_KINDS and s.comp and s.id not in _NOT_SPONTANEOUS]


def candidate_solids(aq: dict, solids: dict) -> list[Solid]:
    present = {k for k, v in aq.items() if v > 1e-14}
    out = []
    for s in CANDIDATES:
        ok = True
        for name, _nu in s.comp:
            comp = component_of(name)
            if comp is not None and comp not in present:
                ok = False
                break
        if ok:
            out.append(s)
    for sid, st in solids.items():
        s = SOLIDS.get(sid)
        if s and s.kind in PPT_KINDS and s.comp and st.get("n", 0) > 0 and s not in out:
            out.append(s)
    return out
