import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import { ShareBox } from '../../components/Share'
import { Badge, Confirm, Empty, Field, Loading } from '../../components/ui'
import { addDays, showDate, today } from '../../util'
import { CourseTabs } from './AdminTemplates'
import { countSlots } from './CourseForm'

const WEEK = ['一', '二', '三', '四', '五', '六', '日']

function span(s) {
  if (!s.first_date) return '沒有未來的時段'
  return `${showDate(s.first_date).slice(5)} ～ ${showDate(s.last_date).slice(5)}`
}

// 時段預約活動列表
export default function AdminSlots() {
  const { handleError } = useApp()
  const [list, setList] = useState(null)
  useEffect(() => { api('admin/slot-sets').then(setList).catch(handleError) }, [handleError])
  return (
    <>
      <CourseTabs value="slots" />
      <div className="row between section-head">
        <h3 className="date-title">時段預約（{list?.length ?? 0}）</h3>
        <Link to="/admin/courses/new?type=slots" className="btn btn-small">＋ 新增時段預約</Link>
      </div>
      {!list ? <Loading /> : list.length === 0 ? (
        <Empty text="還沒有時段預約">
          <p className="muted small center">私人課、場地租借這類「球友自己挑時段」的活動，<br />先設好每天的時段與名額就能開放預約。</p>
        </Empty>
      ) : list.map((s) => (
        <Link key={s.id} to={`/admin/slots/${s.id}`} className="card ccard slot-set-row">
          <span className="slot-ico" aria-hidden="true">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round"><rect x="3.5" y="5" width="17" height="15" rx="2.5" /><path d="M3.5 9.5h17M8 13h2M14 13h2M8 16.5h2" /></svg>
          </span>
          <div className="ccard-main">
            <h2 className="ccard-title">{s.name}</h2>
            <div className="ccard-chips">
              <span className="cchip">{span(s)}</span>
              <span className="cchip">{s.slot_count} 個時段 · 每段 {s.capacity} 位</span>
              <span className="cchip">{s.fee > 0 ? `NT$ ${s.fee.toLocaleString()}` : s.cost > 0 ? '課卡' : '免費'}</span>
              {!s.listed && <span className="cchip beginner">只限連結</span>}
            </div>
          </div>
          <div className={`cap ${s.unpaid ? 'near' : ''}`}>
            <b>{s.booked}</b>
            <small>{s.unpaid ? `${s.unpaid} 筆待收款` : '已預約'}</small>
          </div>
        </Link>
      ))}
    </>
  )
}

