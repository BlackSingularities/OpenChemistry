import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import {
  ArrowRightLeft, ChevronRight, CircleDot, Eraser, Flame, FlaskConical, Info, MoveDown, Power, RotateCw, Spline,
  TestTube2, Thermometer, Trash2, Unplug,
} from 'lucide-react'
import { useLab } from '../store'
import { applyTool } from './tools'
import { HEAT_OPTS, TESTS } from './ActionBar'

type Item =
  | { label: string; icon: JSX.Element; run: () => void; danger?: boolean; on?: boolean }
  | { label: string; icon: JSX.Element; sub: { label: string; run: () => void; on?: boolean }[] }

/** Menu pod prawym przyciskiem myszy (lub długim przytrzymaniem) na naczyniu. */
export default function ContextMenu() {
  const ctx = useLab((s) => s.ctx)
  const views = useLab((s) => s.views)
  const catalog = useLab((s) => s.catalog)
  const [open, setOpen] = useState<number | null>(null)
  const [pos, setPos] = useState<{ left: number; top: number } | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => { setOpen(null); setPos(null) }, [ctx?.v, ctx?.x, ctx?.y])

  useEffect(() => {
    if (!ctx) return
    const close = () => useLab.getState().setCtx(null)
    const key = (e: KeyboardEvent) => e.key === 'Escape' && close()
    window.addEventListener('keydown', key)
    window.addEventListener('resize', close)
    return () => { window.removeEventListener('keydown', key); window.removeEventListener('resize', close) }
  }, [ctx])

  // dopasowanie położenia do krawędzi okna
  useLayoutEffect(() => {
    if (!ctx || !ref.current) return
    const r = ref.current.getBoundingClientRect()
    const left = Math.max(8, Math.min(ctx.x, window.innerWidth - r.width - 8))
    const top = Math.max(8, Math.min(ctx.y, window.innerHeight - r.height - 8))
    if (!pos || pos.left !== left || pos.top !== top) setPos({ left, top })
  })

  if (!ctx) return null
  const id = ctx.v
  const v = views[id]
  if (!v) return null
  const eq = catalog?.equipment.find((e) => e.id === v.type)
  const kind = eq?.kind || 'vessel'
  const st = useLab.getState()
  const act = st.act
  const close = () => st.setCtx(null)
  const hasLiquid = v.vol > 0.05 || (v.arms?.some((a) => a.vol > 0.05) ?? false)

  const items: Item[] = []
  if (kind !== 'candle') {
    items.push({
      label: 'Dodaj odczynnik…', icon: <FlaskConical size={15} />,
      run: () => { st.select(id); document.querySelector<HTMLInputElement>('.shelf .search input')?.focus(); st.setToast('Wybierz odczynnik na półce – trafi do zaznaczonego naczynia.') },
    })
  }
  if (hasLiquid && kind !== 'burette') items.push({ label: 'Przelej do…', icon: <ArrowRightLeft size={15} />, run: () => { st.select(id); st.setLink({ kind: 'pour', from: id }) } })
  if (hasLiquid) items.push({ label: 'Wymieszaj', icon: <RotateCw size={15} />, run: () => applyTool('stir', id) })
  if (kind !== 'burette' && kind !== 'candle') {
    const opts = eq?.heatable ? HEAT_OPTS : HEAT_OPTS.filter(([h]) => h === '' || h.includes('bath'))
    items.push({
      label: eq?.heatable ? 'Ogrzewanie' : 'Łaźnia', icon: eq?.heatable ? <Flame size={15} /> : <Thermometer size={15} />,
      sub: opts.map(([h, label]) => ({ label, on: (v.heat || '') === h, run: () => act({ op: 'heat', v: id, source: h || null }) })),
    })
  }
  if (kind !== 'candle' && kind !== 'funnel') {
    items.push({ label: 'Zbadaj', icon: <TestTube2 size={15} />, sub: TESTS.map(([t, label]) => ({ label, run: () => applyTool(t, id) })) })
  }
  if (['vessel', 'jar', 'fountain'].includes(kind)) {
    items.push({
      label: kind === 'jar' ? (v.stopper ? 'Zdejmij pokrywkę' : 'Przykryj') : v.stopper ? 'Wyjmij korek' : 'Zatkaj korkiem',
      icon: <CircleDot size={15} />, on: Boolean(v.stopper), run: () => act({ op: 'stopper', v: id, on: !v.stopper }),
    })
  }
  if (kind === 'vessel') {
    items.push(v.outlet
      ? { label: 'Odłącz rurkę', icon: <Unplug size={15} />, run: () => act({ op: 'connect', v: id, to: null }) }
      : { label: 'Rurka odprowadzająca do…', icon: <Spline size={15} />, run: () => { st.select(id); st.setLink({ kind: 'outlet', from: id }) } })
  }
  if (kind === 'spoon' || kind === 'candle') {
    items.push(v.parent
      ? { label: 'Wyjmij z cylindra', icon: <MoveDown size={15} />, run: () => act({ op: 'parent', v: id, to: null }) }
      : { label: 'Wsuń do cylindra…', icon: <MoveDown size={15} />, run: () => { st.select(id); st.setLink({ kind: 'parent', from: id }) } })
  }
  if (['spoon', 'candle', 'crucible', 'vessel'].includes(kind)) items.push({ label: 'Podpal', icon: <Flame size={15} />, run: () => applyTool('ignite', id) })
  if (kind === 'burette' || kind === 'funnel') {
    items.push({ label: 'Ustaw nad naczyniem…', icon: <MoveDown size={15} />, run: () => { st.select(id); st.setLink({ kind: kind === 'burette' ? 'burette' : 'funnel', from: id }) } })
  }
  if (kind === 'utube') {
    items.push({ label: v.power ? 'Wyłącz zasilacz' : 'Włącz zasilacz', icon: <Power size={15} />, on: Boolean(v.power), run: () => act({ op: 'power', v: id, on: !v.power }) })
  }
  items.push({ label: 'Szczegóły naczynia', icon: <Info size={15} />, run: () => { st.select(id); st.setPanel('vessel') } })
  items.push({ label: 'Opróżnij', icon: <Eraser size={15} />, run: () => act({ op: 'empty', v: id }) })
  items.push({ label: 'Zdejmij ze stołu', icon: <Trash2 size={15} />, danger: true, run: () => act({ op: 'remove', v: id }) })

  return (
    <>
      <div className="ctx-veil" onPointerDown={close} onContextMenu={(e) => { e.preventDefault(); close() }} />
      <div className="ctx-menu" ref={ref} role="menu" style={{ left: pos?.left ?? ctx.x, top: pos?.top ?? ctx.y, visibility: pos ? 'visible' : 'hidden' }}
           onContextMenu={(e) => e.preventDefault()}>
        <div className="ctx-head">{eq?.name || v.type}<small>{id}</small></div>
        {items.map((it, i) => 'sub' in it ? (
          <div key={it.label} className="ctx-group">
            <button role="menuitem" aria-expanded={open === i} className={open === i ? 'open' : ''} onClick={() => setOpen(open === i ? null : i)}>
              {it.icon}<span>{it.label}</span><ChevronRight size={14} className="chev" />
            </button>
            {open === i && (
              <div className="ctx-sub">
                {it.sub.map((s) => (
                  <button key={s.label} role="menuitem" className={s.on ? 'on' : ''} onClick={() => { s.run(); close() }}>{s.label}</button>
                ))}
              </div>
            )}
          </div>
        ) : (
          <button key={it.label} role="menuitem" className={`${it.danger ? 'danger' : ''}${it.on ? ' on' : ''}`} onClick={() => { it.run(); close() }}>
            {it.icon}<span>{it.label}</span>
          </button>
        ))}
      </div>
    </>
  )
}
