import { useEffect } from 'react'
import { ArrowRightLeft, Flame, FlaskConical, MousePointerClick, Play, TestTube2, X } from 'lucide-react'
import { useLab } from '../store'

const WELCOME_KEY = 'openchemistry.welcome.v1'

export function welcomeSeen(): boolean {
  try {
    return localStorage.getItem(WELCOME_KEY) === '1'
  } catch {
    return false
  }
}

function markSeen() {
  try {
    localStorage.setItem(WELCOME_KEY, '1')
  } catch {
    /* brak dostępu do localStorage */
  }
}

const STEPS = [
  { icon: <FlaskConical size={18} />, title: 'Weź odczynnik z półki', text: 'Przeciągnij go na naczynie albo kliknij odczynnik, a potem naczynie. Wybierzesz ilość w okienku.' },
  { icon: <ArrowRightLeft size={18} />, title: 'Przelewaj i łącz', text: 'Przeciągnij naczynie na inne, aby przelać. Rurką odprowadzającą poprowadzisz gaz do drugiego naczynia.' },
  { icon: <MousePointerClick size={18} />, title: 'Prawy przycisk = menu', text: 'Kliknij naczynie prawym przyciskiem (na telefonie przytrzymaj), by ogrzać, zbadać, zatkać korkiem lub opróżnić.' },
  { icon: <Flame size={18} />, title: 'Ogrzewaj i czekaj', text: 'Reakcje biegną w czasie. Przyspiesz je przyciskami ×2…×20 na górnym pasku albo zatrzymaj pauzą.' },
  { icon: <TestTube2 size={18} />, title: 'Badaj i notuj', text: 'Łuczywo, papierki, pH-metr, próba płomieniowa. Każda obserwacja trafia do dziennika w prawym panelu.' },
]

export default function Welcome() {
  const open = useLab((s) => s.welcome)
  const experiment = useLab((s) => s.experiment)

  useEffect(() => {
    if (!open) return
    const key = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', key)
    return () => window.removeEventListener('keydown', key)
  }, [open])

  if (!open) return null
  function close() {
    markSeen()
    useLab.getState().setWelcome(false)
  }
  return (
    <div className="modal-veil" onPointerDown={close}>
      <div className="modal welcome" onPointerDown={(e) => e.stopPropagation()} role="dialog" aria-modal="true" aria-labelledby="welcome-title">
        <div className="modal-head">
          <h3 id="welcome-title">Witaj w laboratorium</h3>
          <button className="icon-only" onClick={close} aria-label="Zamknij"><X size={16} /></button>
        </div>
        <div className="modal-body">
          <p className="welcome-lead">
            {experiment
              ? <>Prowadzi Cię przewodnik w prawym panelu. Wykonuj kroki sam albo kliknij <b>Wykonaj ten krok</b> – zobaczysz, jak to zrobić.</>
              : <>To swobodny stół laboratoryjny: wszystko reaguje ze wszystkim według prawdziwej chemii. Eksperymentuj śmiało – tu nic nie wybuchnie naprawdę.</>}
          </p>
          <ol className="welcome-steps">
            {STEPS.map((s) => (
              <li key={s.title}>
                <span className="ws-icon">{s.icon}</span>
                <div><b>{s.title}</b><p>{s.text}</p></div>
              </li>
            ))}
          </ol>
          <p className="note">Instrukcję otworzysz ponownie przyciskiem <b>?</b> na górnym pasku.</p>
        </div>
        <div className="modal-foot">
          <button className="primary" onClick={close} autoFocus><Play size={15} /> Zaczynamy</button>
        </div>
      </div>
    </div>
  )
}
