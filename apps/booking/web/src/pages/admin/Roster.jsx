import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api, downloadFile } from '../../api'
import { ShareBox } from '../../components/Share'
import { Badge, Confirm, Empty, Loading, Modal } from '../../components/ui'
import { duprRange, rating, showDate } from '../../util'

const STATUS = { booked: ['已預約', 'brand'], attended: ['出席', 'success'], absent: ['缺席', 'danger'], waitlist: ['候補', 'warn'] }

export default function Roster() {
  const { id } = useParams()
  const { handleError, showToast } = useApp()
  const [c, setC] = useState(null)
  const [adding, setAdding] = useState(false)
  const [removing, setRemoving] = useState(null)
  const [refund, setRefund] = useState(true)

  const load = useCallback(() => api(`admin/courses/${id}/roster`).then(setC).catch(handleError), [id, handleError])
  useEffect(() => { load() }, [load])

  if (!c) return <Loading />
  const booked = c.roster.filter((r) => r.status !== 'waitlist')
  const waiting = c.roster.filter((r) => r.status === 'waitlist')

  const setPaid = async (r, paid) => {
    try {
      await api(`admin/reservations/${r.id}/payment`, { method: 'POST', body: { paid } })
      showToast(paid ? `已確認收到 ${r.name} 的報名費` : '已改為未付款')
      load()
    } catch (e) { handleError(e) }
  }
  const feeRows = booked.filter((r) => r.fee > 0)
  const setStatus = async (r, status, extra = {}) => {
    try {
      await api(`admin/reservations/${r.id}`, { method: 'POST', body: { status, ...extra } })
      load()
    } catch (e) { handleError(e) }
  }

  return (
    <>
      <section className="card">
        <div className="row between">
          <Link to={`/admin/courses?date=${c.date}`} className="muted small">‹ 回課程列表</Link>
          <Link to={`/admin/courses/${c.id}/edit`} className="small text-brand">編輯課程</Link>
        </div>
        <h2 className="detail-title">{c.name}</h2>
        <p className="course-meta"><b className="course-time">{showDate(c.date)} {c.start_time}~{c.end_time}</b> · {c.teacher?.name || '未指定老師'}</p>
        {c.dupr_required && (
          <div className="row between">
            <p className="small"><Badge tone="dupr">DUPR 場</Badge> {duprRange(c)}</p>
            <Link to={`/admin/courses/${c.id}/event`} className="btn btn-small">賽事</Link>
          </div>
        )}
        <div className="stats stats-3">
          <div className="stat"><span>預約</span><b>{c.booked_count}/{c.capacity}</b></div>
          <div className="stat"><span>出席</span><b>{c.roster.filter((r) => r.status === 'attended').length}</b></div>
          <div className="stat"><span>候補</span><b>{c.waitlist_count}</b></div>
        </div>
        {feeRows.length > 0 && (
          <p className="small fee-summary">
            報名費已收 <b className="text-success">NT$ {feeRows.filter((r) => r.paid).reduce((s, r) => s + r.fee, 0).toLocaleString()}</b>
            ／應收 NT$ {feeRows.reduce((s, r) => s + r.fee, 0).toLocaleString()}
            {feeRows.some((r) => !r.paid) && <span className="text-warn">（{feeRows.filter((r) => !r.paid).length} 人待付款）</span>}
          </p>
        )}
      </section>

      {c.share_code && <ShareBox c={c} />}

      <div className="row between section-head">
        <h3 className="date-title">學員名單</h3>
        <div className="row gap-sm">
          <button className="btn btn-small btn-light" onClick={() => downloadFile(`admin/courses/${c.id}/roster/export`, `名單_${c.date}_${c.name}.xlsx`).catch(handleError)}>下載名單</button>
          <button className="btn btn-small" onClick={() => setAdding(true)}>＋ 加人</button>
        </div>
      </div>
      {booked.length === 0 ? <Empty text="還沒有人預約" /> : (
        <section className="card">
          {booked.map((r, i) => (
            <div key={r.id} className="roster-row">
              <div className="row between">
                <div>
                  <b>{i + 1}. {r.name}</b> <Badge tone={STATUS[r.status][1]}>{STATUS[r.status][0]}</Badge>
                  {r.dupr_id && <span className="small dupr-inline"> DUPR {rating(r[`dupr_${c.dupr_format}`])}{r.dupr_verified ? ' ✓' : ''}</span>}
                  <p className="muted small">{r.phone && <><a href={`tel:${r.phone}`}>{r.phone}</a> · </>}{r.fee > 0 ? `報名費 NT$ ${r.fee.toLocaleString()}` : r.card_name ? `${r.card_name}（扣 ${r.charged}）` : '未扣卡'}</p>
                  {r.fee > 0 && (
                    <p className="small">
                      {r.paid ? <Badge tone="success">已付款</Badge> : <Badge tone="warn">待付款</Badge>}
                      {r.pay_note && <span className="muted"> 學員回報：{r.pay_note}</span>}
                      {!r.paid && !r.pay_note && r.pay_due && <span className="muted"> 期限 {r.pay_due.slice(5, 16).replace('-', '/').replace('T', ' ')}</span>}
                    </p>
                  )}
                </div>
              </div>
              <div className="admin-actions">
                <button className={`btn btn-small ${r.status === 'attended' ? '' : 'btn-light'}`} onClick={() => setStatus(r, r.status === 'attended' ? 'booked' : 'attended')}>出席</button>
                <button className={`btn btn-small ${r.status === 'absent' ? 'btn-danger' : 'btn-light'}`} onClick={() => setStatus(r, r.status === 'absent' ? 'booked' : 'absent')}>缺席</button>
                {r.fee > 0 && (
                  <button className={`btn btn-small ${r.paid ? 'btn-light' : ''}`} onClick={() => setPaid(r, !r.paid)}>{r.paid ? '改為未付款' : '確認收款'}</button>
                )}
                <button className="btn btn-small btn-light text-danger" onClick={() => { setRefund(true); setRemoving(r) }}>取消預約</button>
              </div>
            </div>
          ))}
        </section>
      )}

      {waiting.length > 0 && (
        <>
          <h3 className="date-title">候補名單</h3>
          <section className="card">
            {waiting.map((r, i) => (
              <div key={r.id} className="roster-row">
                <div className="row between">
                  <div><b>候補 {i + 1}. {r.name}</b><p className="muted small">{r.phone}{r.dupr_id && ` · DUPR ${rating(r[`dupr_${c.dupr_format}`])}`}</p></div>
                  <div className="admin-actions">
                    <button className="btn btn-small" onClick={() => setStatus(r, 'booked')}>轉為正式</button>
                    <button className="btn btn-small btn-light" onClick={() => setStatus(r, 'cancelled')}>移除</button>
                  </div>
                </div>
              </div>
            ))}
          </section>
        </>
      )}

      {removing && (
        <Confirm title={`取消 ${removing.name} 的預約？`} danger okText="確定取消" onClose={() => setRemoving(null)}
          onOk={async () => { await setStatus(removing, 'cancelled', { refund }); setRemoving(null); showToast('已取消並通知學員') }}>
          {removing.fee > 0
            ? removing.paid && <p className="alert warn small">這位學員已付報名費 NT$ {removing.fee.toLocaleString()}，請另外處理退費。</p>
            : <label className="check"><input type="checkbox" checked={refund} onChange={(e) => setRefund(e.target.checked)} /> 退還課卡</label>}
          <p className="muted small">若有候補，會自動遞補下一位。</p>
        </Confirm>
      )}
      {adding && <AddMember courseId={c.id} onClose={() => setAdding(false)} onDone={() => { setAdding(false); showToast('已加入名單'); load() }} />}
    </>
  )
}

