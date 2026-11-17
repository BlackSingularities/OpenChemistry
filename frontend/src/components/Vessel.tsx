import { memo, useMemo } from 'react'
import { SHAPES, glassPath, halfWidthAt, levelFor, type Shape } from '../shapes'
import type { SolidView, VesselView } from '../types'

function rnd(seed: number) {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453
  return x - Math.floor(x)
}

function hexToRgb(h: string): [number, number, number] {
  const s = h.replace('#', '')
  return [parseInt(s.slice(0, 2), 16), parseInt(s.slice(2, 4), 16), parseInt(s.slice(4, 6), 16)]
}

export function liquidFill(view: VesselView): { fill: string; opacity: number } {
  if (!view.liquid) return { fill: '#cfe8ff', opacity: 0.22 }
  const [r, g, b] = hexToRgb(view.liquid)
  const absorb = view.absorb ?? 0
  const op = Math.min(0.92, 0.2 + absorb * 1.6)
  // ciecz bezbarwna: delikatny błękitny połysk wody
  if (r > 238 && g > 238 && b > 238) return { fill: '#a9d4ff', opacity: 0.3 }
  return { fill: `rgb(${r},${g},${b})`, opacity: op }
}

function bubbleCount(rate: number, boiling: boolean): number {
  if (boiling) return 16
  if (!rate || rate < 2e-7) return 0
  return Math.max(2, Math.min(22, Math.round((Math.log10(rate) + 6.7) * 4)))
}

const BIG_STYLES = new Set(['nail', 'wire', 'foil', 'ribbon', 'granules', 'chips', 'lump', 'chunk', 'tree', 'deposit',
  'pellets', 'wool', 'slice', 'candle', 'molten'])

interface Props {
  view: VesselView
  selected: boolean
  hot?: boolean
}

