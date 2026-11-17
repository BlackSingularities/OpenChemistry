export interface SolidView {
  id: string
  name: string
  formula: string
  color: string
  style: string
  mass: number
  vol: number
  settled: number
}

export interface ContentItem {
  kind: 'aq' | 'org' | 's'
  id: string
  name: string
  c?: number
  n?: number
  g?: number
  formula?: string
}

export interface VesselView {
  id: string
  type: string
  vol: number
  org_vol: number
  T: number
  heat: string | null
  stopper: boolean
  outlet: string | null
  mirror?: number | null
  fx: Record<string, any>
  pH: number | null
  liquid: string | null
  absorb?: number
  color_name?: string
  org_color?: string
  turbid?: number
  turbid_color?: string
  solids: SolidView[]
  gas_color: string | null
  gas_alpha?: number
  gas: Record<string, number>
  gas_ml: number
  kappa?: number
  contents: ContentItem[]
  parent?: string | null
  target?: string | null
  flow?: number
  source?: string | null
  arms?: VesselView[]
  power?: boolean
  current?: number
  electrode?: string
}

export interface SimEvent {
  t: number
  v: string | null
  kind: 'obs' | 'ppt' | 'info' | 'warn' | 'test' | 'color' | 'error'
  text: string
  eq?: string
  color?: string
  result?: any
  flame?: string
  id?: number
}

export interface Reading {
  emf: number
  cathode: string
  metals: string[]
}

export interface Bench {
  vessels: Record<string, any>
  t: number
  seq?: number
  links?: { a: string; b: string }[]
}

export interface StepResult {
  bench: Bench
  events: SimEvent[]
  views: Record<string, VesselView>
  readings: Record<string, Reading>
  created: string[]
  errors: string[]
}

export interface EquipmentItem {
  id: string
  name: string
  group: string
  cap: number
  kind: string
  heatable: boolean
  desc: string
  diam: number
}

export interface ReagentItem {
  id: string
  name: string
  group: string
  kind: 'solution' | 'solid' | 'liquid' | 'gas' | 'indicator'
  formula: string
  hazards: string[]
  unit: string
  presets: number[]
  note: string
  color?: string
  style?: string
  piece?: number | null
}

export interface ToolItem {
  id: string
  name: string
  group: string
  kind: 'heat' | 'test' | 'action'
  desc?: string
}

export interface Catalog {
  equipment: EquipmentItem[]
  reagents: ReagentItem[]
  tools: ToolItem[]
  hazards: Record<string, string>
}

export interface ExpSummary {
  id: string
  title: string
  cat: string
  level: string
  summary: string
  tags: string[]
  steps: number
}

export interface Category {
  id: string
  name: string
  icon: string
  count: number
}

export interface ExpStep {
  text: string
  actions: any[]
  wait: number
  hint?: string | null
}

export interface ExpDetail {
  id: string
  title: string
  cat: string
  catName: string
  level: string
  summary: string
  theory: string
  equations: string[]
  safety: string
  observe: string
  steps: ExpStep[]
  tags: string[]
  setup: { id: string; etype: string; x: number | null; label?: string | null }[]
}
