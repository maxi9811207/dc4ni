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
  dupr_required: false, dupr_format: 'doubles', dupr_min: '', dupr_max: '', dupr_verified_only: false,
  match_format: 'rotating', games_to: 11, listed: true, fee: 0,
}

// template=true 時編輯課程範本（沒有日期，可同步更新之後的課程）
function fromSource(c) {
  return {
    ...EMPTY,
    ...Object.fromEntries(Object.keys(EMPTY).filter((k) => k in c && c[k] !== null).map((k) => [k, c[k]])),
    teacher_id: c.teacher?.id || c.teacher_id || '',
    dupr_min: c.dupr_min ?? '',
    dupr_max: c.dupr_max ?? '',
  }
}

export default function CourseForm({ template = false }) {
  const { id } = useParams()
  const [params] = useSearchParams()
  const { venue, handleError, showToast } = useApp()
  const navigate = useNavigate()
  const [form, setForm] = useState(null)
  const [teachers, setTeachers] = useState([])
  const [plans, setPlans] = useState([])
  const [busy, setBusy] = useState(false)
  const [templates, setTemplates] = useState([])
  const [applyFuture, setApplyFuture] = useState(true)

  useEffect(() => {
    api('admin/teachers').then((l) => setTeachers(l.filter((t) => t.active))).catch(handleError)
    api('admin/plans').then(setPlans).catch(handleError)
    if (!template && !id) api('admin/templates').then((l) => setTemplates(l.filter((t) => t.active))).catch(handleError)
    if (template) {
      if (!id) { setForm({ ...EMPTY, category: venue?.categories?.[0] || '' }); return }
      api(`admin/templates/${id}`).then((t) => setForm(fromSource(t))).catch(handleError)
      return
    }
    if (params.get('template')) {
      api(`admin/templates/${params.get('template')}`).then((t) => setForm({ ...fromSource(t), template_id: t.id, date: params.get('date') || today() })).catch(handleError)
      return
    }
    const source = id || params.get('copy')
    if (!source) {
      setForm({ ...EMPTY, date: params.get('date') || today(), category: venue?.categories?.[0] || '' })
      return
    }
    api(`courses/${source}`).then((c) => setForm({
      ...fromSource(c),
      template_id: c.template_id,
      ...(id ? {} : { date: params.get('date') || c.date }),
    })).catch(handleError)
  }, [id, params, venue, handleError, template])

  if (!form) return <Loading />
  const set = (k, cast = (v) => v) => (e) => setForm({ ...form, [k]: cast(e.target.type === 'checkbox' ? e.target.checked : e.target.value) })
  const togglePlan = (pid) => setForm({ ...form, plan_ids: form.plan_ids.includes(pid) ? form.plan_ids.filter((x) => x !== pid) : [...form.plan_ids, pid] })
  const useTemplate = (tid) => {
    const t = templates.find((x) => String(x.id) === tid)
    setForm(t ? { ...fromSource(t), template_id: t.id, date: form.date, repeat_weeks: form.repeat_weeks } : { ...form, template_id: null })
  }
  const categories = Array.from(new Set([...(venue?.categories || []), form.category].filter(Boolean)))
  const payMode = form.fee > 0 ? 'fee' : form.cost > 0 ? 'card' : 'free'
  const setPayMode = (m) => setForm({ ...form, fee: m === 'fee' ? (form.fee || 500) : 0, cost: m === 'card' ? (form.cost || 1) : 0 })

  const submit = async (e) => {
    e.preventDefault()
    if (form.end_time <= form.start_time) return showToast('結束時間需晚於開始時間')
    if (form.dupr_required && form.dupr_min !== '' && form.dupr_max !== '' && Number(form.dupr_min) > Number(form.dupr_max)) return showToast('DUPR 最低分不能高於最高分')
    setBusy(true)
    try {
      if (template) {
        if (id) {
          const r = await api(`admin/templates/${id}`, { method: 'PUT', body: { ...form, apply_future: applyFuture } })
          showToast(applyFuture && r.updated ? `已儲存，並更新之後的 ${r.updated} 堂課` : '已儲存範本')
        } else {
          await api('admin/templates', { method: 'POST', body: form })
          showToast('已建立課程範本')
        }
        navigate('/admin/templates')
        return
      }
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
      <h3 className="card-title">{template ? (id ? '編輯課程範本' : '新增課程範本') : id ? '編輯課程' : params.get('copy') ? '複製課程' : '新增課程'}</h3>
      {template && <p className="muted small">範本是課程的預設內容，建好後用「排課」一次排出多堂課。</p>}
      {!template && !id && templates.length > 0 && (
        <Field label="從課程範本帶入" hint="帶入範本的內容與時間，仍可再修改">
          <select className="input" value={form.template_id || ''} onChange={(e) => useTemplate(e.target.value)}>
            <option value="">不使用範本</option>
            {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
      )}
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
      {!template && <Field label="日期"><input className="input" type="date" value={form.date} onChange={set('date')} required /></Field>}
      <div className="grid2">
        <Field label="開始時間"><input className="input" type="time" value={form.start_time} onChange={set('start_time')} required /></Field>
        <Field label="結束時間"><input className="input" type="time" value={form.end_time} onChange={set('end_time')} required /></Field>
      </div>
      {!id && !template && (
        <Field label="重複排課" hint="每週同一時間自動建立，最多 26 週">
          <select className="input" value={form.repeat_weeks} onChange={set('repeat_weeks', Number)}>
            {[1, 2, 4, 8, 12, 26].map((n) => <option key={n} value={n}>{n === 1 ? '只有這一堂' : `連續 ${n} 週`}</option>)}
          </select>
        </Field>
      )}
      <div className="grid2">
        <Field label="名額"><input className="input" type="number" min="1" value={form.capacity} onChange={set('capacity', Number)} required /></Field>
        <Field label="付費方式">
          <select className="input" value={payMode} onChange={(e) => setPayMode(e.target.value)}>
            <option value="card">使用課卡</option>
            <option value="fee">單次報名費</option>
            <option value="free">免費</option>
          </select>
        </Field>
      </div>
      {payMode === 'card' && (
        <Field label="點數卡扣點" hint="堂數卡固定扣 1 堂、無限卡不扣；學員需有可用課卡才能報名">
          <input className="input" type="number" min="1" value={form.cost} onChange={set('cost', Number)} required />
        </Field>
      )}
      {payMode === 'fee' && (
        <Field label="報名費（NT$）" hint="不需課卡。報名後保留名額，學員依「場館設定 → 付款說明」付款，您在名單頁確認收款">
          <input className="input" type="number" min="1" value={form.fee || ''} onChange={set('fee', Number)} required placeholder="500" />
        </Field>
      )}
      <label className="check"><input type="checkbox" checked={form.beginner} onChange={set('beginner')} /> 標示「新手友善」</label>
      <label className="check">
        <input type="checkbox" checked={!form.listed} onChange={(e) => setForm({ ...form, listed: !e.target.checked })} />
        只限連結報名（不出現在課表，適合一次性活動；建立後到名單頁複製報名連結）
      </label>
      <div className={`dupr-box ${form.dupr_required ? 'on' : ''}`}>
        <label className="check strong">
          <input type="checkbox" checked={form.dupr_required} onChange={(e) => setForm({ ...form, dupr_required: e.target.checked, category: e.target.checked && categories.includes('DUPR 場') ? 'DUPR 場' : form.category })} />
          DUPR 場（限綁定 DUPR 帳號的學員報名）
        </label>
        {form.dupr_required && (
          <>
            <div className="grid2">
              <Field label="依據分數">
                <select className="input" value={form.dupr_format} onChange={set('dupr_format')}>
                  <option value="doubles">雙打 Doubles</option>
                  <option value="singles">單打 Singles</option>
                </select>
              </Field>
              <div />
              <Field label="最低分" hint="留空＝不限"><input className="input" type="number" step="0.001" min="1" max="8" value={form.dupr_min} onChange={set('dupr_min')} placeholder="3.000" /></Field>
              <Field label="最高分" hint="留空＝不限"><input className="input" type="number" step="0.001" min="1" max="8" value={form.dupr_max} onChange={set('dupr_max')} placeholder="4.000" /></Field>
            </div>
            <label className="check"><input type="checkbox" checked={form.dupr_verified_only} onChange={set('dupr_verified_only')} /> 只限場館已驗證的 DUPR 帳號</label>
            <div className="grid2">
              <Field label="賽制" hint={form.dupr_format === 'singles' ? '單打場固定為單打循環賽' : form.match_format === 'fixed' ? '兩人一隊，學員可指定隊友' : '每局換搭檔，每組 4～7 人'}>
                <select className="input" value={form.dupr_format === 'singles' ? 'singles' : form.match_format} onChange={set('match_format')} disabled={form.dupr_format === 'singles'}>
                  {form.dupr_format === 'singles' && <option value="singles">單打循環賽</option>}
                  <option value="rotating">輪換搭檔</option>
                  <option value="fixed">固定搭檔</option>
                </select>
              </Field>
              <Field label="每局分數" hint="領先 2 分獲勝">
                <select className="input" value={form.games_to} onChange={set('games_to', Number)}>
                  {[11, 15, 21].map((n) => <option key={n} value={n}>打到 {n} 分</option>)}
                </select>
              </Field>
            </div>
          </>
        )}
      </div>
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
      {template && id && (
        <label className="check strong"><input type="checkbox" checked={applyFuture} onChange={(e) => setApplyFuture(e.target.checked)} /> 同步更新這個範本之後、尚未開始的課程（時間不變，名額不會少於已報名人數）</label>
      )}
      <div className="row gap">
        <button type="button" className="btn btn-light flex1" onClick={() => navigate(-1)}>取消</button>
        <button className="btn flex1" disabled={busy}>{busy ? '儲存中…' : '儲存'}</button>
      </div>
    </form>
  )
}