export const VesselGraphic = memo(function VesselGraphic({ view, selected }: Props) {
  const s = SHAPES[view.type] || SHAPES.beaker_100
  const id = view.id.replace(/[^a-zA-Z0-9]/g, '')
  const cx = s.w / 2
  const bottom = s.profile[s.profile.length - 1][0]
  const inner = useMemo(() => glassPath(s, s.wall), [view.type])
  const outer = useMemo(() => glassPath(s, 0), [view.type])
  const level = levelFor(view.type, s, view.vol)
  const orgLevel = levelFor(view.type, s, view.vol + view.org_vol)
  const { fill, opacity } = liquidFill(view)
  const boiling = Boolean(view.fx?.boiling)
  const nb = bubbleCount(view.fx?.bubbles || 0, boiling)
  const hasLiquid = view.vol > 0.05
  const topLiquid = Math.min(level, orgLevel)

  // osady: układamy warstwy od dna
  const settledLayers: { s: SolidView; y0: number; y1: number }[] = []
  const bigs: SolidView[] = []
  let acc = 0
  for (const so of view.solids) {
    if (BIG_STYLES.has(so.style)) {
      bigs.push(so)
      continue
    }
    const sv = so.vol * (hasLiquid ? so.settled : 1)
    if (sv < 0.0005) continue
    const y0 = levelFor(view.type, s, acc)
    acc += Math.max(sv * 1.1, 0.02)
    const y1 = levelFor(view.type, s, acc)
    settledLayers.push({ s: so, y0, y1: Math.min(y1, y0 - 1.2) })
  }
  const sedTop = settledLayers.length ? settledLayers[settledLayers.length - 1].y1 : bottom

  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={s.w} height={s.h} viewBox={`0 0 ${s.w} ${s.h}`}
         overflow="visible">
      <defs>
        <clipPath id={`clip-${id}`}><path d={inner + ' Z'} /></clipPath>
        <linearGradient id={`liq-${id}`} x1="0" x2="1" y1="0" y2="0">
          <stop offset="0" stopColor={fill} stopOpacity={Math.min(1, opacity * 1.25)} />
          <stop offset=".45" stopColor={fill} stopOpacity={opacity * 0.86} />
          <stop offset="1" stopColor={fill} stopOpacity={Math.min(1, opacity * 1.2)} />
        </linearGradient>
      </defs>

      {/* gaz nad cieczą */}
      {view.gas_color && (
        <g clipPath={`url(#clip-${id})`}>
          <rect x={0} y={0} width={s.w} height={topLiquid} fill={view.gas_color}
                opacity={Math.min(0.85, (view.gas_alpha || 0.3) + 0.1)} className="gas-fill" />
        </g>
      )}

      <g clipPath={`url(#clip-${id})`}>
        {/* lustro srebrne na ściankach */}
        {view.mirror ? <rect x={0} y={Math.max(level - 6, 0)} width={s.w} height={bottom} fill="url(#mirror)"
                             opacity={0.85} /> : null}
        {/* faza wodna */}
        {hasLiquid && (
          <>
            <rect x={0} y={level} width={s.w} height={bottom - level + 2} fill={`url(#liq-${id})`}
                  className="liquid" />
            {view.turbid ? (
              <rect x={0} y={level} width={s.w} height={bottom - level + 2} fill={view.turbid_color || '#fff'}
                    opacity={Math.min(0.95, view.turbid * 0.92)} className="turbid" />
            ) : null}
            {view.turbid && view.turbid > 0.05 ? <Flakes s={s} level={level} bottom={sedTop} color={view.turbid_color || '#fff'}
                                                         seed={id.length} amount={view.turbid} /> : null}
          </>
        )}
        {/* faza organiczna */}
        {view.org_vol > 0.05 && (
          <rect x={0} y={orgLevel} width={s.w} height={Math.max(level - orgLevel, 0.5)}
                fill={view.org_color || '#fff6d8'} opacity={view.org_color ? 0.75 : 0.35} className="liquid" />
        )}
        {/* osady na dnie */}
        {settledLayers.map(({ s: so, y0, y1 }, i) => (
          <Sediment key={so.id + i} so={so} shape={s} y0={y0} y1={y1} />
        ))}
        {/* duże kawałki ciał stałych */}
        {bigs.map((so, i) => (
          <BigSolid key={so.id} so={so} shape={s} index={i} bottom={sedTop} level={level} hasLiquid={hasLiquid}
                    floatTop={Boolean(view.fx?.float) && (so.id === 'Na' || so.id === 'K' || so.id === 'Li')}
                    skate={Boolean(view.fx?.skate)} />
        ))}
        {/* powierzchnia cieczy */}
        {hasLiquid && <rect x={0} y={topLiquid} width={s.w} height={2.2} fill="#e0f2ff" opacity=".35" />}
        {/* menisk */}
        {hasLiquid && (
          <path d={`M${cx - halfWidthAt(s, level) + s.wall},${level} Q${cx},${level + 3.2} ${cx + halfWidthAt(s, level) - s.wall},${level}`}
                fill="none" stroke="#fff" strokeOpacity=".55" strokeWidth="1.1" />
        )}
        {/* pęcherzyki */}
        {hasLiquid && nb > 0 && Array.from({ length: nb }).map((_, i) => {
          const hw = Math.max(halfWidthAt(s, (level + bottom) / 2) - s.wall - 3, 2)
          const x = cx + (rnd(i * 7.1 + id.length) - 0.5) * 2 * hw
          const r = boiling ? 1.6 + rnd(i * 3.3) * 2.6 : 0.8 + rnd(i * 5.1) * 1.6
          const dur = (boiling ? 0.7 : 1.2) + rnd(i * 2.7) * 1.4
          const rise = Math.max(bottom - level - 4, 3)
          return <circle key={i} className="bubble" cx={x} cy={bottom - 3} r={r}
                         style={{ ['--rise' as any]: `${-rise}px`, animationDuration: `${dur}s`,
                                  animationDelay: `${-rnd(i * 9.7) * dur}s` }} />
        })}
        {/* chemiluminescencja */}
        {view.fx?.lum && hasLiquid ? <rect x={0} y={level} width={s.w} height={bottom - level} fill={view.fx.lum}
                                            className="lum" /> : null}
        {/* odblask na ściance */}
        <rect x={cx - (s.profile[0][1]) * 0.62} y={0} width={Math.max(s.profile[0][1] * 0.16, 2)} height={s.h}
              fill="#fff" opacity=".09" />
      </g>

      {/* szkło */}
      <path d={outer} className="glass" />
      <path d={outer} className="glass-edge" />
      {s.marks?.map((m) => {
        const y = levelFor(view.type, s, m)
        const hw = halfWidthAt(s, y)
        return <line key={m} x1={cx - hw + 4} x2={cx - hw + (m % 50 === 0 ? 13 : 9)} y1={y} y2={y}
                     className="grad" />
      })}
      {s.lip ? <rect x={cx - s.profile[0][1] - s.lip} y={-1.5} width={(s.profile[0][1] + s.lip) * 2} height={3.5}
                     rx={1.6} className="lip" /> : null}
      {view.stopper && view.type !== 'gas_jar' && view.type !== 'fountain' && (
        <path d={`M${cx - s.profile[0][1] - 2.5},-12 L${cx + s.profile[0][1] + 2.5},-12 L${cx + s.profile[0][1] - 1},8 L${cx - s.profile[0][1] + 1},8 Z`}
              className="stopper" />
      )}
      {view.type === 'gas_jar' && view.stopper && (
        <rect x={cx - s.profile[0][1] - 6} y={-5} width={(s.profile[0][1] + 6) * 2} height={4} rx={1.5} className="lid" />
      )}
      {view.fx?.frost || view.T < 1 ? <path d={outer} className="frost" /> : null}
    </svg>
  )
})

