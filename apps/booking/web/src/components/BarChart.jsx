import { useState } from 'react'

// 單一數列直條圖：品牌藍、4px 圓角頂端、2px 間隔、hover／點擊顯示數值
// 期間超過 45 天時自動改為每週加總
export default function BarChart({ data, format = (v) => v, label }) {
  const [hover, setHover] = useState(null)
  const points = data.length > 45 ? weekly(data) : data.map((d) => ({ ...d, label: d.date.slice(5).replace('-', '/') }))
  const max = Math.max(...points.map((p) => p.value), 0)
  const total = points.reduce((s, p) => s + p.value, 0)
  const every = Math.ceil(points.length / 7)
  const peak = points.findIndex((p) => p.value === max && max > 0)

  return (
    <figure className="bar-chart" aria-label={label}>
      <div className="bar-plot" onMouseLeave={() => setHover(null)}>
        {[1, 0.5].map((f) => (
          <div key={f} className="bar-grid" style={{ bottom: `${f * 100}%` }}><span>{max ? format(Math.round(max * f)) : ''}</span></div>
        ))}
        <div className="bar-cols" style={{ gridTemplateColumns: `repeat(${points.length}, 1fr)` }}>
          {points.map((p, i) => (
            <button
              key={p.date}
              type="button"
              className={`bar-col ${hover === i ? 'on' : ''}`}
              onMouseEnter={() => setHover(i)}
              onFocus={() => setHover(i)}
              onClick={() => setHover(hover === i ? null : i)}
              aria-label={`${p.label}：${format(p.value)}`}
            >
              <span className="bar" style={{ height: max ? `${(p.value / max) * 100}%` : 0 }} />
              {i === peak && hover === null && <span className="bar-peak">{format(p.value)}</span>}
            </button>
          ))}
        </div>
        {hover !== null && (
          <div className="bar-tip" style={{ left: `${((hover + 0.5) / points.length) * 100}%` }}>
            <span>{points[hover].label}</span><b>{format(points[hover].value)}</b>
          </div>
        )}
      </div>
      <div className="bar-axis" style={{ gridTemplateColumns: `repeat(${points.length}, 1fr)` }}>
        {points.map((p, i) => <span key={p.date}>{i % every === 0 ? p.label : ''}</span>)}
      </div>
      <details className="bar-table">
        <summary>查看數據表（合計 {format(total)}）</summary>
        <table>
          <tbody>
            {points.filter((p) => p.value).map((p) => <tr key={p.date}><td>{p.label}</td><td>{format(p.value)}</td></tr>)}
          </tbody>
        </table>
      </details>
    </figure>
  )
}

function weekly(data) {
  const out = []
  data.forEach((d, i) => {
    if (i % 7 === 0) out.push({ date: d.date, label: d.date.slice(5).replace('-', '/') + ' 週', value: 0 })
    out[out.length - 1].value += d.value
  })
  return out
}
