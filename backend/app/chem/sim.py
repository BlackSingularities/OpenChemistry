"""Silnik symulacji stołu laboratoryjnego.

Stan stołu (bench) jest w całości przesyłany między przeglądarką a serwerem – serwer jest bezstanowy.
Funkcja step() wykonuje akcje użytkownika, a następnie symuluje upływ czasu w krokach ≤ 0,25 s:
reakcje kinetyczne, wymiana gazów, przepływy, bilans cieplny, równowagi i strącanie osadów.
"""
from __future__ import annotations

import copy
import math
import re

from .appearance import ORG_SPECIES, color_name, flame_color_for, hex2rgb, view
from .data import ACIDS, AIR, FLAME_COLORS, GASES, IONS, MOLECULES, SMELL_SPECIES, SOLIDS
from .equilibrium import (apply_solid_delta, candidate_solids, component_of, max_precipitable, saturation_index,
                          speciate)
from .equipment import EQUIPMENT, Equipment
from .reagents import REAGENTS
from .rules import RULES, Ctx

AMB = 20.0
MOLV = 24000.0  # mL/mol
MAX_VESSELS = 40
FLAME_T = {"alcohol": 650.0, "bunsen": 1100.0}
BIG = {"nail", "wire", "foil", "ribbon", "granules", "chips", "lump", "chunk", "candle", "slice", "tree", "deposit",
       "pellets", "wool"}
RESUSPEND = {"powder", "gel", "curdy", "crystals", "spangles", "fluffy", "needles", "octahedra", "flakes", "sand"}
SMOKE_SOLIDS = {"P4O10", "NaCl_smoke", "FeCl3_smoke", "CuCl2·2H2O"}
PARTITION = {"I2": 85.0, "Br2": 27.0}
AIR_INF = {"O2": 0.21, "N2": 0.78, "CO2": 0.0004}

ARM = Equipment("utube_arm", "Ramię elektrolizera", "", 30, 1.8, 40, 0.15, 0.0, heatable=False, kind="arm",
                mouth=0.0, closed=True)
EQ = dict(EQUIPMENT)
EQ["utube_arm"] = ARM


class Events(list):
    def add(self, t, vid, kind, text, eq=None, **extra):
        item = {"t": round(t, 2), "v": vid, "kind": kind, "text": text}
        if eq:
            item["eq"] = eq
        item.update(extra)
        self.append(item)


# ---------------------------------------------------------------------------------------------------------------
# Naczynia
# ---------------------------------------------------------------------------------------------------------------
def _air(cap_mol: float) -> dict:
    return {k: v * cap_mol for k, v in AIR.items()}


def solid_volume(v) -> float:
    tot = 0.0
    for sid, st in v.get("solids", {}).items():
        s = SOLIDS.get(sid)
        if s:
            tot += st.get("n", 0.0) * s.mm / max(s.density, 0.3)
    return tot


def head_cap(v) -> float:
    e = EQ[v["type"]]
    free = e.cap - v["vol"] - v.get("org_vol", 0.0) - solid_volume(v)
    return max(free, 0.3) / MOLV


def is_closed(v) -> bool:
    return bool(v.get("stopper") or v.get("lid"))


def new_vessel(etype: str, vid: str, x: float = 0.0) -> dict:
    e = EQ[etype]
    v = {"id": vid, "type": etype, "x": x, "aq": {}, "vol": 0.0, "org": {}, "org_vol": 0.0, "solids": {},
         "gas": {}, "T": AMB, "heat": None, "stopper": False, "lid": e.closed and e.kind in ("jar", "fountain"),
         "outlet": None, "stir": 0.0, "seen": [], "prog": {}, "fx": {}, "parent": None, "target": None,
         "flow": 0.0, "source": None}
    if e.kind == "fountain":
        v["stopper"] = True
    v["gas"] = _air(head_cap(v)) if e.kind not in ("spoon", "candle", "funnel") else {}
    if e.kind == "utube":
        v["arms"] = [new_vessel("utube_arm", f"{vid}#0"), new_vessel("utube_arm", f"{vid}#1")]
        for a in v["arms"]:
            a["gas"] = {}
            a["stopper"] = True
        v["power"] = False
        v["electrode"] = "C"
    if e.kind == "candle":
        v["solids"]["Wax"] = {"n": 5.0 / SOLIDS["Wax"].mm, "susp": 0.0}
    return v


def _eth_ml(v):
    return v["aq"].get("EtOH", 0.0) * 46.07 / 0.789


# ---------------------------------------------------------------------------------------------------------------
# Przelewanie i dodawanie odczynników
# ---------------------------------------------------------------------------------------------------------------
def take(v, ml: float, everything: bool = False) -> dict:
    """Pobiera porcję zawartości naczynia (najpierw warstwę organiczną – leży na wierzchu)."""
    if v.get("arms"):
        parts = [take(a, ml / 2, everything) for a in v["arms"]]
        out = parts[0]
        _merge_portion(out, parts[1])
        return out
    total = v["vol"] + v.get("org_vol", 0.0)
    portion = {"aq": {}, "vol": 0.0, "org": {}, "org_vol": 0.0, "solids": {}, "T": v["T"]}
    if total <= 1e-9 and not everything:
        return portion
    if ml >= total - 1e-6 or everything:
        portion["aq"], portion["vol"] = v["aq"], v["vol"]
        portion["org"], portion["org_vol"] = v.get("org", {}), v.get("org_vol", 0.0)
        keep = {}
        for sid, st in v["solids"].items():
            s = SOLIDS.get(sid)
            if (s and s.style in BIG and not everything) or (s and v["vol"] < 0.05 and not everything):
                keep[sid] = st
            else:
                portion["solids"][sid] = {"n": st["n"], "susp": 1.0}
        v["aq"], v["vol"], v["org"], v["org_vol"], v["solids"] = {}, 0.0, {}, 0.0, keep
        return portion
    o = min(v.get("org_vol", 0.0), ml)
    if o > 0:
        f = o / v["org_vol"]
        for k, n in list(v["org"].items()):
            portion["org"][k] = n * f
            v["org"][k] = n * (1 - f)
        portion["org_vol"] = o
        v["org_vol"] -= o
    rest = ml - o
    if rest > 0 and v["vol"] > 0:
        f = min(1.0, rest / v["vol"])
        for k, n in list(v["aq"].items()):
            portion["aq"][k] = n * f
            v["aq"][k] = n * (1 - f)
        portion["vol"] = v["vol"] * f
        v["vol"] -= portion["vol"]
        for sid, st in list(v["solids"].items()):
            s = SOLIDS.get(sid)
            if not s or s.style in BIG:
                continue
            moved = st["n"] * st.get("susp", 0.0) * f
            if moved > 0:
                portion["solids"][sid] = {"n": moved, "susp": 1.0}
                remaining = st["n"] - moved
                st["susp"] = (st["n"] * st.get("susp", 0.0) - moved) / remaining if remaining > 1e-15 else 0.0
                st["n"] = remaining
    return portion


def _merge_portion(a, b):
    for k, n in b["aq"].items():
        a["aq"][k] = a["aq"].get(k, 0.0) + n
    for k, n in b["org"].items():
        a["org"][k] = a["org"].get(k, 0.0) + n
    for k, st in b["solids"].items():
        cur = a["solids"].setdefault(k, {"n": 0.0, "susp": 1.0})
        cur["n"] += st["n"]
    a["vol"] += b["vol"]
    a["org_vol"] += b["org_vol"]


def heat_capacity(v) -> float:
    e = EQ[v["type"]]
    c = v["vol"] * 4.18 + v.get("org_vol", 0.0) * 2.0 + e.glass * 0.84
    for sid, st in v.get("solids", {}).items():
        s = SOLIDS.get(sid)
        if s:
            c += st["n"] * s.mm * 0.8
    return max(c, 0.5)


def _h_oh_moles(aq, vol, t):
    if vol <= 0.01:
        return 0.0, 0.0
    sp = speciate(aq, vol, t)
    return sp.h * vol / 1000.0, sp.oh * vol / 1000.0


def _dilution_state(aq, vol):
    n = aq.get("SO4", 0.0)
    if n <= 0 or vol <= 0:
        return 0.0
    c = n / (vol / 1000.0)
    return n * 70000.0 * min(c, 18.0) / 18.0