function Flakes({ s, level, bottom, color, seed, amount }: { s: Shape; level: number; bottom: number; color: string;
  seed: number; amount: number }) {
  const n = Math.min(26, Math.round(amount * 30))
  const cx = s.w / 2
  return (
    <g opacity={0.8}>
      {Array.from({ length: n }).map((_, i) => {
        const y = level + rnd(i * 4.4 + seed) * Math.max(bottom - level - 2, 1)
        const hw = Math.max(halfWidthAt(s, y) - s.wall - 2, 1)
        const x = cx + (rnd(i * 8.8 + seed) - 0.5) * 2 * hw
        return <circle key={i} cx={x} cy={y} r={0.7 + rnd(i) * 0.9} fill={color} className="flake"
                       style={{ animationDelay: `${-rnd(i * 3.1) * 6}s` }} />
      })}
    </g>
  )
}

function Sediment({ so, shape, y0, y1 }: { so: SolidView; shape: Shape; y0: number; y1: number }) {
  const cx = shape.w / 2
  const h = Math.max(y0 - y1, 1.2)
  const top = y0 - h
  const w = halfWidthAt(shape, top) * 2 + 2
  const pat = so.style === 'crystals' || so.style === 'needles' || so.style === 'octahedra' || so.style === 'spangles'
    ? 'url(#pat-crystal)' : so.style === 'gel' || so.style === 'curdy' || so.style === 'fluffy' ? 'url(#pat-gel)'
      : so.style === 'char' ? 'url(#pat-char)' : 'url(#pat-powder)'
  return (
    <g>
      <path d={`M${cx - w / 2},${y0 + 4} L${cx - w / 2},${top + 1.5} Q${cx},${top - Math.min(h * 0.5, 3)} ${cx + w / 2},${top + 1.5} L${cx + w / 2},${y0 + 4} Z`}
            fill={so.color} />
      <path d={`M${cx - w / 2},${y0 + 4} L${cx - w / 2},${top + 1.5} Q${cx},${top - Math.min(h * 0.5, 3)} ${cx + w / 2},${top + 1.5} L${cx + w / 2},${y0 + 4} Z`}
            fill={pat} opacity={0.55} />
      {so.style === 'spangles' && Array.from({ length: 8 }).map((_, i) => (
        <rect key={i} x={cx + (rnd(i * 3) - 0.5) * w * 0.8} y={top - 2 - rnd(i * 7) * 6} width={2.6} height={1.2}
              fill="#ffe27a" className="sparkle" style={{ animationDelay: `${rnd(i) * 2}s` }}
              transform={`rotate(${rnd(i * 5) * 180} ${cx} ${top})`} />
      ))}
    </g>
  )
}

