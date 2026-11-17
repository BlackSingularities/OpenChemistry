import { SHAPES, glassPath, levelFor } from '../shapes'
import type { VesselView } from '../types'
import { liquidFill } from './Vessel'
import { BurnFlame } from './Effects'

export function BuretteGraphic({ view, selected, height }: { view: VesselView; selected: boolean; height: number }) {
  const s = SHAPES.burette
  const level = levelFor('burette', s, view.vol)
  const { fill, opacity } = liquidFill(view)
  const open = (view.flow || 0) > 0
  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={70} height={height} viewBox={`-26 0 70 ${height}`}
         overflow="visible">
      {/* statyw */}
      <rect x={-24} y={0} width={4} height={height} fill="#4b5563" />
      <rect x={-34} y={height - 6} width={58} height={6} rx={2} fill="#374151" />
      <rect x={-22} y={70} width={30} height={5} fill="#6b7280" />
      <defs>
        <clipPath id={`clip-bur-${view.id}`}><path d={glassPath(s, s.wall) + ' Z'} /></clipPath>
      </defs>
      <g clipPath={`url(#clip-bur-${view.id})`}>
        <rect x={0} y={level} width={s.w} height={s.h} fill={fill} opacity={Math.max(opacity, 0.35)} />
      </g>
      <path d={glassPath(s, 0)} className="glass" />
      <path d={glassPath(s, 0)} className="glass-edge" />
      {Array.from({ length: 11 }).map((_, i) => {
        const y = levelFor('burette', s, 50 - i * 5)
        return <g key={i}>
          <line x1={s.w - 1} x2={s.w + 5} y1={y} y2={y} className="grad" />
          <text x={s.w + 7} y={y + 2.5} className="tick-label">{i * 5}</text>
        </g>
      })}
      {/* kurek i wylot */}
      <rect x={-3} y={266} width={s.w + 6} height={8} rx={2} fill="#cbd5e1" opacity=".7" />
      <rect x={s.w / 2 - 9} y={267} width={18} height={6} rx={2} fill={open ? '#2dd4bf' : '#64748b'}
            transform={open ? `rotate(90 ${s.w / 2} 270)` : undefined} />
      <path d={`M${s.w / 2 - 2},274 L${s.w / 2 - 1},296 L${s.w / 2 + 1},296 L${s.w / 2 + 2},274`} className="glass" />
      {open && view.vol > 0.01 && <circle className="drip" cx={s.w / 2} cy={298} r={2} fill={fill}
                                          style={{ animationDuration: `${Math.max(0.15, 0.8 / Math.max(view.flow || 0.1, 0.1))}s` }} />}
    </svg>
  )
}

