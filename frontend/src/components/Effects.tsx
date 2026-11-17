import type { VesselView } from '../types'

function rnd(seed: number) {
  const x = Math.sin(seed * 12.9898 + 78.233) * 43758.5453
  return x - Math.floor(x)
}

/** Efekty nad wylotem naczynia: para, dym, płomień, iskry, piana. Współrzędne względem środka wylotu. */
export function MouthEffects({ view, width }: { view: VesselView; width: number }) {
  const fx = view.fx || {}
  const steam = Math.max(fx.steam || 0, view.vol > 0.5 && view.T > 70 ? (view.T - 70) / 40 : 0)
  const smoke = fx.smoke_level ? Math.min(1, fx.smoke_level) : 0
  const flame: string | undefined = fx.flame
  const intensity = Math.min(1, fx.intensity ?? 0.6)
  return (
    <svg className="mouth-fx" width={width + 120} height={220} viewBox={`${-(width + 120) / 2} -200 ${width + 120} 220`}
         overflow="visible">
      {steam > 0.04 && Array.from({ length: 4 }).map((_, i) => (
        <path key={`st${i}`} className="steam" d={`M${(i - 1.5) * width * 0.14},0 c-8,-14 10,-24 0,-40 c-8,-12 8,-22 2,-36`}
              style={{ animationDelay: `${-i * 0.7}s`, opacity: Math.min(0.7, steam) }} />
      ))}
      {smoke > 0.03 && Array.from({ length: 7 }).map((_, i) => (
        <circle key={`sm${i}`} className="smoke" cx={(rnd(i * 3.3) - 0.5) * width * 0.5} cy={-6} r={6 + rnd(i) * 8}
                fill={fx.smoke || '#eeeeee'}
                style={{ animationDelay: `${-rnd(i * 7.7) * 3}s`, opacity: 0.25 + smoke * 0.5 }} />
      ))}
      {fx.foam && (
        <g className="foam" style={{ ['--foam' as any]: `${Math.min(1, intensity + 0.3)}` }}>
          {Array.from({ length: 14 }).map((_, i) => (
            <circle key={i} cx={(rnd(i * 2.1) - 0.5) * width * 0.9} cy={-8 - rnd(i * 5.5) * 70 * (0.4 + intensity)}
                    r={8 + rnd(i * 4.4) * 10} fill={fx.foam} />
          ))}
        </g>
      )}
      {fx.blacksnake && (
        <path className="blacksnake" d={`M${-width * 0.28},6 C${-width * 0.3},-40 ${width * 0.3},-60 ${width * 0.12},-110 C0,-130 ${-width * 0.1},-120 ${-width * 0.02},-100 C${width * 0.2},-60 ${width * 0.3},-30 ${width * 0.28},6 Z`}
              fill="#151210" />
      )}
      {fx.volcano && Array.from({ length: 10 }).map((_, i) => (
        <circle key={`v${i}`} className="ash" cx={(rnd(i) - 0.5) * 30} cy={-10} r={2 + rnd(i * 2) * 3} fill="#3f6e2e"
                style={{ animationDelay: `${-rnd(i * 6) * 1.5}s` }} />
      ))}
    </svg>
  )
}

/** Płomień spalanej substancji (łyżka, tygiel, świeca). */
export function BurnFlame({ color, bright, sparks, glow, small }: { color?: string; bright?: boolean;
  sparks?: string; glow?: boolean; small?: boolean }) {
  const k = small ? 0.55 : 1
  return (
    <svg className="burn-flame" width={160} height={180} viewBox="-80 -160 160 180" overflow="visible">
      {bright && <circle cx={0} cy={-14} r={60} fill="url(#brightGlow)" className="bright-glow" />}
      {color && (
        <g className="flame-flicker" transform={`scale(${k})`}>
          <path d="M0,0 C-16,-10 -18,-34 -6,-56 C-2,-64 0,-78 2,-84 C8,-66 20,-48 18,-26 C16,-10 10,-2 0,0 Z"
                fill={color} opacity={0.82} />
          <path d="M0,-2 C-8,-10 -9,-26 -2,-40 C1,-46 2,-52 3,-56 C7,-42 12,-30 10,-18 C9,-8 5,-3 0,-2 Z"
                fill="#fffbe8" opacity={bright ? 0.95 : 0.6} />
        </g>
      )}
      {glow && <circle cx={0} cy={-4} r={14} fill="url(#emberGlow)" className="ember" />}
      {sparks && Array.from({ length: 16 }).map((_, i) => {
        const a = (-Math.PI / 2) + (rnd(i * 3.7) - 0.5) * 2.6
        return (
          <line key={i} className="spark" x1={0} y1={-6} x2={Math.cos(a) * 9} y2={-6 + Math.sin(a) * 9}
                stroke={sparks} strokeWidth={1.6} strokeLinecap="round"
                style={{ ['--dx' as any]: `${Math.cos(a) * (40 + rnd(i) * 50)}px`,
                         ['--dy' as any]: `${Math.sin(a) * (40 + rnd(i) * 50) + 30}px`,
                         animationDelay: `${-rnd(i * 5.5) * 0.9}s` }} />
        )
      })}
    </svg>
  )
}

