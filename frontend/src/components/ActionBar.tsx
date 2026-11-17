import { useState } from 'react'
import {
  ArrowRightLeft, Cable, ChevronDown, Droplets, Flame, FlaskConical, Link2, Power, RotateCw, Spline, Trash2,
  TestTube2, Thermometer, Unplug, Wind, Zap, Eraser, CircleDot, MoveDown,
} from 'lucide-react'
import { useLab } from '../store'
import { applyTool } from './tools'

export const HEAT_OPTS = [
  ['', 'Bez ogrzewania'], ['alcohol', 'Palnik spirytusowy'], ['bunsen', 'Palnik gazowy'], ['hotplate', 'Płyta grzejna'],
  ['water_bath', 'Łaźnia wodna 80 °C'], ['ice_bath', 'Łaźnia lodowa 0 °C'],
] as const

export const TESTS = [
  ['glowing_splint', 'Żarzące się łuczywo'], ['burning_splint', 'Płonące łuczywo'], ['gas_litmus', 'Papierki lakmusowe (gaz)'],
  ['univ_paper', 'Papierek uniwersalny'], ['litmus_red', 'Czerwony papierek lakmusowy'], ['litmus_blue', 'Niebieski papierek lakmusowy'],
  ['flame_test', 'Próba płomieniowa'], ['cobalt_glass', 'Płomień przez szkło kobaltowe'], ['smell', 'Zapach (ostrożnie)'],
  ['conductivity', 'Przewodnictwo (żarówka)'], ['thermometer', 'Termometr'], ['ph_meter', 'pH-metr'],
] as const

function Menu({ label, icon, children }: { label: string; icon: JSX.Element; children: (close: () => void) => JSX.Element }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="menu">
      <button onClick={() => setOpen(!open)} className={open ? 'on' : ''}>{icon}<span>{label}</span><ChevronDown size={13} /></button>
      {open && (
        <>
          <div className="menu-veil" onClick={() => setOpen(false)} />
          <div className="menu-pop">{children(() => setOpen(false))}</div>
        </>
      )}
    </div>
  )
}

