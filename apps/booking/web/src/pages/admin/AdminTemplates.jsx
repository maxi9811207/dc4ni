import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import { Avatar, Badge, Chips, Confirm, Empty, Field, Loading, Modal } from '../../components/ui'
import { addDays, duprRange, fromISO, today } from '../../util'

const WEEKDAYS = [['0', '一'], ['1', '二'], ['2', '三'], ['3', '四'], ['4', '五'], ['5', '六'], ['6', '日']]

export function CourseTabs({ value }) {
  return (
    <div className="chips">
      <Link to="/admin/templates" className={`chip ${value === 'templates' ? 'active' : ''}`}>課程範本</Link>
      <Link to="/admin/courses" className={`chip ${value === 'daily' ? 'active' : ''}`}>每日課程</Link>
    </div>
  )
}

export default function AdminTemplates() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const [scheduling, setScheduling] = useState(null)
  const [removing, setRemoving] = useState(null)
  const load = useCallback(() => api('admin/templates').then(setList).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

  const remove = async () => {
    try {
      await api(`admin/templates/${removing.id}`, { method: 'DELETE' })
      showToast('已刪除範本，已排的課程保留')
      setRemoving(null)
      load()
    } catch (e) { handleError(e) }
  }

  return (
    <>
      <CourseTabs value="templates" />
      <div className="row between section-head">
        <h3 className="date-title">課程範本（{list?.length ?? 0}）</h3>
        <Link to="/admin/templates/new" className="btn btn-small">＋ 新增範本</Link>
      </div>
      {!list ? <Loading /> : list.length === 0 ? (
        <Empty text="還沒有課程範本">
          <p className="muted small center">把固定開的課（例如每週二、四的中階班）建成範本，<br />之後一次排好幾週的課。</p>
        </Empty>
      ) : list.map((t) => (
        <div key={t.id} className={`card admin-course ${t.active ? '' : 'dim'}`}>
          <div className="row gap">
            <Avatar src={t.teacher?.photo_url} name={t.teacher?.name} />
            <div className="flex1 min0">
              <h2 className="course-name">
                {t.name}
                {t.dupr_required && <span className="badge badge-dupr">{duprRange(t, true)}</span>}
                {!t.active && <Badge tone="gray">停用</Badge>}
              </h2>
              <p className="course-meta"><b className="course-time">{t.start_time}~{t.end_time}</b> · {t.category || '未分類'} · 名額 {t.capacity}</p>
              <p className="small muted">{t.teacher?.name || '未指定老師'} · {t.upcoming ? `之後已排 ${t.upcoming} 堂，下一堂 ${t.next_date.slice(5).replace('-', '/')}` : '尚未排課'}</p>
            </div>
          </div>
          <div className="admin-actions">
            <button className="btn btn-small" onClick={() => setScheduling(t)}>排課</button>
            <Link to={`/admin/templates/${t.id}/edit`} className="btn btn-small btn-light">編輯</Link>
            <button className="btn btn-small btn-light text-danger" onClick={() => setRemoving(t)}>刪除</button>
          </div>
        </div>
      ))}
      {scheduling && <ScheduleDialog t={scheduling} onClose={() => setScheduling(null)} onDone={() => { setScheduling(null); load() }} />}
      {removing && (
        <Confirm title={`刪除「${removing.name}」？`} danger okText="刪除" onClose={() => setRemoving(null)} onOk={remove}
          text="只會刪除範本，已經排好的課程和報名都會保留。" />
      )}
    </>
  )
}

function ScheduleDialog({ t, onClose, onDone }) {
  const { handleError, showToast } = useApp()
  const start = addDays(today(), 1)
  const [form, setForm] = useState({ from: start, to: addDays(start, 27), weekdays: [], start_time: t.start_time, end_time: t.end_time })
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const toggle = (d) => setForm({ ...form, weekdays: form.weekdays.includes(d) ? form.weekdays.filter((x) => x !== d) : [...form.weekdays, d] })

  // 預估堂數
  let count = 0
  if (form.from && form.to && form.from <= form.to) {
    for (let d = form.from; d <= form.to; d = addDays(d, 1)) {
      if (form.weekdays.includes(String((fromISO(d).getDay() + 6) % 7))) count++
      if (count > 400) break
    }
  }

  const submit = async () => {
    setBusy(true)
    try {
      const r = await api(`admin/templates/${t.id}/schedule`, { method: 'POST', body: { ...form, weekdays: form.weekdays.map(Number) } })
      showToast(r.skipped ? `已排 ${r.created} 堂課（${r.skipped} 堂已存在，略過）` : `已排 ${r.created} 堂課`)
      onDone()
    } catch (e) { handleError(e) } finally { setBusy(false) }
  }

  return (
    <Modal onClose={onClose}>
      <h3 className="dialog-title">排課：{t.name}</h3>
      <div className="grid2">
        <Field label="從"><input className="input" type="date" value={form.from} onChange={set('from')} /></Field>
        <Field label="到"><input className="input" type="date" value={form.to} onChange={set('to')} /></Field>
      </div>
      <Field label="每週上課日">
        <div className="weekday-picks">
          {WEEKDAYS.map(([v, l]) => (
            <button key={v} type="button" className={`weekday-pick ${form.weekdays.includes(v) ? 'on' : ''}`} onClick={() => toggle(v)}>{l}</button>
          ))}
        </div>
      </Field>
      <div className="grid2">
        <Field label="開始時間"><input className="input" type="time" value={form.start_time} onChange={set('start_time')} /></Field>
        <Field label="結束時間"><input className="input" type="time" value={form.end_time} onChange={set('end_time')} /></Field>
      </div>
      <Chips value="" onChange={(n) => setForm({ ...form, to: addDays(form.from, Number(n) * 7 - 1) })}
        options={[['4', '4 週'], ['8', '8 週'], ['12', '12 週']]} />
      <p className="pay-info small">將建立 <b>{count > 400 ? '400+' : count}</b> 堂課。同一天同時段已經排過的會自動略過。</p>
      <button className="btn btn-block" disabled={busy || count === 0} onClick={submit}>{busy ? '排課中…' : `確認排課`}</button>
    </Modal>
  )
}
