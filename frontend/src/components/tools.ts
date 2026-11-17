import { useLab } from '../store'

const HEAT = new Set(['alcohol', 'bunsen', 'hotplate', 'water_bath', 'ice_bath'])

export function applyTool(tool: string, vessel: string) {
  const st = useLab.getState()
  st.setPick(null)
  if (HEAT.has(tool)) {
    const cur = st.views[vessel]?.heat
    st.act({ op: 'heat', v: vessel, source: cur === tool ? null : tool })
    return
  }
  if (tool === 'stir' || tool === 'shake') {
    st.act({ op: 'stir', v: vessel, seconds: tool === 'shake' ? 5 : 4 })
    return
  }
  if (tool === 'ignite') {
    st.act({ op: 'ignite', v: vessel })
    return
  }
  st.act({ op: 'test', v: vessel, tool })
}
