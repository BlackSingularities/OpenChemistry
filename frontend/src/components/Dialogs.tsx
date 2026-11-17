import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { useLab } from '../store'
import { Chem, fmt } from '../chem'

export default function Dialogs() {
  const dialog = useLab((s) => s.dialog)
  if (!dialog) return null
  return (
    <div className="modal-veil" onPointerDown={() => useLab.getState().setDialog(null)}>
      <div className="modal" onPointerDown={(e) => e.stopPropagation()} role="dialog" aria-modal="true">
        {dialog.kind === 'reagent' && <ReagentDialog vessel={dialog.vessel} reagent={dialog.reagent} />}
        {dialog.kind === 'pour' && <PourDialog from={dialog.from} to={dialog.to} />}
        {dialog.kind === 'burette' && <BuretteDialog vessel={dialog.vessel} target={dialog.target} />}
      </div>
    </div>
  )
}

function Head({ title }: { title: string }) {
  return (
    <div className="modal-head">
      <h3>{title}</h3>
      <button className="icon-only" onClick={() => useLab.getState().setDialog(null)} aria-label="Zamknij"><X size={16} /></button>
    </div>
  )
}

function ReagentDialog({ vessel, reagent }: { vessel: string; reagent: string }) {
  const r = useLab((s) => s.catalog?.reagents.find((x) => x.id === reagent))
  const view = useLab((s) => s.views[vessel])
  const cap = useLab((s) => s.catalog?.equipment.find((e) => e.id === view?.type)?.cap ?? 0)
  const [amount, setAmount] = useState<number>(r?.piece ?? r?.presets[Math.min(1, (r?.presets.length ?? 1) - 1)] ?? 1)
  useEffect(() => { if (r) setAmount(r.piece ?? r.presets[Math.min(1, r.presets.length - 1)]) }, [reagent])
  if (!r || !view) return null
  const unit = r.kind === 'indicator' ? 'kropli' : r.unit
  const free = cap - (view.vol || 0) - (view.org_vol || 0)
  const ok = amount > 0 && (r.unit !== 'mL' || amount <= free + 1e-6 || view.type === 'funnel')
  const submit = () => {
    useLab.getState().act({ op: 'reagent', v: vessel, reagent, amount })
    useLab.getState().setDialog(null)
  }
  return (
    <>
      <Head title="Dodaj odczynnik" />
      <div className="modal-body">
        <p className="reagent-name"><b>{r.name}</b>{r.formula && <> · <Chem text={r.formula} /></>}</p>
        {r.note && <p className="note">{r.note}</p>}
        <div className="presets">
          {r.presets.map((p) => (
            <button key={p} className={p === amount ? 'on' : ''} onClick={() => setAmount(p)}>{fmt(p, 2)} {unit}</button>
          ))}
        </div>
        <label className="amount">
          Ilość
          <input type="number" min={0} step={r.unit === 'g' ? 0.05 : r.kind === 'indicator' ? 1 : 0.5} value={amount}
                 onChange={(e) => setAmount(Number(e.target.value))} onKeyDown={(e) => e.key === 'Enter' && ok && submit()} autoFocus />
          <span>{unit}</span>
        </label>
        {r.unit === 'mL' && <p className="note">Wolne miejsce w naczyniu: {fmt(Math.max(free, 0), 1)} mL</p>}
        {r.hazards.length > 0 && <p className="note warn">Zachowaj ostrożność: substancja oznaczona jako niebezpieczna.</p>}
      </div>
      <div className="modal-foot">
        <button onClick={() => useLab.getState().setDialog(null)}>Anuluj</button>
        <button className="primary" disabled={!ok} onClick={submit}>Dodaj</button>
      </div>
    </>
  )
}

function PourDialog({ from, to }: { from: string; to: string }) {
  const src = useLab((s) => s.views[from])
  const dst = useLab((s) => s.views[to])
  const cap = useLab((s) => s.catalog?.equipment.find((e) => e.id === dst?.type)?.cap ?? 0)
  const total = src ? (src.arms ? src.arms.reduce((a, x) => a + x.vol, 0) : src.vol + src.org_vol) : 0
  const room = dst?.type === 'funnel' ? total : Math.max(0, cap - (dst?.vol || 0) - (dst?.org_vol || 0))
  const max = Math.min(total, room || total)
  const [ml, setMl] = useState(Math.min(max, Math.max(1, Math.round(max / 2))))
  if (!src || !dst) return null
  const submit = (all = false) => {
    useLab.getState().act({ op: 'pour', from, to, ml: all ? max : ml, all: all && max >= total - 1e-6 })
    useLab.getState().setDialog(null)
  }
  return (
    <>
      <Head title={`Przelej ${from} → ${to}`} />
      <div className="modal-body">
        <p>W naczyniu źródłowym: <b>{fmt(total, 1)} mL</b>. Miejsce w docelowym: <b>{fmt(room, 1)} mL</b>.</p>
        <input type="range" min={0} max={max} step={max > 20 ? 1 : 0.1} value={ml} onChange={(e) => setMl(Number(e.target.value))} />
        <label className="amount">
          Objętość
          <input type="number" min={0} max={max} step={0.5} value={ml} onChange={(e) => setMl(Number(e.target.value))}
                 onKeyDown={(e) => e.key === 'Enter' && submit()} autoFocus />
          <span>mL</span>
        </label>
        <div className="presets">
          {[1, 2, 5, 10, 20].filter((x) => x <= max).map((x) => <button key={x} onClick={() => setMl(x)}>{x} mL</button>)}
        </div>
      </div>
      <div className="modal-foot">
        <button onClick={() => useLab.getState().setDialog(null)}>Anuluj</button>
        <button onClick={() => submit(true)}>Całość</button>
        <button className="primary" disabled={ml <= 0} onClick={() => submit()}>Przelej</button>
      </div>
    </>
  )
}

function BuretteDialog({ vessel, target }: { vessel: string; target: string }) {
  const [flow, setFlow] = useState(0.5)
  return (
    <>
      <Head title="Biureta nad naczyniem" />
      <div className="modal-body">
        <p>Biureta zostanie ustawiona nad naczyniem <b>{target}</b>. Ustaw szybkość wypływu titranta:</p>
        <input type="range" min={0} max={2} step={0.05} value={flow} onChange={(e) => setFlow(Number(e.target.value))} />
        <p><b>{fmt(flow, 2)} mL/s</b> {flow === 0 ? '(kurek zamknięty)' : flow <= 0.1 ? '(kroplami)' : ''}</p>
      </div>
      <div className="modal-foot">
        <button onClick={() => { useLab.getState().act({ op: 'burette', v: vessel, target, flow: 0 }); useLab.getState().setDialog(null) }}>
          Ustaw, kurek zamknięty
        </button>
        <button className="primary" onClick={() => { useLab.getState().act({ op: 'burette', v: vessel, target, flow }); useLab.getState().setDialog(null) }}>
          Otwórz kurek
        </button>
      </div>
    </>
  )
}
