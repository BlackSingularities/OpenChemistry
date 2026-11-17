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
    __slots__ = ("ph", "h", "oh", "free", "vol_l", "t", "ionic")

    def __init__(self, ph, h, oh, free, vol_l, t):
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
                if lig == "NH3":
                    if tot.get("NH3", 0) <= 0:
                        ok = False
                elif tot.get(lig, 0) <= 0:
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
        nh3_tot = tot.get("NH3", 0.0)
        nh3_alpha = _alphas(ACIDS["NH3"].pka, ph)[1] if nh3_tot > 0 else 0.0
        if centers:
            # całkowite stężenia dostępnych ligandów (dla NH3 – tylko forma niesprotonowana)
            avail = {}
            for lig in lig_ids:
                avail[lig] = nh3_tot * nh3_alpha if lig == "NH3" else tot.get(lig, 0.0)
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
                    mx = max(0.0, max(lg for _, lg in terms))
                    denom = math.exp(-mx * LN10) + sum(math.exp((lg - mx) * LN10) for _, lg in terms)
                    fc = ct * math.exp(-mx * LN10) / denom
                    free_center[cen] = fc
                    for cx, lg in terms:
                        cx_conc[cx.id] = ct * math.exp((lg - mx) * LN10) / denom
                        cx_terms.append(cx)
                # suma związanych ligandów / wolny ligand
                svals = {lig: 0.0 for lig in lig_ids}
                for cxid, conc in cx_conc.items():
                    cx = _CX_BY_ID[cxid]
                    for lig, n in cx.ligands:
                        if lig != "OH-":
                            svals[lig] += n * conc / max(L[lig], 1e-300)
                change = 0.0
                for lig in lig_ids:
                    if lig == "NH3":
                        new = nh3_tot * nh3_alpha / (1.0 + nh3_alpha * svals[lig])
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
            for k in bound:
                lt = tot.get(k, 0.0)
                if bound[k] > lt:
                    bound[k] = lt
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
            if sysd.id == "NH3":
                c = max(c - bound.get("NH3", 0.0), 0.0)
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
    return Speciation(ph, 10 ** (-ph), kw / 10 ** (-ph), free, vol_l, t)


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
    for name, nu in s.comp:
        c = sp.free.get(name, 0.0)
        if c <= 0:
            return -99.0
        lq += nu * math.log10(c)
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