export default function ActionBar() {
  const selected = useLab((s) => s.selected)
  const views = useLab((s) => s.views)
  const catalog = useLab((s) => s.catalog)
  const bench = useLab((s) => s.bench)
  const v = selected ? views[selected] : null
  if (!v || !selected) {
    return (
      <div className="action-bar empty">
        <span>Zaznacz naczynie na stole, aby zobaczyć dostępne czynności. Przeciągnij naczynie na inne, aby przelać.</span>
      </div>
    )
  }
  const eq = catalog?.equipment.find((e) => e.id === v.type)
  const st = useLab.getState()
  const act = st.act
  const kind = eq?.kind || 'vessel'
  const hasLiquid = v.vol > 0.05 || (v.arms?.some((a) => a.vol > 0.05) ?? false)
  const raw = bench.vessels[selected]

  return (
    <div className="action-bar">
      <div className="ab-title">
        <b>{eq?.name || v.type}</b>
        <small>{selected}</small>
      </div>
      <div className="ab-buttons">
        {kind !== 'candle' && (
          <button onClick={() => { st.setPanel('vessel'); document.querySelector<HTMLInputElement>('.shelf .search input')?.focus() }}
                  title="Wybierz odczynnik na półce i kliknij go">
            <FlaskConical size={16} /><span>Dodaj</span>
          </button>
        )}
        {hasLiquid && kind !== 'burette' && (
          <button onClick={() => st.setLink({ kind: 'pour', from: selected })}><ArrowRightLeft size={16} /><span>Przelej…</span></button>
        )}
        {eq?.heatable && (
          <Menu label="Ogrzewanie" icon={<Flame size={16} />}>
            {(close) => (
              <>{HEAT_OPTS.map(([id, label]) => (
                <button key={id} className={(v.heat || '') === id ? 'on' : ''}
                        onClick={() => { act({ op: 'heat', v: selected, source: id || null }); close() }}>{label}</button>
              ))}</>
            )}
          </Menu>
        )}
        {!eq?.heatable && kind !== 'burette' && kind !== 'candle' && (
          <Menu label="Łaźnia" icon={<Thermometer size={16} />}>
            {(close) => (
              <>{HEAT_OPTS.filter(([id]) => id === '' || id.includes('bath')).map(([id, label]) => (
                <button key={id} className={(v.heat || '') === id ? 'on' : ''}
                        onClick={() => { act({ op: 'heat', v: selected, source: id || null }); close() }}>{label}</button>
              ))}</>
            )}
          </Menu>
        )}
        {hasLiquid && <button onClick={() => applyTool('stir', selected)}><RotateCw size={16} /><span>Mieszaj</span></button>}
        {['vessel', 'jar', 'fountain'].includes(kind) && (
          <button className={v.stopper ? 'on' : ''} onClick={() => act({ op: 'stopper', v: selected, on: !v.stopper })}>
            <CircleDot size={16} /><span>{kind === 'jar' ? (v.stopper ? 'Zdejmij pokrywkę' : 'Przykryj') : v.stopper ? 'Wyjmij korek' : 'Korek'}</span>
          </button>
        )}
        {kind === 'vessel' && (
          v.outlet
            ? <button className="on" onClick={() => act({ op: 'connect', v: selected, to: null })}><Unplug size={16} /><span>Odłącz rurkę</span></button>
            : <button onClick={() => st.setLink({ kind: 'outlet', from: selected })}><Spline size={16} /><span>Rurka do…</span></button>
        )}
        {(kind === 'spoon' || kind === 'candle') && (
          v.parent
            ? <button className="on" onClick={() => act({ op: 'parent', v: selected, to: null })}><MoveDown size={16} /><span>Wyjmij z cylindra</span></button>
            : <button onClick={() => st.setLink({ kind: 'parent', from: selected })}><MoveDown size={16} /><span>Do cylindra…</span></button>
        )}
        {(kind === 'spoon' || kind === 'candle' || kind === 'crucible' || kind === 'vessel') && (
          <button onClick={() => applyTool('ignite', selected)}><Flame size={16} /><span>Podpal</span></button>
        )}
        {kind === 'burette' && (
          <>
            <button onClick={() => st.setLink({ kind: 'burette', from: selected })}><MoveDown size={16} /><span>{v.target ? 'Zmień naczynie' : 'Ustaw nad…'}</span></button>
            {v.target && (
              <div className="flow">
                <Droplets size={15} />
                <input type="range" min={0} max={2} step={0.05} value={raw?.flow ?? 0}
                       onChange={(e) => act({ op: 'burette', v: selected, target: v.target, flow: Number(e.target.value) })} />
                <span>{(raw?.flow ?? 0).toFixed(2)} mL/s</span>
                <button onClick={() => act({ op: 'burette', v: selected, target: v.target, flow: 0 })}>Zamknij</button>
                <button onClick={() => act({ op: 'burette', v: selected, target: v.target, flow: 0.05 })} title="Kroplami">Kroplami</button>
              </div>
            )}
          </>
        )}
        {kind === 'funnel' && (
          <button onClick={() => st.setLink({ kind: 'funnel', from: selected })}><MoveDown size={16} /><span>Ustaw nad…</span></button>
        )}
        {kind === 'fountain' && (
          <button onClick={() => st.setLink({ kind: 'source', from: selected })}><Link2 size={16} /><span>Rurka do zlewki…</span></button>
        )}
        {kind === 'utube' && (
          <>
            <button className={v.power ? 'on' : ''} onClick={() => act({ op: 'power', v: selected, on: !v.power })}>
              <Power size={16} /><span>{v.power ? 'Wyłącz zasilacz' : 'Włącz zasilacz'}</span>
            </button>
            <Menu label={`Elektrody: ${v.electrode === 'Cu' ? 'miedziane' : 'grafitowe'}`} icon={<Zap size={16} />}>
              {(close) => (
                <>
                  <button onClick={() => { act({ op: 'power', v: selected, on: v.power, electrode: 'C' }); close() }}>Grafitowe (obojętne)</button>
                  <button onClick={() => { act({ op: 'power', v: selected, on: v.power, electrode: 'Cu' }); close() }}>Miedziane</button>
                </>
              )}
            </Menu>
          </>
        )}
        {kind === 'vessel' && (
          <button onClick={() => st.setLink({ kind: 'bridge', from: selected })}><Cable size={16} /><span>Klucz elektrolit.</span></button>
        )}
        {kind !== 'candle' && kind !== 'funnel' && (
          <Menu label="Testy" icon={<TestTube2 size={16} />}>
            {(close) => (
              <>{TESTS.map(([id, label]) => (
                <button key={id} onClick={() => { applyTool(id, selected); close() }}>{label}</button>
              ))}</>
            )}
          </Menu>
        )}
        <button onClick={() => act({ op: 'empty', v: selected })} title="Wylej zawartość"><Eraser size={16} /><span>Opróżnij</span></button>
        <button className="danger" onClick={() => act({ op: 'remove', v: selected })} title="Zdejmij ze stołu"><Trash2 size={16} /><span>Usuń</span></button>
        {(v.gas && Object.keys(v.gas).some((g) => !['N2', 'O2', 'CO2'].includes(g))) && (
          <span className="gas-hint"><Wind size={14} /> W naczyniu jest gaz – zbadaj go testami.</span>
        )}
      </div>
    </div>
  )
}