function BigSolid({ so, shape, index, bottom, level, hasLiquid, floatTop, skate }: { so: SolidView; shape: Shape;
  index: number; bottom: number; level: number; hasLiquid: boolean; floatTop: boolean; skate: boolean }) {
  const cx = shape.w / 2 + (index % 2 === 0 ? -1 : 1) * index * 5
  const hw = halfWidthAt(shape, bottom - 6) - shape.wall
  const scale = Math.max(0.55, Math.min(1.6, Math.cbrt(Math.max(so.mass, 0.005)) * 1.3))
  const y = bottom - 2
  const col = so.color
  switch (so.style) {
    case 'nail': {
      const len = Math.min(hw * 2 - 4, 46)
      return (
        <g transform={`rotate(-8 ${cx} ${y})`}>
          <rect x={cx - len / 2} y={y - 4} width={len} height={3.2} rx={1} fill={col} />
          <rect x={cx - len / 2 - 2} y={y - 6} width={3} height={7} rx={1} fill={col} />
          <rect x={cx - len / 2} y={y - 4} width={len} height={1} fill="#fff" opacity=".25" />
        </g>
      )
    }
    case 'wire':
      return (
        <path d={`M${cx - 6},${y} q4,-14 0,-20 q-4,-6 0,-12 q4,-6 0,-12 q-4,-6 0,-12`} fill="none" stroke={col}
              strokeWidth="1.8" />
      )
    case 'ribbon':
      return <path d={`M${cx - 10},${y - 2} q8,-8 14,-2 t10,-3`} fill="none" stroke={col} strokeWidth="2.2"
                   strokeLinecap="round" />
    case 'foil':
      return <path d={`M${cx - 8 * scale},${y} l3,-9 l6,2 l5,-6 l4,8 l-3,5 z`} fill={col} stroke="#fff" strokeOpacity=".3"
                   strokeWidth=".6" />
    case 'tree':
    case 'deposit':
      return (
        <g stroke={col} strokeWidth="1.3" fill="none" opacity=".95">
          {Array.from({ length: 7 }).map((_, i) => {
            const x0 = cx + (rnd(i * 2.3) - 0.5) * hw * 1.4
            const hgt = (10 + rnd(i * 4.1) * 18) * scale
            return <path key={i} d={`M${x0},${y} l${(rnd(i) - 0.5) * 6},${-hgt * 0.5} l${(rnd(i * 3) - 0.5) * 8},${-hgt * 0.5} m${-(rnd(i * 3) - 0.5) * 4},${hgt * 0.25} l5,-4`} />
          })}
        </g>
      )
    case 'molten':
      return <ellipse cx={cx} cy={y - 3} rx={hw * 0.6} ry={4} fill={col} className="glowing" />
    case 'lump': {
      const yy = floatTop && hasLiquid ? level - 1 : y - 4
      return (
        <g className={skate && floatTop ? 'skate' : ''}>
          <ellipse cx={cx} cy={yy} rx={5 * scale} ry={3.6 * scale} fill={col} />
          <ellipse cx={cx - 1.5} cy={yy - 1} rx={2 * scale} ry={1} fill="#fff" opacity=".6" />
        </g>
      )
    }
    case 'chips':
    case 'chunk':
    case 'pellets':
    case 'granules':
    case 'wool':
    case 'slice':
    default: {
      const n = so.style === 'pellets' ? 6 : so.style === 'granules' ? 3 : so.style === 'chips' ? 4 : 2
      return (
        <g>
          {Array.from({ length: n }).map((_, i) => {
            const x0 = cx + (rnd(i * 5.3 + index) - 0.5) * hw * 1.2
            const rr = (so.style === 'pellets' ? 2.6 : so.style === 'wool' ? 7 : 4.2) * scale
            if (so.style === 'wool')
              return <circle key={i} cx={x0} cy={y - rr} r={rr} fill="none" stroke={col} strokeWidth=".7"
                             strokeDasharray="1.5 1" />
            if (so.style === 'chips')
              return <path key={i} d={`M${x0 - rr},${y} l${rr * 0.4},${-rr * 1.3} l${rr * 1.2},${-rr * 0.3} l${rr * 0.6},${rr * 1.6} z`}
                           fill={col} stroke="#00000020" />
            if (so.style === 'slice')
              return <rect key={i} x={x0 - 9} y={y - 4} width={18} height={4} rx={2} fill={col} />
            return <ellipse key={i} cx={x0} cy={y - rr * 0.8} rx={rr} ry={rr * 0.8} fill={col} stroke="#00000025" />
          })}
        </g>
      )
    }
  }
}
