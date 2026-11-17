from . import Exp, S, V, add, heat, register, stir, stop_heat, stopper, test

C = "gases"


def gen(id, title, level, summary, fill_gen, add_steps, target_kind, expect, theory, eq, gen_type="flask_250",
        target_fill=(), collect=True, tests=(), heat_src=None, wait=30, tags=(), safety=""):
    setup = [V("g", gen_type, 300, *fill_gen, stopper=True, outlet="r", label="generator"),
             V("r", target_kind, 650, *target_fill, collect=collect, lid=collect or None, label="odbieralnik")]
    steps = [S(add_steps[0], *add_steps[1:], wait=2)]
    if heat_src:
        steps.append(S("Ogrzewaj mieszaninę w generatorze.", heat("g", heat_src), wait=wait))
    else:
        steps.append(S("Odczekaj, aż gaz wypełni odbieralnik.", wait=wait))
    if tests:
        steps.append(S("Zbadaj zebrany gaz.", *[test("r", t) for t in tests], wait=1))
    return Exp(id, title, C, level, summary, setup, steps, expect, theory=theory, equations=eq, tags=tags,
               safety=safety)


register(
    gen("gas-o2-h2o2", "Tlen z nadtlenku wodoru (katalizator MnO₂)", "podstawowy",
        "Rozkład wody utlenionej z MnO₂, zbieranie tlenu i próba żarzącym się łuczywem.",
        [("H2O2_3", 60)], ["Wsyp do kolby szczyptę MnO₂ (katalizator).", add("g", "MnO2", 0.5)], "gas_jar",
        [("gas", "r", "O2", ">", 0.6), ("event", "rozżarza się")],
        "Tlenek manganu(IV) katalizuje rozkład nadtlenku wodoru. Tlen podtrzymuje palenie – żarzące się łuczywo "
        "rozpala się w nim jasnym płomieniem. Gaz zbierany jest w cylindrze wypełnionym wodą (metodą wypierania "
        "wody).", ["2H2O2 → 2H2O + O2↑ (MnO2)"], tests=("glowing_splint",), wait=40, tags=("tlen", "kataliza")),
    gen("gas-o2-kmno4", "Tlen z prażenia manganianu(VII) potasu", "średni",
        "Ogrzewanie KMnO₄ w probówce i zbieranie tlenu metodą wypierania wody.",
        [("KMnO4_s", 3)], ["Sprawdź szczelność zestawu i zamknij probówkę korkiem z rurką.", stopper("g")],
        "gas_jar", [("gas", "r", "O2", ">", 0.5), ("ppt", "g", "MnO2"), ("event", "rozżarza się")],
        "Manganian(VII) potasu rozkłada się po ogrzaniu powyżej ok. 220 °C. Pierwsze porcje gazu to powietrze "
        "z probówki, dlatego zbiera się gaz po chwili.", ["2KMnO4 → K2MnO4 + MnO2 + O2↑"], gen_type="test_tube",
        heat_src="bunsen", tests=("glowing_splint",), wait=40, tags=("tlen", "rozkład termiczny")),
    gen("gas-o2-kclo3", "Tlen z chloranu(V) potasu z katalizatorem", "rozszerzony",
        "Chloran(V) potasu z MnO₂ rozkłada się w niższej temperaturze, wydzielając tlen.",
        [("KClO3_s", 1.5), ("MnO2", 0.3)], ["Wymieszaj KClO₃ z MnO₂.", stir("g")], "gas_jar",
        [("gas", "r", "O2", ">", 0.5), ("event", "katalizator")],
        "Katalizator MnO₂ obniża temperaturę rozkładu KClO₃ z ok. 400 °C do ok. 200 °C.",
        ["2KClO3 → 2KCl + 3O2↑ (MnO2, t)"], gen_type="test_tube", heat_src="bunsen", tests=("glowing_splint",),
        wait=40, tags=("tlen", "kataliza"), safety="KClO₃ z substancjami organicznymi tworzy mieszaniny wybuchowe."),
    gen("gas-h2-zn", "Otrzymywanie i badanie wodoru", "podstawowy",
        "Cynk z kwasem solnym w kolbie, zbieranie wodoru i próba płonącym łuczywem.",
        [("HCl_2", 50)], ["Wrzuć do kolby granulki cynku.", add("g", "Zn", 3.0)], "gas_jar",
        [("gas", "r", "H2", ">", 0.5), ("event", "wodór")],
        "Wodór jest najlżejszym gazem. Czysty spala się spokojnie, a z powietrzem tworzy mieszaninę piorunującą "
        "– stąd pyknięcie.", ["Zn + 2HCl → ZnCl2 + H2↑", "2H2 + O2 → 2H2O"], tests=("burning_splint",), wait=60,
        tags=("wodór",)),
    gen("gas-co2-limewater", "Tlenek węgla(IV) i woda wapienna", "podstawowy",
        "CO₂ z marmuru i kwasu solnego przepuszczany przez wodę wapienną – najpierw zmętnienie, potem klarowanie.",
        [("HCl_2", 40)], ["Wrzuć kawałki marmuru do kolby.", add("g", "Marble", 6)], "test_tube",
        [("event", "CaCO3"), ("event", "rozpuszcza")],
        "CO₂ tworzy z Ca(OH)₂ nierozpuszczalny CaCO₃ (zmętnienie). Nadmiar CO₂ przekształca go w rozpuszczalny "
        "Ca(HCO₃)₂ – roztwór się klaruje. Tak powstają też jaskinie krasowe.",
        ["CaCO3 + 2HCl → CaCl2 + H2O + CO2↑", "Ca(OH)2 + CO2 → CaCO3↓ + H2O",
         "CaCO3 + CO2 + H2O → Ca(HCO3)2"], target_fill=(("LimeWater", 5), ("Water", 5)), collect=False, wait=360,
        tags=("CO2", "woda wapienna")),
    gen("gas-co2-extinguish", "CO₂ nie podtrzymuje palenia", "podstawowy",
        "Cylinder napełniony dwutlenkiem węgla gasi płonące łuczywo.",
        [("HCl_2", 40)], ["Wrzuć kawałki marmuru do kolby.", add("g", "Marble", 6)], "gas_jar",
        [("gas", "r", "CO2", ">", 0.6), ("event", "gaśnie")],
        "CO₂ nie pali się i nie podtrzymuje palenia, a jest cięższy od powietrza – dlatego stosuje się go w "
        "gaśnicach.", ["CaCO3 + 2HCl → CaCl2 + H2O + CO2↑"], tests=("burning_splint", "gas_litmus"), wait=90,
        tags=("CO2",)),
    gen("gas-nh3", "Otrzymywanie amoniaku", "średni",
        "Ogrzewanie soli amonowej z zasadą – wilgotny papierek lakmusowy niebieszczeje.",
        [("NH4Cl_1", 10), ("NaOH_2", 10)], ["Wymieszaj roztwory w probówce.", stir("g")], "gas_jar",
        [("event", "niebiesko"), ("gas", "r", "NH3", ">", 0.01)],
        "Mocna zasada wypiera słabą – amoniak – z jej soli. Po ogrzaniu amoniak (bardzo dobrze rozpuszczalny w "
        "wodzie) uchodzi z roztworu. Zbiera się go w odwróconym naczyniu, bo jest lżejszy od powietrza.",
        ["NH4Cl + NaOH → NaCl + NH3↑ + H2O"], gen_type="boiling_tube", heat_src="bunsen",
        tests=("gas_litmus", "smell"), wait=50, tags=("amoniak",)),
    Exp("gas-nh3-hcl", "Amoniak i chlorowodór – biały dym", C, "średni",
        "Amoniak wprowadzony do cylindra z chlorowodorem tworzy gęsty biały dym NH₄Cl.",
        [V("g", "boiling_tube", 300, ("NH4Cl_1", 10), ("NaOH_2", 10), stopper=True, outlet="r"),
         V("r", "gas_jar", 650, gas="gas_HCl", lid=True, collect=True)],
        [S("Ogrzewaj probówkę z mieszaniną soli amonowej i zasady.", heat("g", "bunsen"), wait=50)],
        [("ppt", "r", "NH4Cl"), ("event", "biały dym")],
        theory="Dwa bezbarwne gazy reagują ze sobą, tworząc stały chlorek amonu – widoczny jako biały dym.",
        equations=["NH3 + HCl → NH4Cl"], tags=("amoniak",)),
    gen("gas-cl2", "Otrzymywanie chloru", "rozszerzony",
        "KMnO₄ ze stężonym kwasem solnym wydziela chlor, który odbarwia wilgotne papierki.",
        [("KMnO4_s", 1.0)], ["Wlej stężony kwas solny do kolby.", add("g", "HCl_conc", 15)], "gas_jar",
        [("event", "żółtozielony"), ("event", "odbarwiają")],
        "Chlor to żółtozielony, ciężki, trujący gaz o właściwościach wybielających (w wilgotnym środowisku tworzy "
        "HClO).", ["2KMnO4 + 16HCl → 2KCl + 2MnCl2 + 5Cl2↑ + 8H2O"], tests=("gas_litmus",), wait=60,
        tags=("chlor",), safety="Chlor jest silnie trujący – tylko pod dygestorium!"),
    gen("gas-so2-kmno4", "SO₂ odbarwia manganian(VII) potasu", "średni",
        "Tlenek siarki(IV) z siarczanu(IV) sodu i kwasu przepuszczany przez zakwaszony KMnO₄.",
        [("Na2SO3_05", 20)], ["Dodaj kwas siarkowy(VI) 1 mol/dm³.", add("g", "H2SO4_1", 20)], "test_tube",
        [("tot", "r", "MnO4-", "<", 1e-6), ("event", "odbarwia")],
        "SO₂ ma właściwości redukujące – odbarwia fioletowy roztwór manganianu(VII).",
        ["Na2SO3 + H2SO4 → Na2SO4 + SO2↑ + H2O", "2MnO4^- + 5SO2 + 2H2O → 2Mn^2+ + 5SO4^2- + 4H^+"],
        target_fill=(("KMnO4_0002", 8), ("H2SO4_1", 2)), collect=False, heat_src="alcohol", wait=60,
        tags=("siarka",)),
    gen("gas-h2s-pb", "Siarkowodór i sole ołowiu", "rozszerzony",
        "H₂S przepuszczany przez roztwór soli ołowiu(II) tworzy czarny osad PbS.",
        [("Na2S_01", 20)], ["Dodaj kwas solny.", add("g", "HCl_2", 5)], "test_tube",
        [("ppt", "r", "PbS")],
        "Siarkowodór (zapach zgniłych jaj) to słaby kwas. Z jonami metali ciężkich tworzy czarne siarczki.",
        ["Na2S + 2HCl → 2NaCl + H2S↑", "Pb^2+ + H2S → PbS↓ + 2H^+"], target_fill=(("PbNO3_01", 8),),
        collect=False, heat_src="alcohol", wait=40, tags=("siarka",), safety="H₂S jest trujący."),
    gen("gas-no2", "Tlenek azotu(IV)", "rozszerzony",
        "Brunatny NO₂ z reakcji miedzi ze stężonym kwasem azotowym(V).",
        [("HNO3_conc", 8)], ["Wrzuć do kolby miedź.", add("g", "Cu", 1.0)], "gas_jar",
        [("gas", "r", "NO2", ">", 0.1)],
        "NO₂ to brunatny, trujący gaz. W wodzie tworzy kwas azotowy(V) i NO – jeden ze składników kwaśnych "
        "deszczów.", ["Cu + 4HNO3 → Cu(NO3)2 + 2NO2↑ + 2H2O"], tests=("gas_litmus",), wait=40, tags=("azot",)),
    gen("gas-acetylene", "Etyn (acetylen) z karbidu", "średni",
        "Karbid reaguje z wodą, wydzielając etyn, który spala się kopcącym płomieniem.",
        [("Water", 50)], ["Wrzuć karbid do kolby.", add("g", "CaC2", 1.5)], "gas_jar",
        [("gas", "g", "C2H2", ">", 0.4), ("event", "kopcącym")],
        "Etyn to węglowodór nienasycony z wiązaniem potrójnym. Ze względu na dużą zawartość węgla spala się "
        "jasnym, kopcącym płomieniem (dawniej w lampach karbidowych).",
        ["CaC2 + 2H2O → C2H2↑ + Ca(OH)2", "2C2H2 + 5O2 → 4CO2 + 2H2O"], tests=("burning_splint",), wait=50,
        tags=("węglowodory",)),
    Exp("gas-co2-btb", "CO₂ zakwasza wodę", C, "podstawowy",
        "Przepuszczanie CO₂ przez wodę z błękitem bromotymolowym zmienia barwę z niebieskiej na żółtą.",
        [V("g", "flask_250", 300, ("HCl_2", 40), stopper=True, outlet="r"),
         V("r", "test_tube", 650, ("Water", 12), ("NaOH_01", 0.05), ("ind_btb", 4))],
        [S("Wrzuć kawałki marmuru do kolby.", add("g", "Marble", 6), wait=2),
         S("Przepuszczaj CO₂ przez roztwór.", wait=90)],
        [("ph", "r", "<", 6.2)],
        theory="CO₂ rozpuszcza się w wodzie, tworząc słaby kwas węglowy – pH spada, a wskaźnik zmienia barwę z "
               "niebieskiej na żółtą.", equations=["CO2 + H2O ⇌ H2CO3 ⇌ H^+ + HCO3^-"], tags=("CO2", "wskaźniki")),
    Exp("gas-air-h2-pop", "Mieszanina piorunująca", C, "średni",
        "Wodór z powietrzem w różnych proporcjach – porównaj odgłos przy zbliżeniu płomienia.",
        [V("j1", "gas_jar", None, gas="gas_H2", lid=True), V("j2", "gas_jar", None, lid=True)],
        [S("Zdejmij pokrywkę z cylindra z wodorem i odczekaj chwilę, aby wymieszał się z powietrzem.",
           stopper("j1", False), wait=20),
         S("Zbliż płonące łuczywo do obu cylindrów.", test("j1", "burning_splint"), test("j2", "burning_splint"))],
        [("event", "szczeknięcie|pyknięcie"), ("event", "bez zmian")],
        theory="Wodór jest lżejszy od powietrza i szybko ulatuje z otwartego naczynia, mieszając się z powietrzem. "
               "Mieszanina 4–75% H₂ z powietrzem spala się wybuchowo.", equations=["2H2 + O2 → 2H2O"],
        tags=("wodór",)),
)
