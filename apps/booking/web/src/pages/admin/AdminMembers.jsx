import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Avatar, Badge, Chips, Empty, Field, Loading, Modal } from '../../components/ui'
import { cardRemain, planOf, rating, showDateTime } from '../../util'

export default function AdminMembers() {
  const { handleError } = useApp()
  const [list, setList] = useState(null)
  const [q, setQ] = useState('')
  const [open, setOpen] = useState(null)
  const load = useCallback(() => api('admin/members').then((l) => {
    setList(l)
    setOpen((cur) => cur && l.find((m) => m.id === cur.id))
  }).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

  const [only, setOnly] = useState('all')
  const shown = (list || []).filter((m) => m.name.includes(q) || (m.phone || '').includes(q) || (m.email || '').includes(q.toLowerCase()))
    .filter((m) => only === 'all' || (only === 'blocked' ? m.noshow?.blocked : m.noshow?.count > 0))
  const blockedN = (list || []).filter((m) => m.noshow?.blocked).length

  return (
    <>
      <input className="input search" placeholder="搜尋姓名、信箱或手機" value={q} onChange={(e) => setQ(e.target.value)} />
      <Chips value={only} onChange={setOnly} options={[['all', '全部'], ['absent', '有缺席紀錄'], ['blocked', `暫停報名中（${blockedN}）`]]} />
      {!list ? <Loading /> : shown.length === 0 ? <Empty text="找不到會員" /> : shown.map((m) => (
        <button key={m.id} className="card member-row text-left" onClick={() => setOpen(m)}>
          <Avatar src={m.avatar_url} name={m.name} size={40} />
          <div className="flex1 min0">
            <b>{m.name}</b>
            {m.role === 'owner' && <Badge>場主</Badge>}
            {m.role === 'coach' && <Badge tone="brand">教練</Badge>}
            {m.suspended ? <Badge tone="danger">停權</Badge> : null}
            {m.noshow?.blocked && <Badge tone="warn">暫停報名</Badge>}
            {m.dupr_id && <Badge tone="dupr">DUPR {rating(m.dupr_doubles)}{m.dupr_verified ? ' ✓' : ''}</Badge>}
            <p className="muted small">{m.line_linked && <span className="badge badge-line">LINE</span>} {m.email || m.phone || ''} · 有效課卡 {m.cards.length} · 預約 {m.bookings} 次{m.absences ? ` · 缺席 ${m.absences}` : ''}{m.noshow?.enabled && m.noshow.count > 0 ? `（計入 ${m.noshow.count}/${m.noshow.limit}）` : ''}</p>
          </div>
          <span className="muted">›</span>
        </button>
      ))}
      {open && <MemberDialog m={open} onClose={() => setOpen(null)} onChanged={load} />}
    </>
  )
}

function MemberDialog({ m, onClose, onChanged }) {
  const { user, handleError, showToast } = useApp()
  const [plans, setPlans] = useState([])
  const [planId, setPlanId] = useState('')
  const [note, setNote] = useState(m.note || '')
  const [reason, setReason] = useState(m.suspend_reason || '')
  const [confirmDelete, setConfirmDelete] = useState(false)
  useEffect(() => { api('admin/plans').then(setPlans).catch(handleError) }, [handleError])

  const run = async (fn, msg) => {
    try { await fn(); showToast(msg); onChanged() } catch (e) { handleError(e) }
  }
  const update = (body, msg) => run(() => api(`admin/members/${m.id}`, { method: 'PUT', body }), msg)
  const adjust = (card) => {
    const v = window.prompt(`調整「${card.name}」剩餘${card.type === 'points' ? '點數' : '堂數'}`, card.remaining)
    if (v !== null && v !== '') run(() => api(`admin/cards/${card.id}`, { method: 'PUT', body: { remaining: Number(v) } }), '已調整')
  }
  const extend = (card) => {
    const v = window.prompt('新的到期日（YYYY-MM-DD）', card.expires_on)
    if (v) run(() => api(`admin/cards/${card.id}`, { method: 'PUT', body: { expires_on: v } }), '已調整到期日')
  }

  return (
    <Modal onClose={onClose}>
      <h3 className="dialog-title">{m.name}</h3>
      <p className="muted center small">{m.line_linked && 'LINE · '}{m.email && <>{m.email} · </>}{m.phone && <><a href={`tel:${m.phone}`}>{m.phone}</a> · </>}加入於 {showDateTime(m.created_at).slice(0, 10)}</p>
      <div className="stats stats-3">
        <div className="stat"><span>預約</span><b>{m.bookings}</b></div>
        <div className="stat"><span>缺席</span><b>{m.absences}</b></div>
        <div className="stat"><span>課卡</span><b>{m.cards.length}</b></div>
      </div>

      {m.role !== 'owner' && <NoShowAdmin m={m} run={run} onChanged={onChanged} />}

      <h4 className="sub-title">有效課卡</h4>
      {m.cards.length === 0 ? <p className="muted small">沒有有效課卡</p> : m.cards.map((c) => (
        <div key={c.id} className="row between list-row">
          <div><b>{c.name}</b><p className="muted small">{cardRemain(c)} · 到期 {c.expires_on}</p></div>
          <div className="admin-actions">
            {c.type !== 'unlimited' && <button className="btn btn-small btn-light" onClick={() => adjust(c)}>調整</button>}
            <button className="btn btn-small btn-light" onClick={() => extend(c)}>展延</button>
          </div>
        </div>
      ))}
      <div className="row gap">
        <select className="input flex1" value={planId} onChange={(e) => setPlanId(e.target.value)}>
          <option value="">選擇方案</option>
          {plans.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <button className="btn btn-small" disabled={!planId}
          onClick={() => run(() => api(`admin/members/${m.id}/cards`, { method: 'POST', body: { plan_id: Number(planId) } }), '已開通課卡')}>開通課卡</button>
      </div>

      <h4 className="sub-title">DUPR</h4>
      <DuprAdmin m={m} run={run} />

      <Field label="備註（僅場主可見）">
        <textarea className="input" rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
      </Field>
      <button className="btn btn-small btn-light" onClick={() => update({ note }, '已儲存備註')}>儲存備註</button>

      {m.id !== user.id && (
        <>
          <h4 className="sub-title">帳號狀態</h4>
          {m.suspended ? (
            <button className="btn btn-block" onClick={() => update({ suspended: false }, '已解除停權')}>解除停權</button>
          ) : (
            <>
              <input className="input" placeholder="停權原因（學員會看到）" value={reason} onChange={(e) => setReason(e.target.value)} />
              <button className="btn btn-block btn-outline-danger" onClick={() => update({ suspended: true, suspend_reason: reason }, '已停權')}>停權此帳號</button>
            </>
          )}
          <RoleEditor m={m} update={update} />
          {confirmDelete ? (
            <div className="alert danger">
              <p>確定刪除「{m.name}」？他的預約、課卡、訂單、評價都會一併刪除，無法復原。</p>
              <div className="row gap" style={{ marginTop: 8 }}>
                <button className="btn btn-small btn-light flex1" onClick={() => setConfirmDelete(false)}>取消</button>
                <button className="btn btn-small btn-danger flex1"
                  onClick={() => run(() => api(`admin/members/${m.id}`, { method: 'DELETE' }), '已刪除會員').then(onClose)}>確定刪除</button>
              </div>
            </div>
          ) : (
            <button className="btn btn-block btn-light text-danger" onClick={() => setConfirmDelete(true)}>刪除會員</button>
          )}
        </>
      )}
    </Modal>
  )
}

function DuprAdmin({ m, run }) {
  const [edit, setEdit] = useState(false)
  const [form, setForm] = useState({ dupr_id: m.dupr_id, doubles: m.dupr_doubles ?? '', singles: m.dupr_singles ?? '' })
  const update = (body, msg) => run(() => api(`admin/members/${m.id}`, { method: 'PUT', body }), msg)
  const source = { api: 'DUPR 官方資料', manual: '學員自填', owner: '場主設定' }[m.dupr_source] || ''
  return (
    <div className="dupr-box on">
      {m.dupr_id ? (
        <>
          <p><b className="text-brand">{m.dupr_id}</b>{m.dupr_name && ` · ${m.dupr_name}`}</p>
          <p className="small">雙打 <b>{rating(m.dupr_doubles)}</b> · 單打 <b>{rating(m.dupr_singles)}</b> <span className="muted">（{source}，{showDateTime(m.dupr_synced_at)}）</span></p>
          <p className="small">{m.dupr_verified ? <span className="text-success">✓ 場館已驗證</span> : <span className="text-warn">尚未驗證</span>}</p>
        </>
      ) : <p className="muted small">尚未綁定 DUPR</p>}
      <div className="admin-actions">
        {m.dupr_id && (m.dupr_verified
          ? <button className="btn btn-small btn-light" onClick={() => update({ dupr_verified: false }, '已取消驗證')}>取消驗證</button>
          : <button className="btn btn-small" onClick={() => update({ dupr_verified: true }, '已驗證 DUPR')}>核對無誤，驗證</button>)}
        <button className="btn btn-small btn-light" onClick={() => setEdit(!edit)}>{m.dupr_id ? '修改' : '代為綁定'}</button>
      </div>
      {edit && (
        <div className="form">
          <input className="input" placeholder="DUPR ID" value={form.dupr_id} onChange={(e) => setForm({ ...form, dupr_id: e.target.value.toUpperCase() })} />
          <div className="grid2">
            <input className="input" type="number" step="0.001" placeholder="雙打" value={form.doubles} onChange={(e) => setForm({ ...form, doubles: e.target.value })} />
            <input className="input" type="number" step="0.001" placeholder="單打" value={form.singles} onChange={(e) => setForm({ ...form, singles: e.target.value })} />
          </div>
          <button className="btn btn-small" onClick={() => { update({ dupr: form }, '已更新 DUPR'); setEdit(false) }}>儲存（視為已驗證）</button>
        </div>
      )}
    </div>
  )
}

// 缺席管理：目前計入次數、暫停狀態、每筆缺席可免記、手動暫停／解除
function NoShowAdmin({ m, run, onChanged }) {
  const { handleError } = useApp()
  const [d, setD] = useState(null)
  const [days, setDays] = useState(14)
  const load = useCallback(() => api(`admin/members/${m.id}/absences`).then(setD).catch(handleError), [m.id, handleError])
  useEffect(() => { load() }, [load, m])
  if (!d) return null
  const s = d.status
  const act = (fn, msg) => run(fn, msg).then(() => { load(); onChanged() })
  return (
    <>
      <h4 className="sub-title">缺席紀錄</h4>
      {s.blocked ? (
        <div className="alert warn">
          <b>暫停報名中</b>，{s.forever ? '直到您解除' : `到 ${s.blocked_until.slice(5).replace('-', '/')}`}（{s.reason}）
          <button className="btn btn-small btn-block mt" onClick={() => act(() => api(`admin/members/${m.id}`, { method: 'PUT', body: { unblock: true } }), '已解除報名限制')}>解除暫停</button>
        </div>
      ) : (
        <p className="small">{s.enabled ? <>目前計入 <b className={s.count >= s.limit - 1 && s.count ? 'text-warn' : ''}>{s.count} / {s.limit}</b> 次（{s.days ? `最近 ${s.days} 天` : '累計'}），滿 {s.limit} 次自動暫停報名</> : '缺席管理未開啟（場館設定可開啟）'}</p>
      )}
      {d.absences.length === 0 ? <p className="muted small">沒有缺席紀錄</p> : d.absences.map((a) => (
        <div key={a.id} className="row between list-row">
          <div className={a.noshow_cleared ? 'dim' : ''}>
            <b className="small">{a.date.slice(5).replace('-', '/')} {a.start_time}</b> <span className="small">{a.name}</span>
            {a.noshow_cleared === 1 && <Badge tone="gray">已免記</Badge>}
            {a.noshow_cleared === 2 && <Badge tone="gray">已計入暫停</Badge>}
          </div>
          {a.noshow_cleared !== 2 && (
            <button className="btn btn-small btn-light" onClick={() => act(() => api(`admin/reservations/${a.id}/excuse`, { method: 'POST', body: { excused: !a.noshow_cleared } }), a.noshow_cleared ? '已恢復計入' : '已免記')}>
              {a.noshow_cleared ? '恢復計入' : '免記'}
            </button>
          )}
        </div>
      ))}
      {!s.blocked && (
        <div className="row gap">
          <select className="input flex1" value={days} onChange={(e) => setDays(Number(e.target.value))}>
            {[[7, '暫停 7 天'], [14, '暫停 14 天'], [30, '暫停 30 天'], [0, '暫停直到解除']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select>
          <button className="btn btn-small btn-outline-warn" onClick={() => act(() => api(`admin/members/${m.id}`, { method: 'PUT', body: { block: { days, reason: '主辦暫停報名' } } }), '已暫停報名')}>手動暫停報名</button>
        </div>
      )}
    </>
  )
}

// 身分：學員／教練（綁老師，只能看、點自己的課）／場主（管理整個後台）；多位管理員與教練是專業方案以上
function RoleEditor({ m, update }) {
  const { venue, handleError } = useApp()
  const plan = planOf(venue)
  const [role, setRole] = useState(m.role)
  const [teacher, setTeacher] = useState(m.teacher_id || '')
  const [teachers, setTeachers] = useState([])
  useEffect(() => { api('admin/teachers').then(setTeachers).catch(handleError) }, [handleError])
  const changed = role !== m.role || (role === 'coach' && String(teacher) !== String(m.teacher_id || ''))
  return (
    <div className="form">
      <Field label="身分" hint={role === 'coach' ? '教練登入後只看得到、點得到這位老師的課，也能看自己的時數' : role === 'owner' ? '場主可以管理整個後台' : ''}>
        <select className="input" value={role} onChange={(e) => setRole(e.target.value)}>
          <option value="student">學員</option>
          <option value="coach" disabled={!plan.has('staff')}>教練{!plan.has('staff') ? `（${plan.needs('staff')}方案）` : ''}</option>
          <option value="owner">場主{!plan.has('staff') && m.role !== 'owner' ? `（第二位場主需${plan.needs('staff')}方案）` : ''}</option>
        </select>
      </Field>
      {role === 'coach' && (
        <Field label="對應的老師">
          <select className="input" value={teacher} onChange={(e) => setTeacher(e.target.value)}>
            <option value="">請選擇</option>
            {teachers.map((t) => <option key={t.id} value={t.id}>{t.name}</option>)}
          </select>
        </Field>
      )}
      <button className="btn btn-block btn-light" disabled={!changed || (role === 'coach' && !teacher)}
        onClick={() => update({ role, teacher_id: teacher || null }, '已更新身分，對方需要重新登入')}>更新身分</button>
    </div>
  )
}
