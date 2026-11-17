import { useState } from 'react'
import { LineChart, X } from 'lucide-react'
import { useLab } from '../store'
import { fmt } from '../chem'

export default function TitrationChart() {
  const titration = useLab((s) => s.titration)
  const [hidden, setHidden] = useState(false)
  const series = Object.entries(titration).filter(([, s]) => s.points.length > 2)
  if (!series.length || hidden) return null
  const [bid, s] = series[series.length - 1]
  const W = 300
  const Hh = 150
  const pad = { l: 30, r: 10, t: 10, b: 24 }
  const maxV = Math.max(5, ...s.points.map((p) => p[0]))
  const xv = (v: number) => pad.l + (v / maxV) * (W - pad.l - pad.r)
  const yv = (ph: number) => pad.t + (1 - Math.max(0, Math.min(14, ph)) / 14) * (Hh - pad.t - pad.b)
  const d = s.points.map((p, i) => `${i ? 'L' : 'M'}${xv(p[0]).toFixed(1)},${yv(p[1]).toFixed(1)}`).join(' ')
  const last = s.points[s.points.length - 1]
  return (
    <div className="chart">
      <div className="chart-head">
        <LineChart size={14} /> Krzywa miareczkowania <small>({bid} → {s.target})</small>
        <button className="icon-only" onClick={() => setHidden(true)} aria-label="Ukryj wykres"><X size={14} /></button>
      </div>
      <svg width="100%" viewBox={`0 0 ${W} ${Hh}`}>
        {[0, 7, 14].map((ph) => (
          <g key={ph}>
            <line x1={pad.l} x2={W - pad.r} y1={yv(ph)} y2={yv(ph)} className="grid" />
            <text x={pad.l - 6} y={yv(ph) + 3} className="axis" textAnchor="end">{ph}</text>
          </g>
        ))}
        {[0, 0.5, 1].map((f) => (
          <text key={f} x={xv(maxV * f)} y={Hh - 8} className="axis" textAnchor="middle">{fmt(maxV * f, 0)}</text>
        ))}
        <text x={W - pad.r} y={Hh - 8} className="axis" textAnchor="end">mL</text>
        <path d={d} className="curve" />
        <circle cx={xv(last[0])} cy={yv(last[1])} r={3.5} className="curve-dot" />
      </svg>
      <div className="chart-foot">V = {fmt(last[0], 2)} mL · pH = {fmt(last[1], 2)}</div>
    </div>
  )
}
