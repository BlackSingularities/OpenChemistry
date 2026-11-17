import { useMemo, useState } from 'react'
import {
  Atom, BatteryCharging, Bolt, Droplet, FlaskConical, Flame, Gem, Hexagon, Leaf, Scale, Search, SearchCheck, Sparkles,
  Thermometer, Wind, ArrowRight, Beaker,
} from 'lucide-react'
import { useLab } from '../store'

const CAT_ICON: Record<string, JSX.Element> = {
  acids: <FlaskConical />, precip: <Droplet />, metals: <Atom />, redox: <Bolt />, gases: <Wind />, combustion: <Flame />,
  electro: <BatteryCharging />, energy: <Thermometer />, equilibrium: <Scale />, solutions: <Gem />, analysis: <SearchCheck />,
  organic: <Hexagon />, bio: <Leaf />, show: <Sparkles />,
}

export const CAT_HUE: Record<string, number> = {
  acids: 330, precip: 200, metals: 30, redox: 270, gases: 175, combustion: 15, electro: 50, energy: 0, equilibrium: 240,
  solutions: 190, analysis: 140, organic: 90, bio: 120, show: 300,
}

const LEVELS = ['podstawowy', 'średni', 'rozszerzony']

export default function Home() {
  const categories = useLab((s) => s.categories)
  const experiments = useLab((s) => s.experiments)
  const catalog = useLab((s) => s.catalog)
  const [q, setQ] = useState('')
  const [cat, setCat] = useState('')
  const [level, setLevel] = useState('')

  const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l')
  const list = useMemo(() => {
    const qq = norm(q)
    return experiments.filter((e) => (!cat || e.cat === cat) && (!level || e.level === level) &&
      (!qq || norm(e.title).includes(qq) || norm(e.summary).includes(qq) || e.tags.some((t) => norm(t).includes(qq))))
  }, [experiments, q, cat, level])

  const catName = (id: string) => categories.find((c) => c.id === id)?.name || id

  return (
    <main className="home">
      <section className="hero">
        <div className="hero-text">
          <h1>Wirtualne laboratorium chemiczne</h1>
          <p>
            Prawdziwy silnik chemiczny liczy pH, równowagi jonowe, iloczyny rozpuszczalności, kinetykę reakcji,
            wydzielanie gazów i ciepło. Wykonuj gotowe doświadczenia krok po kroku albo eksperymentuj swobodnie –
            wszystko za darmo, bez logowania.
          </p>
          <div className="hero-cta">
            <button className="primary big" onClick={() => useLab.getState().openSandbox()}>
              <Beaker size={18} /> Otwórz laboratorium swobodne
            </button>
            <a className="ghost big" href="#katalog">Przeglądaj doświadczenia <ArrowRight size={16} /></a>
          </div>
          <div className="stats">
            <div><b>{experiments.length}</b><span>doświadczeń</span></div>
            <div><b>{catalog?.reagents.length ?? '…'}</b><span>odczynników</span></div>
            <div><b>{catalog?.equipment.length ?? '…'}</b><span>rodzajów sprzętu</span></div>
            <div><b>{categories.length}</b><span>działów</span></div>
          </div>
        </div>
        <HeroArt />
      </section>

      <section className="catalog" id="katalog">
        <div className="catalog-bar">
          <label className="search big">
            <Search size={16} />
            <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Szukaj doświadczenia, np. „miedź”, „pH”, „tlen”…" />
          </label>
          <div className="levels">
            <button className={!level ? 'on' : ''} onClick={() => setLevel('')}>Każdy poziom</button>
            {LEVELS.map((l) => <button key={l} className={level === l ? 'on' : ''} onClick={() => setLevel(l)}>{l[0].toUpperCase() + l.slice(1)}</button>)}
          </div>
        </div>
        <div className="cats">
          <button className={!cat ? 'on' : ''} onClick={() => setCat('')}>Wszystkie <i>{experiments.length}</i></button>
          {categories.map((c) => (
            <button key={c.id} className={cat === c.id ? 'on' : ''} onClick={() => setCat(cat === c.id ? '' : c.id)}
                    style={{ ['--hue' as any]: CAT_HUE[c.id] }}>
              {CAT_ICON[c.id]}{c.name} <i>{c.count}</i>
            </button>
          ))}
        </div>
        <div className="grid">
          {list.map((e) => (
            <button key={e.id} className="card" onClick={() => useLab.getState().openExperiment(e.id)}
                    style={{ ['--hue' as any]: CAT_HUE[e.cat] }}>
              <div className="card-top">
                <span className="card-icon">{CAT_ICON[e.cat]}</span>
                <span className={`level level-${e.level}`}>{e.level}</span>
              </div>
              <h3>{e.title}</h3>
              <p>{e.summary}</p>
              <div className="card-foot">
                <span>{catName(e.cat)}</span>
                <span>{e.steps} {e.steps === 1 ? 'krok' : e.steps < 5 ? 'kroki' : 'kroków'}</span>
              </div>
            </button>
          ))}
          {!list.length && <p className="nothing">Brak doświadczeń spełniających kryteria.</p>}
        </div>
      </section>
    </main>
  )
}

