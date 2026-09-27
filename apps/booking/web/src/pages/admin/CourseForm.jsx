import { useEffect, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import ImageInput from '../../components/ImageInput'
import { Field, Loading } from '../../components/ui'
import { PLAN_TYPES, addDays, fromISO, today } from '../../util'

const EMPTY = {
  name: '', category: '', teacher_id: '', substitute: false, date: today(), start_time: '19:00', end_time: '21:00',
  capacity: 10, cost: 0, beginner: false, location: '', description: '', booking_deadline_min: 120,
  cancel_deadline_min: 720, plan_ids: [], repeat_weeks: 1,
  dupr_required: false, dupr_format: 'doubles', dupr_min: '', dupr_max: '', dupr_verified_only: false,
  match_format: 'rotating', games_to: 11, listed: true, fee: 0, pay_hours: 48, cover_url: '', show_attendees: true,
}
// 時段預約的產生設定
const SLOT_GEN = { from: today(), to: addDays(today(), 13), weekdays: [0, 1, 2, 3, 4, 5, 6], open: '09:00', close: '21:00', minutes: 60 }

export const TYPES = [
  ['single', '單次活動', '選好日期時間，球友按「報名」就能參加。課程、球敘、一次性活動都用這個'],
  ['dupr', 'DUPR 活動', '限綁定 DUPR 的球友報名，可設分數範圍；人到齊後排賽程、記比分'],
  ['slots', '時段預約', '先設好每天的時段和每段名額，球友自己挑時段。私人課、場地租借用這個'],
]
const WEEK = ['一', '二', '三', '四', '五', '六', '日']
const toMin = (t) => Number(t.slice(0, 2)) * 60 + Number(t.slice(3, 5))

export function countSlots(g) {
  if (!g.from || !g.to || g.to < g.from || !g.minutes) return 0
  const per = Math.max(Math.floor((toMin(g.close) - toMin(g.open)) / g.minutes), 0)
  let n = 0
  for (let d = g.from; d <= g.to && n < 100000; d = addDays(d, 1)) {
    if (g.weekdays.includes((fromISO(d).getDay() + 6) % 7)) n += per
  }
  return n
}

function fromSource(c) {
  return {
    ...EMPTY,
    ...Object.fromEntries(Object.keys(EMPTY).filter((k) => k in c && c[k] !== null).map((k) => [k, c[k]])),
    teacher_id: c.teacher?.id || c.teacher_id || '',
    dupr_min: c.dupr_min ?? '',
    dupr_max: c.dupr_max ?? '',
  }
}

function Step({ n, title, tag, children }) {
  return (
    <section className="card form form-step">
      <div className="step-head">
        {n && <span className="step-n">{n}</span>}
        <h3>{title}</h3>
        {tag && <span className={`step-tag ${tag === '必填' ? 'req' : ''}`}>{tag}</span>}
      </div>
      {children}
    </section>
  )
}

// 課程（單次／DUPR）、課程範本（template）、時段預約（type=slots，或 slotId 編輯）共用的建立表單
export default function CourseForm({ template = false, slotId }) {
  const { id } = useParams()
  const [params] = useSearchParams()
  const { venue, handleError, showToast } = useApp()
  const navigate = useNavigate()
  const [form, setForm] = useState(null)
  const [type, setType] = useState(params.get('type') === 'slots' || slotId ? 'slots' : params.get('type') === 'dupr' ? 'dupr' : 'single')
  const [gen, setGen] = useState(SLOT_GEN)
  const [teachers, setTeachers] = useState([])
  const [plans, setPlans] = useState([])
  const [busy, setBusy] = useState(false)
  const [templates, setTemplates] = useState([])
  const [applyFuture, setApplyFuture] = useState(true)
  const [slotOf, setSlotOf] = useState(null)
  const editing = Boolean(id || slotId)

  useEffect(() => {
    api('admin/teachers').then((l) => setTeachers(l.filter((t) => t.active))).catch(handleError)
    api('admin/plans').then(setPlans).catch(handleError)
    if (!template && !id && !slotId) api('admin/templates').then((l) => setTemplates(l.filter((t) => t.active))).catch(handleError)
    const fresh = { ...EMPTY, date: params.get('date') || today() }
    if (slotId) {
      api(`admin/slot-sets/${slotId}`).then((s) => setForm(fromSource(s))).catch(handleError)
      return
    }
    if (template) {
      if (!id) { setForm(fresh); return }
      api(`admin/templates/${id}`).then((t) => { setForm(fromSource(t)); setType(t.dupr_required ? 'dupr' : 'single') }).catch(handleError)
      return
    }
    if (params.get('template')) {
      api(`admin/templates/${params.get('template')}`).then((t) => { setForm({ ...fromSource(t), template_id: t.id, date: params.get('date') || today() }); setType(t.dupr_required ? 'dupr' : 'single') }).catch(handleError)
      return
    }
    const source = id || params.get('copy')
    if (!source) { setForm(fresh); return }
    api(`courses/${source}`).then((c) => {
      setForm({ ...fromSource(c), template_id: c.template_id, ...(id ? {} : { date: params.get('date') || c.date }) })
      setType(c.dupr_required ? 'dupr' : 'single')
      setSlotOf(c.slot_set)
    }).catch(handleError)
  }, [id, slotId, params, handleError, template])

  if (!form) return <Loading />
  const isSlots = type === 'slots'
  const set = (k, cast = (v) => v) => (e) => setForm({ ...form, [k]: cast(e.target.type === 'checkbox' ? e.target.checked : e.target.value) })
  const setG = (k, cast = (v) => v) => (e) => setGen({ ...gen, [k]: cast(e.target.value) })
  const togglePlan = (pid) => setForm({ ...form, plan_ids: form.plan_ids.includes(pid) ? form.plan_ids.filter((x) => x !== pid) : [...form.plan_ids, pid] })
  const toggleDay = (d) => setGen({ ...gen, weekdays: gen.weekdays.includes(d) ? gen.weekdays.filter((x) => x !== d) : [...gen.weekdays, d].sort() })
  const useTemplate = (tid) => {
    const t = templates.find((x) => String(x.id) === tid)
    if (!t) return setForm({ ...form, template_id: null })
    setForm({ ...fromSource(t), template_id: t.id, date: form.date, repeat_weeks: form.repeat_weeks })
    setType(t.dupr_required ? 'dupr' : 'single')
  }
  const pickType = (t) => {
    setType(t)
    if (t === 'slots') setForm({ ...form, capacity: form.capacity === EMPTY.capacity ? 1 : form.capacity, booking_deadline_min: 60, cancel_deadline_min: 1440, show_attendees: false })
    else if (type === 'slots') setForm({ ...form, show_attendees: true })
  }
  const categories = Array.from(new Set([...(venue?.categories || []), form.category].filter(Boolean)))
  const payMode = form.fee > 0 ? 'fee' : form.cost > 0 ? 'card' : 'free'
  const setPayMode = (m) => setForm({ ...form, fee: m === 'fee' ? (form.fee || 300) : 0, cost: m === 'card' ? (form.cost || 1) : 0 })
  const slotCount = isSlots && !slotId ? countSlots(gen) : 0
  const noun = isSlots ? '活動' : template ? '範本' : '活動'

  const submit = async (e) => {
    e.preventDefault()
    if (!form.name.trim()) return showToast('請填活動名稱')
    if (!isSlots && form.end_time <= form.start_time) return showToast('結束時間要晚於開始時間')
    if (isSlots && !slotId) {
      if (gen.to < gen.from) return showToast('結束日期不能早於開始日期')
      if (!gen.weekdays.length) return showToast('請至少選一個星期')
      if (!slotCount) return showToast('這個設定產生不出任何時段，請檢查營業時間與每段長度')
    }
    if (payMode === 'fee' && !(form.fee > 0)) return showToast('請填報名費金額')
    if (type === 'dupr' && form.dupr_min !== '' && form.dupr_max !== '' && Number(form.dupr_min) > Number(form.dupr_max)) return showToast('DUPR 最低分不能高於最高分')
    const body = { ...form, dupr_required: type === 'dupr' }
    setBusy(true)
    try {
      if (isSlots) {
        if (slotId) {
          const r = await api(`admin/slot-sets/${slotId}`, { method: 'PUT', body })
          showToast(r.updated ? `已儲存，並更新 ${r.updated} 個還沒開始的時段` : '已儲存')
          return navigate(`/admin/slots/${slotId}`)
        }
        const r = await api('admin/slot-sets', { method: 'POST', body: { ...body, ...gen } })
        showToast(`已建立 ${r.created} 個時段，把連結分享出去吧`)
        return navigate(`/admin/slots/${r.id}`)
      }
      if (template) {
        if (id) {
          const r = await api(`admin/templates/${id}`, { method: 'PUT', body: { ...body, apply_future: applyFuture } })
          showToast(applyFuture && r.updated ? `已儲存，並更新之後的 ${r.updated} 堂課` : '已儲存範本')
        } else {
          await api('admin/templates', { method: 'POST', body })
          showToast('已建立課程範本')
        }
        return navigate('/admin/templates')
      }
      if (id) {
        await api(`admin/courses/${id}`, { method: 'PUT', body })
        showToast('已儲存')
      } else {
        const r = await api('admin/courses', { method: 'POST', body })
        showToast(r.ids.length > 1 ? `已建立 ${r.ids.length} 場` : '已建立，把報名連結分享出去吧')
        if (r.ids.length === 1) return navigate(`/admin/courses/${r.ids[0]}`)
      }
      navigate(`/admin/courses?date=${form.date}`)
    } catch (err) { handleError(err) } finally { setBusy(false) }
  }

  const types = TYPES.filter(([k]) => !(template && k === 'slots'))
  let n = 0
  const step = () => ++n

  return (
    <form className="form-steps" onSubmit={submit}>
      <div className="form-intro">
        <h2>{slotId ? '時段預約設定' : template ? (id ? '編輯課程範本' : '新增課程範本') : id ? '編輯活動' : params.get('copy') ? '複製活動' : '建立活動'}</h2>
        <p className="muted small">{template ? '範本是固定開的課的預設內容，建好後用「排課」一次排好幾週。' : '只有標「必填」的要填，其他都有預設值，之後也可以再改。'}</p>
      </div>
      {slotOf && (
        <p className="alert warn">這是「{slotOf.name}」的其中一個時段，這裡只改這一段。要改全部時段請到 <Link className="strong" to={`/admin/slots/${slotOf.id}/edit`}>活動設定</Link>。</p>
      )}

      {!editing && !slotOf && (
        <Step n={step()} title="這是哪一種活動？">
          <div className="type-picks">
            {types.map(([k, label, desc]) => (
              <button key={k} type="button" className={`type-pick ${type === k ? 'on' : ''}`} onClick={() => pickType(k)} aria-pressed={type === k}>
                <b>{label}</b><span>{desc}</span>
              </button>
            ))}
          </div>
          {!isSlots && templates.length > 0 && (
            <Field label="從課程範本帶入（選填）" hint="固定開的課可以先建範本，這裡一鍵帶入">
              <select className="input" value={form.template_id || ''} onChange={(e) => useTemplate(e.target.value)}>
                <option value="">不使用範本</option>
                {templates.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </Field>
          )}
        </Step>
      )}
      {editing && !isSlots && !slotOf && (
        <Step title="活動類型">
          <div className="seg">
            {types.filter(([k]) => k !== 'slots').map(([k, label]) => <button key={k} type="button" className={type === k ? 'active' : ''} onClick={() => setType(k)}>{label}</button>)}
          </div>
        </Step>
      )}

      <Step n={step()} title="名稱與時間" tag="必填">
        <Field label={`${noun}名稱`}>
          <input className="input" value={form.name} onChange={set('name')} required placeholder={isSlots ? '例：場地租借、一對一私人課' : type === 'dupr' ? '例：DUPR 積分雙打團 3.0–4.0' : '例：週六下午球敘'} />
        </Field>
        {isSlots ? (
          slotId ? <p className="muted small">時段在活動頁用「新增時段」加，個別時段可以停掉或刪除。</p> : (
            <>
              <div className="grid2">
                <Field label="從哪天開始"><input className="input" type="date" value={gen.from} onChange={setG('from')} required /></Field>
                <Field label="到哪天"><input className="input" type="date" value={gen.to} min={gen.from} onChange={setG('to')} required /></Field>
              </div>
              <Field label="哪幾天開放">
                <div className="weekday-picks">
                  {WEEK.map((w, i) => <button key={w} type="button" className={`weekday-pick ${gen.weekdays.includes(i) ? 'on' : ''}`} onClick={() => toggleDay(i)}>{w}</button>)}
                </div>
              </Field>
              <div className="grid2">
                <Field label="每天從幾點"><input className="input" type="time" value={gen.open} onChange={setG('open')} required /></Field>
                <Field label="到幾點"><input className="input" type="time" value={gen.close} onChange={setG('close')} required /></Field>
              </div>
              <Field label="每個時段多長">
                <select className="input" value={gen.minutes} onChange={setG('minutes', Number)}>
                  {[30, 60, 90, 120, 180].map((m) => <option key={m} value={m}>{m < 60 ? `${m} 分鐘` : `${m / 60} 小時`}</option>)}
                </select>
              </Field>
            </>
          )
        ) : (
          <>
            {!template && <Field label="日期"><input className="input" type="date" value={form.date} onChange={set('date')} required /></Field>}
            <div className="grid2">
              <Field label="開始"><input className="input" type="time" value={form.start_time} onChange={set('start_time')} required /></Field>
              <Field label="結束"><input className="input" type="time" value={form.end_time} onChange={set('end_time')} required /></Field>
            </div>
          </>
        )}
        <Field label={isSlots ? '每個時段可預約幾位' : '名額'} hint={isSlots ? '場地有 2 面就填 2；一對一私人課填 1' : '滿了之後可以候補'}>
          <input className="input" type="number" min="1" value={form.capacity} onChange={set('capacity', Number)} required />
        </Field>
        {isSlots && !slotId && (
          <p className={`slot-preview ${slotCount ? '' : 'bad'}`}>
            {slotCount ? `會建立 ${slotCount} 個時段（每段 ${form.capacity} 位）` : '目前的設定產生不出時段'}
          </p>
        )}
      </Step>

      <Step n={step()} title="要收費嗎？" tag="必填">
        <div className="seg">
          <button type="button" className={payMode === 'free' ? 'active' : ''} onClick={() => setPayMode('free')}>免費</button>
          <button type="button" className={payMode === 'fee' ? 'active' : ''} onClick={() => setPayMode('fee')}>付費（匯款）</button>
          {plans.length > 0 && <button type="button" className={payMode === 'card' ? 'active' : ''} onClick={() => setPayMode('card')}>扣課卡</button>}
        </div>
        {payMode === 'free' && <p className="muted small">球友按報名就完成，不用付錢。</p>}
        {payMode === 'fee' && (
          <>
            <Field label={isSlots ? '每個時段的費用（NT$）' : '報名費（NT$）'}>
              <input className="input" type="number" min="1" value={form.fee || ''} onChange={set('fee', Number)} required placeholder="300" />
            </Field>
            <div className="pay-flow">
              <b>球友會這樣付款</b>
              <ol>
                <li>報名後，名額先保留</li>
                <li>看到下面的匯款資訊，自己去匯款</li>
                <li>回到活動頁填「匯款帳號後五碼」</li>
                <li>您在「付款審核」對帳後按「確認收款」</li>
              </ol>
              {venue?.payment_ready
                ? <p className="pre small pay-info">{venue.payment_info}</p>
                : <p className="alert warn small">還沒設定匯款資訊，球友會看到「請洽主辦」。<Link className="strong" to="/admin/settings">去場館設定填寫 ›</Link></p>}
            </div>
            <Field label="多久內要付款" hint="時間到還沒付、也沒回報後五碼，名額會自動讓給候補">
              <select className="input" value={form.pay_hours} onChange={set('pay_hours', Number)}>
                {[[24, '報名後 24 小時'], [48, '報名後 48 小時'], [72, '報名後 72 小時'], [0, '不限（開始前付就好）']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
          </>
        )}
        {payMode === 'card' && (
          <>
            <Field label="點數卡扣幾點" hint="堂數卡固定扣 1 堂、無限卡不扣；沒有課卡的人要先買卡">
              <input className="input" type="number" min="1" value={form.cost} onChange={set('cost', Number)} required />
            </Field>
            <Field label="哪些課卡可以用（選填）" hint="都不勾＝所有課卡都能用">
              <div className="checks">
                {plans.map((p) => (
                  <label key={p.id} className="check"><input type="checkbox" checked={form.plan_ids.includes(p.id)} onChange={() => togglePlan(p.id)} /> {p.name}<span className="muted small">（{PLAN_TYPES[p.type]}）</span></label>
                ))}
              </div>
            </Field>
          </>
        )}
      </Step>

      {type === 'dupr' && (
        <Step n={step()} title="DUPR 條件" tag="選填">
          <div className="grid2">
            <Field label="最低分" hint="留空＝不限"><input className="input" type="number" step="0.001" min="1" max="8" value={form.dupr_min} onChange={set('dupr_min')} placeholder="3.000" /></Field>
            <Field label="最高分" hint="留空＝不限"><input className="input" type="number" step="0.001" min="1" max="8" value={form.dupr_max} onChange={set('dupr_max')} placeholder="4.000" /></Field>
          </div>
          <div className="grid2">
            <Field label="看哪種分數">
              <select className="input" value={form.dupr_format} onChange={set('dupr_format')}>
                <option value="doubles">雙打</option>
                <option value="singles">單打</option>
              </select>
            </Field>
            <Field label="賽制" hint={form.dupr_format === 'singles' ? '單打固定循環賽' : form.match_format === 'fixed' ? '兩人一隊，可指定隊友' : '每局換搭檔'}>
              <select className="input" value={form.dupr_format === 'singles' ? 'singles' : form.match_format} onChange={set('match_format')} disabled={form.dupr_format === 'singles'}>
                {form.dupr_format === 'singles' && <option value="singles">單打循環賽</option>}
                <option value="rotating">輪換搭檔</option>
                <option value="fixed">固定搭檔</option>
              </select>
            </Field>
          </div>
          <Field label="每局打到幾分" hint="領先 2 分獲勝">
            <select className="input" value={form.games_to} onChange={set('games_to', Number)}>
              {[11, 15, 21].map((v) => <option key={v} value={v}>{v} 分</option>)}
            </select>
          </Field>
          <label className="check"><input type="checkbox" checked={form.dupr_verified_only} onChange={set('dupr_verified_only')} /> 只限場館驗證過的 DUPR 帳號</label>
        </Step>
      )}

      <details className="card more-settings" open={editing}>
        <summary>
          <span className="step-n muted-n">+</span><b>更多設定</b><span className="step-tag">選填，不填也可以</span>
        </summary>
        <div className="form">
          <Field label="地點" hint="沒填就不顯示"><input className="input" value={form.location} onChange={set('location')} placeholder="例：自強國小體育館" /></Field>
          <Field label="介紹" hint="要帶什麼、怎麼集合、注意事項"><textarea className="input" rows={3} value={form.description} onChange={set('description')} /></Field>
          <Field label="封面圖片" hint="顯示在活動頁最上方，分享到 LINE 也會用這張；建議橫式 16:9">
            <ImageInput value={form.cover_url} onChange={(v) => setForm({ ...form, cover_url: v })} />
          </Field>
          <div className="grid2">
            <Field label="類別">
              <select className="input" value={form.category} onChange={set('category')}>
                <option value="">（無）</option>
                {categories.map((c) => <option key={c}>{c}</option>)}
              </select>
            </Field>
            <Field label={isSlots ? '負責的老師' : '老師／團主'}>
              <select className="input" value={form.teacher_id} onChange={set('teacher_id')}>
                <option value="">未指定</option>
                {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
              </select>
            </Field>
          </div>
          {!isSlots && form.teacher_id && <label className="check"><input type="checkbox" checked={form.substitute} onChange={set('substitute')} /> 這次是代課</label>}
          {!isSlots && !id && !template && (
            <Field label="每週重複" hint="每週同一時間自動建立，最多 26 週">
              <select className="input" value={form.repeat_weeks} onChange={set('repeat_weeks', Number)}>
                {[1, 2, 4, 8, 12, 26].map((w) => <option key={w} value={w}>{w === 1 ? '不重複' : `連續 ${w} 週`}</option>)}
              </select>
            </Field>
          )}
          <div className="grid2">
            <Field label="報名截止">
              <select className="input" value={form.booking_deadline_min} onChange={set('booking_deadline_min', Number)}>
                {[0, 30, 60, 120, 180, 360, 720, 1440].map((m) => <option key={m} value={m}>{m === 0 ? '開始前都可以' : m < 60 ? `開始前 ${m} 分鐘` : `開始前 ${m / 60} 小時`}</option>)}
              </select>
            </Field>
            <Field label="自己取消的期限">
              <select className="input" value={form.cancel_deadline_min} onChange={set('cancel_deadline_min', Number)}>
                {[0, 60, 120, 360, 720, 1440, 2880].map((m) => <option key={m} value={m}>{m === 0 ? '開始前都可以' : `開始前 ${m / 60} 小時`}</option>)}
              </select>
            </Field>
          </div>
          {!isSlots && <label className="check"><input type="checkbox" checked={form.beginner} onChange={set('beginner')} /> 標示「新手友善」</label>}
          <label className="check">
            <input type="checkbox" checked={form.show_attendees} onChange={set('show_attendees')} />
            <span>公開「要去的球友」<span className="muted small">（報名者的頭像與名字，名字會遮罩；{isSlots ? '場地租借通常不公開' : 'DUPR 場會附上分數'}）</span></span>
          </label>
          <label className="check">
            <input type="checkbox" checked={form.listed} onChange={set('listed')} />
            <span>公開在首頁課表<span className="muted small">（不勾＝只有拿到報名連結的人看得到）</span></span>
          </label>
        </div>
      </details>

      {template && id && (
        <label className="check strong card"><input type="checkbox" checked={applyFuture} onChange={(e) => setApplyFuture(e.target.checked)} /> 同步更新這個範本之後、還沒開始的課（時間不變，名額不會少於已報名人數）</label>
      )}
      <div className="form-submit">
        <button type="button" className="btn btn-light" onClick={() => navigate(-1)}>取消</button>
        <button className="btn flex1 btn-lg" disabled={busy}>
          {busy ? '儲存中…' : editing ? '儲存' : isSlots ? (slotCount ? `建立 ${slotCount} 個時段` : '建立') : template ? '建立範本' : form.repeat_weeks > 1 ? `建立 ${form.repeat_weeks} 場` : '建立活動'}
        </button>
      </div>
    </form>
  )
}
