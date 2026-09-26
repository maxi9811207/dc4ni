import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import { Loading } from '../../components/ui'
import { addDays, duprRange, fromISO, mondayOf, today } from '../../util'

const WEEK = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

// 週曆：一天一欄，可左右捲動；點課程進名單，點「＋」在那天新增課程
export default function AdminCalendar() {
  const { venue, handleError } = useApp()
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const monday = mondayOf(params.get('week') || today())
  const [courses, setCourses] = useState(null)
  const [teachers, setTeachers] = useState([])
  const [teacher, setTeacher] = useState('')
  const [category, setCategory] = useState('')
  const scroller = useRef(null)

  useEffect(() => { api('admin/teachers').then(setTeachers).catch(handleError) }, [handleError])
  useEffect(() => {
    setCourses(null)
    api(`admin/courses?from=${monday}&to=${addDays(monday, 6)}`).then(setCourses).catch(handleError)
  }, [monday, handleError])

  // 本週時自動捲到今天那一欄
  useEffect(() => {
    const el = scroller.current?.querySelector('.cal-col.is-today')
    if (el && courses) scroller.current.scrollLeft = el.offsetLeft - 8
  }, [courses])

  const days = Array.from({ length: 7 }, (_, i) => addDays(monday, i))
  const shown = useMemo(() => (courses || []).filter((c) =>
    (!teacher || String(c.teacher?.id || '') === teacher) && (!category || c.category === category)), [courses, teacher, category])
  const categories = Array.from(new Set([...(venue?.categories || []), ...(courses || []).map((c) => c.category)].filter(Boolean)))
  const t = today()
  const m = fromISO(monday)
  const sunday = fromISO(addDays(monday, 6))

  return (
    <>
      <div className="row between section-head">
        <h3 className="date-title">{m.getMonth() + 1}/{m.getDate()} – {sunday.getMonth() + 1}/{sunday.getDate()}</h3>
        <Link to={`/admin/courses/new?date=${days.includes(t) ? t : monday}`} className="btn btn-small">＋ 新增課程</Link>
      </div>
      <div className="grid2">
        <select className="input" value={teacher} onChange={(e) => setTeacher(e.target.value)} aria-label="篩選老師">
          <option value="">全部老師</option>
          {teachers.map((x) => <option key={x.id} value={x.id}>{x.name}</option>)}
        </select>
        <select className="input" value={category} onChange={(e) => setCategory(e.target.value)} aria-label="篩選類別">
          <option value="">全部類別</option>
          {categories.map((x) => <option key={x}>{x}</option>)}
        </select>
      </div>
      <div className="row gap-sm">
        <button className="btn btn-small btn-light" onClick={() => setParams({ week: addDays(monday, -7) }, { replace: true })}>‹ 上一週</button>
        <button className="btn btn-small btn-light" onClick={() => setParams({}, { replace: true })}>本週</button>
        <button className="btn btn-small btn-light" onClick={() => setParams({ week: addDays(monday, 7) }, { replace: true })}>下一週 ›</button>
        <span className="muted small flex1 right">{shown.length} 堂</span>
      </div>

      {!courses ? <Loading /> : (
        <div className="cal" ref={scroller}>
          {days.map((d, i) => {
            const list = shown.filter((c) => c.date === d)
            const date = fromISO(d)
            return (
              <div key={d} className={`cal-col ${d === t ? 'is-today' : ''} ${d < t ? 'is-past' : ''}`}>
                <div className="cal-head">
                  <b>{date.getMonth() + 1}月{date.getDate()}日</b>
                  <span>{WEEK[i]}</span>
                  <button className="cal-add" aria-label={`${d} 新增課程`} onClick={() => navigate(`/admin/courses/new?date=${d}`)}>＋</button>
                </div>
                {list.length === 0 && <p className="cal-empty">無課程</p>}
                {list.map((c) => (
                  <Link key={c.id} to={`/admin/courses/${c.id}`} className={`cal-item ${c.status === 'cancelled' ? 'cancelled' : ''} ${c.remain === 0 ? 'full' : ''}`}>
                    <span className="cal-time">{c.start_time}~{c.end_time}</span>
                    <b className="cal-name">{c.name}</b>
                    {c.dupr_required && <span className="badge badge-dupr">{duprRange(c, true)}</span>}
                    <span className="cal-meta">👤 {c.teacher?.name || '未指定'}</span>
                    <span className="cal-meta">
                      {c.status === 'cancelled' ? '停課' : `名額：${c.booked_count} / ${c.capacity}`}
                      {c.waitlist_count > 0 && c.status !== 'cancelled' && <em>（候補 {c.waitlist_count}）</em>}
                    </span>
                  </Link>
                ))}
              </div>
            )
          })}
        </div>
      )}
    </>
  )
}