export function UTubeGraphic({ view, selected }: { view: VesselView; selected: boolean }) {
  const arms = view.arms || []
  const W = 130
  const armW = 22
  const H = 170
  const xs = [22, W - 22]
  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={W} height={H + 70} viewBox={`0 -60 ${W} ${H + 70}`}
         overflow="visible">
      {/* zasilacz */}
      <g transform={`translate(${W / 2 - 28},-58)`}>
        <rect width={56} height={30} rx={5} fill="#1f2937" stroke="#334155" />
        <text x={28} y={13} className="psu-text">{view.power ? `${(view.current || 0).toFixed(2)} A` : 'OFF'}</text>
        <text x={28} y={24} className="psu-sub">12 V</text>
        <circle cx={8} cy={22} r={3} fill="#3b82f6" />
        <circle cx={48} cy={22} r={3} fill="#ef4444" />
      </g>
      <path d={`M${W / 2 - 20},-36 C${W / 2 - 30},-20 ${xs[0]},-30 ${xs[0]},-6`} stroke="#3b82f6" strokeWidth="1.6" fill="none" />
      <path d={`M${W / 2 + 20},-36 C${W / 2 + 30},-20 ${xs[1]},-30 ${xs[1]},-6`} stroke="#ef4444" strokeWidth="1.6" fill="none" />
      {arms.map((a, i) => {
        const x = xs[i]
        const { fill, opacity } = liquidFill(a)
        const frac = Math.min(1, a.vol / 30)
        const gasMl = a.gas_ml || 0
        const liquidTop = 20 + (1 - frac) * (H - 40) + Math.min(gasMl, 30) / 30 * (H - 40) * 0.6
        const bub = (a.fx?.bubbles || 0) > 1e-7
        return (
          <g key={i}>
            <rect x={x - armW / 2 + 2} y={Math.min(liquidTop, H - 30)} width={armW - 4}
                  height={Math.max(H - Math.min(liquidTop, H - 30) - 6, 0)} fill={fill} opacity={Math.max(opacity, 0.3)} />
            {a.turbid ? <rect x={x - armW / 2 + 2} y={liquidTop} width={armW - 4} height={H - liquidTop - 6}
                              fill={a.turbid_color} opacity={a.turbid * 0.8} /> : null}
            {gasMl > 0.05 && <rect x={x - armW / 2 + 2} y={8} width={armW - 4} height={Math.max(liquidTop - 8, 0)}
                                   fill={a.gas_color || '#ffffff'} opacity={a.gas_color ? 0.5 : 0.07} />}
            {/* elektroda */}
            <rect x={x - 2.5} y={-6} width={5} height={H - 60} fill={view.electrode === 'Cu' ? '#c27a45' : '#2f3237'} />
            {a.solids.some((s) => s.id === 'Cu_dep') && <rect x={x - 3.5} y={H - 120} width={7} height={54} fill="#b2602f" rx={2} />}
            {bub && Array.from({ length: 8 }).map((_, j) => (
              <circle key={j} className="bubble" cx={x + (j % 3 - 1) * 3} cy={H - 70} r={1.2}
                      style={{ ['--rise' as any]: `${-(H - 70 - liquidTop)}px`, animationDuration: `${0.8 + (j % 4) * 0.3}s`,
                               animationDelay: `${-j * 0.17}s` }} />
            ))}
            <text x={x} y={H + 8} className="arm-label">{i === 0 ? 'K (−)' : 'A (+)'}</text>
            {gasMl > 0.05 && <text x={x + armW / 2 + 3} y={30} className="tick-label">{gasMl.toFixed(1)} mL</text>}
          </g>
        )
      })}
      {/* szkło U */}
      <path d={`M${xs[0] - armW / 2},0 L${xs[0] - armW / 2},${H - 20} Q${xs[0] - armW / 2},${H} ${W / 2},${H}
                Q${xs[1] + armW / 2},${H} ${xs[1] + armW / 2},${H - 20} L${xs[1] + armW / 2},0 M${xs[1] - armW / 2},0
                L${xs[1] - armW / 2},${H - 30} Q${xs[1] - armW / 2},${H - armW} ${W / 2},${H - armW}
                Q${xs[0] + armW / 2},${H - armW} ${xs[0] + armW / 2},${H - 30} L${xs[0] + armW / 2},0`}
            className="glass" fill="none" />
    </svg>
  )
}

export function SpoonGraphic({ view, selected }: { view: VesselView; selected: boolean }) {
  const content = view.solids[0]
  const fx = view.fx || {}
  const hot = view.T > 450
  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={60} height={170} viewBox="-30 -150 60 170"
         overflow="visible">
      <rect x={-1.2} y={-150} width={2.4} height={146} fill="#9aa3ad" />
      <rect x={-12} y={-150} width={24} height={5} rx={2} fill="#6b7280" />
      <path d="M-11,-4 Q0,10 11,-4 Z" fill={hot ? '#ff7a3a' : '#8b949e'} />
      {content && <ellipse cx={0} cy={-4} rx={9} ry={3.4} fill={content.color} />}
      {view.solids.slice(1, 3).map((s, i) => <ellipse key={s.id} cx={(i - 0.5) * 6} cy={-6} rx={4} ry={2} fill={s.color} />)}
      <g transform="translate(0,-6)">
        <BurnFlame color={fx.flame} bright={fx.bright} sparks={fx.sparks} glow={fx.glow || hot} small />
      </g>
    </svg>
  )
}

