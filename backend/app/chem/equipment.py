"""Sprzęt laboratoryjny: pojemności, parametry cieplne, kształt (wykorzystywany przez front do rysowania)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Equipment:
    id: str
    name: str
    group: str
    cap: float  # pojemność [mL]
    diam: float  # średnica / droga optyczna [cm]
    glass: float  # masa szkła [g]
    hA: float  # współczynnik strat ciepła [W/K]
    g: float  # sprzężenie z płomieniem [W/K]
    heatable: bool = True
    kind: str = "vessel"  # vessel, jar, burette, spoon, utube, funnel, trough, candle, fountain, crucible
    mouth: float = 1.0  # względna wymiana gazów z otoczeniem
    closed: bool = False  # domyślnie zamknięty (pokrywka)
    desc: str = ""


EQUIPMENT: dict[str, Equipment] = {e.id: e for e in [
    Equipment("test_tube", "Probówka", "Naczynia", 20, 1.6, 12, 0.12, 0.12, mouth=0.25,
              desc="Do reakcji w małej skali. Można ogrzewać bezpośrednio w płomieniu."),
    Equipment("boiling_tube", "Probówka duża", "Naczynia", 40, 2.4, 20, 0.16, 0.14, mouth=0.35),
    Equipment("beaker_100", "Zlewka 100 mL", "Naczynia", 100, 5.0, 50, 0.45, 0.25, mouth=1.0),
    Equipment("beaker_250", "Zlewka 250 mL", "Naczynia", 250, 7.0, 100, 0.65, 0.35, mouth=1.4),
    Equipment("beaker_600", "Zlewka 600 mL", "Naczynia", 600, 9.0, 190, 0.95, 0.45, mouth=2.0),
    Equipment("flask_250", "Kolba stożkowa 250 mL", "Naczynia", 250, 6.0, 110, 0.6, 0.33, mouth=0.4,
              desc="Kolba Erlenmeyera – do miareczkowania i otrzymywania gazów."),
    Equipment("round_flask", "Kolba okrągłodenna 250 mL", "Naczynia", 250, 7.0, 120, 0.6, 0.35, mouth=0.35),
    Equipment("cylinder_100", "Cylinder miarowy 100 mL", "Naczynia", 100, 3.0, 90, 0.4, 0.0, heatable=False,
              mouth=0.4),
    Equipment("gas_jar", "Cylinder na gazy", "Gazy", 250, 5.5, 160, 0.5, 0.0, heatable=False, kind="jar",
              mouth=1.0, closed=True, desc="Szklany cylinder z pokrywką – do zbierania gazów i spalania w nich."),
    Equipment("evap_dish", "Parownica", "Naczynia", 60, 8.0, 60, 0.7, 0.4, mouth=3.0,
              desc="Do odparowywania roztworów i krystalizacji."),
    Equipment("crucible", "Tygiel porcelanowy", "Naczynia", 15, 3.2, 30, 0.12, 0.30, kind="crucible", mouth=1.0,
              desc="Do prażenia substancji stałych w wysokiej temperaturze."),
    Equipment("trough", "Krystalizator z wodą", "Naczynia", 1000, 15.0, 400, 1.8, 0.0, heatable=False,
              kind="trough", mouth=4.0, desc="Szerokie naczynie – do reakcji metali alkalicznych z wodą."),
    Equipment("watch_glass", "Szkiełko zegarkowe", "Naczynia", 5, 5.0, 15, 0.3, 0.0, heatable=False, mouth=4.0),
    Equipment("petri", "Szalka Petriego", "Naczynia", 40, 9.0, 40, 0.6, 0.0, heatable=False, mouth=4.0),
    Equipment("burette", "Biureta 50 mL", "Miareczkowanie", 50, 1.1, 60, 0.2, 0.0, heatable=False, kind="burette",
              mouth=0.1, desc="Ustaw nad naczyniem i otwórz kurek, aby dozować titrant."),
    Equipment("utube", "Elektrolizer (rurka U)", "Elektrochemia", 60, 1.8, 80, 0.3, 0.0, heatable=False,
              kind="utube", mouth=0.2, desc="Dwie elektrody grafitowe i zasilacz 6 V."),
    Equipment("spoon", "Łyżka do spalań", "Spalanie", 3, 1.5, 15, 0.05, 0.40, kind="spoon", mouth=3.0,
              desc="Ogrzej zawartość w płomieniu, a potem wprowadź do cylindra z gazem."),
    Equipment("candle", "Świeca", "Spalanie", 0, 2.0, 0, 0.05, 0.0, heatable=False, kind="candle", mouth=3.0),
    Equipment("funnel", "Lejek z sączkiem", "Rozdzielanie", 0, 6.0, 40, 0.3, 0.0, heatable=False, kind="funnel",
              desc="Ustaw nad naczyniem i wlej mieszaninę – osad zostanie na sączku."),
    Equipment("fountain", "Kolba do fontanny", "Gazy", 250, 7.0, 130, 0.5, 0.0, heatable=False, kind="fountain",
              mouth=0.0, closed=True, desc="Zamknięta kolba z rurką zanurzoną w zlewce poniżej."),
]}