def put(bench, dst, portion, t, events: Events, mix_heat=True):
    """Dodaje porcję do naczynia: bilans cieplny, ciepło zobojętniania i rozcieńczania."""
    e = EQ[dst["type"]]
    if e.kind == "funnel":
        for sid, st in portion["solids"].items():
            cur = dst["solids"].setdefault(sid, {"n": 0.0, "susp": 0.0})
            cur["n"] += st["n"]
            cur["susp"] = 0.0
        if portion["solids"]:
            events.add(t, dst["id"], "obs", "Osad zatrzymuje się na sączku – przesącz jest klarowny.")
        portion["solids"] = {}
        tgt = bench["vessels"].get(dst.get("target") or "")
        if tgt and (portion["vol"] > 0 or portion["org_vol"] > 0):
            put(bench, tgt, portion, t, events)
        return
    if dst.get("arms"):
        half = {"aq": {k: n / 2 for k, n in portion["aq"].items()}, "vol": portion["vol"] / 2,
                "org": {k: n / 2 for k, n in portion["org"].items()}, "org_vol": portion["org_vol"] / 2,
                "solids": {k: {"n": s["n"] / 2, "susp": 1.0} for k, s in portion["solids"].items()},
                "T": portion["T"]}
        for a in dst["arms"]:
            put(bench, a, {k: (dict(vv) if isinstance(vv, dict) else vv) for k, vv in half.items()}, t, events)
        return
    c_dst = heat_capacity(dst)
    c_por = portion["vol"] * 4.18 + portion["org_vol"] * 2.0 + sum(
        st["n"] * SOLIDS[sid].mm * 0.8 for sid, st in portion["solids"].items() if sid in SOLIDS)
    q = 0.0
    if mix_heat and portion["vol"] > 0 and dst["vol"] > 0:
        h1, o1 = _h_oh_moles(dst["aq"], dst["vol"], dst["T"])
        h2, o2 = _h_oh_moles(portion["aq"], portion["vol"], portion["T"])
        d_before = _dilution_state(dst["aq"], dst["vol"]) + _dilution_state(portion["aq"], portion["vol"])
    else:
        h1 = o1 = h2 = o2 = None
        d_before = 0.0
    for k, n in portion["aq"].items():
        dst["aq"][k] = dst["aq"].get(k, 0.0) + n
    for k, n in portion["org"].items():
        dst["org"][k] = dst["org"].get(k, 0.0) + n
    for sid, st in portion["solids"].items():
        cur = dst["solids"].setdefault(sid, {"n": 0.0, "susp": 0.0})
        tot = cur["n"] + st["n"]
        cur["susp"] = (cur["n"] * cur.get("susp", 0.0) + st["n"] * st.get("susp", 1.0)) / tot if tot > 0 else 0
        cur["n"] = tot
    vol_before = dst["vol"]
    dst["vol"] += portion["vol"]
    dst["org_vol"] = dst.get("org_vol", 0.0) + portion["org_vol"]
    tot_c = c_dst + c_por
    if tot_c > 0:
        dst["T"] = (dst["T"] * c_dst + portion["T"] * c_por) / tot_c
    cap_l = e.cap if e.kind != "arm" else 30.0
    over = dst["vol"] + dst.get("org_vol", 0.0) - cap_l
    if over > 1e-6 and cap_l > 0:
        _spill(dst, over)
        events.add(t, dst["id"], "warn", "Ciecz przelewa się przez brzeg naczynia – nadmiar wylał się na stół.")
    if h1 is not None:
        h3, o3 = _h_oh_moles(dst["aq"], dst["vol"], dst["T"])
        neut = max((h1 + h2) - h3, (o1 + o2) - o3, 0.0)
        q += 56000.0 * neut
        q += max(0.0, d_before - _dilution_state(dst["aq"], dst["vol"]))
        if d_before > 0 and dst["aq"].get("SO4", 0) / max(dst["vol"], 0.01) * 1000 > 2 and \
                portion["vol"] > 0 and vol_before > 0:
            conc_frac = portion["aq"].get("SO4", 0.0) / (portion["vol"] / 1000) if portion["vol"] else 0
            if conc_frac < 5 and dst["aq"].get("SO4", 0) / (vol_before / 1000) > 12 and portion["vol"] > 0.5:
                events.add(t, dst["id"], "warn", "Uwaga! Wlewanie wody do stężonego kwasu powoduje gwałtowne "
                                                  "wrzenie i rozpryskiwanie – zawsze wlewaj kwas do wody!")
                dst["fx"]["spatter"] = 1
    elif mix_heat and portion["vol"] > 0 and vol_before <= 0 and portion["solids"] == {}:
        pass
    if q:
        dst["T"] += q / heat_capacity(dst)
    dst["stable"] = False
    _fit_headspace(bench, dst, t, events)


def _spill(v, over):
    """Usuwa nadmiar cieczy (najpierw warstwa organiczna z wierzchu, potem roztwór i zawiesina)."""
    o = min(v.get("org_vol", 0.0), over)
    if o > 0:
        f = o / v["org_vol"]
        for k in list(v["org"]):
            v["org"][k] *= 1 - f
        v["org_vol"] -= o
        over -= o
    if over > 0 and v["vol"] > 0:
        f = min(1.0, over / v["vol"])
        for k in list(v["aq"]):
            v["aq"][k] *= 1 - f
        for st in v["solids"].values():
            st["n"] -= st["n"] * st.get("susp", 0.0) * f
        v["vol"] -= v["vol"] * f


def _fit_headspace(bench, v, t, events):
    """Po dolaniu cieczy gaz z przestrzeni nad nią jest wypierany."""
    cap = head_cap(v)
    tot = sum(v["gas"].values())
    if tot > cap * 1.0001 and not is_closed(v):
        f = cap / tot
        for k in v["gas"]:
            v["gas"][k] *= f


def add_reagent(bench, v, rid: str, amount: float, t: float, events: Events):
    r = REAGENTS.get(rid)
    if not r:
        raise ValueError("nieznany odczynnik")
    e = EQ[v["type"]]
    amount = max(0.0, float(amount))
    if r.kind == "gas":
        g = next(iter(r.comp))
        cap = head_cap(v)
        v["gas"] = {g: cap}
        events.add(t, v["id"], "info", f"Naczynie napełniono gazem: {GASES[g].name}.")
        v["stable"] = False
        return
    if e.kind in ("spoon", "crucible", "candle") and r.kind != "solid" and e.kind != "crucible":
        raise ValueError("Do tego naczynia można dodać tylko substancje stałe.")
    if r.kind in ("solution", "indicator"):
        ml = amount * 0.05 if r.kind == "indicator" else amount
        portion = {"aq": {k: c * ml / 1000.0 for k, c in r.comp.items()}, "vol": ml, "org": {}, "org_vol": 0.0,
                   "solids": {}, "T": AMB}
        if "EtOH" in r.comp or "Glycerol" in r.comp:
            pass
        put(bench, v, portion, t, events)
    elif r.kind == "liquid":
        portion = {"aq": {}, "vol": 0.0, "org": {k: c * amount for k, c in r.org.items()}, "org_vol": amount,
                   "solids": {}, "T": AMB}
        put(bench, v, portion, t, events)
    elif r.kind == "solid":
        sid = next(iter(r.comp))
        s = SOLIDS[sid]
        n = amount / s.mm
        susp = 0.4 if (v["vol"] > 0.5 and s.style in ("powder",)) else 0.0
        put(bench, v, {"aq": {}, "vol": 0.0, "org": {}, "org_vol": 0.0, "solids": {sid: {"n": n, "susp": susp}},
                       "T": AMB}, t, events, mix_heat=False)
    v["stable"] = False


# ---------------------------------------------------------------------------------------------------------------
# Równowagi i strącanie
# ---------------------------------------------------------------------------------------------------------------
def _fmt_ion(name: str) -> str:
    if "^" in name:
        return name
    m = re.match(r"^(.*?[A-Za-z\)\]])(\d?[+-])$", name)
    if m:
        return f"{m.group(1)}^{m.group(2)}"
    return name


def ppt_equation(s) -> str:
    parts = []
    for sp_, nu in s.comp:
        parts.append(f"{nu if nu > 1 else ''}{_fmt_ion(sp_)}")
    return " + ".join(parts) + f" → {s.formula}↓"


