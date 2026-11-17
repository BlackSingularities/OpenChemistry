import { create } from 'zustand'

export interface DragItem {
  kind: 'reagent' | 'tool' | 'equipment'
  id: string
  label: string
  color?: string
}

interface DragState {
  item: DragItem | null
  x: number
  y: number
  start: (item: DragItem, x: number, y: number) => void
  move: (x: number, y: number) => void
  end: () => void
}

export const useDrag = create<DragState>((set) => ({
  item: null,
  x: 0,
  y: 0,
  start: (item, x, y) => set({ item, x, y }),
  move: (x, y) => set({ x, y }),
  end: () => set({ item: null }),
}))

/** Zwraca funkcję obsługi pointerdown dla elementu półki – przeciąganie lub kliknięcie. */
export function shelfPointerDown(item: DragItem, onClick: () => void) {
  return (e: React.PointerEvent) => {
    if (e.button !== 0) return
    const sx = e.clientX
    const sy = e.clientY
    let dragging = false
    const moveH = (ev: PointerEvent) => {
      if (!dragging && Math.hypot(ev.clientX - sx, ev.clientY - sy) > 6) {
        dragging = true
        useDrag.getState().start(item, ev.clientX, ev.clientY)
      }
      if (dragging) useDrag.getState().move(ev.clientX, ev.clientY)
    }
    const upH = (ev: PointerEvent) => {
      window.removeEventListener('pointermove', moveH)
      window.removeEventListener('pointerup', upH)
      if (dragging) {
        window.dispatchEvent(new CustomEvent('lab-drop', { detail: { item, x: ev.clientX, y: ev.clientY } }))
        useDrag.getState().end()
      } else onClick()
    }
    window.addEventListener('pointermove', moveH)
    window.addEventListener('pointerup', upH)
  }
}
