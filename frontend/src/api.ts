import type { Bench, Catalog, Category, ExpDetail, ExpSummary, StepResult } from './types'

const BASE = `${import.meta.env.BASE_URL}api`

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  })
  if (!r.ok) {
    let msg = `Błąd serwera (${r.status})`
    try {
      const j = await r.json()
      if (j?.detail) msg = j.detail
    } catch {
      /* brak treści */
    }
    throw new Error(msg)
  }
  return r.json() as Promise<T>
}

export const api = {
  catalog: () => req<Catalog>('/catalog'),
  experiments: () => req<{ categories: Category[]; experiments: ExpSummary[] }>('/experiments'),
  experiment: (id: string) => req<ExpDetail>(`/experiments/${encodeURIComponent(id)}`),
  setup: (id: string) => req<StepResult>(`/setup/${encodeURIComponent(id)}`, { method: 'POST' }),
  step: (bench: Bench, actions: any[], dt: number) =>
    req<StepResult>('/step', { method: 'POST', body: JSON.stringify({ bench, actions, dt }) }),
}
