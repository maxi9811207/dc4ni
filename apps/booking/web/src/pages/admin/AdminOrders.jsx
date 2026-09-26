import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Badge, Chips, Confirm, Empty, Loading } from '../../components/ui'
import { Link } from 'react-router-dom'
import { money, showDate, showDateTime } from '../../util'

const STATUS = { pending: ['待確認', 'warn'], paid: ['已開通', 'success'], cancelled: ['已取消', 'gray'] }

export default function AdminOrders() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const [filter, setFilter] = useState('pending')
  const [confirm, setConfirm] = useState(null)
  const [fees, setFees] = useState(null)
  const load = useCallback(() => {
    api('admin/orders').then(setList).catch(handleError)
    api('admin/fees').then(setFees).catch(handleError)
  }, [handleError])
  useEffect(() => { load() }, [load])
  const unpaid = (fees || []).filter((f) => !f.paid)
  const markPaid = async (f) => {
    try {
      await api(`admin/reservations/${f.id}/payment`, { method: 'POST', body: { paid: true } })
      showToast(`已確認收到 ${f.user_name} 的報名費`)
      load()
    } catch (e) { handleError(e) }
  }

  const shown = (list || []).filter((o) => filter === 'all' || o.status === filter)
  const update = async (o, status) => {
    try {
      await api(`admin/orders/${o.id}`, { method: 'POST', body: { status } })
      showToast(status === 'paid' ? '已確認收款，課卡已開通' : '已取消訂單')
      setConfirm(null)
      load()
    } catch (e) { handleError(e) }
  }

  return (
    <>
      <Chips value={filter} onChange={setFilter}
        options={[['pending', `課卡待確認（${(list || []).filter((o) => o.status === 'pending').length}）`], ['fees', `報名費待收（${unpaid.length}）`], ['paid', '已開通'], ['cancelled', '已取消'], ['all', '全部']]} />
      {filter === 'fees' ? (
        !fees ? <Loading /> : fees.length === 0 ? <Empty text="沒有報名費紀錄" /> : fees.map((f) => (
          <div key={f.id} className="card">
            <div className="row between">
              <Link to={`/admin/courses/${f.course_id}`}><b>{f.course_name}</b></Link>
              {f.paid ? <Badge tone="success">已收</Badge> : f.pay_note ? <Badge tone="brand">學員已回報</Badge> : <Badge tone="warn">待付款</Badge>}
            </div>
            <p className="small">{f.user_name}{f.phone && <> · <a href={`tel:${f.phone}`}>{f.phone}</a></>} · {showDate(f.date)} {f.start_time}</p>
            {f.pay_note && <p className="small">學員回報：<b>{f.pay_note}</b></p>}
            {!f.paid && f.pay_due && <p className="muted small">付款期限 {f.pay_due.slice(5, 16).replace('-', '/').replace('T', ' ')}，逾期未付款會自動讓給候補</p>}
            <div className="row between">
              <span className="muted small">{f.paid ? `收款 ${showDateTime(f.paid_at)}` : `報名 ${showDateTime(f.created_at)}`}</span>
              <b className="price">{money(f.fee)}</b>
            </div>
            {!f.paid && <div className="admin-actions"><button className="btn btn-small" onClick={() => markPaid(f)}>確認收款</button></div>}
          </div>
        ))
      ) : !list ? <Loading /> : shown.length === 0 ? <Empty text="沒有訂單" /> : shown.map((o) => (
        <div key={o.id} className="card">
          <div className="row between">
            <b>{o.plan_name}</b>
            <Badge tone={STATUS[o.status][1]}>{STATUS[o.status][0]}</Badge>
          </div>
          <p className="small">{o.user_name}{o.phone && <> · <a href={`tel:${o.phone}`}>{o.phone}</a></>}</p>
          <div className="row between">
            <span className="muted small">#{o.id} · {showDateTime(o.created_at)}</span>
            <b className="price">{money(o.amount)}</b>
          </div>
          {o.status === 'pending' && (
            <div className="admin-actions">
              <button className="btn btn-small" onClick={() => setConfirm({ o, status: 'paid' })}>確認收款並開通</button>
              <button className="btn btn-small btn-light" onClick={() => setConfirm({ o, status: 'cancelled' })}>取消訂單</button>
            </div>
          )}
        </div>
      ))}
      {confirm && (
        <Confirm
          title={confirm.status === 'paid' ? '確認收款？' : '取消訂單？'}
          text={confirm.status === 'paid'
            ? `確認已收到 ${confirm.o.user_name} 的 ${money(confirm.o.amount)}，將立即開通「${confirm.o.plan_name}」。`
            : `將取消 ${confirm.o.user_name} 的「${confirm.o.plan_name}」購買申請並通知學員。`}
          danger={confirm.status !== 'paid'}
          okText={confirm.status === 'paid' ? '確認開通' : '取消訂單'}
          onClose={() => setConfirm(null)} onOk={() => update(confirm.o, confirm.status)} />
      )}
    </>
  )
}
