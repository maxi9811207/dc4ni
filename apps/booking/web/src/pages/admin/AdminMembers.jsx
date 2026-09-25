import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Badge, Empty, Field, Loading, Modal } from '../../components/ui'
import { cardRemain, rating, showDateTime } from '../../util'

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

  const shown = (list || []).filter((m) => m.name.includes(q) || m.phone.includes(q))

  return (
    <>
      <input className="input search" placeholder="搜尋姓名或手機" value={q} onChange={(e) => setQ(e.target.value)} />
      {!list ? <Loading /> : shown.length === 0 ? <Empty text="找不到會員" /> : shown.map((m) => (
        <button key={m.id} className="card member-row text-left" onClick={() => setOpen(m)}>
          <div className="avatar" style={{ width: 40, height: 40, fontSize: 17 }}><span>{m.name.slice(0, 1)}</span></div>
          <div className="flex1 min0">
            <b>{m.name}</b>
            {m.role === 'owner' && <Badge>場主</Badge>}
            {m.suspended ? <Badge tone="danger">停權</Badge> : null}
            {m.dupr_id && <Badge tone="dupr">DUPR {rating(m.dupr_doubles)}{m.dupr_verified ? ' ✓' : ''}</Badge>}
            <p className="muted small">{m.phone} · 有效課卡 {m.cards.length} · 預約 {m.bookings} 次{m.absences ? ` · 缺席 ${m.absences}` : ''}</p>
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
      <p className="muted center small"><a href={`tel:${m.phone}`}>{m.phone}</a> · 加入於 {showDateTime(m.created_at).slice(0, 10)}</p>
      <div className="stats stats-3">
        <div className="stat"><span>預約</span><b>{m.bookings}</b></div>
        <div className="stat"><span>缺席</span><b>{m.absences}</b></div>
        <div className="stat"><span>課卡</span><b>{m.cards.length}</b></div>
      </div>

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
          <button className="btn btn-block btn-light" onClick={() => update({ role: m.role === 'owner' ? 'student' : 'owner' }, '已更新權限')}>
            {m.role === 'owner' ? '取消場主權限' : '設為場主（可管理後台）'}
          </button>
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
