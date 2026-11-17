import { Fragment, type ReactNode } from 'react'

/**
 * Renderuje zapis chemiczny: cyfry po symbolach jako indeksy dolne, ładunki po „^” jako górne.
 * Przykłady: "Cu^2+ + 2OH^- → Cu(OH)2↓", "CuSO4·5H2O", "[Cu(NH3)4]^2+".
 */
export function Chem({ text, className }: { text: string; className?: string }) {
  return <span className={`chem ${className || ''}`}>{renderChem(text)}</span>
}

export function renderChem(text: string): ReactNode[] {
  const out: ReactNode[] = []
  const tokens = text.split(/(\s+)/)
  tokens.forEach((tok, ti) => {
    if (/^\s+$/.test(tok) || tok === '') {
      out.push(tok)
      return
    }
    out.push(<Fragment key={ti}>{renderToken(tok)}</Fragment>)
  })
  return out
}

const NON_FORMULA = /^(→|⇌|\+|=|−|-|ΔH|kJ|kJ\/mol|\(.*\)|t|hν|[a-ząćęłńóśźż]{3,}.*)$/

function renderToken(tok: string): ReactNode[] {
  if (NON_FORMULA.test(tok) && !/^\([A-Z]/.test(tok)) return [tok]
  const parts: ReactNode[] = []
  let i = 0
  // współczynnik stechiometryczny na początku
  const coef = tok.match(/^(\d+(?:[.,]\d+)?)(?=[A-Z([\[])/)
  if (coef) {
    parts.push(coef[1])
    i = coef[1].length
  }
  let buf = ''
  const flush = () => {
    if (buf) {
      parts.push(buf)
      buf = ''
    }
  }
  while (i < tok.length) {
    const ch = tok[i]
    if (ch === '^') {
      flush()
      let j = i + 1
      let sup = ''
      while (j < tok.length && /[0-9+\-−]/.test(tok[j])) {
        sup += tok[j]
        j++
      }
      parts.push(<sup key={`p${i}`}>{sup.replace('-', '−')}</sup>)
      i = j
      continue
    }
    if (/\d/.test(ch)) {
      const prev = tok[i - 1]
      if (prev && /[A-Za-z)\]]/.test(prev)) {
        flush()
        let j = i
        let sub = ''
        while (j < tok.length && /\d/.test(tok[j])) {
          sub += tok[j]
          j++
        }
        parts.push(<sub key={`b${i}`}>{sub}</sub>)
        i = j
        continue
      }
    }
    buf += ch
    i++
  }
  flush()
  return parts
}

/** Formatowanie liczb po polsku */
export function fmt(x: number | null | undefined, digits = 2): string {
  if (x === null || x === undefined || Number.isNaN(x)) return '–'
  const a = Math.abs(x)
  if (a !== 0 && (a < 0.001 || a >= 1e5)) {
    const e = x.toExponential(digits - 1)
    const [m, p] = e.split('e')
    return `${m.replace('.', ',')}·10${toSup(p.replace('+', ''))}`
  }
  return x.toLocaleString('pl-PL', { maximumFractionDigits: digits, minimumFractionDigits: 0 })
}

const SUPS: Record<string, string> = {
  '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴', '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹', '-': '⁻',
}

function toSup(s: string) {
  return s.split('').map((c) => SUPS[c] ?? c).join('')
}
