import { create } from 'zustand'
import { api } from './api'
import { welcomeSeen } from './components/Welcome'
import type {
  Bench, Catalog, Category, ExpDetail, ExpSummary, Reading, SimEvent, StepResult, VesselView,
} from './types'

export type Mode = 'home' | 'lab'

export type Pick =
  | { kind: 'reagent'; id: string }
  | { kind: 'tool'; id: string }
  | { kind: 'equipment'; id: string }
  | null

export type LinkMode =
  | { kind: 'pour' | 'outlet' | 'parent' | 'burette' | 'funnel' | 'source' | 'bridge'; from: string }
  | null

export type Dialog =
  | { kind: 'reagent'; vessel: string; reagent: string }
  | { kind: 'pour'; from: string; to: string }
  | { kind: 'burette'; vessel: string; target: string }
  | null

export interface TitrationSeries {
  target: string
  startVol: number
  points: [number, number][]
}

export interface Flash {
  id: number
  v: string
  kind: 'flame' | 'paper' | 'pop' | 'splint'
  color?: string
  text?: string
  at: number
}

interface State {
  mode: Mode
  catalog: Catalog | null
  categories: Category[]
  experiments: ExpSummary[]
  bench: Bench
  views: Record<string, VesselView>
  readings: Record<string, Reading>
  events: SimEvent[]
  selected: string | null
  running: boolean
  speed: number
  busy: boolean
  queue: any[]
  experiment: ExpDetail | null
  stepDone: boolean[]
  autoplay: boolean
  pick: Pick
  link: LinkMode
  dialog: Dialog
  titration: Record<string, TitrationSeries>
  flashes: Flash[]
  toast: string | null
  panel: 'guide' | 'vessel' | 'journal'
  showReadings: boolean
  lastNewEvent: number
  ctx: { v: string; x: number; y: number } | null
  welcome: boolean
  init: () => Promise<void>
  goHome: () => void
  openSandbox: (fresh?: boolean) => void
  openExperiment: (id: string) => Promise<void>
  act: (...a: any[]) => void
  tick: (dt: number) => Promise<void>
  setRunning: (r: boolean) => void
  setSpeed: (s: number) => void
  select: (id: string | null) => void
  setPick: (p: Pick) => void
  setLink: (l: LinkMode) => void
  setDialog: (d: Dialog) => void
  setPanel: (p: State['panel']) => void
  setToast: (t: string | null) => void
  addVessel: (etype: string, x?: number) => void
  runStep: (i: number) => void
  setAutoplay: (on: boolean) => void
  resetBench: () => void
  toggleReadings: () => void
  setCtx: (c: State['ctx']) => void
  setWelcome: (on: boolean) => void
}

let eventSeq = 1
let flashSeq = 1
const SANDBOX_KEY = 'openchemistry.sandbox.v1'

function loadSandbox(): Bench | null {
  try {
    const raw = localStorage.getItem(SANDBOX_KEY)
    if (!raw) return null
    const b = JSON.parse(raw)
    if (b && typeof b === 'object' && b.vessels) return b
  } catch {
    /* brak dostępu do localStorage */
  }
  return null
}

function saveSandbox(b: Bench) {
  try {
    localStorage.setItem(SANDBOX_KEY, JSON.stringify(b))
  } catch {
    /* ignoruj */
  }
}

const DEFAULT_SANDBOX: any[] = [
  { op: 'add_vessel', etype: 'beaker_250', x: 330 },
  { op: 'add_vessel', etype: 'test_tube', x: 440 },
  { op: 'add_vessel', etype: 'test_tube', x: 490 },
  { op: 'add_vessel', etype: 'test_tube', x: 540 },
  { op: 'add_vessel', etype: 'flask_250', x: 660 },
]

function actionMatches(user: any, step: any): boolean {
  if (user.op !== step.op) return false
  const keys = ['v', 'from', 'to', 'reagent', 'tool', 'source', 'target', 'a', 'b', 'src']
  for (const k of keys) {
    if (step[k] !== undefined && step[k] !== null && user[k] !== step[k]) return false
  }
  if (step.op === 'burette' && step.flow > 0 !== user.flow > 0) return false
  if (step.op === 'power' && Boolean(step.on) !== Boolean(user.on)) return false
  return true
}

