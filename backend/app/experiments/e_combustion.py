from . import Exp, S, V, add, heat, ignite, into, pour, register, source, stir, stop_heat, stopper, test

C = "combustion"


def burn(id, title, level, summary, fuel, amount, jar_gas, expect, theory, eq, jar_fill=(), after=(), heat_t=25,
         src="bunsen", tags=()):
    setup = [V("sp", "spoon", 300, (fuel, amount), label="łyżka do spalań")]
    jar = V("j", "gas_jar", 650, *jar_fill, gas=jar_gas, lid=True) if jar_gas else None
    if jar:
        setup.append(jar)
    steps = [S("Ogrzej łyżkę z substancją w płomieniu palnika.", heat("sp", src), wait=heat_t)]
    if jar:
        steps.append(S("Wprowadź łyżkę do cylindra z gazem.", into("sp", "j"), wait=20))
    else:
        steps.append(S("Obserwuj spalanie w powietrzu.", wait=20))
    steps += list(after)
    return Exp(id, title, C, level, summary, setup, steps, expect, theory=theory, equations=eq, tags=tags)


register(
    burn("cmb-mg-air", "Spalanie magnezu w powietrzu", "podstawowy",
         "Magnez spala się oślepiająco jasnym płomieniem, tworząc biały tlenek.", "Mg", 0.05, None,
         [("ppt", "sp", "MgO"), ("event", "oślepiająco")],
         "Magnez ma duże powinowactwo do tlenu. Spalanie wydziela tyle energii, że powstaje intensywne światło "
         "(dawniej w lampach błyskowych).", ["2Mg + O2 → 2MgO"], tags=("metale",)),
    burn("cmb-mg-o2", "Magnez w tlenie", "podstawowy",
         "Spalanie magnezu w czystym tlenie jest jeszcze gwałtowniejsze.", "Mg", 0.05, "gas_O2",
         [("ppt", "sp", "MgO")], "W czystym tlenie stężenie utleniacza jest prawie 5 razy większe niż w powietrzu, "
                                 "więc reakcja przebiega szybciej.", ["2Mg + O2 → 2MgO"], tags=("tlen",)),
    burn("cmb-fe-o2", "Spalanie żelaza w tlenie", "podstawowy",
         "Rozżarzona wata stalowa spala się w tlenie, rozsypując snopy iskier.", "Fe_wool", 0.3, "gas_O2",
         [("ppt", "sp", "Fe3O4"), ("event", "snopy jasnych iskier")],
         "Żelazo, które w powietrzu jedynie się żarzy, w czystym tlenie spala się z iskrzeniem do Fe₃O₄ "
         "(tlenku żelaza(II,III)).", ["3Fe + 2O2 → Fe3O4"], heat_t=14, tags=("tlen", "metale")),
    burn("cmb-s-o2", "Spalanie siarki – powietrze i tlen", "średni",
         "Siarka pali się w powietrzu słabym niebieskim płomieniem, a w tlenie – jasnym fioletowoniebieskim.",
         "S", 0.1, "gas_O2", [("event", "SO₂"), ("ph", "j", "<", 4)],
         "Produktem spalania siarki jest SO₂ – tlenek kwasowy, który z wodą na dnie cylindra tworzy kwas "
         "siarkowy(IV). To jedna z przyczyn kwaśnych deszczy.", ["S + O2 → SO2", "SO2 + H2O ⇌ H2SO3"],
         jar_fill=(("Water", 20), ("ind_univ", 3)),
         after=(S("Wyjmij łyżkę, przykryj cylinder i wstrząśnij nim.", into("sp", None), stir("j", 10), wait=20),),
         heat_t=20, tags=("tlen", "kwaśne deszcze")),
    burn("cmb-c-o2", "Spalanie węgla w tlenie", "podstawowy",
         "Rozżarzony węgiel drzewny jaśnieje w tlenie; produkt mętni wodę wapienną.", "C", 0.3, "gas_O2",
         [("event", "węgiel drzewny"), ("ppt", "j", "CaCO3")],
         "Węgiel spala się do CO₂, który wykrywamy wodą wapienną.", ["C + O2 → CO2", "CO2 + Ca(OH)2 → CaCO3↓ + H2O"],
         jar_fill=(("LimeWater", 20),),
         after=(S("Wyjmij łyżkę i wstrząśnij cylindrem z wodą wapienną.", into("sp", None), stir("j", 30),
                  wait=40),), heat_t=30, tags=("tlen", "CO2")),
    burn("cmb-p-o2", "Spalanie fosforu", "średni",
         "Fosfor spala się w tlenie, tworząc gęsty biały dym P₄O₁₀, który z wodą daje kwas.", "P", 0.1, "gas_O2",
         [("event", "biały dym"), ("ph", "j", "<", 3)],
         "Tlenek fosforu(V) jest silnie higroskopijny – z wodą tworzy kwas fosforowy(V).",
         ["4P + 5O2 → P4O10", "P4O10 + 6H2O → 4H3PO4"], jar_fill=(("Water", 20), ("ind_univ", 3)),
         after=(S("Wstrząśnij cylindrem.", into("sp", None), stir("j", 10), wait=20),), heat_t=15,
         tags=("tlen", "tlenki kwasowe")),
    burn("cmb-na-cl2", "Sód w chlorze", "rozszerzony",
         "Rozgrzany sód spala się w chlorze żółtym płomieniem, tworząc biały dym chlorku sodu.", "Na", 0.1,
         "gas_Cl2", [("event", "chlorze"), ("ppt", "j", "NaCl_smoke")],
         "Synteza soli kuchennej z pierwiastków: metalu, który gwałtownie reaguje z wodą, i trującego gazu.",
         ["2Na + Cl2 → 2NaCl"], heat_t=10, tags=("chlor", "metale")),
    burn("cmb-fe-cl2", "Żelazo w chlorze", "rozszerzony",
         "Rozżarzona wata stalowa spala się w chlorze z wydzieleniem brunatnego dymu FeCl₃.", "Fe_wool", 0.3,
         "gas_Cl2", [("ppt", "j", "FeCl3_smoke")],
         "Chlor jako silny utleniacz utlenia żelazo od razu do stopnia +III.", ["2Fe + 3Cl2 → 2FeCl3"],
         heat_t=15, tags=("chlor",)),
    burn("cmb-mg-co2", "Magnez pali się w CO₂", "rozszerzony",
         "Płonący magnez nie gaśnie w tlenku węgla(IV) – odbiera mu tlen!", "Mg", 0.05, "gas_CO2",
         [("ppt", "sp", "C_char"), ("event", "CO₂")],
         "Magnez ma tak duże powinowactwo do tlenu, że redukuje CO₂ do węgla. Dlatego płonącego magnezu nie "
         "wolno gasić gaśnicą śniegową.", ["2Mg + CO2 → 2MgO + C"], heat_t=30, tags=("metale",)),
    Exp("cmb-candle-jar", "Świeca pod szklanym cylindrem", C, "podstawowy",
        "Świeca w zamkniętym naczyniu gaśnie po zużyciu części tlenu; powstaje CO₂.",
        [V("c", "candle", 300), V("j", "gas_jar", 650, lid=True)],
        [S("Zapal świecę.", ignite("c"), wait=4),
         S("Wstaw świecę do cylindra i zamknij go.", into("c", "j"), wait=40),
         S("Wlej do cylindra wodę wapienną i wstrząśnij.", into("c", None), add("j", "LimeWater", 20),
           stir("j", 30), wait=40)],
        [("gas", "j", "O2", "<", 0.18), ("ppt", "j", "CaCO3")],
        theory="Świeca gaśnie, gdy zawartość tlenu spadnie do ok. 16%. Produkty spalania parafiny to CO₂ i woda.",
        equations=["C25H52 + 38O2 → 25CO2 + 26H2O"], tags=("spalanie", "tlen")),
    Exp("cmb-air-oxygen", "Zawartość tlenu w powietrzu", C, "średni",
        "Fosfor spala się w zamkniętej kolbie, a po ostygnięciu woda wpływa i zajmuje ok. 1/5 objętości.",
        [V("f", "round_flask", 350, ("P", 0.15), stopper=True), V("b", "beaker_600", 700, ("Water", 400))],
        [S("Podpal fosfor w szczelnie zamkniętej kolbie.", ignite("f"), wait=200),
         S("Poczekaj, aż kolba ostygnie, i zanurz rurkę w zlewce z wodą (otwórz zacisk).", source("f", "b"),
           wait=60)],
        [("vol", "f", ">", 35), ("vol", "f", "<", 60)],
        theory="Fosfor zużywa tlen z powietrza w kolbie, a stały P₄O₁₀ rozpuszcza się w wodzie. Ubytek gazu "
               "wynosi ok. 21% objętości – tyle tlenu zawiera powietrze.", equations=["4P + 5O2 → P4O10"],
        tags=("powietrze",)),
    Exp("cmb-na-air", "Spalanie sodu w powietrzu", C, "średni",
        "Sód po stopieniu spala się intensywnie żółtym płomieniem.",
        [V("sp", "crucible", None, ("Na", 0.1))],
        [S("Ogrzewaj tygiel z sodem w płomieniu.", heat("sp", "alcohol"), wait=20),
         S("Zdejmij z palnika i obserwuj.", stop_heat("sp"), wait=10)],
        [("ppt", "sp", "Na2O2"), ("event", "żółtym płomieniem")],
        theory="Przy spalaniu sodu w nadmiarze tlenu powstaje głównie nadtlenek sodu Na₂O₂.",
        equations=["2Na + O2 → Na2O2"], tags=("metale",)),
)
