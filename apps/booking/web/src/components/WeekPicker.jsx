import { useRef } from 'react'
import { addDays, fromISO, mondayOf, today } from '../util'

const HEAD = ['一', '二', '三', '四', '五', '六', '日']

// 日期方塊列：一次一週，選到的那天用綠色；換週時整排往切換的方向滑過去，也可以左右滑動切換
export default function WeekPicker({ value, onChange, maxDate, allowPast = true }) {
  const monday = mondayOf(value)
  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i))
  const t = today()
  const d = fromISO(value)
  const disabled = (iso) => (!allowPast && iso < t) || (maxDate && iso > maxDate)

  // 換週時決定滑入方向（下一週從右邊進來、上一週從左邊進來）；方向跟著這一週記住，
  // 之後課表載入造成的重新繪製不會把動畫中斷
  const anim = useRef({ monday, dir: '' })
  if (anim.current.monday !== monday) anim.current = { monday, dir: monday > anim.current.monday ? 'next' : 'prev' }
  const dir = anim.current.dir
  const touch = useRef(null)
  const canPrev = allowPast || monday > t
  const canNext = !maxDate || addDays(monday, 7) <= maxDate

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
        <button className="week-nav" aria-label="上一週" disabled={!canPrev} onClick={() => shift(-1)}>‹</button>
        <button className="week-nav" aria-label="下一週" disabled={!canNext} onClick={() => shift(1)}>›</button>
      </div>
      <div
        className="dstrip-wrap"
        onTouchStart={(e) => { touch.current = [e.touches[0].clientX, e.touches[0].clientY] }}
        onTouchEnd={(e) => {
          if (!touch.current) return
          const dx = e.changedTouches[0].clientX - touch.current[0]
          const dy = e.changedTouches[0].clientY - touch.current[1]
          touch.current = null
          if (Math.abs(dx) < 50 || Math.abs(dx) < Math.abs(dy) * 1.5) return  // 太短或是上下捲動就不算
          if (dx < 0 && canNext) shift(1)
          if (dx > 0 && canPrev) shift(-1)
        }}
      >
      <div key={monday} className={`dstrip ${dir ? `slide-${dir}` : ''}`}>
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
    </div>
  )
}