// 單一時段預約活動：分享連結、各日時段與預約狀況、新增時段
export function SlotAdmin() {
  const { id } = useParams()
  const { handleError, showToast } = useApp()
  const navigate = useNavigate()
  const [d, setD] = useState(null)
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [gen, setGen] = useState(null)
  const load = useCallback(() => api(`admin/slot-sets/${id}`).then((x) => {
    setD(x)
    setGen((g) => g || { from: x.last_date ? addDays(x.last_date, 1) : today(), to: addDays(x.last_date || today(), 7), weekdays: [0, 1, 2, 3, 4, 5, 6], open: '09:00', close: '21:00', minutes: 60, capacity: x.capacity })
  }).catch(handleError), [id, handleError])
  useEffect(() => { load() }, [load])
  if (!d) return <Loading />

  const setG = (k, cast = (v) => v) => (e) => setGen({ ...gen, [k]: cast(e.target.value) })
  const n = countSlots(gen)
  const addSlots = async (e) => {
    e.preventDefault()
    try {
      const r = await api(`admin/slot-sets/${id}/slots`, { method: 'POST', body: gen })
      showToast(r.created ? `已新增 ${r.created} 個時段` : '這些時段都已經有了')
      setAdding(false)
      load()
    } catch (err) { handleError(err) }
  }
  const remove = async () => {
    try {
      await api(`admin/slot-sets/${id}`, { method: 'DELETE' })
      showToast('已刪除')
      navigate('/admin/slots')
    } catch (err) { handleError(err); setRemoving(false) }
  }

  return (
    <>
      <section className="card">
        <div className="row between">
          <Link to="/admin/slots" className="muted small">‹ 回時段預約</Link>
          <Link to={`/admin/slots/${id}/edit`} className="small text-brand">編輯設定</Link>
        </div>
        <h2 className="detail-title">{d.name}</h2>
        <p className="muted small">{span(d)} · 每段 {d.capacity} 位 · {d.fee > 0 ? `每段 NT$ ${d.fee.toLocaleString()}（匯款）` : d.cost > 0 ? '扣課卡' : '免費'}</p>
        <div className="stats stats-3">
          <div className="stat"><span>未來時段</span><b>{d.slot_count}</b></div>
          <div className="stat"><span>已預約</span><b>{d.booked}</b></div>
          <Link to="/admin/orders?tab=fees" className="stat"><span>待收款</span><b className={d.unpaid ? 'text-warn' : ''}>{d.unpaid}</b></Link>
        </div>
      </section>

      <ShareBox c={d} />

      <div className="row between section-head">
        <h3 className="date-title">各時段預約狀況</h3>
        <button className="btn btn-small" onClick={() => setAdding(!adding)}>{adding ? '收起' : '＋ 新增時段'}</button>
      </div>

      {adding && gen && (
        <form className="card form" onSubmit={addSlots}>
          <p className="muted small">已經有的時段會自動略過，不會重複。</p>
          <div className="grid2">
            <Field label="從哪天"><input className="input" type="date" value={gen.from} onChange={setG('from')} required /></Field>
            <Field label="到哪天"><input className="input" type="date" value={gen.to} min={gen.from} onChange={setG('to')} required /></Field>
          </div>
          <div className="weekday-picks">
            {WEEK.map((w, i) => (
              <button key={w} type="button" className={`weekday-pick ${gen.weekdays.includes(i) ? 'on' : ''}`}
                onClick={() => setGen({ ...gen, weekdays: gen.weekdays.includes(i) ? gen.weekdays.filter((x) => x !== i) : [...gen.weekdays, i] })}>{w}</button>
            ))}
          </div>
          <div className="grid2">
            <Field label="每天從幾點"><input className="input" type="time" value={gen.open} onChange={setG('open')} required /></Field>
            <Field label="到幾點"><input className="input" type="time" value={gen.close} onChange={setG('close')} required /></Field>
            <Field label="每段多長">
              <select className="input" value={gen.minutes} onChange={setG('minutes', Number)}>
                {[30, 60, 90, 120, 180].map((m) => <option key={m} value={m}>{m < 60 ? `${m} 分鐘` : `${m / 60} 小時`}</option>)}
              </select>
            </Field>
            <Field label="每段幾位"><input className="input" type="number" min="1" value={gen.capacity} onChange={setG('capacity', Number)} required /></Field>
          </div>
          <button className="btn btn-block" disabled={!n}>{n ? `新增 ${n} 個時段` : '這個設定產生不出時段'}</button>
        </form>
      )}

      {d.days.length === 0 ? <Empty text="沒有未來的時段，按「新增時段」開放" /> : d.days.map((day) => (
        <section key={day.date} className="card">
          <div className="sec-head">
            <h3>{showDate(day.date)}</h3>
            <span>預約 {day.slots.reduce((t, s) => t + s.booked_count, 0)} / {day.slots.reduce((t, s) => t + s.capacity, 0)}</span>
          </div>
          <div className="slot-grid admin">
            {day.slots.map((s) => (
              <Link key={s.id} to={`/admin/courses/${s.id}`}
                className={`slot ${s.booked_count >= s.capacity ? 'full' : ''} ${s.booked_count > 0 ? 'has' : ''} ${s.status === 'cancelled' ? 'off' : ''}`}>
                <b>{s.start_time}</b>
                <small>{s.status === 'cancelled' ? '已停' : `${s.booked_count}/${s.capacity}`}{s.waitlist_count > 0 && ` +候補${s.waitlist_count}`}</small>
                {s.unpaid > 0 && <Badge tone="warn">{s.unpaid} 待收</Badge>}
              </Link>
            ))}
          </div>
        </section>
      ))}

      <button className="btn btn-light text-danger" onClick={() => setRemoving(true)}>刪除這個時段預約</button>
      {removing && (
        <Confirm title="刪除整個時段預約？" danger okText="刪除" onClose={() => setRemoving(false)} onOk={remove}
          text="所有時段都會一起刪除，無法復原。已經有人預約的話不能刪，可改成不公開，或到個別時段停掉。" />
      )}
    </>
  )
}