def equilibrate(v, dt, t, events: Events, heat_acc: list):
    aq = v["aq"]
    solids = v["solids"]
    vol = v["vol"] if v["vol"] > 0.02 else 0.02
    T = v["T"]
    cands = candidate_solids(aq, solids)
    sp = speciate(aq, vol, T)
    if not cands:
        return sp
    for _it in range(10):
        best, best_score, mode = None, 0.0, None
        for s in cands:
            si = saturation_index(s, sp)
            n_s = solids.get(s.id, {}).get("n", 0.0)
            if s.kind == "ppt":
                thr = 0.02 if n_s > 1e-9 else s.nucleation
            else:
                thr = 0.04 if n_s > 1e-9 else 0.3
            if si > thr:
                score = si
                if score > best_score:
                    best, best_score, mode = s, score, "ppt"
            elif si < -0.02 and n_s > 1e-13 and v["vol"] > 0.02:
                score = -si
                if score > best_score:
                    best, best_score, mode = s, score, "dis"
        if best is None:
            break
        s = best
        n_s = solids.get(s.id, {}).get("n", 0.0)

        def si_at(x):
            return saturation_index(s, speciate(apply_solid_delta(aq, s, x), vol, T))

        if mode == "ppt":
            hi = max_precipitable(aq, s) * (1 - 1e-9)
            if hi <= 1e-10 and best_score > 0.5:
                # składnik ograniczający siedzi w innym osadzie – przemiana osadu (np. AgCl -> AgI)
                comps = {component_of(n_) for n_, _ in s.comp} - {None}
                donor = None
                for sid2, st2 in solids.items():
                    s2 = SOLIDS.get(sid2)
                    if s2 is None or s2 is s or s2.kind not in ("ppt", "salt") or st2.get("n", 0) <= 1e-12:
                        continue
                    if comps & ({component_of(n_) for n_, _ in s2.comp} - {None}):
                        donor = (s2, st2)
                        break
                if donor:
                    s2, st2 = donor
                    k2 = s2.k_dis * (3.0 if v.get("stir", 0) > 0 else 1.0)
                    dx = min(st2["n"], st2["n"] * (1 - math.exp(-k2 * max(dt, 0.05))) + 1e-7)
                    aq = apply_solid_delta(aq, s2, -dx)
                    st2["n"] -= dx
                    if st2["n"] <= 1e-14:
                        solids.pop(s2.id, None)
                    sp = speciate(aq, vol, T)
                    continue
            if hi <= 1e-15:
                cands = [c for c in cands if c is not s]
                continue
            lo = 0.0
            if si_at(hi) > 0:
                x = hi
            else:
                for _ in range(24):
                    mid = 0.5 * (lo + hi)
                    if si_at(mid) > 0:
                        lo = mid
                    else:
                        hi = mid
                x = 0.5 * (lo + hi)
            if s.kind == "salt" and dt > 0 and v["vol"] > 0.05:
                x *= 1 - math.exp(-0.6 * dt)
        else:
            stir = 3.0 if v.get("stir", 0) > 0 else 1.0
            k = s.k_dis * stir * (1 + max(0.0, T - 20) / 25.0)
            cap = n_s * (1 - math.exp(-k * max(dt, 0.05))) + 2e-6 * max(dt, 0.05) * k
            cap = min(cap, n_s)
            lo, hi = -cap, 0.0
            if si_at(lo) < 0:
                x = lo
            else:
                for _ in range(24):
                    mid = 0.5 * (lo + hi)
                    if si_at(mid) > 0:
                        lo = mid
                    else:
                        hi = mid
                x = 0.5 * (lo + hi)
        if abs(x) < 1e-16:
            cands = [c for c in cands if c is not s]
            continue
        aq = apply_solid_delta(aq, s, x)
        st = solids.setdefault(s.id, {"n": 0.0, "susp": 0.0})
        n_old = st["n"]
        st["n"] = max(0.0, n_old + x)
        if x > 0:
            st["susp"] = (n_old * st.get("susp", 0.0) + x) / st["n"] if st["n"] > 0 else 0.0
            if s.kind == "salt":
                st["susp"] = min(st["susp"], 0.2)
        heat_acc[0] += s.dh_sol * 1000.0 * x
        key = f"ppt:{s.id}"
        if x > 0 and n_old < 2e-7 <= st["n"] and key not in v["seen"]:
            v["seen"].append(key)
            cname = color_name(hex2rgb(s.color))
            if cname == "bezbarwny":
                cname = "biały"
            if s.kind == "salt":
                events.add(t, v["id"], "obs", f"Wykrystalizowuje {s.name} ({s.formula}) – pojawiają się kryształy.",
                           ppt_equation(s))
            else:
                events.add(t, v["id"], "ppt", f"Wytrąca się {cname} osad: {s.name} ({s.formula}).", ppt_equation(s),
                           color=s.color)
            if key + ":dis" in v["seen"]:
                v["seen"].remove(key + ":dis")
        if x < 0 and st["n"] < 1e-9 and (n_old > 2e-7 or key in v["seen"]):
            dkey = key + ":dis"
            if dkey not in v["seen"] and s.kind == "ppt" and key in v["seen"]:
                v["seen"].append(dkey)
                events.add(t, v["id"], "obs", f"Osad {s.name} ({s.formula}) rozpuszcza się.")
            if key in v["seen"]:
                v["seen"].remove(key)
        if st["n"] <= 1e-14:
            solids.pop(s.id, None)
        sp = speciate(aq, vol, T)
    v["aq"] = {k: n for k, n in aq.items() if n > 1e-16}
    return sp


# ---------------------------------------------------------------------------------------------------------------
# Gazy: wymiana ciecz–gaz, przestrzeń nad cieczą, rurki odprowadzające
# ---------------------------------------------------------------------------------------------------------------
VOLATILES = []
for _s in ACIDS.values():
    if _s.volatile:
        idx, gid, H, coef = _s.volatile
        VOLATILES.append((_s.forms[idx], _s.id, gid, H, coef))
for _m in MOLECULES.values():
    if _m.volatile:
        gid, H, coef = _m.volatile
        VOLATILES.append((_m.id, _m.id, gid, H, coef))

ABSORB = {"NH3": 0.99, "HCl": 0.99, "SO2": 0.9, "Cl2": 0.55, "H2S": 0.6, "NO2": 0.7, "Br2": 0.8, "I2": 0.3}


def absorb_gas(dst, gas: dict, sp_dst):
    """Gaz przepuszczany przez ciecz (rurka zanurzona w roztworze). Zwraca to, co nie zostało pochłonięte."""
    left = {}
    for gid, n in gas.items():
        if n <= 0:
            continue
        f = ABSORB.get(gid, 0.0)
        if gid == "CO2":
            f = 0.95 if (sp_dst and sp_dst.ph > 8) else 0.25
        if dst["vol"] < 1.0:
            f = 0.0
        a = n * f
        if a > 0:
            if gid == "NH3":
                dst["aq"]["NH3"] = dst["aq"].get("NH3", 0.0) + a
            elif gid == "HCl":
                dst["aq"]["Cl-"] = dst["aq"].get("Cl-", 0.0) + a
            elif gid == "SO2":
                dst["aq"]["SO3"] = dst["aq"].get("SO3", 0.0) + a
            elif gid == "CO2":
                dst["aq"]["CO3"] = dst["aq"].get("CO3", 0.0) + a
            elif gid == "H2S":
                dst["aq"]["S"] = dst["aq"].get("S", 0.0) + a
            elif gid == "NO2":
                dst["aq"]["NO3-"] = dst["aq"].get("NO3-", 0.0) + a * 2 / 3
                left["NO"] = left.get("NO", 0.0) + a / 3
            elif gid in ("Cl2", "Br2", "I2"):
                dst["aq"][gid] = dst["aq"].get(gid, 0.0) + a
        if n - a > 0:
            left[gid] = left.get(gid, 0.0) + n - a
    return left


def route_gas(bench, v, gas: dict, t, events, depth=0):
    """Gaz opuszczający naczynie: rurką do innego naczynia albo do atmosfery."""
    if not gas or depth > 4:
        return
    tgt = bench["vessels"].get(v.get("outlet") or "")
    if not tgt:
        return
    if tgt.get("arms"):
        return
    passed = gas
    if tgt["vol"] > 1.0:
        sp = speciate(tgt["aq"], tgt["vol"], tgt["T"])
        passed = absorb_gas(tgt, gas, sp)
        bub = sum(gas.values()) / max(bench.get("_dt", 0.25), 1e-3)
        tgt["_inbub"] = tgt.get("_inbub", 0.0) + bub
        tgt["stable"] = False
    if passed:
        for g, n in passed.items():
            tgt["gas"][g] = tgt["gas"].get(g, 0.0) + n
        _vent(bench, tgt, t, events, depth + 1)


def _vent(bench, v, t, events, depth=0):
    """Nadmiar gazu ponad pojemność przestrzeni nad cieczą."""
    cap = head_cap(v)
    tot = sum(v["gas"].values())
    if tot <= cap * 1.0001:
        return
    e = EQ[v["type"]]
    if e.kind == "arm":
        return  # ramię elektrolizera zbiera gaz (wypiera ciecz)
    excess = tot - cap
    if v.get("collect") and not v.get("outlet"):
        f = excess / tot
        for k in v["gas"]:
            v["gas"][k] *= (1 - f)
        return
    if is_closed(v) and not v.get("outlet"):
        if tot > cap * 1.8 and v.get("stopper") and e.kind not in ("fountain",):
            v["stopper"] = False
            events.add(t, v["id"], "warn", "Ciśnienie gazu wypycha korek z naczynia!")
        return
    f = excess / tot
    out = {k: n * f for k, n in v["gas"].items()}
    for k in v["gas"]:
        v["gas"][k] *= (1 - f)
    if v.get("outlet") and is_closed(v):
        route_gas(bench, v, out, t, events, depth)


def gas_exchange(bench, v, sp, dt, t, events, boiling):
    """Wymiana substancji lotnych między cieczą a gazem; zwraca intensywność pęcherzyków [mol/s]."""
    e = EQ[v["type"]]
    bubbles = 0.0
    if v["vol"] < 0.3 or sp is None:
        return 0.0
    cap = head_cap(v)
    tot = max(sum(v["gas"].values()), 1e-12)
    P = tot / cap
    area = (e.diam / 4.0) ** 2
    stir = 3.0 if v.get("stir", 0) > 0 else 1.0
    if boiling:
        stir *= 6.0
    V = v["vol"] / 1000.0
    for form, comp, gid, H, coef in VOLATILES:
        c = sp.free.get(form, 0.0)
        ng = v["gas"].get(gid, 0.0)
        if c <= 1e-9 and ng <= 1e-12:
            continue
        HT = H * math.exp(-coef * (v["T"] - 25.0))
        p_eq = c / HT
        p_head = ng / cap
        J = area * (p_eq - p_head) / (1 / 0.004 + 1 / (0.0004 * HT * stir)) * stir
        if p_eq > P * 1.02:
            Jb = 0.25 * stir * V * (c - HT * P * 1.02)
            J += Jb
            bubbles += Jb
        if J > 0:
            avail = v["aq"].get(comp, 0.0) * (c / max(_comp_conc(v, comp), 1e-30)) if comp in ACIDS else \
                v["aq"].get(comp, 0.0)
            d = min(J * dt, avail * 0.9)
            if d <= 0:
                continue
            v["aq"][comp] = v["aq"].get(comp, 0.0) - d
            v["gas"][gid] = v["gas"].get(gid, 0.0) + d
        else:
            d = min(-J * dt, ng * 0.9)
            if d <= 0:
                continue
            v["gas"][gid] = ng - d
            v["aq"][comp] = v["aq"].get(comp, 0.0) + d
    # chlorowodór ze stężonego kwasu solnego
    cl = sp.free.get("Cl-", 0.0)
    if cl > 3 and sp.h > 3:
        p = sp.h * cl / 720.0
        p_head = v["gas"].get("HCl", 0.0) / cap
        J = area * (p - p_head) * 0.002 * stir
        if J > 0:
            d = min(J * dt, v["aq"]["Cl-"] * 0.05)
            v["aq"]["Cl-"] -= d
            v["gas"]["HCl"] = v["gas"].get("HCl", 0.0) + d
    # chlorowodór z przestrzeni gazowej bardzo szybko rozpuszcza się w wodzie
    hcl_g = v["gas"].get("HCl", 0.0)
    if hcl_g > 1e-12 and not (cl > 3 and sp.h > 3):
        d = hcl_g * (1 - math.exp(-0.6 * area * stir * dt))
        v["gas"]["HCl"] = hcl_g - d
        v["aq"]["Cl-"] = v["aq"].get("Cl-", 0.0) + d
    # NO2 pochłaniany przez wodę
    no2 = v["gas"].get("NO2", 0.0)
    if no2 > 1e-9:
        d = no2 * (1 - math.exp(-0.05 * area * dt))
        v["gas"]["NO2"] -= d
        v["aq"]["NO3-"] = v["aq"].get("NO3-", 0.0) + d * 2 / 3
        v["gas"]["NO"] = v["gas"].get("NO", 0.0) + d / 3
    return bubbles


