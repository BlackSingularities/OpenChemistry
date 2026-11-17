import { useEffect, useState } from 'react'
import { Beaker, CircleHelp, BookOpen, Eye, EyeOff, FlaskConical, Gauge, Home as HomeIcon, Pause, Play, RotateCcw, Shapes, X } from 'lucide-react'
import { useLab } from './store'
import { useDrag } from './dnd'
import Home from './components/Home'
import Bench from './components/Bench'
import Shelf from './components/Shelf'
import ActionBar from './components/ActionBar'
import SidePanel from './components/SidePanel'
import Dialogs from './components/Dialogs'
import ContextMenu from './components/ContextMenu'
import Welcome from './components/Welcome'
import { fmt } from './chem'

const SPEEDS = [1, 2, 5, 10, 20]

export default function App() {
  const mode = useLab((s) => s.mode)
  const toast = useLab((s) => s.toast)
  const init = useLab((s) => s.init)

  useEffect(() => {
    const route = () => {
      const h = decodeURIComponent(location.hash || '')
      const m = h.match(/^#\/doswiadczenie\/(.+)$/)
      const st = useLab.getState()
      if (m) {
        if (st.experiment?.id !== m[1] || st.mode !== 'lab') st.openExperiment(m[1])
      } else if (h.startsWith('#/laboratorium')) {
        if (st.mode !== 'lab' || st.experiment) st.openSandbox()
      }
    }
    init().then(route)
    window.addEventListener('hashchange', route)
    return () => window.removeEventListener('hashchange', route)
  }, [])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => useLab.getState().setToast(null), 4200)
    return () => clearTimeout(t)
  }, [toast])

  return (
    <div className={`app mode-${mode}`}>
      <TopBar />
      {mode === 'home' ? <Home /> : <Lab />}
      <Dialogs />
      {mode === 'lab' && <ContextMenu />}
      {mode === 'lab' && <Welcome />}
      <DragGhost />
      {toast && <div className="toast" onClick={() => useLab.getState().setToast(null)}>{toast}</div>}
      {mode === 'home' && <Footer />}
    </div>
  )
}

function TopBar() {
  const mode = useLab((s) => s.mode)
  const running = useLab((s) => s.running)
  const speed = useLab((s) => s.speed)
  const t = useLab((s) => s.bench.t)
  const experiment = useLab((s) => s.experiment)
  const showReadings = useLab((s) => s.showReadings)
  return (
    <header className="topbar">
      <button className="brand" onClick={() => useLab.getState().goHome()} aria-label="Strona główna">
        <svg width="28" height="28" viewBox="0 0 64 64" aria-hidden="true">
          <path d="M25 10h14v4h-2v12l12 20a5 5 0 0 1-4.3 7.5H19.3A5 5 0 0 1 15 46l12-20V14h-2z" fill="none" stroke="#cbd5e1" strokeWidth="3" strokeLinejoin="round" />
          <path d="M20.5 38h23l4.3 7.4a3 3 0 0 1-2.6 4.6H18.8a3 3 0 0 1-2.6-4.6z" fill="#2dd4bf" />
        </svg>
        <span>Open<b>Chemistry</b></span>
      </button>
      <nav>
        <button className={mode === 'home' ? 'on' : ''} onClick={() => useLab.getState().goHome()}><HomeIcon size={16} /><span>Doświadczenia</span></button>
        <button className={mode === 'lab' && !experiment ? 'on' : ''} onClick={() => useLab.getState().openSandbox()}><Beaker size={16} /><span>Laboratorium</span></button>
        {experiment && mode === 'lab' && <span className="exp-title"><BookOpen size={15} /> {experiment.title}</span>}
      </nav>
      {mode === 'lab' && (
        <div className="sim-ctrl">
          <button className="play" onClick={() => useLab.getState().setRunning(!running)} aria-label={running ? 'Pauza' : 'Start'}>
            {running ? <Pause size={16} /> : <Play size={16} />}
          </button>
          <div className="speeds" title="Tempo upływu czasu">
            <Gauge size={14} />
            {SPEEDS.map((s) => (
              <button key={s} className={speed === s ? 'on' : ''} onClick={() => useLab.getState().setSpeed(s)}>×{s}</button>
            ))}
          </div>
          <span className="clock">{fmtTime(t)}</span>
          <button className="icon-only" onClick={() => useLab.getState().toggleReadings()} title="Pokaż/ukryj odczyty przy naczyniach">
            {showReadings ? <Eye size={16} /> : <EyeOff size={16} />}
          </button>
          <button className="icon-only" onClick={() => useLab.getState().setWelcome(true)} title="Jak korzystać z laboratorium" aria-label="Instrukcja">
            <CircleHelp size={16} />
          </button>
          <button className="icon-only" onClick={() => useLab.getState().resetBench()} title={experiment ? 'Zacznij doświadczenie od nowa' : 'Wyczyść stół'}>
            <RotateCcw size={16} />
          </button>
        </div>
      )}
    </header>
  )
}

function fmtTime(t: number) {
  const m = Math.floor(t / 60)
  const s = Math.floor(t % 60)
  return `${m}:${String(s).padStart(2, '0')}`
}

function Lab() {
  const [shelfOpen, setShelfOpen] = useState(false)
  const [sideOpen, setSideOpen] = useState(false)
  return (
    <main className={`lab${shelfOpen ? ' shelf-open' : ''}${sideOpen ? ' side-open' : ''}`}>
      <Shelf onClose={() => setShelfOpen(false)} />
      <section className="center">
        <Bench />
        <ActionBar />
      </section>
      <SidePanel />
      <div className="mobile-toggles">
        <button onClick={() => { setShelfOpen(!shelfOpen); setSideOpen(false) }} className={shelfOpen ? 'on' : ''}><Shapes size={16} /> Półka</button>
        <button onClick={() => { setSideOpen(!sideOpen); setShelfOpen(false) }} className={sideOpen ? 'on' : ''}><FlaskConical size={16} /> Panel</button>
      </div>
    </main>
  )
}

function DragGhost() {
  const item = useDrag((s) => s.item)
  const x = useDrag((s) => s.x)
  const y = useDrag((s) => s.y)
  if (!item) return null
  return (
    <div className="drag-ghost" style={{ left: x + 12, top: y + 12 }}>
      {item.color && <span className="swatch solid" style={{ background: item.color }} />}
      {item.label}
    </div>
  )
}

function Footer() {
  return (
    <footer className="footer">
      <p>Pomysł i wykonanie: <b>Adam Rędzikowski</b> · <a href="https://redzikowski.com" target="_blank" rel="noopener">redzikowski.com</a></p>
      <p>
        Darmowe i bez reklam. Jeśli laboratorium Ci się przydaje, możesz{' '}
        <a href="https://buycoffee.to/adamredzikowski" target="_blank" rel="noopener">postawić mi kawę</a>.
      </p>
      <p className="small">Symulacja ma charakter edukacyjny – prawdziwe doświadczenia wykonuj tylko pod opieką nauczyciela i z zachowaniem zasad BHP.</p>
    </footer>
  )
}

export { fmt, X }