function HeroArt() {
  return (
    <svg className="hero-art" viewBox="0 0 420 320" aria-hidden="true">
      <defs>
        <linearGradient id="hA" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#e0368f" stopOpacity=".9" /><stop offset="1" stopColor="#9d174d" stopOpacity=".95" /></linearGradient>
        <linearGradient id="hB" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#3f63ee" stopOpacity=".85" /><stop offset="1" stopColor="#1e3a8a" stopOpacity=".95" /></linearGradient>
        <linearGradient id="hC" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor="#f2c21b" stopOpacity=".9" /><stop offset="1" stopColor="#b45309" stopOpacity=".95" /></linearGradient>
        <radialGradient id="hGlow"><stop offset="0" stopColor="#5eead4" stopOpacity=".35" /><stop offset="1" stopColor="#5eead4" stopOpacity="0" /></radialGradient>
      </defs>
      <circle cx="210" cy="170" r="160" fill="url(#hGlow)" />
      <rect x="20" y="268" width="380" height="10" rx="5" fill="#1e293b" />
      {/* kolba stożkowa */}
      <g className="float-a">
        <path d="M150,70 h36 v58 l52,112 a12,12 0 0 1 -11,17 h-118 a12,12 0 0 1 -11,-17 l52,-112 z" fill="#ffffff10" stroke="#cbd5e1" strokeOpacity=".7" strokeWidth="2.4" />
        <path d="M125,190 h86 l26,57 a8,8 0 0 1 -7,11 h-124 a8,8 0 0 1 -7,-11 z" fill="url(#hA)" />
        {[0, 1, 2, 3, 4].map((i) => <circle key={i} className="bubble hero-b" cx={150 + i * 9} cy={250} r={2 + (i % 3)} style={{ ['--rise' as any]: '-60px', animationDelay: `${-i * 0.4}s`, animationDuration: '2.2s' }} />)}
      </g>
      {/* probówki */}
      <g className="float-b">
        <path d="M272,100 v130 a14,14 0 0 0 28,0 v-130" fill="#ffffff10" stroke="#cbd5e1" strokeOpacity=".7" strokeWidth="2.2" />
        <path d="M274,170 v60 a12,12 0 0 0 24,0 v-60 z" fill="url(#hB)" />
        <path d="M322,100 v130 a14,14 0 0 0 28,0 v-130" fill="#ffffff10" stroke="#cbd5e1" strokeOpacity=".7" strokeWidth="2.2" />
        <path d="M324,190 v40 a12,12 0 0 0 24,0 v-40 z" fill="url(#hC)" />
        <ellipse cx="336" cy="238" rx="9" ry="4" fill="#f2c21b" />
      </g>
      {/* zlewka */}
      <g className="float-c">
        <path d="M40,160 h80 v90 a10,10 0 0 1 -10,10 h-60 a10,10 0 0 1 -10,-10 z" fill="#ffffff10" stroke="#cbd5e1" strokeOpacity=".7" strokeWidth="2.2" />
        <rect x="42" y="205" width="76" height="53" rx="8" fill="#5aaee8" opacity=".55" />
        <path d="M60,190 c-6,-14 8,-22 0,-38" className="steam" />
        <path d="M84,190 c-6,-14 8,-22 0,-38" className="steam" style={{ animationDelay: '-.8s' }} />
      </g>
    </svg>
  )
}