def _comp_conc(v, comp):
    return v["aq"].get(comp, 0.0) / (max(v["vol"], 0.05) / 1000.0)


def headspace(bench, v, dt, t, events):
    """Reakcje w fazie gazowej, wymiana z powietrzem, ciśnienie, zasysanie cieczy."""
    g = v["gas"]
    e = EQ[v["type"]]
    # NO + O2 -> NO2
    no, o2 = g.get("NO", 0.0), g.get("O2", 0.0)
    if no > 1e-12 and o2 > 1e-12:
        d = min(no, 2 * o2) * (1 - math.exp(-3.0 * dt))
        g["NO"] -= d
        g["O2"] -= d / 2
        g["NO2"] = g.get("NO2", 0.0) + d
        if d > 1e-7 and "gas:NO2" not in v["seen"]:
            v["seen"].append("gas:NO2")
            events.add(t, v["id"], "obs", "Bezbarwny NO w kontakcie z powietrzem brunatnieje – tworzy się NO₂.",
                       "2NO + O2 → 2NO2")
    # NH3 + HCl -> NH4Cl (biały dym)
    nh3, hcl = g.get("NH3", 0.0), g.get("HCl", 0.0)
    if nh3 > 1e-10 and hcl > 1e-10:
        d = min(nh3, hcl) * (1 - math.exp(-5.0 * dt))
        g["NH3"] -= d
        g["HCl"] -= d
        st = v["solids"].setdefault("NH4Cl", {"n": 0.0, "susp": 0.0})
        st["n"] += d
        v["fx"]["smoke"] = "#f4f4f4"
        v["fx"]["smoke_level"] = min(1.0, v["fx"].get("smoke_level", 0.0) + d * 3000)
        if "gas:NH4Cl" not in v["seen"]:
            v["seen"].append("gas:NH4Cl")
            events.add(t, v["id"], "obs", "Powstaje gęsty, biały dym – drobne kryształki chlorku amonu.",
                       "NH3 + HCl → NH4Cl")
    # para wodna skrapla się
    if g.get("H2O", 0.0) > 0:
        g["H2O"] *= math.exp(-0.5 * dt)
    for k in [k for k, n in g.items() if n < 1e-14]:
        g.pop(k)
    cap = head_cap(v)
    # wymiana z atmosferą (naczynia otwarte)
    if not is_closed(v) and e.kind not in ("arm",):
        k0 = 0.03 * e.mouth
        for gid in set(g) | set(AIR):
            dens = GASES[gid].density if gid in GASES else 1.0
            k = k0 / max(0.4, dens) ** 0.6
            target = AIR.get(gid, 0.0) * cap
            cur = g.get(gid, 0.0)
            g[gid] = target + (cur - target) * math.exp(-k * dt)
    _vent(bench, v, t, events)
    # podciśnienie: zasysanie cieczy (fontanna, pomiar zawartości tlenu)
    src = bench["vessels"].get(v.get("source") or "")
    if src and is_closed(v):
        tot = sum(g.values())
        P = tot / max(head_cap(v), 1e-9)
        if P < 0.97 and src["vol"] > 0.5:
            rate = 12.0 * (1 - P) * (e.cap / 250.0)
            ml = min(rate * dt, src["vol"] - 0.2, (1 - P) * head_cap(v) * MOLV)
            if ml > 0.01:
                portion = take(src, ml)
                put(bench, v, portion, t, events)
                v["fx"]["fountain"] = rate
                if "fountain" not in v["seen"]:
                    v["seen"].append("fountain")
                    events.add(t, v["id"], "obs", "Ciecz zostaje gwałtownie zassana do kolby – powstaje fontanna "
                                                  "(gaz rozpuścił się w wodzie i spadło ciśnienie)."
                               if e.kind == "fountain" else
                               "Woda zostaje zassana do naczynia, zajmując objętość zużytego gazu.")


# ---------------------------------------------------------------------------------------------------------------
# Elektroliza (rurka U)
# ---------------------------------------------------------------------------------------------------------------
def conductivity(v, sp) -> float:
    """Przewodnictwo właściwe [S/cm]."""
    if v["vol"] < 0.3 or sp is None:
        return 0.0
    k = 350.0 * sp.h + 198.0 * sp.oh
    from .equilibrium import _COMPLEX_BY_CENTER  # noqa
    for name, c in sp.free.items():
        if name in ("H+", "OH-"):
            continue
        if name in IONS:
            k += IONS[name].lam * c
            continue
        for sysd in ACIDS.values():
            if name in sysd.forms:
                k += sysd.lam[sysd.forms.index(name)] * c
                break
        else:
            if name.startswith("[") or name.endswith("-") or name.endswith("+"):
                k += 60.0 * c
    return k / 1000.0 + 5.5e-8


def electrolysis(bench, u, dt, t, events, sps):
    if not u.get("power"):
        return 0.0
    cat, an = u["arms"]
    if cat["vol"] < 1 or an["vol"] < 1:
        return 0.0
    k = 0.5 * (conductivity(cat, sps[0]) + conductivity(an, sps[1]))
    R = 2.0 / max(k, 1e-9)
    I = max(0.0, min(1.0, (12.0 - 2.0) / R))
    u["current"] = I
    ne = I * dt / 96485.0
    if ne <= 0:
        return I
    # katoda
    cand = None
    for ion, metal, n, e0 in (("Ag+", "Ag", 1, 0.8), ("Cu2+", "Cu_dep", 2, 0.34), ("Pb2+", "Pb_dep", 2, -0.13),
                              ("Ni2+", "Ni", 2, -0.25), ("Zn2+", "Zn_powder", 2, -0.76)):
        c = cat["aq"].get(ion, 0.0) / (cat["vol"] / 1000)
        if c > (0.002 if e0 > 0 else 0.3):
            cand = (ion, metal, n)
            break
    if cand:
        ion, metal, n = cand
        d = min(ne / n, cat["aq"][ion] * 0.99)
        cat["aq"][ion] -= d
        st = cat["solids"].setdefault(metal, {"n": 0.0, "susp": 0.0})
        st["n"] += d
        rest = ne - d * n
        if "el:cat:metal" not in cat["seen"]:
            cat["seen"].append("el:cat:metal")
            events.add(t, u["id"], "obs", f"Na katodzie osadza się metal ({SOLIDS[metal].name}).",
                       f"Katoda (−): {_fmt_ion(ion)} + {n}e^- → {SOLIDS[metal].formula}")
    else:
        rest = ne
    if rest > 0:
        cat["gas"]["H2"] = cat["gas"].get("H2", 0.0) + rest / 2
        cat["fx"]["bubbles"] = cat["fx"].get("bubbles", 0.0) + rest / 2 / dt
        if "el:cat:H2" not in cat["seen"]:
            cat["seen"].append("el:cat:H2")
            events.add(t, u["id"], "obs", "Na katodzie wydziela się bezbarwny gaz – wodór; roztwór przy katodzie "
                                          "staje się zasadowy.", "Katoda (−): 2H2O + 2e^- → H2↑ + 2OH^-")
    # anoda
    an_c = lambda ion: an["aq"].get(ion, 0.0) / (an["vol"] / 1000)  # noqa
    if u.get("electrode") == "Cu":
        an["aq"]["Cu2+"] = an["aq"].get("Cu2+", 0.0) + ne / 2
        if "el:an:Cu" not in an["seen"]:
            an["seen"].append("el:an:Cu")
            events.add(t, u["id"], "obs", "Miedziana anoda roztwarza się – przechodzą do roztworu jony Cu²⁺.",
                       "Anoda (+): Cu → Cu^2+ + 2e^-")
    elif an_c("I-") > 1e-3:
        d = min(ne, an["aq"]["I-"] * 0.99)
        an["aq"]["I-"] -= d
        an["aq"]["I2"] = an["aq"].get("I2", 0.0) + d / 2
        if "el:an:I2" not in an["seen"]:
            an["seen"].append("el:an:I2")
            events.add(t, u["id"], "obs", "Przy anodzie roztwór brunatnieje – wydziela się jod.",
                       "Anoda (+): 2I^- → I2 + 2e^-")
    elif an_c("Br-") > 0.01:
        d = min(ne, an["aq"]["Br-"] * 0.99)
        an["aq"]["Br-"] -= d
        an["aq"]["Br2"] = an["aq"].get("Br2", 0.0) + d / 2
        if "el:an:Br2" not in an["seen"]:
            an["seen"].append("el:an:Br2")
            events.add(t, u["id"], "obs", "Przy anodzie roztwór żółknie/pomarańczowieje – wydziela się brom.",
                       "Anoda (+): 2Br^- → Br2 + 2e^-")
    elif an_c("Cl-") > 0.25:
        d = min(ne, an["aq"]["Cl-"] * 0.99)
        an["aq"]["Cl-"] -= d
        an["aq"]["Cl2"] = an["aq"].get("Cl2", 0.0) + d / 2
        an["fx"]["bubbles"] = an["fx"].get("bubbles", 0.0) + d / 2 / dt
        if "el:an:Cl2" not in an["seen"]:
            an["seen"].append("el:an:Cl2")
            events.add(t, u["id"], "obs", "Na anodzie wydziela się żółtozielony chlor o duszącym zapachu.",
                       "Anoda (+): 2Cl^- → Cl2↑ + 2e^-")
    else:
        an["gas"]["O2"] = an["gas"].get("O2", 0.0) + ne / 4
        an["fx"]["bubbles"] = an["fx"].get("bubbles", 0.0) + ne / 4 / dt
        if "el:an:O2" not in an["seen"]:
            an["seen"].append("el:an:O2")
            events.add(t, u["id"], "obs", "Na anodzie wydziela się bezbarwny gaz – tlen; roztwór przy anodzie "
                                          "staje się kwasowy.", "Anoda (+): 2H2O → O2↑ + 4H^+ + 4e^-")
    # migracja anionów do anody (elektroobojętność)
    anions = {"Cl-": 1, "Br-": 1, "I-": 1, "NO3-": 1, "SO4": 2, "CH3COO": 1, "MnO4-": 1}
    eq_tot = sum(cat["aq"].get(a, 0.0) * z for a, z in anions.items())
    if eq_tot > 0:
        move = min(ne, eq_tot * 0.95)
        for a, z in anions.items():
            n = cat["aq"].get(a, 0.0)
            if n <= 0:
                continue
            d = move * (n * z / eq_tot) / z
            cat["aq"][a] = n - d
            an["aq"][a] = an["aq"].get(a, 0.0) + d
    cat["stable"] = an["stable"] = False
    return I