export const useLab = create<State>((set, get) => ({
  mode: 'home',
  catalog: null,
  categories: [],
  experiments: [],
  bench: { vessels: {}, t: 0, seq: 0, links: [] },
  views: {},
  readings: {},
  events: [],
  selected: null,
  running: true,
  speed: 1,
  busy: false,
  queue: [],
  experiment: null,
  stepDone: [],
  autoplay: false,
  pick: null,
  link: null,
  dialog: null,
  titration: {},
  flashes: [],
  toast: null,
  panel: 'guide',
  showReadings: true,
  lastNewEvent: 0,
  ctx: null,
  welcome: false,

  init: async () => {
    try {
      const [cat, ex] = await Promise.all([api.catalog(), api.experiments()])
      set({ catalog: cat, categories: ex.categories, experiments: ex.experiments })
    } catch (e: any) {
      set({ toast: `Nie udało się połączyć z serwerem: ${e.message}` })
    }
  },

  goHome: () => {
    set({ mode: 'home', ctx: null, welcome: false, link: null, pick: null, dialog: null, autoplay: false })
    if (location.hash) history.replaceState(null, '', location.pathname)
  },

  openSandbox: (fresh = false) => {
    const saved = fresh ? null : loadSandbox()
    set({
      mode: 'lab', experiment: null, stepDone: [], ctx: null, welcome: !welcomeSeen(), events: [], selected: null, titration: {}, panel: 'vessel',
      bench: saved || { vessels: {}, t: 0, seq: 0, links: [] }, views: {}, readings: {}, autoplay: false,
      queue: saved && Object.keys(saved.vessels).length ? [] : [...DEFAULT_SANDBOX],
    })
    history.replaceState(null, '', '#/laboratorium')
    get().tick(0)
  },

  openExperiment: async (id: string) => {
    try {
      const [detail, res] = await Promise.all([api.experiment(id), api.setup(id)])
      set({
        mode: 'lab', experiment: detail, stepDone: detail.steps.map(() => false), events: [], selected: null,
        titration: {}, bench: res.bench, views: res.views, readings: res.readings, queue: [], panel: 'guide',
        autoplay: false, running: true, link: null, pick: null, dialog: null, ctx: null, welcome: !welcomeSeen(),
      })
      history.replaceState(null, '', `#/doswiadczenie/${id}`)
    } catch (e: any) {
      set({ toast: e.message })
    }
  },

  act: (...a: any[]) => {
    const st = get()
    const exp = st.experiment
    if (exp) {
      // automatyczne odhaczanie kroków przewodnika
      const done = [...st.stepDone]
      let changed = false
      exp.steps.forEach((s, i) => {
        if (done[i] || s.actions.length === 0) return
        const firstUndone = done.findIndex((d, j) => !d && exp.steps[j].actions.length > 0)
        if (i !== firstUndone) return
        const allMatched = s.actions.every((sa) => a.some((ua) => actionMatches(ua, sa)))
        const anyMatched = s.actions.some((sa) => a.some((ua) => actionMatches(ua, sa)))
        if (allMatched || (anyMatched && s.actions.length > 1 && a.length === 1 && s.actions.length <= 2)) {
          done[i] = true
          changed = true
        }
      })
      if (changed) set({ stepDone: done })
    }
    set({ queue: [...st.queue, ...a] })
    if (!st.busy) get().tick(0)
  },

  tick: async (dt: number) => {
    const st = get()
    if (st.busy || st.mode !== 'lab') return
    const actions = st.queue
    set({ busy: true, queue: [] })
    try {
      const res: StepResult = await api.step(st.bench, actions, dt)
      const now = Date.now()
      const newEvents = res.events.map((e) => ({ ...e, id: eventSeq++ }))
      const flashes = [...get().flashes.filter((f) => now - f.at < 3500)]
      for (const e of newEvents) {
        if (e.kind === 'test' && e.v) {
          if (e.flame) flashes.push({ id: flashSeq++, v: e.v, kind: 'flame', color: e.flame, at: now })
          else if (typeof e.result === 'string' && e.result.startsWith('#'))
            flashes.push({ id: flashSeq++, v: e.v, kind: 'paper', color: e.result, at: now })
          else if (e.result === 'pop') flashes.push({ id: flashSeq++, v: e.v, kind: 'pop', text: 'PYK!', at: now })
          else if (e.result) flashes.push({ id: flashSeq++, v: e.v, kind: 'splint', text: String(e.result), at: now })
        }
      }
      // krzywe miareczkowania
      const titration = { ...get().titration }
      for (const [vid, v] of Object.entries(res.bench.vessels)) {
        if (v.type !== 'burette') continue
        const tgt = v.target
        if (!tgt || !res.views[tgt]) continue
        let series = titration[vid]
        if (!series || series.target !== tgt) {
          const prevVol = st.bench.vessels[vid]?.vol ?? v.vol
          series = { target: tgt, startVol: prevVol, points: [] }
        }
        const added = Math.max(0, series.startVol - v.vol)
        const ph = res.views[tgt].pH
        if (ph !== null && ph !== undefined) {
          const last = series.points[series.points.length - 1]
          if (!last || Math.abs(last[0] - added) > 0.02 || series.points.length === 0) {
            series = { ...series, points: [...series.points, [added, ph]] }
          }
        }
        titration[vid] = series
      }
      const events = [...get().events, ...newEvents].slice(-400)
      set({
        bench: res.bench, views: res.views, readings: res.readings, events, flashes, titration,
        lastNewEvent: newEvents.some((e) => e.kind !== 'color') ? now : get().lastNewEvent,
      })
      if (res.created.length) set({ selected: res.created[res.created.length - 1] })
      if (res.errors.length) set({ toast: res.errors[0] })
      if (!get().experiment) saveSandbox(res.bench)
      const sel = get().selected
      if (sel && !res.bench.vessels[sel]) set({ selected: null })
    } catch (e: any) {
      set({ toast: e.message })
    } finally {
      set({ busy: false })
    }
    if (get().queue.length) get().tick(0)
  },

  setRunning: (r) => set({ running: r }),
  setSpeed: (s) => set({ speed: s }),
  select: (id) => set({ selected: id, panel: id ? (get().panel === 'guide' && get().experiment ? 'guide' : 'vessel') : get().panel }),
  setPick: (p) => set({ pick: p, link: null }),
  setLink: (l) => set({ link: l, pick: null }),
  setDialog: (d) => set({ dialog: d }),
  setPanel: (p) => set({ panel: p }),
  setToast: (t) => set({ toast: t }),

  addVessel: (etype, x) => {
    const st = get()
    let pos = x
    if (pos === undefined) {
      const xs = Object.values(st.bench.vessels).map((v: any) => v.x as number).sort((a, b) => a - b)
      pos = xs.length ? xs[xs.length - 1] + 110 : 500
      if (pos > 940) {
        pos = 60
        for (const vx of xs) if (Math.abs(vx - pos) < 80) pos = vx + 85
      }
    }
    get().act({ op: 'add_vessel', etype, x: pos })
  },

  runStep: (i) => {
    const exp = get().experiment
    if (!exp) return
    const s = exp.steps[i]
    const done = [...get().stepDone]
    done[i] = true
    set({ stepDone: done })
    set({ queue: [...get().queue, ...s.actions] })
    if (!get().busy) get().tick(0)
  },

  setAutoplay: (on) => set({ autoplay: on }),

  resetBench: () => {
    const exp = get().experiment
    if (exp) get().openExperiment(exp.id)
    else {
      try {
        localStorage.removeItem(SANDBOX_KEY)
      } catch {
        /* ignoruj */
      }
      get().openSandbox(true)
    }
  },

  toggleReadings: () => set({ showReadings: !get().showReadings }),
  setCtx: (c) => set({ ctx: c }),
  setWelcome: (on) => set({ welcome: on }),
}))

// pętla symulacji: co ~0,5 s rzeczywistego czasu wysyłamy krok o długości 0,5·prędkość
let last = performance.now()
let autoWaitUntil = 0
setInterval(() => {
  const st = useLab.getState()
  const now = performance.now()
  if (st.mode !== 'lab') {
    last = now
    return
  }
  if (st.busy) return
  const elapsed = (now - last) / 1000
  if (st.queue.length) {
    last = now
    st.tick(st.running ? Math.min(elapsed, 1) * st.speed : 0)
    return
  }
  if (st.running && elapsed >= 0.45) {
    last = now
    st.tick(Math.min(elapsed, 1.0) * st.speed)
  }
  // autoodtwarzanie kroków doświadczenia
  if (st.autoplay && st.experiment && st.running) {
    if (now < autoWaitUntil) return
    const i = st.stepDone.findIndex((d) => !d)
    if (i < 0) {
      useLab.setState({ autoplay: false })
      return
    }
    st.runStep(i)
    const wait = st.experiment.steps[i].wait || 3
    autoWaitUntil = now + (wait / st.speed) * 1000 + 600
  }
}, 120)
