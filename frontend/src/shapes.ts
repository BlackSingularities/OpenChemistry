/**
 * Geometria naczyń. Każde naczynie opisane jest profilem wnętrza: lista punktów (y, r) od wylotu do dna
 * (y rośnie w dół, r – połowa szerokości wnętrza). Na tej podstawie rysujemy kontur szkła oraz liczymy,
 * na jakiej wysokości znajduje się powierzchnia cieczy dla danej objętości (całka z πr²).
 */

export interface Shape {
  w: number
  h: number
  profile: [number, number][]
  wall: number
  cap: number
  flat?: boolean // naczynie płaskie (objętość ∝ szerokość, nie πr²)
  lip?: number
  spout?: boolean
  marks?: number[]
  label?: string
}

function circleBottom(yStart: number, r: number, n = 10): [number, number][] {
  const pts: [number, number][] = []
  for (let i = 1; i <= n; i++) {
    const a = (i / n) * (Math.PI / 2)
    pts.push([yStart + Math.sin(a) * r, Math.cos(a) * r])
  }
  return pts
}

function roundedFlat(yBottom: number, r: number, cr: number): [number, number][] {
  const pts: [number, number][] = []
  for (let i = 0; i <= 6; i++) {
    const a = (i / 6) * (Math.PI / 2)
    pts.push([yBottom - cr + Math.sin(a) * cr, r - cr + Math.cos(a) * cr])
  }
  pts.push([yBottom, 0])
  return pts
}

function sphereProfile(neckR: number, neckLen: number, R: number, n = 22): [number, number][] {
  const cy = neckLen + Math.sqrt(R * R - neckR * neckR)
  const pts: [number, number][] = [[0, neckR], [neckLen, neckR]]
  const a0 = Math.asin(neckR / R)
  for (let i = 1; i <= n; i++) {
    const a = a0 + (i / n) * (Math.PI - a0)
    const y = cy - Math.cos(a) * R
    const r = Math.sin(a) * R
    pts.push([y, Math.max(r, 0)])
  }
  return pts
}

export const SHAPES: Record<string, Shape> = {
  test_tube: { w: 30, h: 168, wall: 1.6, cap: 20, lip: 2, profile: [[0, 11], [154, 11], ...circleBottom(154, 11)] },
  boiling_tube: { w: 40, h: 196, wall: 1.8, cap: 40, lip: 2, profile: [[0, 15], [178, 15], ...circleBottom(178, 15)] },
  beaker_100: {
    w: 76, h: 96, wall: 2, cap: 100, spout: true, marks: [25, 50, 75], profile: [[0, 34], ...roundedFlat(92, 34, 5)],
  },
  beaker_250: {
    w: 98, h: 122, wall: 2.2, cap: 250, spout: true, marks: [50, 100, 150, 200],
    profile: [[0, 45], ...roundedFlat(118, 45, 6)],
  },
  beaker_600: {
    w: 126, h: 152, wall: 2.4, cap: 600, spout: true, marks: [100, 200, 300, 400, 500],
    profile: [[0, 59], ...roundedFlat(148, 59, 7)],
  },
  flask_250: {
    w: 120, h: 166, wall: 2.2, cap: 250, lip: 2, marks: [50, 100, 150, 200],
    profile: [[0, 13], [42, 13], [60, 22], [158, 56], [161, 55], [163.5, 50], [164, 0]],
  },
  round_flask: { w: 128, h: 178, wall: 2.2, cap: 250, lip: 2, profile: sphereProfile(12, 46, 62) },
  cylinder_100: {
    w: 34, h: 214, wall: 1.8, cap: 100, spout: true, marks: [10, 20, 30, 40, 50, 60, 70, 80, 90],
    profile: [[0, 14], ...roundedFlat(200, 14, 2)],
  },
  gas_jar: { w: 76, h: 158, wall: 2.4, cap: 250, lip: 3, profile: [[0, 33], ...roundedFlat(154, 33, 5)] },
  evap_dish: {
    w: 140, h: 44, wall: 2.6, cap: 60,
    profile: [[0, 66], [8, 63], [16, 57], [24, 47], [31, 34], [36, 20], [39, 8], [40, 0]],
  },
  crucible: { w: 50, h: 46, wall: 3, cap: 15, profile: [[0, 22], [34, 15], [38, 12], [40, 0]] },
  trough: { w: 290, h: 92, wall: 3, cap: 1000, flat: true, profile: [[0, 140], ...roundedFlat(88, 140, 10)] },
  watch_glass: { w: 92, h: 16, wall: 2, cap: 5, flat: true, profile: [[0, 44], [6, 36], [11, 20], [14, 0]] },
  petri: { w: 120, h: 20, wall: 2, cap: 40, flat: true, profile: [[0, 58], [17, 58], [18, 0]] },
  burette: { w: 18, h: 300, wall: 1.4, cap: 50, profile: [[0, 5.5], [262, 5.5], [266, 0]] },
  fountain: { w: 128, h: 178, wall: 2.2, cap: 250, profile: [] },
  funnel: { w: 76, h: 86, wall: 2, cap: 0, profile: [[0, 36], [46, 5], [86, 3]] },
  spoon: { w: 26, h: 24, wall: 2, cap: 3, profile: [[0, 11], [8, 9], [12, 0]] },
  candle: { w: 22, h: 80, wall: 0, cap: 0, profile: [] },
  utube: { w: 130, h: 190, wall: 2, cap: 60, profile: [] },
}