# ---------------------------------------------------------------------------------------------------------------
# Krok symulacji pojedynczego naczynia
# ---------------------------------------------------------------------------------------------------------------
def env_for(bench, v):
    p = bench["vessels"].get(v.get("parent") or "")
    if p:
        return p["gas"], head_cap(p), False, p
    e = EQ[v["type"]]
    if e.kind in ("spoon", "candle", "crucible", "funnel") or (e.kind == "evap_dish"):
        return AIR_INF, math.inf, True, None
    return v["gas"], head_cap(v), not is_closed(v), None


def boiling_point(v) -> float:
    if v["vol"] <= 0:
        return 100.0
    ions = 0.0
    for k, n in v["aq"].items():
        if k in IONS or k in ACIDS:
            ions += n
    m = ions / max(v["vol"] / 1000.0, 1e-3)
    eth = min(1.0, _eth_ml(v) / max(v["vol"], 1e-6))
    return max(78.4, 100.0 + 0.51 * min(m, 12.0) - 22.0 * eth)


def thermal(bench, v, dt, q_rx, t, events):
    e = EQ[v["type"]]
    C = heat_capacity(v)
    T = v["T"]
    P = 0.0
    src = v.get("heat")
    if src in FLAME_T and e.g > 0:
        P = e.g * (FLAME_T[src] - T)
    elif src == "hotplate" and e.heatable:
        P = 0.8 * math.sqrt(max(e.cap, 10) / 250.0) * (330.0 - T)
    elif src == "water_bath":
        P = 2.0 * math.sqrt(max(e.cap, 10) / 100.0) * (80.0 - T)
    elif src == "ice_bath":
        P = 2.0 * math.sqrt(max(e.cap, 10) / 100.0) * (0.0 - T)
    loss = e.hA * (T - AMB)
    if T > 300:
        loss += 2e-12 * ((T + 273) ** 4 - 293 ** 4) * e.hA * 5
    Tn = T + ((P - loss) * dt + q_rx) / C
    boiling = False
    if v["vol"] > 0.02:
        bp = boiling_point(v)
        if Tn > bp:
            E = (Tn - bp) * C
            mass = E / 2257.0
            Tn = bp
            boiling = True
            evap = min(mass, v["vol"])
            _evaporate(bench, v, evap, t, events)
        elif Tn > 50:
            area = (e.diam / 4.0) ** 2
            evap = 0.004 * area * ((Tn - 50) / 50.0) ** 2 * dt
            if evap > 0:
                _evaporate(bench, v, min(evap, v["vol"]), t, events, condense=False)
    v["T"] = max(-40.0, min(Tn, 1600.0))
    if v["vol"] <= 0.02 and v["vol"] > 0:
        v["vol"] = 0.0
        if "dry" not in v["seen"]:
            v["seen"].append("dry")
            events.add(t, v["id"], "obs", "Rozpuszczalnik odparował do sucha – na dnie pozostała stała pozostałość.")
    if boiling and "boil" not in v["seen"]:
        v["seen"].append("boil")
        events.add(t, v["id"], "info", f"Ciecz wrze (ok. {v['T']:.0f} °C).")
    if not boiling and v["T"] < 60 and "boil" in v["seen"]:
        v["seen"].remove("boil")
    return boiling


def _evaporate(bench, v, ml, t, events, condense=True):
    if ml <= 0 or v["vol"] <= 0:
        return
    eth_ml = _eth_ml(v)
    water_ml = max(v["vol"] - eth_ml, 0.0)
    eth_frac = eth_ml / max(v["vol"], 1e-9)
    e_part = min(eth_ml, ml * min(1.0, 2.5 * eth_frac))
    w_part = min(water_ml, ml - e_part)
    n_eth = e_part * 0.789 / 46.07
    v["vol"] = max(0.0, v["vol"] - e_part - w_part)
    if n_eth > 0:
        v["aq"]["EtOH"] = max(0.0, v["aq"].get("EtOH", 0.0) - n_eth)
    v["fx"]["steam"] = min(1.0, v["fx"].get("steam", 0.0) + ml * 2)
    # para wodna wypycha gazy z przestrzeni nad cieczą
    if v["gas"]:
        vapor_ml = (e_part + w_part) / 18.0 * 30600.0
        f = min(0.95, vapor_ml / max(head_cap(v) * MOLV, 1.0) * 0.5)
        if f > 0:
            pushed = {k: n * f for k, n in v["gas"].items()}
            for k in v["gas"]:
                v["gas"][k] *= (1 - f)
            if v.get("outlet") and is_closed(v):
                route_gas(bench, v, pushed, 0.0, Events())
            elif is_closed(v):
                for k, n in pushed.items():
                    v["gas"][k] += n  # zamknięte naczynie – para tylko podnosi ciśnienie
            else:
                cap = head_cap(v)
                for k, frac in AIR.items():
                    v["gas"][k] = v["gas"].get(k, 0.0) + frac * cap * f
    tgt = bench["vessels"].get(v.get("outlet") or "")
    if condense and tgt and is_closed(v):
        aq = {"EtOH": n_eth} if n_eth > 0 else {}
        put(bench, tgt, {"aq": aq, "vol": e_part + w_part, "org": {}, "org_vol": 0.0, "solids": {}, "T": 25.0}, t,
            events, mix_heat=False)
        if "distill" not in v["seen"]:
            v["seen"].append("distill")
            events.add(t, v["id"], "obs", "Pary skraplają się w chłodnicy, a destylat spływa do odbieralnika.")


def partition(v, dt):
    if v.get("org_vol", 0.0) <= 0 or v["vol"] <= 0:
        return
    k = 1.5 if v.get("stir", 0) > 0 else 0.01
    for sp_id, K in PARTITION.items():
        na, no = v["aq"].get(sp_id, 0.0), v["org"].get(sp_id, 0.0)
        r = K * v["org_vol"] / v["vol"]
        tot = na + no
        if tot <= 0:
            continue
        no_eq = tot * r / (1 + r)
        d = (no_eq - no) * (1 - math.exp(-k * dt))
        v["org"][sp_id] = no + d
        v["aq"][sp_id] = max(0.0, na - d)


def apply_rx(bench, v, rx, ext, env, env_vessel):
    st = rx.st
    for comp, k in st.get("aq", {}).items():
        v["aq"][comp] = max(0.0, v["aq"].get(comp, 0.0) + k * ext)
    for comp, k in st.get("org", {}).items():
        v["org"][comp] = max(0.0, v["org"].get(comp, 0.0) + k * ext)
    for sid, k in st.get("s", {}).items():
        if k == 0:
            continue
        target = v
        if k > 0 and sid in SMOKE_SOLIDS and env_vessel is not None:
            target = env_vessel
        cur = target["solids"].setdefault(sid, {"n": 0.0, "susp": 0.0})
        n_old = cur["n"]
        cur["n"] = max(0.0, n_old + k * ext)
        if k > 0 and target["vol"] > 0.3:
            s = SOLIDS.get(sid)
            fresh = 1.0 if (s and s.style not in BIG and s.kind != "metal") else 0.0
            cur["susp"] = (n_old * cur.get("susp", 0.0) + k * ext * fresh) / cur["n"] if cur["n"] > 0 else 0
        if cur["n"] <= 1e-15:
            target["solids"].pop(sid, None)
    if st.get("vol"):
        v["vol"] = max(0.0, v["vol"] + st["vol"] * 1000.0 * ext)
    gas_target = v["gas"] if EQ[v["type"]].kind not in ("spoon", "candle", "crucible", "funnel") else None
    if env_vessel is not None:
        gas_target = env_vessel["gas"]
    for gid, k in st.get("g", {}).items():
        if gas_target is not None:
            gas_target[gid] = gas_target.get(gid, 0.0) + k * ext
    for gid, k in st.get("env", {}).items():
        if env is AIR_INF:
            continue
        env[gid] = max(0.0, env.get(gid, 0.0) + k * ext)


