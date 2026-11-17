from app.chem.reagents import REAGENTS
from app.chem.sim import step


def test_stock_solutions_are_clear():
    """Roztwory z półki nie mogą same z siebie wytrącać osadów."""
    bad = []
    for rid, r in REAGENTS.items():
        if r.kind != "solution":
            continue
        b = {"vessels": {}}
        res = step(b, [{"op": "add_vessel", "etype": "beaker_100", "id": "b"},
                       {"op": "reagent", "v": "b", "reagent": rid, "amount": 20}], 2.0)
        sol = [s["id"] for s in res["views"]["b"]["solids"] if s["mass"] > 1e-4]
        if sol:
            bad.append((rid, sol))
    assert not bad, bad
