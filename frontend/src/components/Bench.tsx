import { useEffect, useMemo, useRef, useState } from 'react'
import { useLab } from '../store'
import { SHAPES, TUBES, levelFor } from '../shapes'
import type { VesselView } from '../types'
import { VesselGraphic } from './Vessel'
import { BurnFlame, HeatSource, MouthEffects, Tripod } from './Effects'
import { BuretteGraphic, CandleGraphic, CrucibleGlow, FountainGraphic, FunnelGraphic, SpoonGraphic, UTubeGraphic } from './Specials'
import { fmt } from '../chem'
import { applyTool } from './tools'

export const W = 1000
export const H = 620
export const TOP = 548

export interface Placed {
  id: string
  view: VesselView
  x: number
  bottom: number // y dna
  top: number // y wylotu
  w: number
  h: number
  lift: number
  kind: string
}

const SPECIAL_SIZE: Record<string, [number, number]> = {
  burette: [18, 300], utube: [130, 190], spoon: [26, 24], candle: [22, 40], funnel: [76, 86],
}

export function layout(views: Record<string, VesselView>, bench: any): Record<string, Placed> {
  const out: Record<string, Placed> = {}
  const order = Object.keys(views).sort((a, b) => {
    const da = views[a].parent || views[a].target || views[a].source ? 1 : 0
    const db = views[b].parent || views[b].target || views[b].source ? 1 : 0
    return da - db
  })
  for (const id of order) {
    const v = views[id]
    const bv = bench.vessels[id]
    if (!bv) continue
    const s = SHAPES[v.type]
    let [w, h] = SPECIAL_SIZE[v.type] || [s?.w || 60, s?.h || 100]
    let x = bv.x
    let lift = 0
    const heat = v.heat
    if (heat === 'alcohol' || heat === 'bunsen') lift = TUBES.has(v.type) ? 64 : v.type === 'spoon' ? 40 : 86
    else if (heat === 'hotplate') lift = 28
    else if (heat === 'water_bath' || heat === 'ice_bath') lift = 6
    let bottom = TOP - lift
    if (v.type === 'burette' && v.target && out[v.target]) {
      const t = out[v.target]
      x = t.x
      bottom = t.top - 6
      h = 300
    } else if (v.type === 'burette') {
      bottom = TOP - 140
    }
    if (v.type === 'funnel' && v.target && out[v.target]) {
      const t = out[v.target]
      x = t.x
      bottom = t.top + 34
    }
    if ((v.type === 'spoon' || v.type === 'candle') && v.parent && out[v.parent]) {
      const p = out[v.parent]
      x = p.x
      bottom = v.type === 'spoon' ? p.bottom - p.h * 0.32 : p.bottom - 3
      lift = 0
    } else if (v.type === 'spoon' && !heat) {
      bottom = TOP - 30
    }
    if (v.type === 'fountain' && v.source && out[v.source]) {
      const sp = out[v.source]
      x = sp.x
      bottom = sp.bottom - 14 - 120
    } else if (v.type === 'fountain') {
      bottom = TOP - 120
    }
    if (v.type === 'utube') bottom = TOP - 4
    out[id] = { id, view: v, x, bottom, top: bottom - h, w, h, lift, kind: v.type }
  }
  return out
}

function Readings({ p }: { p: Placed }) {
  const v = p.view
  const chips: string[] = []
  if (v.arms) {
    return null
  }
  if (v.vol > 0.05 && v.type !== 'burette') chips.push(`${fmt(v.vol, v.vol < 10 ? 1 : 0)} mL`)
  if (Math.abs(v.T - 20) > 0.6 || v.heat) chips.push(`${fmt(v.T, 0)} °C`)
  if (v.pH !== null && v.vol > 0.3 && v.type !== 'burette') chips.push(`pH ${fmt(v.pH, 1)}`)
  if (!chips.length) return null
  return <div className={`readings${p.w < 50 ? ' narrow' : ''}`}>{chips.map((c) => <span key={c}>{c}</span>)}</div>
}

