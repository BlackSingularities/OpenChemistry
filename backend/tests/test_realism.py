"""Realizm „wszystko ze wszystkim”: macierz kation × anion porównana z tablicą rozpuszczalności.

Każdą parę mieszamy (3 mL + 3 mL) i sprawdzamy, czy osad zawierający dany kation powstaje dokładnie wtedy,
gdy powinien. Pary, w których wynik zależy od szczegółów (np. redoks), pomijamy jawnie.
"""
import pytest

from app.chem import sim
from app.chem.data import SOLIDS

CATIONS = {
    "Ag+": "AgNO3_01", "Pb2+": "PbNO3_01", "Ba2+": "BaCl2_01", "Ca2+": "CaCl2_05", "Cu2+": "CuSO4_05",
    "Fe3+": "FeCl3_01", "Fe2+": "FeSO4_02", "Zn2+": "ZnSO4_05", "Al3+": "AlCl3_02", "Mg2+": "MgSO4_05",
    "Ni2+": "NiSO4_05", "Co2+": "CoCl2_05", "Mn2+": "MnSO4_05", "K+": "KCl_05", "Sr2+": "SrCl2_05",
}
ANIONS = ["NaCl_1", "KBr_05", "KI_05", "Na2SO4_05", "Na2CO3_1", "Na3PO4_01", "NaOH_01", "NaOH_1", "Na2S_01",
          "K2CrO4_01", "Na2C2O4_005", "KSCN_01", "NaNO3_05", "NaAc_1", "Na2SO3_05", "K4FeCN6_01", "K3FeCN6_01"]

# 1 = powinien wytrącić się osad z tym kationem, 0 = roztwór klarowny, None = pomijamy (redoks, zależy od nadmiaru)
P = {
    "Ag+": dict(NaCl_1=1, KBr_05=1, KI_05=1, Na2SO4_05=1, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=1, Na2S_01=1,
                K2CrO4_01=1, Na2C2O4_005=1, KSCN_01=1, NaNO3_05=0, NaAc_1=None, Na2SO3_05=None, K4FeCN6_01=1,
                K3FeCN6_01=None),
    "Pb2+": dict(NaCl_1=1, KBr_05=1, KI_05=1, Na2SO4_05=1, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=0, Na2S_01=1,
                 K2CrO4_01=1, Na2C2O4_005=1, KSCN_01=0, NaNO3_05=0, NaAc_1=0, Na2SO3_05=1, K4FeCN6_01=None,
                 K3FeCN6_01=None),
    "Ba2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=1, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=0, NaOH_1=0,
                 Na2S_01=0, K2CrO4_01=1, Na2C2O4_005=1, KSCN_01=0, NaNO3_05=0, NaAc_1=0, Na2SO3_05=1),
    "Sr2+": dict(NaCl_1=0, KI_05=0, Na2SO4_05=1, Na2CO3_1=1, NaNO3_05=0, NaAc_1=0, Na2C2O4_005=1),
    "Ca2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=1, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, Na2S_01=None,
                 K2CrO4_01=0, Na2C2O4_005=1, KSCN_01=0, NaNO3_05=0, NaAc_1=0, Na2SO3_05=1),
    "Cu2+": dict(NaCl_1=0, KBr_05=0, KI_05=1, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=1, Na2S_01=1,
                 Na2C2O4_005=1, NaNO3_05=0, NaAc_1=0, K4FeCN6_01=1),
    "Fe3+": dict(NaCl_1=0, KBr_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_1=1, KSCN_01=0, NaNO3_05=0,
                 K4FeCN6_01=1),
    "Fe2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, NaOH_1=1, Na2S_01=1, KSCN_01=0, NaNO3_05=0,
                 K3FeCN6_01=1),
    "Zn2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, Na2S_01=1,
                 Na2C2O4_005=1, KSCN_01=0, NaNO3_05=0, NaAc_1=0, K4FeCN6_01=1),
    "Al3+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, Na2S_01=1,
                 KSCN_01=0, NaNO3_05=0),
    "Mg2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=1, Na2S_01=1,
                 Na2C2O4_005=1, KSCN_01=0, NaNO3_05=0, NaAc_1=0, K2CrO4_01=0),
    "Ni2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=1, Na2S_01=1,
                 KSCN_01=0, NaNO3_05=0, NaAc_1=0),
    "Co2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=1, Na2S_01=1,
                 KSCN_01=0, NaNO3_05=0, NaAc_1=0),
    "Mn2+": dict(NaCl_1=0, KBr_05=0, KI_05=0, Na2SO4_05=0, Na2CO3_1=1, Na3PO4_01=1, NaOH_01=1, NaOH_1=1, Na2S_01=1,
                 KSCN_01=0, NaNO3_05=0, NaAc_1=0),
    "K+": {a: 0 for a in ANIONS},
}

CASES = [(cat, an, exp) for cat, row in P.items() for an, exp in row.items() if exp is not None]


def cation_solids(view, cation):
    import re
    el = re.match(r"[A-Z][a-z]?", cation).group(0)
    out = []
    for s in view["solids"]:
        sd = SOLIDS[s["id"]]
        has = any(sp == cation for sp, _ in sd.comp) or (not sd.comp and re.search(el + r"(?![a-z])", sd.formula))
        if has and s["mass"] > 2e-4:
            out.append(s["id"])
    return out


@pytest.mark.parametrize("cation,anion,expected", CASES, ids=[f"{c}+{a}" for c, a, _ in CASES])
def test_solubility_matrix(cation, anion, expected):
    b = {"vessels": {}}
    r = sim.step(b, [{"op": "add_vessel", "etype": "test_tube", "id": "t"},
                     {"op": "reagent", "v": "t", "reagent": CATIONS[cation], "amount": 3},
                     {"op": "reagent", "v": "t", "reagent": anion, "amount": 3}], 0.0)
    r = sim.step(r["bench"], [], 5.0)
    got = cation_solids(r["views"]["t"], cation)
    if expected:
        assert got, f"{cation} + {anion}: oczekiwano osadu, roztwór jest klarowny"
    else:
        assert not got, f"{cation} + {anion}: nie powinno być osadu, a jest {got}"
