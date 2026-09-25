import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import WeekPicker from '../../components/WeekPicker'
import { Avatar, Badge, Confirm, Empty, Loading } from '../../components/ui'
import { addDays, mondayOf, showDate, today } from '../../util'

export default function AdminCourses() {
  const { handleError, showToast } = useApp()
  const [params, setParams] = useSearchParams()
  const date = params.get('date') || today()
  const [week, setWeek] = useState(null)
  const [confirm, setConfirm] = useState(null)

  const monday = mondayOf(date)
  const load = useCallback(() => {
    api(`admin/courses?from=${monday}&to=${addDays(monday, 6)}`).then(setWeek).catch(handleError)
  }, [monday, handleError])
  useEffect(() => { load() }, [load])

  const dayCourses = (week || []).filter((c) => c.date === date)

  const run = async (fn, msg) => {
    try { await fn(); showToast(msg); setConfirm(null); load() } catch (e) { handleError(e); setConfirm(null) }
  }

  return (
    <>
      <WeekPicker value={date} onChange={(d) => setParams({ date: d }, { replace: true })} />
      {week && (
        <p className="muted small week-summary">
          本週共 {week.length} 堂課，{week.reduce((s, c) => s + c.booked_count, 0)} 人次預約
        </p>
      )}
      <div className="row between section-head">
        <h3 className="date-title">{showDate(date)}</h3>
        <Link to={`/admin/courses/new?date=${date}`} className="btn btn-small">＋ 新增課程</Link>
      </div>
      {!week ? <Loading /> : dayCourses.length === 0 ? <Empty text="這天沒有課程" /> : dayCourses.map((c) => (
        <div key={c.id} className={`card admin-course ${c.status === 'cancelled' ? 'dim' : ''}`}>
          <Link to={`/admin/courses/${c.id}`} className="row gap">
            <Avatar src={c.teacher?.photo_url} name={c.teacher?.name} />
            <div className="flex1 min0">
              <h2 className="course-name">{c.name}{c.status === 'cancelled' && <Badge tone="gray">已停課</Badge>}</h2>
              <p className="course-meta"><b className="course-time">{c.start_time}~{c.end_time}</b> · {c.category}</p>
              <p className="small">{c.teacher?.name || '未指定老師'}{c.substitute && '（代課）'}</p>
            </div>
            <div className="right">
              <b className={c.remain === 0 ? 'text-danger' : 'text-brand'}>{c.booked_count}/{c.capacity}</b>
              {c.waitlist_count > 0 && <p className="small text-warn">候補 {c.waitlist_count}</p>}
            </div>
          </Link>
          <div className="admin-actions">
            <Link to={`/admin/courses/${c.id}`} className="btn btn-small">名單點名</Link>
            <Link to={`/admin/courses/${c.id}/edit`} className="btn btn-small btn-light">編輯</Link>
            <Link to={`/admin/courses/new?copy=${c.id}`} className="btn btn-small btn-light">複製</Link>
            {c.status === 'cancelled'
              ? <button className="btn btn-small btn-light" onClick={() => run(() => api(`admin/courses/${c.id}/status`, { method: 'POST', body: { status: 'open' } }), '已恢復開課')}>恢復</button>
              : <button className="btn btn-small btn-light" onClick={() => setConfirm({ kind: 'stop', c })}>停課</button>}
            <button className="btn btn-small btn-light text-danger" onClick={() => setConfirm({ kind: 'delete', c })}>刪除</button>
          </div>
        </div>
      ))}
      {confirm?.kind === 'stop' && (
        <Confirm title="確定停課？" danger okText="停課" onClose={() => setConfirm(null)}
          text={`「${confirm.c.name}」的 ${confirm.c.booked_count} 位預約與 ${confirm.c.waitlist_count} 位候補會被取消，課卡自動退還並通知學生。`}
          onOk={() => run(() => api(`admin/courses/${confirm.c.id}/status`, { method: 'POST', body: { status: 'cancelled' } }), '已停課並通知學生')} />
      )}
      {confirm?.kind === 'delete' && (
        <Confirm title="確定刪除？" danger okText="刪除" onClose={() => setConfirm(null)}
          text={`刪除「${confirm.c.name}」後無法復原。已有人預約的課程請改用停課。`}
          onOk={() => run(() => api(`admin/courses/${confirm.c.id}`, { method: 'DELETE' }), '已刪除')} />
      )}
    </>
  )
}