export default function Bench() {
  const views = useLab((s) => s.views)
  const bench = useLab((s) => s.bench)
  const selected = useLab((s) => s.selected)
  const link = useLab((s) => s.link)
  const pick = useLab((s) => s.pick)
  const readings = useLab((s) => s.readings)
  const flashes = useLab((s) => s.flashes)
  const showReadings = useLab((s) => s.showReadings)
  const experiment = useLab((s) => s.experiment)
  const wrap = useRef<HTMLDivElement>(null)
  const [box, setBox] = useState({ w: 800, h: 500 })
  const [drag, setDrag] = useState<{ id: string; dx: number; dy: number } | null>(null)
  const placed = useMemo(() => layout(views, bench), [views, bench])
  const links = bench.links || []
  const labels = useMemo(() => {
    const m: Record<string, string> = {}
    experiment?.setup.forEach((s) => { if (s.label) m[s.id] = s.label })
    return m
  }, [experiment])

  useEffect(() => {
    const el = wrap.current
    if (!el) return
    const ro = new ResizeObserver(() => {
      const r = el.getBoundingClientRect()
      setBox({ w: r.width, h: r.height })
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

  // automatyczne kadrowanie: przybliżamy widok do zajętej części stołu
  const frame = useMemo(() => {
    const ps = Object.values(placed)
    let left = 330
    let right = 670
    let top = TOP - 260
    for (const p of ps) {
      left = Math.min(left, p.x - p.w / 2 - 50)
      right = Math.max(right, p.x + p.w / 2 + 50)
      top = Math.min(top, p.top - (p.view.type === 'burette' ? 30 : 110))
    }
    if (links.length) top = Math.min(top, ...links.map((lk) => Math.min(placed[lk.a]?.top ?? TOP, placed[lk.b]?.top ?? TOP) - 130))
    const bottom = TOP + 46
    const s = Math.max(0.28, Math.min(box.w / (right - left), box.h / (bottom - top), 1.7))
    const tx = (box.w - (right - left) * s) / 2 - left * s
    const ty = box.h - bottom * s
    return { s, tx, ty }
  }, [placed, box])
  const scale = frame.s

  const toLogical = (cx: number, cy: number) => {
    const el = wrap.current?.querySelector('.bench-stage') as HTMLElement | null
    if (!el) return { x: 0, y: 0 }
    const r = el.getBoundingClientRect()
    return { x: (cx - r.left) / scale, y: (cy - r.top) / scale }
  }

  const hit = (x: number, y: number, exclude?: string): Placed | null => {
    let best: Placed | null = null
    for (const p of Object.values(placed)) {
      if (p.id === exclude) continue
      const pad = 14
      if (x >= p.x - p.w / 2 - pad && x <= p.x + p.w / 2 + pad && y >= p.top - 40 && y <= p.bottom + 20) {
        if (!best || p.w < best.w) best = p
      }
    }
    return best
  }

  // upuszczenie elementu z półki
  useEffect(() => {
    const onDrop = (e: Event) => {
      const { item, x, y } = (e as CustomEvent).detail
      const el = wrap.current
      if (!el) return
      const r = el.getBoundingClientRect()
      if (x < r.left || x > r.right || y < r.top || y > r.bottom) return
      const p = toLogical(x, y)
      const st = useLab.getState()
      if (item.kind === 'equipment') {
        st.addVessel(item.id, Math.max(40, Math.min(960, p.x)))
        return
      }
      const target = hit(p.x, p.y)
      if (!target) {
        st.setToast('Upuść na naczynie na stole.')
        return
      }
      if (item.kind === 'reagent') openReagent(target.id, item.id)
      if (item.kind === 'tool') applyTool(item.id, target.id)
    }
    window.addEventListener('lab-drop', onDrop)
    return () => window.removeEventListener('lab-drop', onDrop)
  })

  const onVesselDown = (e: React.PointerEvent, id: string) => {
    if (e.button !== 0) return
    e.stopPropagation()
    const start = toLogical(e.clientX, e.clientY)
    let moved = false
    const mv = (ev: PointerEvent) => {
      const p = toLogical(ev.clientX, ev.clientY)
      if (!moved && Math.hypot(p.x - start.x, p.y - start.y) > 6) moved = true
      if (moved) setDrag({ id, dx: p.x - start.x, dy: p.y - start.y })
    }
    const up = (ev: PointerEvent) => {
      window.removeEventListener('pointermove', mv)
      window.removeEventListener('pointerup', up)
      setDrag(null)
      const st = useLab.getState()
      if (!moved) {
        clickVessel(id)
        return
      }
      const p = toLogical(ev.clientX, ev.clientY)
      const target = hit(p.x, p.y, id)
      const me = st.views[id]
      if (target && target.id !== id) {
        if (me.type === 'spoon' || me.type === 'candle') st.act({ op: 'parent', v: id, to: target.id })
        else if (me.type === 'burette') st.setDialog({ kind: 'burette', vessel: id, target: target.id })
        else if (me.type === 'funnel') st.act({ op: 'funnel', v: id, target: target.id })
        else if (me.type === 'fountain') st.act({ op: 'source', v: id, src: target.id })
        else st.setDialog({ kind: 'pour', from: id, to: target.id })
        return
      }
      const nx = Math.max(30, Math.min(970, (st.bench.vessels[id]?.x ?? 500) + (p.x - start.x)))
      const acts: any[] = [{ op: 'move', v: id, x: nx }]
      if (me.parent) acts.push({ op: 'parent', v: id, to: null })
      if (me.type === 'burette' && me.target) acts.push({ op: 'burette', v: id, target: null, flow: 0 })
      if (me.type === 'funnel' && me.target) acts.push({ op: 'funnel', v: id, target: null })
      if (me.type === 'fountain' && me.source) acts.push({ op: 'source', v: id, src: null })
      st.act(...acts)
    }
    window.addEventListener('pointermove', mv)
    window.addEventListener('pointerup', up)
  }

  const clickVessel = (id: string) => {
    const st = useLab.getState()
    if (st.link) {
      completeLink(st.link, id)
      return
    }
    if (st.pick) {
      if (st.pick.kind === 'reagent') openReagent(id, st.pick.id)
      else if (st.pick.kind === 'tool') applyTool(st.pick.id, id)
      return
    }
    st.select(id)
  }

  const tubes = Object.values(placed).filter((p) => p.view.outlet && placed[p.view.outlet])

  return (
    <div className={`bench-wrap${link || pick ? ' targeting' : ''}`} ref={wrap}
         onPointerDown={() => { const st = useLab.getState(); if (!st.link && !st.pick) st.select(null) }}>
      <div className="bench-stage" style={{ width: W, height: H, transform: `translate(${frame.tx}px, ${frame.ty}px) scale(${scale})` }}>
        <div className="wall" />
        <BackShelf />
        <div className="counter" style={{ top: TOP }} />
        <svg className="defs-svg" width="0" height="0">
          <defs>
            <pattern id="pat-powder" width="4" height="4" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r=".6" fill="#000" opacity=".25" /><circle cx="3" cy="3" r=".5" fill="#fff" opacity=".35" />
            </pattern>
            <pattern id="pat-crystal" width="7" height="6" patternUnits="userSpaceOnUse">
              <path d="M0,6 L3,0 L6,6 Z" fill="#fff" opacity=".35" /><path d="M3,6 L5,2 L7,6Z" fill="#000" opacity=".12" />
            </pattern>
            <pattern id="pat-gel" width="10" height="8" patternUnits="userSpaceOnUse">
              <ellipse cx="4" cy="4" rx="4" ry="2.4" fill="#fff" opacity=".18" />
            </pattern>
            <pattern id="pat-char" width="6" height="6" patternUnits="userSpaceOnUse">
              <circle cx="3" cy="3" r="1.6" fill="#000" opacity=".5" />
            </pattern>
            <linearGradient id="mirror" x1="0" x2="1">
              <stop offset="0" stopColor="#7d8590" /><stop offset=".3" stopColor="#f4f6f8" />
              <stop offset=".55" stopColor="#9aa3ad" /><stop offset=".8" stopColor="#e6e9ec" /><stop offset="1" stopColor="#6e7681" />
            </linearGradient>
            <radialGradient id="brightGlow"><stop offset="0" stopColor="#fff" stopOpacity=".95" /><stop offset=".4" stopColor="#fff8e0" stopOpacity=".5" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></radialGradient>
            <radialGradient id="emberGlow"><stop offset="0" stopColor="#fff3b0" /><stop offset=".5" stopColor="#ff7a2a" stopOpacity=".8" /><stop offset="1" stopColor="#ff3d00" stopOpacity="0" /></radialGradient>
            <linearGradient id="hotplateGlow" x1="0" x2="1"><stop offset="0" stopColor="#ff5a2a" /><stop offset=".5" stopColor="#ff9a4a" /><stop offset="1" stopColor="#ff5a2a" /></linearGradient>
          </defs>
        </svg>

        {/* rurki odprowadzające */}
        <svg className="tubes" width={W} height={H}>
          {tubes.map((p) => {
            const t = placed[p.view.outlet!]
            const sx = p.x
            const sy = p.top - 8
            const into = t.view.vol > 1 && t.view.type !== 'gas_jar'
            const ex = t.x + (t.w > 40 ? -t.w * 0.12 : 0)
            const ey = into ? t.bottom - 10 : t.top + Math.min(40, t.h * 0.4)
            const up = Math.min(sy, t.top) - 36
            const d = `M${sx},${sy} L${sx},${up + 14} Q${sx},${up} ${sx + Math.sign(ex - sx) * 14},${up} L${ex - Math.sign(ex - sx) * 14},${up} Q${ex},${up} ${ex},${up + 14} L${ex},${ey}`
            return (
              <g key={p.id}>
                <path d={d} className="tube-outer" />
                <path d={d} className="tube-inner" />
              </g>
            )
          })}
          {links.map((lk) => {
            const a = placed[lk.a]
            const b = placed[lk.b]
            if (!a || !b) return null
            const y0 = Math.min(a.top, b.top) - 24
            const ax = a.x + a.w * 0.18
            const bx = b.x - b.w * 0.18
            const d = `M${ax},${a.bottom - 20} L${ax},${y0 + 10} Q${ax},${y0} ${ax + 10},${y0} L${bx - 10},${y0} Q${bx},${y0} ${bx},${y0 + 10} L${bx},${b.bottom - 20}`
            const r = readings[`${lk.a}|${lk.b}`] || readings[`${lk.b}|${lk.a}`]
            return (
              <g key={`${lk.a}-${lk.b}`}>
                <path d={d} className="bridge-outer" />
                <path d={d} className="bridge-inner" />
                <path d={`M${a.x - a.w * 0.15},${a.top + 6} C${a.x - 30},${y0 - 70} ${(a.x + b.x) / 2 - 20},${y0 - 70} ${(a.x + b.x) / 2 - 18},${y0 - 52}`} stroke="#111827" strokeWidth="2" fill="none" />
                <path d={`M${b.x + b.w * 0.15},${b.top + 6} C${b.x + 30},${y0 - 70} ${(a.x + b.x) / 2 + 20},${y0 - 70} ${(a.x + b.x) / 2 + 18},${y0 - 52}`} stroke="#b91c1c" strokeWidth="2" fill="none" />
                <g transform={`translate(${(a.x + b.x) / 2 - 38},${y0 - 92})`}>
                  <rect width={76} height={40} rx={7} fill="#0f172a" stroke="#334155" />
                  <rect x={6} y={6} width={64} height={20} rx={3} fill="#0b3b2e" />
                  <text x={38} y={21} className="lcd">{r ? `${r.emf.toFixed(3)} V` : '0.000 V'}</text>
                  <text x={38} y={35} className="lcd-sub">woltomierz</text>
                </g>
              </g>
            )
          })}
        </svg>

        {/* naczynia */}
        {Object.values(placed).map((p) => {
          const v = p.view
          const sel = selected === p.id
          const isDrag = drag?.id === p.id
          const style: React.CSSProperties = {
            left: p.x - p.w / 2 + (isDrag ? drag.dx : 0),
            top: p.top + (isDrag ? drag.dy : 0),
            width: p.w,
            height: p.h,
            zIndex: isDrag ? 50 : v.parent ? 6 : v.type === 'burette' || v.type === 'funnel' || v.type === 'fountain' ? 5 : 4,
          }
          let graphic: JSX.Element
          if (v.type === 'burette') graphic = <BuretteGraphic view={v} selected={sel} height={TOP - p.top} />
          else if (v.type === 'utube') graphic = <UTubeGraphic view={v} selected={sel} />
          else if (v.type === 'spoon') graphic = <SpoonGraphic view={v} selected={sel} />
          else if (v.type === 'candle') graphic = <CandleGraphic view={v} selected={sel} />
          else if (v.type === 'funnel') graphic = <FunnelGraphic view={v} selected={sel} />
          else if (v.type === 'fountain') graphic = <FountainGraphic view={v} selected={sel} />
          else graphic = <VesselGraphic view={v} selected={sel} />
          const isTargetable = Boolean(link || pick)
          const burn = v.type === 'crucible' || v.type === 'evap_dish'
          return (
            <div key={p.id} className={`vessel${sel ? ' selected' : ''}${isTargetable ? ' targetable' : ''}${isDrag ? ' dragging' : ''}`}
                 style={style} onPointerDown={(e) => onVesselDown(e, p.id)}
                 onContextMenu={(e) => {
                   e.preventDefault()
                   e.stopPropagation()
                   const st = useLab.getState()
                   st.setLink(null)
                   st.select(p.id)
                   st.setCtx({ v: p.id, x: e.clientX, y: e.clientY })
                 }}>
              {v.heat && !v.parent && v.type !== 'burette' && (
                <div className={`heat-stand heat-${v.heat}`} style={{ top: p.h, width: p.w }}>
                  {(v.heat === 'alcohol' || v.heat === 'bunsen') && !TUBES.has(v.type) && v.type !== 'spoon' && <Tripod width={p.w} />}
                  {(v.heat === 'alcohol' || v.heat === 'bunsen') && <HeatSource kind={v.heat} width={p.w} tube={TUBES.has(v.type) || v.type === 'spoon'} />}
                  {v.heat === 'hotplate' && <HeatSource kind="hotplate" width={p.w} tube={false} />}
                </div>
              )}
              {(v.heat === 'water_bath' || v.heat === 'ice_bath') && (
                <div className="bath-wrap" style={{ width: p.w + 34, left: -17 }}>
                  <HeatSource kind={v.heat} width={p.w} tube={false} />
                </div>
              )}
              {graphic}
              {burn && <CrucibleGlow T={v.T} />}
              {burn && (v.fx?.flame || v.fx?.sparks || v.fx?.glow) && (
                <div className="burn-anchor" style={{ left: p.w / 2, top: 8 }}>
                  <BurnFlame color={v.fx.flame} bright={v.fx.bright} sparks={v.fx.sparks} glow={v.fx.glow} />
                </div>
              )}
              {!['burette', 'utube', 'spoon', 'candle', 'funnel', 'fountain'].includes(v.type) && (
                <div className="mouth-anchor" style={{ left: p.w / 2 }}>
                  <MouthEffects view={v} width={p.w} />
                </div>
              )}
              {flashes.filter((f) => f.v === p.id).map((f) => <FlashView key={f.id} f={f} />)}
              {showReadings && <Readings p={p} />}
              {(labels[p.id]) && <div className="vlabel">{labels[p.id]}</div>}
            </div>
          )
        })}
        {Object.values(placed).length === 0 && (
          <div className="bench-empty">
            <p>Stół jest pusty.</p>
            <p>Przeciągnij sprzęt z półki po lewej albo kliknij go, aby postawić na stole.</p>
          </div>
        )}
      </div>
      {(link || pick) && (
        <div className="target-hint" onPointerDown={(e) => e.stopPropagation()}>
          {link ? linkHint(link.kind) : pick?.kind === 'reagent' ? 'Kliknij naczynie, do którego chcesz dodać odczynnik' : 'Kliknij naczynie, którego dotyczy narzędzie'}
          <button onClick={() => useLab.getState().setLink(null)}>Anuluj</button>
        </div>
      )}
    </div>
  )
}

function linkHint(kind: string) {
  return ({
    pour: 'Kliknij naczynie, do którego chcesz przelać ciecz',
    outlet: 'Kliknij naczynie, do którego ma prowadzić rurka',
    parent: 'Kliknij cylinder, do którego chcesz wprowadzić łyżkę/świecę',
    burette: 'Kliknij naczynie pod biuretą',
    funnel: 'Kliknij naczynie pod lejkiem',
    source: 'Kliknij zlewkę z wodą pod kolbą',
    bridge: 'Kliknij drugie naczynie (klucz elektrolityczny)',
  } as Record<string, string>)[kind]
}

export function openReagent(vessel: string, reagent: string) {
  const st = useLab.getState()
  const r = st.catalog?.reagents.find((x) => x.id === reagent)
  if (!r) return
  if (r.kind === 'gas') {
    st.act({ op: 'reagent', v: vessel, reagent, amount: 1 })
    return
  }
  st.setDialog({ kind: 'reagent', vessel, reagent })
}

export function completeLink(link: NonNullable<ReturnType<typeof useLab.getState>['link']>, target: string) {
  const st = useLab.getState()
  st.setLink(null)
  if (target === link.from) return
  switch (link.kind) {
    case 'pour': st.setDialog({ kind: 'pour', from: link.from, to: target }); break
    case 'outlet': st.act({ op: 'connect', v: link.from, to: target }); break
    case 'parent': st.act({ op: 'parent', v: link.from, to: target }); break
    case 'burette': st.setDialog({ kind: 'burette', vessel: link.from, target }); break
    case 'funnel': st.act({ op: 'funnel', v: link.from, target }); break
    case 'source': st.act({ op: 'source', v: link.from, src: target }); break
    case 'bridge': st.act({ op: 'bridge', a: link.from, b: target, on: true }); break
  }
}

function FlashView({ f }: { f: { kind: string; color?: string; text?: string } }) {
  if (f.kind === 'flame')
    return (
      <div className="flash flash-flame">
        <svg width="60" height="90" viewBox="-30 -80 60 90">
          <path className="flame-flicker" d="M0,0 C-14,-10 -16,-34 -4,-56 C0,-64 1,-74 2,-80 C10,-60 18,-42 16,-24 C14,-8 8,-2 0,0 Z" fill={f.color} opacity=".9" />
          <path d="M0,-2 C-6,-8 -6,-20 0,-30 C6,-20 6,-8 0,-2 Z" fill="#fff" opacity=".55" />
        </svg>
      </div>
    )
  if (f.kind === 'paper')
    return <div className="flash flash-paper"><span style={{ background: f.color }} /></div>
  if (f.kind === 'pop') return <div className="flash flash-pop">PYK!</div>
  const icon = f.text === 'relight' ? '🔥' : f.text === 'out' ? '💨' : f.text === 'soot' ? '🌫️' : f.text === 'bright' ? '✨' : null
  if (!icon) return null
  return <div className="flash flash-splint">{icon}</div>
}

export { levelFor }

function BackShelf() {
  const bottles = [
    ['#7dd3fc', 34], ['#fca5a5', 28], ['#fde68a', 40], ['#a7f3d0', 30], ['#c4b5fd', 36], ['#f9a8d4', 26], ['#93c5fd', 38],
    ['#fdba74', 30], ['#86efac', 34], ['#e9d5ff', 28],
  ] as const
  return (
    <svg className="back-shelf" width={W} height={200} viewBox={`0 0 ${W} 200`}>
      <rect x={60} y={150} width={W - 120} height={8} rx={3} fill="#2a2119" />
      <rect x={60} y={158} width={W - 120} height={4} fill="#00000055" />
      {bottles.map(([c, h], i) => {
        const x = 110 + i * 82
        return (
          <g key={i} opacity=".55">
            <rect x={x} y={150 - h - 10} width={22} height={h + 10} rx={4} fill="#ffffff0d" stroke="#cbd5e1" strokeOpacity=".22" />
            <rect x={x + 2} y={150 - h * 0.6} width={18} height={h * 0.6 - 1} rx={3} fill={c} opacity=".35" />
            <rect x={x + 5} y={150 - h - 16} width={12} height={7} rx={2} fill="#334155" />
            <rect x={x + 3} y={150 - h * 0.85} width={16} height={8} rx={1} fill="#e2e8f0" opacity=".18" />
          </g>
        )
      })}
    </svg>
  )
}
