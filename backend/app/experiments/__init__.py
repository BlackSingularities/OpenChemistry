"""Biblioteka doświadczeń. Każde doświadczenie to przygotowany stół, kroki (akcje wykonywane przez silnik)
oraz oczekiwane wyniki, które są automatycznie sprawdzane w testach – dzięki temu opis zawsze zgadza się
z tym, co faktycznie pokazuje symulacja."""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from functools import lru_cache

from ..chem import sim

CATEGORIES = [
    ("acids", "Kwasy, zasady i wskaźniki", "flask"),
    ("precip", "Reakcje strąceniowe", "drop"),
    ("metals", "Metale i ich aktywność", "metal"),
    ("redox", "Utlenianie i redukcja", "bolt"),
    ("gases", "Gazy – otrzymywanie i badanie", "bubbles"),
    ("combustion", "Spalanie", "flame"),
    ("electro", "Elektrochemia", "battery"),
    ("energy", "Energetyka i kinetyka", "thermo"),
    ("equilibrium", "Równowaga chemiczna", "balance"),
    ("solutions", "Roztwory i krystalizacja", "crystal"),
    ("analysis", "Analiza jakościowa", "search"),
    ("organic", "Chemia organiczna", "hexagon"),
    ("bio", "Biochemia i chemia żywności", "leaf"),
    ("show", "Efektowne pokazy", "sparkles"),
]
CAT_NAMES = {c[0]: c[1] for c in CATEGORIES}


@dataclass
class Exp:
    id: str
    title: str
    cat: str
    level: str
    summary: str
    setup: list
    steps: list
    expect: list = field(default_factory=list)
    theory: str = ""
    equations: list = field(default_factory=list)
    safety: str = ""
    tags: tuple = ()
    observe: str = ""


def V(id, etype, x=None, *fill, **kw):
    return {"id": id, "etype": etype, "x": x, "fill": list(fill), **kw}


def S(text, *actions, wait=3.0, hint=None):
    return {"text": text, "actions": list(actions), "wait": wait, "hint": hint}


# --- skróty akcji ---
def add(v, reagent, amount):
    return {"op": "reagent", "v": v, "reagent": reagent, "amount": amount}


def pour(a, b, ml, all=False):
    d = {"op": "pour", "from": a, "to": b, "ml": ml}
    if all:
        d["all"] = True
    return d


def heat(v, src="alcohol"):
    return {"op": "heat", "v": v, "source": src}


def stop_heat(v):
    return {"op": "heat", "v": v, "source": None}


def stir(v, s=4.0):
    return {"op": "stir", "v": v, "seconds": s}


def test(v, tool):
    return {"op": "test", "v": v, "tool": tool}


def connect(a, b):
    return {"op": "connect", "v": a, "to": b}


def disconnect(a):
    return {"op": "connect", "v": a, "to": None}


def stopper(v, on=True):
    return {"op": "stopper", "v": v, "on": on}


def into(v, jar):
    return {"op": "parent", "v": v, "to": jar}


def ignite(v):
    return {"op": "ignite", "v": v}


def burette(v, target, flow):
    return {"op": "burette", "v": v, "target": target, "flow": flow}


def power(v, on=True, electrode=None):
    d = {"op": "power", "v": v, "on": on}
    if electrode:
        d["electrode"] = electrode
    return d


def bridge(a, b):
    return {"op": "bridge", "a": a, "b": b, "on": True}


def source(v, src):
    return {"op": "source", "v": v, "src": src}


WIDTHS = {"test_tube": 30, "boiling_tube": 40, "beaker_100": 76, "beaker_250": 98, "beaker_600": 126, "flask_250": 120,
          "round_flask": 128, "cylinder_100": 34, "gas_jar": 76, "evap_dish": 140, "crucible": 50, "trough": 290,
          "watch_glass": 92, "petri": 120, "burette": 18, "utube": 130, "spoon": 26, "candle": 22, "funnel": 76,
          "fountain": 128}

REGISTRY: dict[str, Exp] = {}