/** Palnik, płyta, łaźnia – wyświetlane pod naczyniem. */
export function HeatSource({ kind, width, tube }: { kind: string; width: number; tube: boolean }) {
  if (kind === 'water_bath' || kind === 'ice_bath') {
    const w = width + 34
    return (
      <svg className="bath" width={w} height={70} viewBox={`0 0 ${w} 70`}>
        <path d={`M2,8 L2,62 Q2,68 8,68 L${w - 8},68 Q${w - 2},68 ${w - 2},62 L${w - 2},8`} fill="none"
              stroke="#cfd8e3" strokeOpacity=".5" strokeWidth="2" />
        <rect x={4} y={22} width={w - 8} height={44} fill={kind === 'ice_bath' ? '#d6efff' : '#7cc3ff'}
              opacity={kind === 'ice_bath' ? 0.35 : 0.3} />
        {kind === 'ice_bath'
          ? Array.from({ length: 6 }).map((_, i) => (
            <rect key={i} x={8 + i * ((w - 26) / 6)} y={18 + (i % 2) * 6} width={12} height={10} rx={2} fill="#f2fbff"
                  opacity=".75" transform={`rotate(${(i % 3) * 12 - 10} ${14 + i * 10} 24)`} />
          ))
          : Array.from({ length: 5 }).map((_, i) => (
            <path key={i} className="steam small" d={`M${12 + i * (w - 24) / 4},20 c-4,-6 4,-10 0,-16`}
                  style={{ animationDelay: `${-i * 0.5}s` }} />
          ))}
      </svg>
    )
  }
  if (kind === 'hotplate') {
    return (
      <svg className="hotplate" width={width + 40} height={34} viewBox={`0 0 ${width + 40} 34`}>
        <rect x={2} y={8} width={width + 36} height={22} rx={4} fill="#2b3442" stroke="#3b475a" />
        <rect x={10} y={2} width={width + 20} height={8} rx={3} fill="url(#hotplateGlow)" />
        <circle cx={width + 26} cy={20} r={3} fill="#ff6b3d" />
      </svg>
    )
  }
  const bunsen = kind === 'bunsen'
  return (
    <svg className="burner" width={70} height={tube ? 120 : 98} viewBox={`-35 ${tube ? -60 : -38} 70 ${tube ? 120 : 98}`}
         overflow="visible">
      <g className="flame-flicker fast">
        {bunsen ? (
          <>
            <path d="M0,0 C-9,-8 -8,-30 0,-52 C8,-30 9,-8 0,0 Z" fill="#5aa9ff" opacity=".45" />
            <path d="M0,-2 C-5,-8 -4,-18 0,-30 C4,-18 5,-8 0,-2 Z" fill="#2d7dff" opacity=".85" />
          </>
        ) : (
          <>
            <path d="M0,0 C-8,-6 -9,-22 -2,-36 C0,-40 1,-46 1,-50 C6,-36 10,-20 8,-10 C6,-4 4,-1 0,0 Z" fill="#ffb347"
                  opacity=".85" />
            <path d="M0,-1 C-4,-5 -4,-12 0,-18 C4,-12 4,-5 0,-1 Z" fill="#6aa8ff" opacity=".8" />
          </>
        )}
      </g>
      {bunsen ? (
        <g>
          <rect x={-5} y={0} width={10} height={44} fill="#9aa4b2" />
          <rect x={-5} y={0} width={3} height={44} fill="#fff" opacity=".25" />
          <rect x={-18} y={44} width={36} height={8} rx={2} fill="#6b7686" />
          <rect x={-7} y={30} width={14} height={6} rx={1} fill="#7b8696" />
        </g>
      ) : (
        <g>
          <rect x={-2} y={0} width={4} height={8} fill="#e8e1cf" />
          <rect x={-5} y={6} width={10} height={6} fill="#8f98a5" />
          <path d="M-20,58 Q-24,30 -12,14 L12,14 Q24,30 20,58 Z" fill="#cde8ff" fillOpacity=".22" stroke="#d7e6f5"
                strokeOpacity=".6" />
          <path d="M-20,58 Q-22,42 -18,34 L18,34 Q22,42 20,58 Z" fill="#9ad0ff" fillOpacity=".35" />
        </g>
      )}
    </svg>
  )
}

export function Tripod({ width }: { width: number }) {
  return (
    <svg className="tripod" width={width + 30} height={86} viewBox={`0 0 ${width + 30} 86`}>
      <rect x={4} y={0} width={width + 22} height={4} fill="#59636f" />
      <path d={`M${8},4 L4,86 M${width + 22},4 L${width + 26},86 M${(width + 30) / 2},4 L${(width + 30) / 2},70`}
            stroke="#59636f" strokeWidth="3" />
      <path d={`M10,2 L${width + 20},2`} stroke="#c0c6cf" strokeDasharray="2 2" strokeWidth="2" />
    </svg>
  )
}
