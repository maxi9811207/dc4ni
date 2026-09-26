import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import WeekPicker from '../../components/WeekPicker'
import { Badge, Chips, Empty, Loading } from '../../components/ui'
import { addDays, showDate, today } from '../../util'

export default function Attendance() {
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'roll'
  const set = (next) => setParams({ ...Object.fromEntries(params), ...next }, { replace: true })
  return (
    <>
      <Chips value={tab} onChange={(t) => set({ tab: t })} options={[['roll', '點名'], ['stats', '出缺席統計']]} />
      {tab === 'roll' ? <RollCall date={params.get('date') || today()} onDate={(d) => set({ date: d })} /> : <Stats />}
    </>
  )
}

function RollCall({ date, onDate }) {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const load = useCallback(() => api(`admin/attendance?date=${date}`).then(setList).catch(handleError), [date, handleError])
  useEffect(() => { setList(null); load() }, [load])

  const mark = async (r, status) => {
    try {
      await api(`admin/reservations/${r.id}`, { method: 'POST', body: { status: r.status === status ? 'booked' : status } })
      load()
    } catch (e) { handleError(e) }
  }
  const markAll = async (c) => {
    try {
      const res = await api(`admin/courses/${c.id}/attendance`, { method: 'POST' })
      showToast(`已將 ${res.updated} 位標記為出席`)
      load()
    } catch (e) { handleError(e) }
  }

  const total = (list || []).reduce((s, c) => s + c.roster.length, 0)
  const done = (list || []).reduce((s, c) => s + c.roster.filter((r) => r.status !== 'booked').length, 0)

  return (
    <>
      <WeekPicker value={date} onChange={onDate} />
      <div className="row between">
        <h3 className="date-title">{showDate(date)}</h3>
        {list && total > 0 && <span className="muted small">已點名 {done} / {total}</span>}
      </div>
      {!list ? <Loading /> : list.length === 0 ? <Empty text="這天沒有課程" /> : list.map((c) => {
        const pending = c.roster.filter((r) => r.status === 'booked').length
        return (
          <section key={c.id} className="card roll-card">
            <div className="row between">
              <div className="min0">
                <Link to={`/admin/courses/${c.id}`} className="course-name">{c.name}</Link>
                <p className="course-meta"><b className="course-time">{c.start_time}~{c.end_time}</b> · {c.teacher?.name || '未指定老師'} · {c.booked_count}/{c.capacity}</p>
              </div>
              {c.roster.length > 0 && (pending === 0
                ? <Badge tone="success">點名完成</Badge>
                : <button className="btn btn-small" onClick={() => markAll(c)}>全部出席</button>)}
            </div>
            {c.roster.length === 0 ? <p className="muted small">沒有學員預約</p> : c.roster.map((r) => (
              <div key={r.id} className="roll-row">
                <span className="flex1 min0"><b>{r.name}</b> <span className="muted small">{r.phone}</span></span>
                <button className={`roll-btn ${r.status === 'attended' ? 'on-ok' : ''}`} onClick={() => mark(r, 'attended')}>出席</button>
                <button className={`roll-btn ${r.status === 'absent' ? 'on-bad' : ''}`} onClick={() => mark(r, 'absent')}>缺席</button>
              </div>
            ))}
          </section>
        )
      })}
    </>
  )
}

const RANGES = [['7', '近 7 天'], ['30', '近 30 天'], ['90', '近 90 天']]

function Stats() {
  const { handleError } = useApp()
  const [range, setRange] = useState('30')
  const [data, setData] = useState(null)
  useEffect(() => {
    setData(null)
    const to = today()
    api(`admin/attendance/stats?from=${addDays(to, -(Number(range) - 1))}&to=${to}`).then(setData).catch(handleError)
  }, [range, handleError])

  if (!data) return <><Chips value={range} onChange={setRange} options={RANGES} /><Loading /></>
  const sum = (k) => data.members.reduce((s, m) => s + (m[k] || 0), 0)
  const marked = sum('attended') + sum('absent')
  return (
    <>
      <Chips value={range} onChange={setRange} options={RANGES} />
      <div className="stats">
        <div className="stat"><span>上課人次</span><b>{sum('total')}</b></div>
        <div className="stat"><span>出席率</span><b>{marked ? Math.round(sum('attended') / marked * 100) + '%' : '—'}</b></div>
        <div className="stat"><span>缺席</span><b className={sum('absent') ? 'text-danger' : ''}>{sum('absent')}</b></div>
        <div className="stat"><span>未點名</span><b className={sum('unmarked') ? 'text-warn' : ''}>{sum('unmarked')}</b></div>
      </div>
      {data.members.length === 0 ? <Empty text="這段期間沒有上課紀錄" /> : (
        <section className="card">
          <div className="stat-table">
            <div className="stat-tr head"><span>學員</span><span>預約</span><span>出席</span><span>缺席</span><span>出席率</span></div>
            {data.members.map((m) => (
              <div key={m.id} className="stat-tr">
                <span className="min0"><b>{m.name}</b>{m.unmarked > 0 && <em className="text-warn small"> 未點 {m.unmarked}</em>}</span>
                <span>{m.total}</span>
                <span className="text-success">{m.attended}</span>
                <span className={m.absent ? 'text-danger strong' : ''}>{m.absent}</span>
                <span>{m.rate === null ? '—' : `${m.rate}%`}</span>
              </div>
            ))}
          </div>
        </section>
      )}
    </>
  )
}