def _limit(v, rx, ext, env):
    st = rx.st
    for comp, k in st.get("aq", {}).items():
        if k < 0:
            ext = min(ext, v["aq"].get(comp, 0.0) / -k)
    for comp, k in st.get("org", {}).items():
        if k < 0:
            ext = min(ext, v["org"].get(comp, 0.0) / -k)
    for sid, k in st.get("s", {}).items():
        if k < 0:
            ext = min(ext, v["solids"].get(sid, {}).get("n", 0.0) / -k)
    if env is not AIR_INF:
        for gid, k in st.get("env", {}).items():
            if k < 0:
                ext = min(ext, env.get(gid, 0.0) / -k)
    if st.get("vol", 0) < 0:
        ext = min(ext, v["vol"] / (-st["vol"] * 1000.0))
    if rx.cap is not None:
        ext = min(ext, max(rx.cap, 0.0))
    return max(ext, 0.0) * 0.999


def vessel_substep(bench, v, dt, t, events: Events, sp=None):
    e = EQ[v["type"]]
    if e.kind == "funnel":
        return None
    heat = [0.0]
    if sp is None:
        sp = speciate(v["aq"], v["vol"] if v["vol"] > 0.02 else 0.02, v["T"])
    env, env_cap, env_open, env_vessel = env_for(bench, v)
    ctx = Ctx(v, e, sp, env, env_cap, env_open, dt)
    bubbles = 0.0
    active = []
    fx_new = {}
    for rule in RULES:
        for rx in rule(ctx) or ():
            if rx.rate <= 0:
                continue
            ext = _limit(v, rx, rx.rate * dt, env)
            if ext <= 0:
                continue
            apply_rx(bench, v, rx, ext, env, env_vessel)
            heat[0] += -rx.dh * 1000.0 * ext
            active.append(rx.key)
            r = ext / dt
            if rx.bubbles and v["vol"] > 0.3:
                gsum = sum(k for k in rx.st.get("g", {}).values() if k > 0)
                bubbles += r * gsum
            for k, val in rx.fx.items():
                fx_new[k] = val
            if rx.fx:
                fx_new["intensity"] = max(fx_new.get("intensity", 0.0), min(1.0, r * 3000))
            frac = 0.0
            for grp in ("aq", "s"):
                for comp, k in rx.st.get(grp, {}).items():
                    if k < 0:
                        avail = v["aq"].get(comp, 0.0) if grp == "aq" else v["solids"].get(comp, {}).get("n", 0.0)
                        frac = max(frac, -k * ext / max(avail + (-k * ext), 1e-30))
            if rx.key not in v["seen"] and (ext > 5e-8 or frac > 0.002):
                v["seen"].append(rx.key)
                events.add(t, v["id"], "obs", rx.obs, rx.eq or None)
    # zachowaj efekty utrzymujące się w czasie
    old = v.get("fx", {})
    fx = {"_active": active}
    for k in ("steam", "smoke_level", "fountain"):
        if old.get(k):
            fx[k] = old[k] * math.exp(-dt / (3.0 if k != "smoke_level" else 25.0))
            if fx[k] < 0.01:
                fx.pop(k)
    if old.get("smoke") and fx.get("smoke_level"):
        fx["smoke"] = old["smoke"]
    for k in ("bubbles", "inlet_bubbles", "spatter", "mirror"):
        if old.get(k) and k == "mirror":
            fx[k] = old[k]
    fx.update(fx_new)
    if fx_new.get("smoke"):
        target = env_vessel if env_vessel is not None else v
        tfx = target.setdefault("fx", {})
        tfx["smoke"] = fx_new["smoke"]
        tfx["smoke_level"] = min(1.0, tfx.get("smoke_level", 0.0) + 0.4 * dt)
        if target is v:
            fx["smoke_level"] = tfx["smoke_level"]
    v["fx"] = fx
    if any(k.startswith("tollens") for k in active):
        v["mirror"] = 1
    inb = v.pop("_inbub", 0.0)
    if inb > 0:
        bubbles += inb
        fx["inlet_bubbles"] = 1
    # elementy przestrzeni gazowej i cieczy
    partition(v, dt)
    boiling = thermal(bench, v, dt, heat[0], t, events)
    hq = [0.0]
    sp2 = equilibrate(v, dt, t, events, hq)
    if hq[0]:
        v["T"] += hq[0] / heat_capacity(v)
    if e.kind not in ("spoon", "candle", "crucible", "funnel"):
        bubbles += gas_exchange(bench, v, sp2, dt, t, events, boiling)
        headspace(bench, v, dt, t, events)
    v["fx"]["bubbles"] = v["fx"].get("bubbles", 0.0) + bubbles
    if boiling:
        v["fx"]["boiling"] = 1
    # sedymentacja
    stir = v.get("stir", 0.0) > 0
    for sid, st in v["solids"].items():
        s = SOLIDS.get(sid)
        if not s:
            continue
        if s.style in BIG or s.kind == "metal":
            st["susp"] = 0.0
        elif stir and s.style in RESUSPEND and v["vol"] > 0.3:
            st["susp"] = max(st.get("susp", 0.0), 0.9)
        else:
            st["susp"] = st.get("susp", 0.0) * math.exp(-dt / max(s.settle, 0.2))
    if v.get("stir", 0) > 0:
        v["stir"] = max(0.0, v["stir"] - dt)
    return sp2


def _q_from_heat_list(h):
    return h[0]


def _process_vessel(bench, v, dt, t, events):
    """Przetwarza naczynie (z uwzględnieniem ramion elektrolizera). Zwraca specjację do widoku."""
    if v.get("arms"):
        sps = []
        for a in v["arms"]:
            a["fx"] = {k: val for k, val in a.get("fx", {}).items() if k in ("steam",)}
            sps.append(speciate(a["aq"], max(a["vol"], 0.02), a["T"]))
        electrolysis(bench, v, dt, t, events, sps)
        # dyfuzja między ramionami
        c0, c1 = v["arms"]
        if c0["vol"] > 0.5 and c1["vol"] > 0.5:
            f = 1 - math.exp(-0.002 * dt)
            for k in set(c0["aq"]) | set(c1["aq"]):
                a0, a1 = c0["aq"].get(k, 0.0) / c0["vol"], c1["aq"].get(k, 0.0) / c1["vol"]
                mean = (a0 * c0["vol"] + a1 * c1["vol"]) / (c0["vol"] + c1["vol"])
                c0["aq"][k] = (a0 + (mean - a0) * f) * c0["vol"]
                c1["aq"][k] = (a1 + (mean - a1) * f) * c1["vol"]
        out = []
        for a in v["arms"]:
            out.append(vessel_substep(bench, a, dt, t, events))
        return out
    v["fx"]["bubbles"] = 0.0
    v["fx"].pop("boiling", None)
    v["fx"].pop("inlet_bubbles", None) if v["fx"].get("_inlet_keep") is None else None
    return vessel_substep(bench, v, dt, t, events)


# ---------------------------------------------------------------------------------------------------------------
# Akcje użytkownika
# ---------------------------------------------------------------------------------------------------------------
def _new_id(bench, prefix="v"):
    i = bench.get("seq", 0) + 1
    while f"{prefix}{i}" in bench["vessels"]:
        i += 1
    bench["seq"] = i
    return f"{prefix}{i}"


