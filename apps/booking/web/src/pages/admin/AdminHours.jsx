import { useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Empty, Loading } from '../../components/ui'
import { showDate } from '../../util'

function monthRange(offset) {
  const d = new Date()
  d.setDate(1)
  d.setMonth(d.getMonth() + offset)
  const y = d.getFullYear(), m = String(d.getMonth() + 1).padStart(2, '0')
  const last = new Date(y, d.getMonth() + 1, 0).getDate()
  return { label: `${y} 年 ${d.getMonth() + 1} 月`, from: `${y}-${m}-01`, to: `${y}-${m}-${String(last).padStart(2, '0')}` }
}

// 教練時數與鐘點費：已開始、未停課的課；場主看全部老師，教練只看自己
export default function AdminHours() {
  const { user, handleError } = useApp()
  const [offset, setOffset] = useState(0)
  const [d, setD] = useState(null)
  const [open, setOpen] = useState(null)
  const r = monthRange(offset)
  useEffect(() => {
    setD(null)
    api(`admin/coach-hours?from=${r.from}&to=${r.to}`).then(setD).catch(handleError)
  }, [r.from, r.to, handleError])
  const total = (d?.teachers || []).reduce((t, x) => t + x.amount, 0)
  return (
    <>
      <div className="row between">
        <button className="btn btn-small btn-light" onClick={() => setOffset(offset - 1)}>‹ 上個月</button>
        <b>{r.label}</b>
        <button className="btn btn-small btn-light" disabled={offset >= 0} onClick={() => setOffset(offset + 1)}>下個月 ›</button>
      </div>
      {!d ? <Loading /> : d.teachers.length === 0 ? <Empty text="這個月沒有課" /> : (
        <>
          {user.role === 'owner' && (
            <div className="stats">
              <div className="stat"><span>本月鐘點費合計</span><b>NT$ {total.toLocaleString()}</b></div>
              <div className="stat"><span>總時數</span><b>{d.teachers.reduce((t, x) => t + x.hours, 0).toFixed(1)}</b></div>
            </div>
          )}
          {d.teachers.map((t) => (
            <section key={t.teacher_id} className="card">
              <button type="button" className="row between hours-head" onClick={() => setOpen(open === t.teacher_id ? null : t.teacher_id)}>
                <b>{t.name}</b>
                <span className="muted small">{t.sessions} 堂・{t.hours} 小時・出席 {t.attended} 人次</span>
              </button>
              <p className="small">{t.rate ? `鐘點費 NT$ ${t.rate.toLocaleString()}／小時 → ` : ''}<b>NT$ {t.amount.toLocaleString()}</b>{!t.rate && user.role === 'owner' && <span className="muted">（到「師資團隊」設定鐘點費）</span>}</p>
              {open === t.teacher_id && (
                <ul className="hours-list">
                  {t.courses.map((c) => <li key={c.id}><span>{showDate(c.date).slice(5)} {c.start_time}–{c.end_time}</span>{c.name}</li>)}
                </ul>
              )}
            </section>
          ))}
        </>
      )}
      <p className="muted small">只計算已經開始、沒有停課的課；時數依課程時間計算。</p>
    </>
  )
}
