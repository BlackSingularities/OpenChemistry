import { useEffect, useMemo, useRef } from 'react'
import {
  AlertTriangle, BookOpen, Check, CircleHelp, Eye, FlaskRound, Info, NotebookPen, Pause, Play, RotateCcw, ScrollText,
  Sparkles, TestTubeDiagonal,
} from 'lucide-react'
import { useLab } from '../store'
import { Chem, fmt } from '../chem'
import TitrationChart from './TitrationChart'

export default function SidePanel() {
  const panel = useLab((s) => s.panel)
  const experiment = useLab((s) => s.experiment)
  const setPanel = useLab((s) => s.setPanel)
  const events = useLab((s) => s.events)
  const unread = events.filter((e) => e.kind !== 'color').length
  return (
    <aside className="side">
      <div className="tabs">
        {experiment && (
          <button className={panel === 'guide' ? 'on' : ''} onClick={() => setPanel('guide')}><BookOpen size={15} /> Przewodnik</button>
        )}
        <button className={panel === 'vessel' ? 'on' : ''} onClick={() => setPanel('vessel')}><FlaskRound size={15} /> Naczynie</button>
        <button className={panel === 'journal' ? 'on' : ''} onClick={() => setPanel('journal')}>
          <NotebookPen size={15} /> Obserwacje{unread ? <i className="badge">{unread}</i> : null}
        </button>
      </div>
      <div className="side-body">
        {panel === 'guide' && experiment && <Guide />}
        {panel === 'vessel' && <Inspector />}
        {panel === 'journal' && <Journal />}
      </div>
      <TitrationChart />
    </aside>
  )
}

function Guide() {
  const exp = useLab((s) => s.experiment)!
  const done = useLab((s) => s.stepDone)
  const autoplay = useLab((s) => s.autoplay)
  const runStep = useLab((s) => s.runStep)
  const next = done.findIndex((d) => !d)
  const allDone = next === -1
  return (
    <div className="guide">
      <div className="guide-head">
        <span className={`level level-${exp.level}`}>{exp.level}</span>
        <span className="cat">{exp.catName}</span>
      </div>
      <h2>{exp.title}</h2>
      <p className="lead">{exp.summary}</p>
      {exp.safety && <div className="safety"><AlertTriangle size={16} /><span>{exp.safety}</span></div>}
      <div className="guide-ctrl">
        <button className="primary" onClick={() => useLab.getState().setAutoplay(!autoplay)}>
          {autoplay ? <><Pause size={15} /> Zatrzymaj pokaz</> : <><Play size={15} /> Pokaż automatycznie</>}
        </button>
        <button onClick={() => useLab.getState().resetBench()}><RotateCcw size={15} /> Od nowa</button>
      </div>
      <ol className="steps">
        {exp.steps.map((s, i) => (
          <li key={i} className={done[i] ? 'done' : i === next ? 'current' : ''}>
            <span className="num">{done[i] ? <Check size={14} /> : i + 1}</span>
            <div>
              <p>{s.text}</p>
              {!done[i] && i === next && s.actions.length > 0 && (
                <button className="mini" onClick={() => runStep(i)}><Sparkles size={13} /> Wykonaj ten krok</button>
              )}
              {!done[i] && i === next && s.actions.length === 0 && (
                <button className="mini" onClick={() => runStep(i)}><Check size={13} /> Gotowe – obserwuję</button>
              )}
              {s.wait > 5 && i === next && <small className="wait">Obserwuj przez ok. {Math.round(s.wait)} s (możesz przyspieszyć czas).</small>}
            </div>
          </li>
        ))}
      </ol>
      {allDone && <div className="done-box"><Check size={16} /> Wszystkie kroki wykonane. Sprawdź obserwacje i wnioski poniżej.</div>}
      {exp.observe && <section><h3><Eye size={15} /> Czego się spodziewać</h3><p>{exp.observe}</p></section>}
      {exp.equations.length > 0 && (
        <section>
          <h3><ScrollText size={15} /> Równania reakcji</h3>
          <ul className="eqs">{exp.equations.map((e) => <li key={e}><Chem text={e} /></li>)}</ul>
        </section>
      )}
      {exp.theory && <section><h3><Info size={15} /> Wyjaśnienie</h3><p>{exp.theory}</p></section>}
      {exp.tags.length > 0 && <div className="tags">{exp.tags.map((t) => <span key={t}>{t}</span>)}</div>}
    </div>
  )
}