def register(*exps: Exp):
    for e in exps:
        if e.id in REGISTRY:
            raise ValueError(f"powtórzone id {e.id}")
        REGISTRY[e.id] = e


def _load():
    from . import (e_acids, e_precip, e_metals, e_redox, e_gases, e_combustion, e_electro, e_energy,  # noqa
                   e_equilibrium, e_solutions, e_analysis, e_organic, e_bio, e_show)


_load()
EXPERIMENTS = REGISTRY


def build_bench(eid: str) -> dict | None:
    e = REGISTRY.get(eid)
    if not e:
        return None
    bench = {"vessels": {}, "t": 0.0, "seq": 0, "links": []}
    ev = sim.Events()
    # automatyczne rozmieszczenie: naczynia obok siebie, wyśrodkowane na stole
    auto = [s for s in e.setup if s.get("x") is None and not (s.get("parent") or (s["etype"] in ("burette", "funnel")
                                                                                     and s.get("target")))]
    gap = 46
    total = sum(WIDTHS.get(s["etype"], 80) for s in auto) + gap * max(0, len(auto) - 1)
    cur = 500 - total / 2
    auto_x = {}
    for s in auto:
        w = WIDTHS.get(s["etype"], 80)
        auto_x[s["id"]] = cur + w / 2
        cur += w + gap
    for spec in e.setup:
        x = spec.get("x")
        if x is None:
            x = auto_x.get(spec["id"], 500)
        v = sim.new_vessel(spec["etype"], spec["id"], float(x))
        bench["vessels"][spec["id"]] = v
    for spec in e.setup:
        v = bench["vessels"][spec["id"]]
        for rid, amount in spec["fill"]:
            sim.add_reagent(bench, v, rid, amount, 0.0, ev)
        for key in ("outlet", "parent", "source", "target"):
            if spec.get(key):
                v[key] = spec[key]
        for key in ("stopper", "lid", "power", "collect"):
            if key in spec:
                v[key] = spec[key]
        if spec.get("collect"):
            v["gas"] = {}
        if spec.get("electrode"):
            v["electrode"] = spec["electrode"]
        if spec.get("heat"):
            v["heat"] = spec["heat"]
        if spec.get("flow"):
            v["flow"] = spec["flow"]
        if spec.get("gas"):
            sim.add_reagent(bench, v, spec["gas"], 1, 0.0, ev)
        if spec.get("T") is not None:
            v["T"] = spec["T"]
    for lk in [s for s in e.setup if s.get("bridge")]:
        bench["links"].append({"a": lk["id"], "b": lk["bridge"]})
    # ustal równowagę początkową, ale nie pokazuj zdarzeń z przygotowania
    sim.step(bench, [], 0.0)
    for v in bench["vessels"].values():
        v["seen"] = [s for s in v["seen"] if s.startswith("ppt:")]
        if v.get("arms"):
            for a in v["arms"]:
                a["seen"] = []
    return bench


def experiment_list():
    out = []
    for e in REGISTRY.values():
        out.append({"id": e.id, "title": e.title, "cat": e.cat, "level": e.level, "summary": e.summary,
                    "tags": list(e.tags), "steps": len(e.steps)})
    return {"categories": [{"id": c, "name": n, "icon": i,
                            "count": sum(1 for e in REGISTRY.values() if e.cat == c)} for c, n, i in CATEGORIES],
            "experiments": out}


@lru_cache(maxsize=512)
def _detail(eid):
    e = REGISTRY[eid]
    return {"id": e.id, "title": e.title, "cat": e.cat, "catName": CAT_NAMES.get(e.cat, e.cat), "level": e.level,
            "summary": e.summary, "theory": e.theory, "equations": e.equations, "safety": e.safety,
            "observe": e.observe, "steps": e.steps, "tags": list(e.tags),
            "setup": [{"id": s["id"], "etype": s["etype"], "x": s.get("x"), "label": s.get("label")} for s in e.setup]}


def experiment_detail(eid):
    if eid not in REGISTRY:
        return None
    return copy.deepcopy(_detail(eid))