function AddMember({ courseId, onClose, onDone }) {
  const { handleError } = useApp()
  const [members, setMembers] = useState([])
  const [q, setQ] = useState('')
  const [charge, setCharge] = useState(true)
  const [guest, setGuest] = useState({ name: '', phone: '' })
  useEffect(() => { api('admin/members').then(setMembers).catch(handleError) }, [handleError])
  const shown = members.filter((m) => m.role === 'student' && (m.name.includes(q) || (m.phone || '').includes(q) || (m.email || '').includes(q))).slice(0, 30)
  const add = (m) => api(`admin/courses/${courseId}/add`, { method: 'POST', body: { user_id: m.id, charge } }).then(onDone).catch(handleError)
  const addGuest = (e) => {
    e.preventDefault()
    api(`admin/courses/${courseId}/add`, { method: 'POST', body: { guest_name: guest.name, guest_phone: guest.phone } }).then(onDone).catch(handleError)
  }
  return (
    <Modal onClose={onClose}>
      <h3 className="dialog-title">加入名單</h3>
      <form className="guest-form" onSubmit={addGuest}>
        <p className="small strong">沒有帳號的人（現場、朋友帶來）</p>
        <div className="row gap-sm">
          <input className="input" placeholder="姓名" value={guest.name} onChange={(e) => setGuest({ ...guest, name: e.target.value })} required />
          <input className="input" placeholder="手機（選填）" inputMode="tel" value={guest.phone} onChange={(e) => setGuest({ ...guest, phone: e.target.value })} />
          <button className="btn btn-small">加入</button>
        </div>
      </form>
      <div className="or"><span>或找已註冊的會員</span></div>
      <input className="input" placeholder="搜尋姓名或手機" value={q} onChange={(e) => setQ(e.target.value)} autoFocus />
      <label className="check"><input type="checkbox" checked={charge} onChange={(e) => setCharge(e.target.checked)} /> 從學員課卡扣除</label>
      <div className="pick-list">
        {shown.map((m) => (
          <button key={m.id} className="pick-item" onClick={() => add(m)}>
            <b>{m.name}</b><span className="muted small">{m.phone || m.email || ''} · 有效課卡 {m.cards.length}</span>
          </button>
        ))}
        {shown.length === 0 && <p className="muted center small">找不到會員</p>}
      </div>
    </Modal>
  )
}