def run_test(bench, v, tool, t, events: Events):
    sp = None
    if v["vol"] > 0.1:
        sp = speciate(v["aq"], v["vol"], v["T"])
    gas = v.get("gas", {})
    tot = sum(gas.values()) or 1.0
    x = {k: n / tot for k, n in gas.items()}
    vid = v["id"]
    if v.get("arms"):
        for i, a in enumerate(v["arms"]):
            label = "katody (−)" if i == 0 else "anody (+)"
            sub = Events()
            run_test(bench, a, tool, t, sub)
            for ev in sub:
                ev["v"] = vid
                ev["text"] = f"Przy ramieniu {label}: " + ev["text"]
                events.append(ev)
        return
    if tool == "glowing_splint":
        if x.get("O2", 0) > 0.33:
            events.add(t, vid, "test", "Żarzące się łuczywo rozżarza się i zapala jasnym płomieniem – obecny tlen!",
                       result="relight")
            gas["O2"] = gas.get("O2", 0) * 0.9
        elif x.get("O2", 0) < 0.12:
            events.add(t, vid, "test", "Żarzące się łuczywo gaśnie – w naczyniu brak tlenu.", result="out")
        else:
            events.add(t, vid, "test", "Łuczywo tli się dalej, tak jak w powietrzu.", result="none")
    elif tool == "burning_splint":
        h2 = x.get("H2", 0)
        if h2 > 0.04 and x.get("O2", 0) > 0.02:
            loud = "głośne „szczeknięcie”" if 0.15 < h2 < 0.8 else "ciche pyknięcie"
            events.add(t, vid, "test", f"Słychać {loud} – mieszanina wodoru z powietrzem spala się wybuchowo.",
                       "2H2 + O2 → 2H2O", result="pop")
            n_h2 = gas.get("H2", 0)
            burn = min(n_h2, 2 * gas.get("O2", 0))
            gas["H2"] = n_h2 - burn
            gas["O2"] = gas.get("O2", 0) - burn / 2
            v["fx"]["pop"] = 1
        elif h2 > 0.8:
            events.add(t, vid, "test", "Czysty wodór spala się spokojnie bladoniebieskim płomieniem u wylotu naczynia.",
                       "2H2 + O2 → 2H2O", result="burn")
        elif x.get("C2H2", 0) > 0.05:
            events.add(t, vid, "test", "Gaz zapala się jasnym, silnie kopcącym płomieniem – etyn (acetylen).",
                       "2C2H2 + 5O2 → 4CO2 + 2H2O", result="soot")
            gas["C2H2"] = 0.0
        elif x.get("CH4", 0) > 0.05:
            events.add(t, vid, "test", "Gaz spala się niebieskim płomieniem.", "CH4 + 2O2 → CO2 + 2H2O")
        elif x.get("CO2", 0) + x.get("N2", 0) > 0.85 or x.get("O2", 0) < 0.12 or x.get("Cl2", 0) > 0.3:
            events.add(t, vid, "test", "Płonące łuczywo gaśnie – gaz nie podtrzymuje palenia.", result="out")
        elif x.get("O2", 0) > 0.33:
            events.add(t, vid, "test", "Łuczywo pali się bardzo jasno – atmosfera wzbogacona w tlen.",
                       result="bright")
        else:
            events.add(t, vid, "test", "Łuczywo pali się dalej bez zmian.", result="none")
    elif tool == "gas_litmus":
        msgs = []
        if x.get("Cl2", 0) > 0.02:
            msgs.append("wilgotne papierki lakmusowe najpierw czerwienieją, a potem odbarwiają się – chlor wybiela")
            res = "bleach"
        elif x.get("NH3", 0) > 0.002:
            msgs.append("wilgotny czerwony papierek lakmusowy barwi się na niebiesko – gaz o odczynie zasadowym (NH₃)")
            res = "blue"
        elif any(x.get(g, 0) > (0.05 if g == "CO2" else 0.002) for g in ("HCl", "SO2", "NO2", "CO2", "H2S")):
            msgs.append("wilgotny niebieski papierek lakmusowy barwi się na czerwono – gaz o odczynie kwasowym")
            res = "red"
        else:
            msgs.append("wilgotne papierki lakmusowe nie zmieniają barwy")
            res = "none"
        events.add(t, vid, "test", "Przy wylocie naczynia " + msgs[0] + ".", result=res)
    elif tool in ("litmus_red", "litmus_blue", "univ_paper"):
        if not sp:
            events.add(t, vid, "test", "W naczyniu nie ma cieczy, w której można zanurzyć papierek.")
            return
        ph = sp.ph
        if tool == "univ_paper":
            from .appearance import _interp_palette
            col = _interp_palette(INDICATOR_UNIV, ph)
            events.add(t, vid, "test", f"Papierek uniwersalny barwi się – pH ≈ {round(ph)}"
                                       f" ({'kwasowy' if ph < 6.5 else 'zasadowy' if ph > 7.5 else 'obojętny'}).",
                       result=col)
        elif tool == "litmus_red":
            col = "#3b4db2" if ph > 8 else "#c8343a"
            events.add(t, vid, "test", "Czerwony papierek lakmusowy " + (
                "barwi się na niebiesko – odczyn zasadowy." if ph > 8 else "nie zmienia barwy."), result=col)
        else:
            col = "#c8343a" if ph < 5 else "#3b4db2"
            events.add(t, vid, "test", "Niebieski papierek lakmusowy " + (
                "barwi się na czerwono – odczyn kwasowy." if ph < 5 else "nie zmienia barwy."), result=col)
    elif tool in ("flame_test", "cobalt_glass"):
        fc = flame_color_for(v)
        if tool == "cobalt_glass" and fc and fc[0] == FLAME_COLORS["Na"][0]:
            has_k = any(k == "K+" for k in v["aq"]) or any(
                any(sp_ == "K+" for sp_, _ in SOLIDS[s].comp) for s in v["solids"] if s in SOLIDS)
            fc = FLAME_COLORS["K"] if has_k else None
        if fc:
            events.add(t, vid, "test", f"Płomień palnika barwi się na kolor {fc[1]}.", result=fc[0], flame=fc[0])
        else:
            events.add(t, vid, "test", "Płomień nie zmienia wyraźnie barwy.", result=None)
    elif tool == "smell":
        notes = []
        for g, frac in x.items():
            gg = GASES.get(g)
            if gg and gg.smell and frac > (0.0005 if g in ("H2S", "Cl2", "NH3", "SO2") else 0.01):
                notes.append(gg.smell)
        if sp:
            for spc, (thr, desc) in SMELL_SPECIES.items():
                if sp.free.get(spc, 0) > thr:
                    notes.append(desc)
            for m in ("EtOH", "EtOAc", "CH3CHO", "HCHO"):
                if sp.free.get(m, 0) > 0.02 and MOLECULES[m].smell:
                    notes.append(MOLECULES[m].smell)
        if v["solids"].get("Caramel"):
            notes.append("zapach karmelu")
        notes = list(dict.fromkeys(notes))
        events.add(t, vid, "test", ("Ostrożne wąchanie (ręką nad wylotem): " + "; ".join(notes) + ".") if notes else
                   "Ostrożne wąchanie: brak wyraźnego zapachu.")
    elif tool == "conductivity":
        k = conductivity(v, sp)
        b = k / (k + 0.006)
        desc = "świeci jasno – dobry przewodnik (mocny elektrolit)" if b > 0.6 else \
            "świeci słabo – słaby elektrolit" if b > 0.05 else "nie świeci – roztwór praktycznie nie przewodzi"
        events.add(t, vid, "test", f"Żarówka {desc}. Przewodnictwo ≈ {k * 1000:.2f} mS/cm.", result=round(b, 3))
    elif tool == "thermometer":
        events.add(t, vid, "test", f"Termometr wskazuje {v['T']:.1f} °C.", result=round(v["T"], 1))
    elif tool == "ph_meter":
        if sp:
            events.add(t, vid, "test", f"pH-metr wskazuje pH = {sp.ph:.2f}.", result=round(sp.ph, 2))
        else:
            events.add(t, vid, "test", "Brak cieczy do pomiaru pH.")
    else:
        raise ValueError("nieznane narzędzie")


INDICATOR_UNIV = None


def _init_univ():
    global INDICATOR_UNIV
    from .data import INDICATORS
    INDICATOR_UNIV = INDICATORS["univ"].palette


_init_univ()


def apply_action(bench, a: dict, events: Events):
    t = bench.get("t", 0.0)
    op = a.get("op")
    V = bench["vessels"]

    def vv(key="v"):
        vid = a.get(key)
        if vid not in V:
            raise ValueError("nie ma takiego naczynia")
        return V[vid]

    if op == "add_vessel":
        if len(V) >= MAX_VESSELS:
            raise ValueError("Na stole nie zmieści się więcej sprzętu.")
        et = a.get("etype")
        if et not in EQUIPMENT:
            raise ValueError("nieznany sprzęt")
        vid = a.get("id") or _new_id(bench)
        if vid in V:
            vid = _new_id(bench)
        V[vid] = new_vessel(et, vid, float(a.get("x", 0)))
        return vid
    if op == "remove":
        v = vv()
        V.pop(v["id"])
        for o in V.values():
            for key in ("outlet", "parent", "target", "source"):
                if o.get(key) == v["id"]:
                    o[key] = None
        return None
    if op == "move":
        v = vv()
        v["x"] = float(a.get("x", v["x"]))
        if "y" in a:
            v["y"] = float(a["y"])
        return None
    if op == "reagent":
        v = vv()
        add_reagent(bench, v, a.get("reagent"), float(a.get("amount", 0)), t, events)
        return None
    if op == "pour":
        src, dst = vv("from"), vv("to")
        if src is dst:
            raise ValueError("nie można przelać do tego samego naczynia")
        ml = float(a.get("ml", 0))
        e = EQ[dst["type"]]
        room = e.cap - dst["vol"] - dst.get("org_vol", 0.0) if e.kind not in ("funnel",) else 1e9
        if dst.get("arms"):
            room = 2 * (ARM.cap - dst["arms"][0]["vol"])
        overflow = ml > room + 1e-6
        ml = max(0.0, min(ml, room))
        portion = take(src, ml, everything=bool(a.get("all")))
        put(bench, dst, portion, t, events)
        if overflow:
            events.add(t, dst["id"], "warn", "Naczynie jest pełne – nadmiar cieczy się nie zmieścił.")
        src["stable"] = False
        return None
    if op == "empty":
        v = vv()
        if v.get("arms"):
            for arm in v["arms"]:
                arm.update({"aq": {}, "vol": 0.0, "org": {}, "org_vol": 0.0, "solids": {}, "gas": {}, "seen": [],
                            "prog": {}, "T": AMB})
        else:
            e = EQ[v["type"]]
            v.update({"aq": {}, "vol": 0.0, "org": {}, "org_vol": 0.0, "solids": {}, "seen": [], "prog": {},
                      "T": AMB, "fx": {}})
            if e.kind == "candle":
                v["solids"]["Wax"] = {"n": 5.0 / SOLIDS["Wax"].mm, "susp": 0.0}
            v["gas"] = _air(head_cap(v)) if e.kind not in ("spoon", "candle", "funnel") else {}
        return None
    if op == "heat":
        v = vv()
        src = a.get("source")
        if src not in (None, "alcohol", "bunsen", "hotplate", "water_bath", "ice_bath"):
            raise ValueError("nieznane źródło ciepła")
        e = EQ[v["type"]]
        if src in ("alcohol", "bunsen", "hotplate") and not e.heatable:
            raise ValueError("Tego naczynia nie wolno ogrzewać płomieniem (szkło niearoodporne).")
        v["heat"] = src
        return None
    if op in ("stir", "shake"):
        v = vv()
        v["stir"] = float(a.get("seconds", 4.0))
        return None
    if op == "stopper":
        v = vv()
        v["stopper"] = bool(a.get("on"))
        if EQ[v["type"]].kind == "jar":
            v["lid"] = bool(a.get("on"))
        return None
    if op == "connect":
        v = vv()
        to = a.get("to")
        if to and to not in V:
            raise ValueError("nie ma takiego naczynia")
        v["outlet"] = to
        if to:
            v["stopper"] = True
        return None
    if op == "source":
        v = vv()
        to = a.get("src")
        v["source"] = to if to in V else None
        return None
    if op == "parent":
        v = vv()
        to = a.get("to")
        v["parent"] = to if to in V else None
        if to:
            v["heat"] = None
        return None
    if op == "burette":
        v = vv()
        tgt = a.get("target")
        v["target"] = tgt if tgt in V else None
        v["flow"] = max(0.0, min(float(a.get("flow", 0.0)), 5.0))
        return None
    if op == "funnel":
        v = vv()
        tgt = a.get("target")
        v["target"] = tgt if tgt in V else None
        return None
    if op == "power":
        v = vv()
        v["power"] = bool(a.get("on"))
        if a.get("electrode") in ("C", "Cu"):
            v["electrode"] = a["electrode"]
        return None
    if op == "ignite":
        v = vv()
        e = EQ[v["type"]]
        if v["vol"] > 1.0:
            events.add(t, v["id"], "info", "Zawartość jest mokra – nie zapala się.")
            return None
        v["T"] = max(v["T"], 760.0 if e.kind in ("spoon", "crucible", "evap_dish") else 300.0)
        for sid in v["solids"]:
            v["prog"][f"lit:{sid}"] = 1.0
        return None
    if op == "test":
        v = vv()
        run_test(bench, v, a.get("tool"), t, events)
        return None
    if op == "bridge":
        links = bench.setdefault("links", [])
        pair = sorted([a.get("a"), a.get("b")])
        if pair[0] not in V or pair[1] not in V:
            raise ValueError("nie ma takiego naczynia")
        links[:] = [lk for lk in links if sorted([lk["a"], lk["b"]]) != pair]
        if a.get("on", True):
            links.append({"a": pair[0], "b": pair[1]})
        return None
    raise ValueError(f"nieznana akcja: {op}")