export function CandleGraphic({ view, selected }: { view: VesselView; selected: boolean }) {
  const wax = view.solids.find((s) => s.id === 'Wax')
  const h = wax ? Math.max(10, Math.min(60, wax.mass * 12)) : 6
  const lit = Boolean(view.fx?.candle || view.fx?.flame)
  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={40} height={110} viewBox="-20 -90 40 110"
         overflow="visible">
      <rect x={-13} y={14} width={26} height={6} rx={2} fill="#4b5563" />
      <rect x={-7} y={14 - h} width={14} height={h} rx={2} fill="#f3eedd" />
      <rect x={-7} y={14 - h} width={4} height={h} fill="#fff" opacity=".4" />
      <line x1={0} y1={14 - h} x2={0} y2={8 - h} stroke="#222" strokeWidth="1.4" />
      {lit && <g transform={`translate(0,${9 - h})`}><BurnFlame color="#ffb347" small /></g>}
    </svg>
  )
}

export function FunnelGraphic({ view, selected }: { view: VesselView; selected: boolean }) {
  const res = view.solids
  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={80} height={90} viewBox="-40 0 80 90" overflow="visible">
      <path d="M-36,0 L-4,46 L-3,86 L3,86 L4,46 L36,0" className="glass" fill="none" />
      <path d="M-30,3 L0,42 L30,3 Z" fill="#f8fafc" opacity=".8" />
      {res.length > 0 && <path d="M-12,26 L0,42 L12,26 Q0,22 -12,26 Z" fill={res[0].color} />}
    </svg>
  )
}

export function FountainGraphic({ view, selected }: { view: VesselView; selected: boolean }) {
  const s = SHAPES.fountain
  const level = levelFor('fountain', s, view.vol)
  const { fill, opacity } = liquidFill(view)
  const jet = (view.fx?.fountain || 0) > 0.05
  const neckBottom = s.profile[s.profile.length - 1][0]
  return (
    <svg className={`vessel-svg${selected ? ' sel' : ''}`} width={s.w} height={s.h + 120} viewBox={`0 0 ${s.w} ${s.h + 120}`}
         overflow="visible">
      <defs><clipPath id={`clip-fo-${view.id}`}><path d={glassPath(s, s.wall) + ' Z'} /></clipPath></defs>
      <g clipPath={`url(#clip-fo-${view.id})`}>
        {view.vol > 0.05 && <rect x={0} y={level} width={s.w} height={s.h} fill={fill} opacity={Math.max(opacity, 0.3)} />}
        {jet && <g>
          <rect x={s.w / 2 - 1.5} y={10} width={3} height={neckBottom} fill={fill} opacity={Math.max(opacity, 0.45)} />
          {Array.from({ length: 10 }).map((_, i) => (
            <circle key={i} className="droplet" cx={s.w / 2 + ((i % 5) - 2) * 12} cy={18} r={2} fill={fill}
                    style={{ animationDelay: `${-i * 0.13}s` }} />
          ))}
        </g>}
      </g>
      <path d={glassPath(s, 0)} className="glass" />
      <path d={glassPath(s, 0)} className="glass-edge" />
      <rect x={s.w / 2 - 14} y={neckBottom - 6} width={28} height={14} rx={2} className="stopper" />
      <rect x={s.w / 2 - 1.6} y={neckBottom} width={3.2} height={118} className="tube-glass" />
    </svg>
  )
}

export function CrucibleGlow({ T }: { T: number }) {
  if (T < 500) return null
  const a = Math.min(0.85, (T - 500) / 700)
  return <div className="crucible-glow" style={{ opacity: a }} />
}
