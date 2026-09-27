import { addDays, fromISO, mondayOf, today } from '../util'

const HEAD = ['一', '二', '三', '四', '五', '六', '日']

// 日期方塊列：一次一週，選到的那天用綠色；今天下方有小點
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
      <div className="week-top">
        <b>{d.getFullYear()} 年 {d.getMonth() + 1} 月</b>
        {value !== t && <button className="today-btn" onClick={() => onChange(t)}>今天</button>}
        <button className="week-nav" aria-label="上一週" disabled={!allowPast && monday <= t} onClick={() => shift(-1)}>‹</button>
        <button className="week-nav" aria-label="下一週" disabled={Boolean(maxDate) && addDays(monday, 7) > maxDate} onClick={() => shift(1)}>›</button>
      </div>
      <div className="dstrip">
        {days.map((iso, i) => (
          <button
            key={iso}
            className={`dtile ${iso === value ? 'selected' : ''} ${iso === t ? 'is-today' : ''}`}
            disabled={disabled(iso)}
            aria-pressed={iso === value}
            aria-label={`${fromISO(iso).getMonth() + 1} 月 ${fromISO(iso).getDate()} 日（${HEAD[i]}）${iso === t ? '，今天' : ''}`}
            onClick={() => onChange(iso)}
          >
            <span>{iso === t ? '今天' : HEAD[i]}</span>
            <b>{fromISO(iso).getDate()}</b>
          </button>
        ))}
      </div>
    </div>
  )
}
