# OpenChemistry – wirtualne laboratorium chemiczne

Darmowe, rozbudowane laboratorium chemiczne w przeglądarce: **199 gotowych doświadczeń** w 14 działach,
**188 odczynników**, 20 rodzajów sprzętu i tryb swobodnego eksperymentowania. Bez logowania, bez reklam.

**Na żywo:** https://redzikowski.com/chemia/

## Co odróżnia je od innych symulatorów

Wyniki nie są nagranymi animacjami – liczy je prawdziwy silnik chemiczny w Pythonie:

- **pH z bilansu ładunku** – jony H⁺/OH⁻ nie są „przechowywane”, tylko wynikają z równowag wszystkich układów
  kwasowo-zasadowych (węglany, amoniak, fosforany, octany, siarczany(IV), siarczki, szczawiany, chromiany…).
  Dzięki temu mieszanie dowolnych roztworów daje poprawne pH, a krzywe miareczkowania mają realny kształt.
- **Kompleksy** – [Cu(NH₃)₄]²⁺, [Ag(NH₃)₂]⁺, [Al(OH)₄]⁻, [Zn(OH)₄]²⁻, [Fe(SCN)]²⁺, [CoCl₄]²⁻ (zależny od temperatury),
  kompleks biuretowy, jod ze skrobią, hydroliza kationów Fe³⁺, Al³⁺, Cu²⁺…
- **Strącanie i rozpuszczanie osadów z iloczynów rozpuszczalności** (ok. 60 osadów, m.in. przemiana AgCl → AgI,
  rozpuszczanie wodorotlenków amfoterycznych, klarowanie wody wapiennej nadmiarem CO₂), krystalizacja soli
  z krzywych rozpuszczalności (KNO₃, ałun, „złoty deszcz” PbI₂).
- **Kinetyka** – metale z kwasami, wodą i zasadami, wypieranie metali z soli wg potencjałów standardowych,
  pasywacja, redoks KMnO₄ (zależnie od odczynu), K₂Cr₂O₇, fluorowce, zegar jodowy, autokataliza, rozkłady termiczne,
  spalanie w tlenie/powietrzu/chlorze, próby Fehlinga, Tollensa, biuretowa, ksantoproteinowa, estryfikacja,
  zmydlanie, denaturacja białek…
- **Gazy** – wymiana ciecz–gaz z prawa Henry’ego, przestrzeń nad cieczą, rurki odprowadzające, zbieranie gazów,
  fontanna amoniakalna, testy łuczywem i papierkami.
- **Ciepło** – entalpie reakcji i rozpuszczania, ciepło zobojętniania i rozcieńczania H₂SO₄, palniki, łaźnie,
  wrzenie i odparowanie do sucha, destylacja.
- **Elektrochemia** – elektroliza w rurce U (prąd z przewodnictwa roztworu, migracja jonów, zmiany pH przy
  elektrodach), ogniwa z równaniem Nernsta, tester przewodnictwa.
- **Barwy z prawa Lamberta-Beera** – intensywność zależy od stężenia i grubości warstwy.

Każde doświadczenie ma automatyczny test (`backend/tests`), który wykonuje wszystkie kroki na silniku
i sprawdza, czy zachodzi opisana obserwacja.

## Technologia

- **Backend:** Python 3.13, FastAPI – silnik w `backend/app/chem`, biblioteka doświadczeń w `backend/app/experiments`.
  Serwer jest bezstanowy: przeglądarka przesyła stan stołu, serwer wykonuje akcje i symuluje upływ czasu.
- **Frontend:** React 18 + TypeScript + Vite + Zustand, grafika naczyń w SVG.

## Uruchomienie lokalne

```bash
cd backend && pip install -r requirements-dev.txt && python -m uvicorn app.main:app --port 8010
```

```bash
cd frontend && npm install && npm run dev
```

Testy: `cd backend && pytest -q`

## Wdrożenie

Push na `main` → GitHub Actions uruchamia testy i wysyła archiwum przez SSH na serwer, gdzie budowany jest
obraz Dockera (`Dockerfile`, `compose.yml`), a proxy nginx (`deploy/nginx.conf`) wystawia aplikację pod `/chemia/`.

---

Pomysł i wykonanie: **Adam Rędzikowski** · [redzikowski.com](https://redzikowski.com) ·
[postaw kawę](https://buycoffee.to/adamredzikowski)
