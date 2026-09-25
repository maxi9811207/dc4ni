import { useEffect, useState } from 'react'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import { Field, Loading } from '../../components/ui'
import { PLAN_TYPES, today } from '../../util'

const EMPTY = {
  name: '', category: '', teacher_id: '', substitute: false, date: today(), start_time: '19:00', end_time: '21:00',
  capacity: 10, cost: 1, beginner: false, location: '', description: '', booking_deadline_min: 120,
  cancel_deadline_min: 720, plan_ids: [], repeat_weeks: 1,
}

export default function CourseForm() {
  const { id } = useParams()
  const [params] = useSearchParams()
  const { venue, handleError, showToast } = useApp()
  const navigate = useNavigate()
  const [form, setForm] = useState(null)
  const [teachers, setTeachers] = useState([])
  const [plans, setPlans] = useState([])
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api('admin/teachers').then((l) => setTeachers(l.filter((t) => t.active))).catch(handleError)
    api('admin/plans').then(setPlans).catch(handleError)
    const source = id || params.get('copy')
    if (!source) {
      setForm({ ...EMPTY, date: params.get('date') || today(), category: venue?.categories?.[0] || '' })
      return
    }
    api(`courses/${source}`).then((c) => setForm({
      ...EMPTY,
      ...Object.fromEntries(Object.keys(EMPTY).filter((k) => k in c).map((k) => [k, c[k]])),
      teacher_id: c.teacher?.id || '',
      ...(id ? {} : { date: params.get('date') || c.date }),
    })).catch(handleError)
  }, [id, params, venue, handleError])

  if (!form) return <Loading />
  const set = (k, cast = (v) => v) => (e) => setForm({ ...form, [k]: cast(e.target.type === 'checkbox' ? e.target.checked : e.target.value) })
  const togglePlan = (pid) => setForm({ ...form, plan_ids: form.plan_ids.includes(pid) ? form.plan_ids.filter((x) => x !== pid) : [...form.plan_ids, pid] })
  const categories = Array.from(new Set([...(venue?.categories || []), form.category].filter(Boolean)))

  const submit = async (e) => {
    e.preventDefault()
    if (form.end_time <= form.start_time) return showToast('結束時間需晚於開始時間')
    setBusy(true)
    try {
      if (id) {
        await api(`admin/courses/${id}`, { method: 'PUT', body: form })
        showToast('已儲存')
      } else {
        const r = await api('admin/courses', { method: 'POST', body: form })
        showToast(r.ids.length > 1 ? `已建立 ${r.ids.length} 堂課` : '已建立課程')
      }
      navigate(`/admin/courses?date=${form.date}`)
    } catch (err) { handleError(err) } finally { setBusy(false) }
  }

  return (
    <form className="card form" onSubmit={submit}>
      <h3 className="card-title">{id ? '編輯課程' : params.get('copy') ? '複製課程' : '新增課程'}</h3>
      <Field label="課程名稱"><input className="input" value={form.name} onChange={set('name')} required placeholder="例：匹克球初階實戰班 Lv.1" /></Field>
      <div className="grid2">
        <Field label="課程類別">
          <select className="input" value={form.category} onChange={set('category')}>
            <option value="">（無）</option>
            {categories.map((c) => <option key={c}>{c}</option>)}
          </select>
        </Field>
        <Field label="老師">
          <select className="input" value={form.teacher_id} onChange={set('teacher_id')}>
            <option value="">未指定</option>
            {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
      </div>
      <label className="check"><input type="checkbox" checked={form.substitute} onChange={set('substitute')} /> 代課</label>
      <Field label="日期"><input className="input" type="date" value={form.date} onChange={set('date')} required /></Field>
      <div className="grid2">
        <Field label="開始時間"><input className="input" type="time" value={form.start_time} onChange={set('start_time')} required /></Field>
        <Field label="結束時間"><input className="input" type="time" value={form.end_time} onChange={set('end_time')} required /></Field>
      </div>
      {!id && (
        <Field label="重複排課" hint="每週同一時間自動建立，最多 26 週">
          <select className="input" value={form.repeat_weeks} onChange={set('repeat_weeks', Number)}>
            {[1, 2, 4, 8, 12, 26].map((n) => <option key={n} value={n}>{n === 1 ? '只有這一堂' : `連續 ${n} 週`}</option>)}
          </select>
        </Field>
      )}
      <div className="grid2">
        <Field label="名額"><input className="input" type="number" min="1" value={form.capacity} onChange={set('capacity', Number)} required /></Field>
        <Field label="點數卡扣點" hint="堂數卡固定扣 1 堂；填 0 為免費課程"><input className="input" type="number" min="0" value={form.cost} onChange={set('cost', Number)} /></Field>
      </div>
      <label className="check"><input type="checkbox" checked={form.beginner} onChange={set('beginner')} /> 標示「新手友善」</label>
      <Field label="上課地點"><input className="input" value={form.location} onChange={set('location')} /></Field>
      <Field label="課程介紹"><textarea className="input" rows={4} value={form.description} onChange={set('description')} /></Field>
      <div className="grid2">
        <Field label="截止預約（開課前）">
          <select className="input" value={form.booking_deadline_min} onChange={set('booking_deadline_min', Number)}>
            {[0, 30, 60, 120, 180, 360, 720, 1440].map((m) => <option key={m} value={m}>{m === 0 ? '開課前都可預約' : m < 60 ? `${m} 分鐘` : `${m / 60} 小時`}</option>)}
          </select>
        </Field>
        <Field label="自行取消期限（開課前）">
          <select className="input" value={form.cancel_deadline_min} onChange={set('cancel_deadline_min', Number)}>
            {[0, 60, 120, 360, 720, 1440, 2880].map((m) => <option key={m} value={m}>{m === 0 ? '開課前都可取消' : `${m / 60} 小時`}</option>)}
          </select>
        </Field>
      </div>
      <Field label="可使用的課卡" hint="都不勾選＝所有課卡都可使用">
        <div className="checks">
          {plans.map((p) => (
            <label key={p.id} className="check"><input type="checkbox" checked={form.plan_ids.includes(p.id)} onChange={() => togglePlan(p.id)} /> {p.name}<span className="muted small">（{PLAN_TYPES[p.type]}）</span></label>
          ))}
        </div>
      </Field>
      <div className="row gap">
        <button type="button" className="btn btn-light flex1" onClick={() => navigate(-1)}>取消</button>
        <button className="btn flex1" disabled={busy}>{busy ? '儲存中…' : '儲存'}</button>
      </div>
    </form>
  )
}