function Inspector() {
  const selected = useLab((s) => s.selected)
  const views = useLab((s) => s.views)
  const catalog = useLab((s) => s.catalog)
  const v = selected ? views[selected] : null
  if (!v) {
    return (
      <div className="inspector empty">
        <CircleHelp size={28} />
        <p>Kliknij naczynie na stole, aby zobaczyć jego zawartość: stężenia jonów, pH, temperaturę, osady i skład gazu.</p>
        <ul className="howto">
          <li><b>Dodawanie:</b> przeciągnij odczynnik z półki na naczynie.</li>
          <li><b>Przelewanie:</b> przeciągnij naczynie na inne naczynie.</li>
          <li><b>Ogrzewanie i testy:</b> przeciągnij narzędzie lub użyj paska akcji.</li>
          <li><b>Czas:</b> przyspiesz symulację przyciskami ×2…×20 na górze.</li>
        </ul>
      </div>
    )
  }
  const eq = catalog?.equipment.find((e) => e.id === v.type)
  const arms = v.arms
  return (
    <div className="inspector">
      <h2>{eq?.name || v.type} <small>{v.id}</small></h2>
      {arms ? arms.map((a, i) => <VesselStats key={i} v={a} title={i === 0 ? 'Ramię katodowe (−)' : 'Ramię anodowe (+)'} />)
        : <VesselStats v={v} />}
    </div>
  )
}

function VesselStats({ v, title }: { v: any; title?: string }) {
  const gas = Object.entries(v.gas || {}).sort((a: any, b: any) => b[1] - a[1])
  return (
    <div className="stats">
      {title && <h3>{title}</h3>}
      <div className="kpis">
        <div><small>Objętość</small><b>{fmt(v.vol, 1)} mL</b></div>
        <div><small>Temperatura</small><b>{fmt(v.T, 1)} °C</b></div>
        <div><small>pH</small><b>{v.pH === null || v.vol < 0.3 ? '–' : fmt(v.pH, 2)}</b></div>
        {v.kappa !== undefined && <div><small>Przewodnictwo</small><b>{fmt(v.kappa, 2)} mS/cm</b></div>}
      </div>
      {v.color_name && v.vol > 0.05 && (
        <div className="colorline"><span className="dot" style={{ background: v.liquid }} /> Barwa: <b>{v.color_name}</b>
          {v.turbid ? <> · zmętnienie {Math.round(v.turbid * 100)}%</> : null}</div>
      )}
      {v.contents?.length > 0 && (
        <table className="contents">
          <thead><tr><th>Składnik</th><th>Wzór</th><th>Ilość</th></tr></thead>
          <tbody>
            {v.contents.map((c: any) => (
              <tr key={c.kind + c.id}>
                <td>{c.name}</td>
                <td>{c.kind === 'aq' && !c.id.startsWith('ind:') ? <Chem text={c.id} /> : c.formula ? <Chem text={c.formula} /> : ''}</td>
                <td>{c.kind === 'aq' ? `${fmt(c.c, 3)} mol/dm³` : c.kind === 's' ? `${fmt(c.g, 3)} g` : `${fmt(c.n, 3)} mol`}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {gas.length > 0 && (
        <div className="gasbar">
          <small>Gaz nad cieczą ({fmt(v.gas_ml, 0)} mL)</small>
          <div className="bar">{gas.map(([g, f]: any) => (
            <span key={g} style={{ width: `${f * 100}%` }} className={`g-${g}`} title={`${g}: ${(f * 100).toFixed(1)}%`}>
              {f > 0.08 ? <Chem text={g} /> : null}
            </span>
          ))}</div>
        </div>
      )}
    </div>
  )
}

const KIND_ICON: Record<string, JSX.Element> = {
  obs: <Eye size={14} />, ppt: <TestTubeDiagonal size={14} />, info: <Info size={14} />, warn: <AlertTriangle size={14} />,
  test: <Sparkles size={14} />, color: <span className="dot" />, error: <AlertTriangle size={14} />,
}

function Journal() {
  const events = useLab((s) => s.events)
  const showColor = true
  const ref = useRef<HTMLDivElement>(null)
  const list = useMemo(() => events.filter((e) => showColor || e.kind !== 'color'), [events])
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight, behavior: 'smooth' })
  }, [list.length])
  if (!list.length)
    return <div className="journal empty"><NotebookPen size={26} /><p>Tu pojawią się obserwacje: zmiany barwy, osady, gazy, wyniki testów i równania reakcji.</p></div>
  return (
    <div className="journal" ref={ref}>
      {list.map((e) => (
        <div key={e.id} className={`ev ev-${e.kind}`}>
          <span className="ev-icon" style={e.kind === 'color' && e.color ? { color: e.color } : undefined}>
            {e.kind === 'color' ? <span className="dot" style={{ background: e.color }} /> : KIND_ICON[e.kind]}
          </span>
          <div>
            <p><small>{fmt(e.t, 0)} s{e.v ? ` · ${e.v}` : ''}</small>{e.text}</p>
            {e.eq && <p className="eq"><Chem text={e.eq} /></p>}
          </div>
        </div>
      ))}
    </div>
  )
}