// fontanna: odwrócona kolba okrągła (szyjka na dole)
{
  const p = sphereProfile(12, 46, 62)
  const H = p[p.length - 1][0]
  SHAPES.fountain.profile = p.map(([y, r]) => [H - y, r] as [number, number]).reverse()
}

export function glassPath(s: Shape, inset = 0): string {
  const cx = s.w / 2
  const left: string[] = []
  const right: string[] = []
  s.profile.forEach(([y, r], i) => {
    const rr = Math.max(r - inset, 0)
    const yy = i === s.profile.length - 1 ? y - inset : y
    left.push(`${(cx - rr).toFixed(2)},${yy.toFixed(2)}`)
    right.push(`${(cx + rr).toFixed(2)},${yy.toFixed(2)}`)
  })
  return `M${left.join(' L')} L${right.reverse().join(' L')}`
}

/** Tabela objętości (od dna) w funkcji wysokości – do wyznaczenia poziomu cieczy. */
const volCache = new Map<string, { ys: number[]; vs: number[] }>()

function volumeTable(key: string, s: Shape) {
  const c = volCache.get(key)
  if (c) return c
  const top = s.profile[0][0]
  const bottom = s.profile[s.profile.length - 1][0]
  const N = 160
  const rAt = (y: number) => {
    const p = s.profile
    for (let i = 0; i < p.length - 1; i++) {
      const [y0, r0] = p[i]
      const [y1, r1] = p[i + 1]
      if ((y >= y0 && y <= y1) || (y <= y0 && y >= y1)) {
        if (y1 === y0) return Math.max(r0, r1)
        return r0 + ((r1 - r0) * (y - y0)) / (y1 - y0)
      }
    }
    return 0
  }
  const ys: number[] = []
  const vs: number[] = []
  let acc = 0
  const dy = (bottom - top) / N
  ys.push(bottom)
  vs.push(0)
  for (let i = 1; i <= N; i++) {
    const y = bottom - i * dy
    const r = Math.max(rAt(y + dy / 2) - s.wall, 0)
    acc += (s.flat ? r * 2 : Math.PI * r * r) * dy
    ys.push(y)
    vs.push(acc)
  }
  // skalowanie: pełne naczynie (do 92% wysokości) = pojemność nominalna
  const fullIdx = Math.floor(N * 0.92)
  const scale = s.cap > 0 ? s.cap / vs[fullIdx] : 1
  const out = { ys, vs: vs.map((v) => v * scale) }
  volCache.set(key, out)
  return out
}

export function levelFor(key: string, s: Shape, vol: number): number {
  const { ys, vs } = volumeTable(key, s)
  if (vol <= 0) return ys[0]
  for (let i = 1; i < vs.length; i++) {
    if (vs[i] >= vol) {
      const t = (vol - vs[i - 1]) / (vs[i] - vs[i - 1] || 1)
      return ys[i - 1] + (ys[i] - ys[i - 1]) * t
    }
  }
  return ys[ys.length - 1]
}

export function halfWidthAt(s: Shape, y: number): number {
  const p = s.profile
  for (let i = 0; i < p.length - 1; i++) {
    const [y0, r0] = p[i]
    const [y1, r1] = p[i + 1]
    if ((y >= y0 && y <= y1) || (y <= y0 && y >= y1)) {
      if (y1 === y0) return Math.max(r0, r1)
      return r0 + ((r1 - r0) * (y - y0)) / (y1 - y0)
    }
  }
  return 0
}

export const KIND_BY_TYPE: Record<string, string> = {
  burette: 'burette', utube: 'utube', spoon: 'spoon', candle: 'candle', funnel: 'funnel', fountain: 'fountain',
  gas_jar: 'jar', crucible: 'crucible', evap_dish: 'dish',
}

export const TUBES = new Set(['test_tube', 'boiling_tube'])
export const SUPPORTED = new Set(['beaker_100', 'beaker_250', 'beaker_600', 'flask_250', 'round_flask', 'evap_dish', 'crucible'])
