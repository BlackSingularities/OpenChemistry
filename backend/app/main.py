"""OpenChemistry – wirtualne laboratorium chemiczne (FastAPI)."""
from __future__ import annotations

import math
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .catalog import catalog_payload
from .chem import sim
from .chem.data import ACIDS, IONS, MOLECULES, SOLIDS, GASES, INDICATORS
from .chem.equipment import EQUIPMENT
from .experiments import EXPERIMENTS, experiment_detail, experiment_list

BASE = Path(__file__).resolve().parent
DIST = Path(os.environ.get("FRONTEND_DIST", BASE.parent.parent / "frontend" / "dist"))
MAX_BODY = 600_000

app = FastAPI(title="OpenChemistry", version="1.0.0", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(GZipMiddleware, minimum_size=1500)

ALLOWED_AQ = set(IONS) | set(ACIDS) | set(MOLECULES) | {f"ind:{k}" for k in INDICATORS}
ALLOWED_ORG = {"C6H14", "C6H10", "Oil", "C6H10Br2", "C6H10(OH)2", "I2", "Br2"}


def _num(x, lo=0.0, hi=1e4, default=0.0):
    try:
        f = float(x)
    except (TypeError, ValueError):
        return default
    if not math.isfinite(f):
        return default
    return max(lo, min(hi, f))


def _clean_vessel(v: dict, vid: str, depth: int = 0) -> dict | None:
    if not isinstance(v, dict):
        return None
    etype = v.get("type")
    if etype not in sim.EQ or (etype == "utube_arm" and depth == 0):
        return None
    out = sim.new_vessel(etype, vid, _num(v.get("x"), -1e4, 1e4))
    if "y" in v:
        out["y"] = _num(v.get("y"), -1e4, 1e4)
    out["aq"] = {k: _num(n, 0, 100) for k, n in (v.get("aq") or {}).items() if k in ALLOWED_AQ}
    out["org"] = {k: _num(n, 0, 100) for k, n in (v.get("org") or {}).items() if k in ALLOWED_ORG}
    out["vol"] = _num(v.get("vol"), 0, 5000)
    out["org_vol"] = _num(v.get("org_vol"), 0, 5000)
    out["solids"] = {}
    for sid, st in (v.get("solids") or {}).items():
        if sid in SOLIDS and isinstance(st, dict):
            out["solids"][sid] = {"n": _num(st.get("n"), 0, 100), "susp": _num(st.get("susp"), 0, 1)}
    out["gas"] = {g: _num(n, 0, 10) for g, n in (v.get("gas") or {}).items() if g in GASES}
    out["T"] = _num(v.get("T"), -60, 2000, 20.0)
    heat = v.get("heat")
    out["heat"] = heat if heat in ("alcohol", "bunsen", "hotplate", "water_bath", "ice_bath") else None
    for key in ("stopper", "lid", "power", "mirror", "collect"):
        if key in v:
            out[key] = bool(v.get(key))
    for key in ("outlet", "parent", "target", "source"):
        val = v.get(key)
        out[key] = val if isinstance(val, str) and len(val) < 40 else None
    out["stir"] = _num(v.get("stir"), 0, 60)
    out["flow"] = _num(v.get("flow"), 0, 5)
    out["current"] = _num(v.get("current"), 0, 10)
    out["electrode"] = v.get("electrode") if v.get("electrode") in ("C", "Cu") else "C"
    out["seen"] = [s for s in (v.get("seen") or []) if isinstance(s, str)][:300]
    out["prog"] = {k: _num(n, 0, 1e6) for k, n in (v.get("prog") or {}).items() if isinstance(k, str)}
    if isinstance(v.get("_col"), str):
        out["_col"] = v["_col"][:40]
        out["_colt"] = _num(v.get("_colt"), -1e9, 1e9)
    fx = v.get("fx") or {}
    out["fx"] = {k: fx[k] for k in ("steam", "smoke", "smoke_level", "mirror") if k in fx and
                 isinstance(fx[k], (int, float, str))}
    if etype == "utube":
        arms = v.get("arms") or []
        out["arms"] = []
        for i in range(2):
            a = arms[i] if i < len(arms) else {}
            cleaned = _clean_vessel({**a, "type": "utube_arm"}, f"{vid}#{i}", depth + 1)
            out["arms"].append(cleaned or sim.new_vessel("utube_arm", f"{vid}#{i}"))
    return out


def clean_bench(raw) -> dict:
    if not isinstance(raw, dict):
        raw = {}
    vessels = {}
    for vid, v in list((raw.get("vessels") or {}).items())[: sim.MAX_VESSELS]:
        if not isinstance(vid, str) or len(vid) > 32:
            continue
        cv = _clean_vessel(v, vid)
        if cv:
            vessels[vid] = cv
    links = []
    for lk in raw.get("links") or []:
        if isinstance(lk, dict) and lk.get("a") in vessels and lk.get("b") in vessels:
            links.append({"a": lk["a"], "b": lk["b"]})
    return {"vessels": vessels, "t": _num(raw.get("t"), 0, 1e7), "seq": int(_num(raw.get("seq"), 0, 1e6)),
            "links": links[:10]}


@app.get("/api/health")
def health():
    return {"ok": True, "experiments": len(EXPERIMENTS)}


@app.get("/api/catalog")
def catalog():
    return catalog_payload()


@app.get("/api/experiments")
def experiments():
    return experiment_list()


@app.get("/api/experiments/{eid}")
def experiment(eid: str):
    d = experiment_detail(eid)
    if not d:
        raise HTTPException(404, "Nie znaleziono doświadczenia")
    return d


@app.post("/api/step")
async def step(request: Request):
    body = await request.body()
    if len(body) > MAX_BODY:
        raise HTTPException(413, "Za duży stan stołu")
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(400, "Niepoprawny JSON")
    bench = clean_bench(data.get("bench"))
    actions = data.get("actions") or []
    if not isinstance(actions, list):
        actions = []
    actions = [a for a in actions if isinstance(a, dict)][:60]
    n_vessels = max(1, len(bench["vessels"]))
    dt = _num(data.get("dt"), 0, 10)
    budget = 900 / n_vessels  # ograniczenie liczby kroków na żądanie
    dt = min(dt, budget * 0.25)
    try:
        res = sim.step(bench, actions, dt)
    except Exception as ex:  # pragma: no cover - zabezpieczenie przed nieprzewidzianym stanem
        raise HTTPException(400, f"Błąd symulacji: {type(ex).__name__}")
    return JSONResponse(res)


@app.post("/api/setup/{eid}")
def setup(eid: str):
    from .experiments import build_bench
    b = build_bench(eid)
    if b is None:
        raise HTTPException(404, "Nie znaleziono doświadczenia")
    return sim.step(b, [], 0.0)


# ------------------------------------------------------------------ frontend
if DIST.exists():
    assets = DIST / "assets"
    if assets.exists():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):
            raise HTTPException(404)
        f = (DIST / path).resolve()
        if path and f.is_file() and DIST.resolve() in f.parents:
            return FileResponse(f)
        return FileResponse(DIST / "index.html", headers={"Cache-Control": "no-cache"})
