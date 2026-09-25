import { addDays, fromISO, mondayOf, today } from '../util'

const HEAD = ['一', '二', '三', '四', '五', '六', '日']

// FitBook 式週曆：今天按鈕、月份、左右切換週
export default function WeekPicker({ value, onChange, maxDate, allowPast = true }) {
  const monday = mondayOf(value)
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i))
  const t = today()
  const d = fromISO(value)
  const disabled = (iso) => (!allowPast && iso < t) || (maxDate && iso > maxDate)

  const shift = (n) => {
    const target = addDays(value, n * 7)
    if (maxDate && target > maxDate) onChange(maxDate > addDays(monday, 7) ? maxDate : value)
    else if (!allowPast && target < t) onChange(t)
    else onChange(target)
  }

  return (
    <div className="card week">
      <div className="week-head">
        <button className="today-btn" onClick={() => onChange(t)}>今天</button>
        <b>{d.getFullYear()}年{String(d.getMonth() + 1).padStart(2, '0')}月</b>
        <span />
      </div>
      <div className="week-body">
        <button className="week-arrow" aria-label="上一週" onClick={() => shift(-1)}>‹</button>
        <div className="week-grid">
          {HEAD.map((h) => <span key={h} className="week-label">{h}</span>)}
          {days.map((iso) => (
            <button
              key={iso}
              className={`week-day ${iso === value ? 'selected' : ''} ${iso === t ? 'is-today' : ''}`}
              disabled={disabled(iso)}
              onClick={() => onChange(iso)}
            >
              {fromISO(iso).getDate()}
            </button>
          ))}
        </div>
        <button className="week-arrow" aria-label="下一週" onClick={() => shift(1)}>›</button>
      </div>
    </div>
  )
}