# ---------------------------------------------------------------------------------------------------------------
# Odczyty (ogniwa)
# ---------------------------------------------------------------------------------------------------------------
E0 = {"Zn": ("Zn2+", -0.76, 2), "Cu": ("Cu2+", 0.34, 2), "Fe": ("Fe2+", -0.44, 2), "Mg": ("Mg2+", -2.37, 2),
      "Ag": ("Ag+", 0.80, 1), "Pb": ("Pb2+", -0.13, 2), "Ni": ("Ni2+", -0.25, 2), "Sn": ("Sn2+", -0.14, 2),
      "Al": ("Al3+", -1.66, 3)}


def electrode_potential(v):
    from .rules import SOLID_METAL
    metals = [SOLID_METAL[s] for s, st in v["solids"].items() if s in SOLID_METAL and st["n"] > 0]
    if not metals or v["vol"] < 1:
        return None
    m = metals[0]
    if m not in E0:
        return None
    ion, e0, n = E0[m]
    c = v["aq"].get(ion, 0.0) / (v["vol"] / 1000)
    if c < 1e-4:
        sp = speciate(v["aq"], v["vol"], v["T"])
        return m, max(e0 + 0.0296 * math.log10(1e-4), -0.059 * sp.ph + (0.0 if m != "Cu" else 0.1)) if m in (
            "Cu", "Ag") else e0 + 0.0296 * math.log10(1e-4)
    return m, e0 + 0.05916 / n * math.log10(c)


def readings(bench):
    out = {}
    for lk in bench.get("links", []):
        a, b = bench["vessels"].get(lk["a"]), bench["vessels"].get(lk["b"])
        if not a or not b:
            continue
        pa, pb = electrode_potential(a), electrode_potential(b)
        if pa and pb:
            emf = abs(pa[1] - pb[1])
            cath = a["id"] if pa[1] > pb[1] else b["id"]
            out[f"{lk['a']}|{lk['b']}"] = {"emf": round(emf, 3), "cathode": cath,
                                           "metals": [pa[0], pb[0]]}
    return out


# ---------------------------------------------------------------------------------------------------------------
# Główna funkcja kroku
# ---------------------------------------------------------------------------------------------------------------
def step(bench: dict, actions: list, dt: float):
    events = Events()
    bench.setdefault("vessels", {})
    bench.setdefault("t", 0.0)
    created = []
    errors = []
    for a in actions or []:
        try:
            r = apply_action(bench, a, events)
            if r:
                created.append(r)
        except ValueError as ex:
            errors.append(str(ex))
            events.add(bench["t"], a.get("v"), "error", str(ex))
    dt = max(0.0, min(float(dt or 0.0), 30.0))
    n_sub = max(1, int(math.ceil(dt / 0.25))) if dt > 0 else 0
    sub = dt / n_sub if n_sub else 0.0
    bench["_dt"] = sub or 0.25
    sps = {}
    order = sorted(bench["vessels"].values(), key=lambda v: 0 if v.get("parent") else 1)
    for _ in range(n_sub):
        bench["t"] += sub
        # przepływy z biuret
        for v in list(bench["vessels"].values()):
            if v.get("flow", 0) > 0 and v.get("target") in bench["vessels"] and v["vol"] > 0.001:
                ml = min(v["flow"] * sub, v["vol"])
                put(bench, bench["vessels"][v["target"]], take(v, ml), bench["t"], events)
        for v in order:
            if v["id"] in bench["vessels"]:
                backup = copy.deepcopy(v)
                try:
                    sps[v["id"]] = _process_vessel(bench, v, sub, bench["t"], events)
                except Exception:  # pragma: no cover - awaryjnie: naczynie zostaje w poprzednim stanie
                    import logging
                    logging.getLogger("chemia").exception("błąd symulacji naczynia %s", v["id"])
                    bench["vessels"][v["id"]] = backup
                    v.clear()
                    v.update(backup)
                    sps[v["id"]] = None
    if n_sub == 0:
        for v in bench["vessels"].values():
            if v.get("arms"):
                for a in v["arms"]:
                    equilibrate(a, 0.0, bench["t"], events, [0.0])
            elif EQ[v["type"]].kind != "funnel":
                sps[v["id"]] = equilibrate(v, 0.0, bench["t"], events, [0.0])
    views = {}
    for vid, v in bench["vessels"].items():
        e = EQ[v["type"]]
        if v.get("arms"):
            arms = []
            for i, a in enumerate(v["arms"]):
                spa = sps.get(vid)[i] if isinstance(sps.get(vid), list) else None
                if spa is None and a["vol"] > 0.01:
                    spa = speciate(a["aq"], a["vol"], a["T"])
                arms.append(view(a, spa, ARM))
            views[vid] = {"id": vid, "type": v["type"], "arms": arms, "power": v.get("power"),
                          "current": round(v.get("current", 0.0), 3) if v.get("power") else 0.0,
                          "electrode": v.get("electrode", "C")}
            continue
        sp = sps.get(vid)
        if (sp is None or isinstance(sp, list)) and v["vol"] > 0.01:
            sp = speciate(v["aq"], v["vol"], v["T"])
        vw = view(v, sp, e)
        if sp is not None and v["vol"] > 0.3:
            vw["kappa"] = round(conductivity(v, sp) * 1000, 4)
        vw["contents"] = contents(v, sp)
        vw["parent"] = v.get("parent")
        vw["target"] = v.get("target")
        vw["flow"] = v.get("flow", 0.0)
        vw["source"] = v.get("source")
        _color_event(v, vw, bench["t"], events)
        views[vid] = vw
    bench.pop("_dt", None)
    return {"bench": bench, "events": events, "views": views, "readings": readings(bench), "created": created,
            "errors": errors}


def _color_event(v, vw, t, events):
    name = vw.get("color_name")
    if not name:
        return
    last = v.get("_col")
    last_t = v.get("_colt", -99)
    if last is None:
        v["_col"] = name
        v["_colt"] = t
        return
    if name != last and t - last_t > 1.0:
        v["_col"] = name
        v["_colt"] = t
        events.add(t, v["id"], "color", f"Barwa roztworu zmienia się: {last} → {name}.", color=vw.get("liquid"))


def contents(v, sp):
    from .appearance import species_label
    out = []
    if sp is not None and v["vol"] > 0.01:
        items = [(k, c) for k, c in sp.free.items() if c > 2e-6 and k not in ("H+", "OH-")]
        items.sort(key=lambda kv: -kv[1])
        for k, c in items[:14]:
            out.append({"kind": "aq", "id": k, "name": species_label(k), "c": float(f"{c:.3g}")})
    for k, n in v.get("org", {}).items():
        if n > 1e-9:
            info = ORG_SPECIES.get(k)
            out.append({"kind": "org", "id": k, "name": info[0] if info else k, "n": float(f"{n:.3g}")})
    for sid, st in v.get("solids", {}).items():
        s = SOLIDS.get(sid)
        if s and st["n"] > 1e-9:
            out.append({"kind": "s", "id": sid, "name": s.name, "formula": s.formula,
                        "g": float(f"{st['n'] * s.mm:.3g}")})
    return out
