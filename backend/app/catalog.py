"""Katalog dla interfejsu: sprzęt, odczynniki, narzędzia."""
from __future__ import annotations

from functools import lru_cache

from .chem.data import SOLIDS
from .chem.equipment import EQUIPMENT
from .chem.reagents import REAGENTS

TOOLS = [
    {"id": "alcohol", "name": "Palnik spirytusowy", "group": "Ogrzewanie", "kind": "heat",
     "desc": "Płomień ok. 650 °C. Podstaw pod naczynie, aby ogrzewać."},
    {"id": "bunsen", "name": "Palnik gazowy (Bunsena)", "group": "Ogrzewanie", "kind": "heat",
     "desc": "Gorący płomień ok. 1100 °C – do prażenia i spalania."},
    {"id": "hotplate", "name": "Płyta grzejna", "group": "Ogrzewanie", "kind": "heat"},
    {"id": "water_bath", "name": "Łaźnia wodna (80 °C)", "group": "Ogrzewanie", "kind": "heat"},
    {"id": "ice_bath", "name": "Łaźnia lodowa (0 °C)", "group": "Ogrzewanie", "kind": "heat"},
    {"id": "stir", "name": "Bagietka (mieszanie)", "group": "Mieszanie", "kind": "action"},
    {"id": "shake", "name": "Wstrząśnij", "group": "Mieszanie", "kind": "action"},
    {"id": "glowing_splint", "name": "Żarzące się łuczywo", "group": "Testy", "kind": "test",
     "desc": "Rozżarza się w tlenie."},
    {"id": "burning_splint", "name": "Płonące łuczywo", "group": "Testy", "kind": "test",
     "desc": "Test na wodór (pyknięcie) i gazy niepodtrzymujące palenia."},
    {"id": "gas_litmus", "name": "Wilgotne papierki lakmusowe (gaz)", "group": "Testy", "kind": "test"},
    {"id": "litmus_red", "name": "Czerwony papierek lakmusowy", "group": "Testy", "kind": "test"},
    {"id": "litmus_blue", "name": "Niebieski papierek lakmusowy", "group": "Testy", "kind": "test"},
    {"id": "univ_paper", "name": "Papierek uniwersalny", "group": "Testy", "kind": "test"},
    {"id": "flame_test", "name": "Drucik do prób płomieniowych", "group": "Testy", "kind": "test"},
    {"id": "cobalt_glass", "name": "Próba płomieniowa przez szkło kobaltowe", "group": "Testy", "kind": "test"},
    {"id": "smell", "name": "Zbadaj zapach (ostrożnie)", "group": "Testy", "kind": "test"},
    {"id": "conductivity", "name": "Tester przewodnictwa (żarówka)", "group": "Pomiary", "kind": "test"},
    {"id": "thermometer", "name": "Termometr", "group": "Pomiary", "kind": "test"},
    {"id": "ph_meter", "name": "pH-metr", "group": "Pomiary", "kind": "test"},
    {"id": "ignite", "name": "Zapałka / podpalenie", "group": "Ogrzewanie", "kind": "action"},
]

HAZARDS = {
    "corr": "żrący", "tox": "toksyczny", "ox": "utleniający", "flam": "łatwopalny", "irr": "drażniący",
    "env": "niebezpieczny dla środowiska",
}


@lru_cache(maxsize=1)
def catalog_payload():
    eq = [{"id": e.id, "name": e.name, "group": e.group, "cap": e.cap, "kind": e.kind, "heatable": e.heatable,
           "desc": e.desc, "diam": e.diam} for e in EQUIPMENT.values()]
    reagents = []
    for r in REAGENTS.values():
        item = {"id": r.id, "name": r.name, "group": r.group, "kind": r.kind, "formula": r.formula,
                "hazards": list(r.hazards), "unit": r.unit, "presets": list(r.presets), "note": r.note}
        if r.kind == "solid":
            sid = next(iter(r.comp))
            s = SOLIDS[sid]
            item["color"] = s.color
            item["style"] = s.style
            item["piece"] = r.piece
        reagents.append(item)
    return {"equipment": eq, "reagents": reagents, "tools": TOOLS, "hazards": HAZARDS}