# --- uruchamianie scenariusza (testy, podgląd) ---
def run_experiment(eid: str):
    e = REGISTRY[eid]
    bench = build_bench(eid)
    events = []
    views = {}
    readings = {}
    for st in e.steps:
        res = sim.step(bench, st["actions"], 0.0)
        events += res["events"]
        wait = st.get("wait", 3.0)
        while wait > 0:
            d = min(wait, 5.0)
            res = sim.step(bench, [], d)
            events += res["events"]
            wait -= d
        views = res["views"]
        readings = res["readings"]
    return bench, events, views, readings


def check_expectations(eid: str):
    e = REGISTRY[eid]
    bench, events, views, readings = run_experiment(eid)
    failures = []
    texts = " | ".join(ev["text"] + " " + ev.get("eq", "") for ev in events)
    errors = [ev for ev in events if ev["kind"] == "error"]
    if errors:
        failures.append(f"błędy akcji: {[x['text'] for x in errors]}")
    for ex in e.expect:
        kind = ex[0]
        ok = True
        try:
            if kind == "event":
                ok = any(alt.lower() in texts.lower() for alt in ex[1].split("|"))
            elif kind == "noevent":
                ok = ex[1].lower() not in texts.lower()
            elif kind in ("ppt", "solid", "nosolid"):
                v = _vessel(bench, ex[1])
                from ..chem.data import SOLIDS
                sl = _solids(v)
                n = sum(sl.get(s, 0) for s in (ex[2] if isinstance(ex[2], tuple) else (ex[2],)))
                mass = sum(sl.get(s, 0) * SOLIDS[s].mm for s in (ex[2] if isinstance(ex[2], tuple) else (ex[2],)))
                present = n > 1e-6 or mass > 5e-4
                ok = present if kind != "nosolid" else not present
            elif kind in ("ph", "T", "vol"):
                vw = _view(views, ex[1])
                val = vw.get({"ph": "pH", "T": "T", "vol": "vol"}[kind])
                ok = val is not None and (_cmp(val, ex[2], ex[3]))
            elif kind == "aq":
                v = _vessel(bench, ex[1])
                sp = sim.speciate(v["aq"], max(v["vol"], 0.05), v["T"])
                ok = _cmp(sp.free.get(ex[2], 0.0), ex[3], ex[4])
            elif kind == "tot":
                v = _vessel(bench, ex[1])
                ok = _cmp(v["aq"].get(ex[2], 0.0), ex[3], ex[4])
            elif kind == "gas":
                v = _vessel(bench, ex[1])
                tot = sum(v["gas"].values()) or 1
                ok = _cmp(v["gas"].get(ex[2], 0.0) / tot, ex[3], ex[4])
            elif kind == "color":
                vw = _view(views, ex[1])
                ok = any(alt in (vw.get("color_name") or "") for alt in ex[2].split("|"))
            elif kind == "org":
                v = _vessel(bench, ex[1])
                ok = _cmp(v["org"].get(ex[2], 0.0), ex[3], ex[4])
            elif kind == "emf":
                vals = [r["emf"] for r in readings.values()]
                ok = bool(vals) and _cmp(max(vals), ex[1], ex[2])
            elif kind == "turbid":
                vw = _view(views, ex[1])
                ok = _cmp(vw.get("turbid", 0.0) or 0.0, ex[2], ex[3])
            else:
                ok = False
        except KeyError:
            ok = False
        if not ok:
            failures.append(str(ex))
    return failures, events, views


def _cmp(a, op, b):
    return a < b if op == "<" else a > b


def _vessel(bench, vid):
    if "#" in vid:
        base, i = vid.split("#")
        return bench["vessels"][base]["arms"][int(i)]
    return bench["vessels"][vid]


def _view(views, vid):
    if "#" in vid:
        base, i = vid.split("#")
        return views[base]["arms"][int(i)]
    return views[vid]


def _solids(v):
    return {k: s["n"] for k, s in v["solids"].items()}
