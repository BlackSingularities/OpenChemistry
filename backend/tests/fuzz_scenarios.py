"""Losowe scenariusze: 2–4 odczynniki, ogrzewanie, mieszanie, przelewanie, testy, długi czas."""
import math, random, sys, json, traceback
from multiprocessing import Pool
from app.chem.reagents import REAGENTS
from app.chem import sim
from app.chem.data import SOLIDS
from app.chem.equipment import EQUIPMENT

IDS = [r.id for r in REAGENTS.values()]
TYPES = ["test_tube", "boiling_tube", "beaker_100", "beaker_250", "flask_250", "evap_dish", "crucible", "gas_jar", "utube"]
TOOLS = ["glowing_splint", "burning_splint", "gas_litmus", "univ_paper", "flame_test", "smell", "conductivity", "ph_meter"]

def amt(r, rng):
    if r.kind == "indicator": return rng.choice([1, 3, 5])
    if r.kind == "gas": return 1
    return rng.choice(r.presets)

def run(seed):
    rng = random.Random(seed)
    bench = {"vessels": {}}
    log = []
    try:
        t1, t2 = rng.choice(TYPES), rng.choice(["beaker_250", "test_tube", "flask_250"])
        acts = [{"op": "add_vessel", "etype": t1, "id": "a"}, {"op": "add_vessel", "etype": t2, "id": "b"}]
        for _ in range(rng.randint(2, 4)):
            r = REAGENTS[rng.choice(IDS)]
            acts.append({"op": "reagent", "v": "a", "reagent": r.id, "amount": amt(r, rng)})
        acts.append({"op": "reagent", "v": "b", "reagent": rng.choice(IDS), "amount": 5})
        if rng.random() < 0.5:
            acts.append({"op": "heat", "v": "a", "source": rng.choice(["alcohol", "bunsen", "hotplate", "water_bath", "ice_bath"])})
        if rng.random() < 0.3:
            acts.append({"op": "connect", "v": "a", "to": "b"})
        if t1 == "utube":
            acts.append({"op": "power", "v": "a", "on": True})
        log.append(acts)
        r = sim.step(bench, acts, 0.0)
        for i in range(8):
            more = []
            if i == 3:
                more.append({"op": "pour", "from": "b", "to": "a", "ml": 3})
                more.append({"op": "stir", "v": "a", "seconds": 4})
            if i == 5:
                more.append({"op": "test", "v": "a", "tool": rng.choice(TOOLS)})
                more.append({"op": "ignite", "v": "a"})
            r = sim.step(r["bench"], more, 10.0)
        issues = []
        for vid, v in r["bench"]["vessels"].items():
            parts = v.get("arms") or [v]
            for p in parts:
                for k, n in list(p["aq"].items()) + [(s, st["n"]) for s, st in p["solids"].items()] + list(p["gas"].items()):
                    if not math.isfinite(n) or n < -1e-12:
                        issues.append(f"{vid}: bad {k}={n}")
                if not math.isfinite(p["T"]) or p["T"] > 1700 or p["T"] < -40:
                    issues.append(f"{vid}: T={p['T']}")
                cap = EQUIPMENT.get(p["type"]).cap if p["type"] in EQUIPMENT else 1e9
                if p["vol"] + p.get("org_vol", 0) > cap * 1.05 + 1:
                    issues.append(f"{vid}: overflow vol={p['vol']:.1f} cap={cap}")
            vw = r["views"][vid]
            if vw.get("pH") is not None and not (-2.5 <= vw["pH"] <= 16.5):
                issues.append(f"{vid}: pH={vw['pH']}")
        return (seed, issues, log) if issues else None
    except Exception as ex:
        return (seed, ["EXC " + repr(ex) + " | " + " / ".join(traceback.format_exc().splitlines()[-4:])], log)

if __name__ == "__main__":
    n = int(sys.argv[1])
    with Pool(20) as p:
        res = [x for x in p.imap_unordered(run, range(n), chunksize=10) if x]
    json.dump(res, open("scratch/fuzz2.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(n, "scenarios,", len(res), "with issues")
