import { useMemo, useState } from 'react'
import { Beaker, FlaskConical, Search, Wrench, X } from 'lucide-react'
import { useLab } from '../store'
import { shelfPointerDown } from '../dnd'
import { Chem } from '../chem'
import type { ReagentItem } from '../types'
import { applyTool } from './tools'

const HAZ_COLORS: Record<string, string> = {
  corr: '#f97316', tox: '#ef4444', ox: '#eab308', flam: '#fb7185', irr: '#a3a3a3', env: '#22c55e',
}

function ReagentSwatch({ r }: { r: ReagentItem }) {
  if (r.kind === 'solid') return <span className="swatch solid" style={{ background: r.color }} />
  if (r.kind === 'gas') return <span className="swatch gas" />
  if (r.kind === 'indicator') return <span className="swatch ind" />
  if (r.kind === 'liquid') return <span className="swatch liquid-org" />
  return <span className="swatch bottle" />
}

export default function Shelf({ onClose }: { onClose?: () => void }) {
  const catalog = useLab((s) => s.catalog)
  const pick = useLab((s) => s.pick)
  const selected = useLab((s) => s.selected)
  const [tab, setTab] = useState<'equipment' | 'reagents' | 'tools'>('reagents')
  const [q, setQ] = useState('')
  const [group, setGroup] = useState<string>('')

  const groups = useMemo(() => {
    if (!catalog) return []
    const src = tab === 'equipment' ? catalog.equipment : tab === 'reagents' ? catalog.reagents : catalog.tools
    return Array.from(new Set(src.map((x: any) => x.group)))
  }, [catalog, tab])

  if (!catalog) return <aside className="shelf"><div className="loading">Ładowanie półki…</div></aside>

  const norm = (s: string) => s.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ł/g, 'l')
  const qq = norm(q)
  const match = (name: string, formula = '') => !qq || norm(name).includes(qq) || norm(formula).includes(qq)

  const clickReagent = (id: string) => {
    const st = useLab.getState()
    if (selected && st.views[selected]) {
      const r = catalog.reagents.find((x) => x.id === id)!
      if (r.kind === 'gas') st.act({ op: 'reagent', v: selected, reagent: id, amount: 1 })
      else st.setDialog({ kind: 'reagent', vessel: selected, reagent: id })
    } else st.setPick(pick?.kind === 'reagent' && pick.id === id ? null : { kind: 'reagent', id })
  }
  const clickTool = (id: string) => {
    const st = useLab.getState()
    if (selected && st.views[selected]) applyTool(id, selected)
    else st.setPick(pick?.kind === 'tool' && pick.id === id ? null : { kind: 'tool', id })
  }

  return (
    <aside className="shelf">
      <div className="shelf-head">
        <div className="tabs" role="tablist">
          <button className={tab === 'reagents' ? 'on' : ''} onClick={() => { setTab('reagents'); setGroup('') }}>
            <FlaskConical size={15} /> Odczynniki
          </button>
          <button className={tab === 'equipment' ? 'on' : ''} onClick={() => { setTab('equipment'); setGroup('') }}>
            <Beaker size={15} /> Sprzęt
          </button>
          <button className={tab === 'tools' ? 'on' : ''} onClick={() => { setTab('tools'); setGroup('') }}>
            <Wrench size={15} /> Narzędzia
          </button>
          {onClose && <button className="icon-only close-shelf" onClick={onClose} aria-label="Zamknij półkę"><X size={16} /></button>}
        </div>
        <label className="search">
          <Search size={14} />
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Szukaj (nazwa lub wzór)…" />
        </label>
        <div className="chips">
          <button className={!group ? 'on' : ''} onClick={() => setGroup('')}>Wszystko</button>
          {groups.map((g) => <button key={g} className={group === g ? 'on' : ''} onClick={() => setGroup(g)}>{g}</button>)}
        </div>
        <p className="shelf-tip">
          {selected ? 'Kliknij pozycję, aby użyć jej z zaznaczonym naczyniem, albo przeciągnij na dowolne naczynie.'
            : 'Przeciągnij na stół lub naczynie. Kliknięcie wybiera pozycję – potem kliknij naczynie.'}
        </p>
      </div>
      <div className="shelf-list">
        {tab === 'equipment' && catalog.equipment.filter((e) => (!group || e.group === group) && match(e.name)).map((e) => (
          <div key={e.id} className="shelf-item" title={e.desc}
               onPointerDown={shelfPointerDown({ kind: 'equipment', id: e.id, label: e.name }, () => useLab.getState().addVessel(e.id))}>
            <span className={`eq-icon eq-${e.id}`} />
            <div><b>{e.name}</b>{e.cap > 0 && <small>{e.cap} mL{e.heatable ? ' · do ogrzewania' : ''}</small>}</div>
          </div>
        ))}
        {tab === 'reagents' && catalog.reagents.filter((r) => (!group || r.group === group) && match(r.name, r.formula)).map((r) => (
          <div key={r.id} className={`shelf-item${pick?.kind === 'reagent' && pick.id === r.id ? ' picked' : ''}`} title={r.note || r.name}
               onPointerDown={shelfPointerDown({ kind: 'reagent', id: r.id, label: r.name, color: r.color }, () => clickReagent(r.id))}>
            <ReagentSwatch r={r} />
            <div>
              <b>{r.name}</b>
              <small>{r.formula && <Chem text={r.formula} />}{r.hazards.map((h) => (
                <i key={h} className="haz" style={{ background: HAZ_COLORS[h] }} title={catalog.hazards[h]} />
              ))}</small>
            </div>
          </div>
        ))}
        {tab === 'tools' && catalog.tools.filter((t) => (!group || t.group === group) && match(t.name)).map((t) => (
          <div key={t.id} className={`shelf-item${pick?.kind === 'tool' && pick.id === t.id ? ' picked' : ''}`} title={t.desc}
               onPointerDown={shelfPointerDown({ kind: 'tool', id: t.id, label: t.name }, () => clickTool(t.id))}>
            <span className={`tool-icon tool-${t.kind}`} />
            <div><b>{t.name}</b>{t.desc && <small>{t.desc}</small>}</div>
          </div>
        ))}
      </div>
    </aside>
  )
}
