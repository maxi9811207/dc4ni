import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Badge, Chips, Confirm, Empty, Loading } from '../../components/ui'
import { money, showDateTime } from '../../util'

const STATUS = { pending: ['待確認', 'warn'], paid: ['已開通', 'success'], cancelled: ['已取消', 'gray'] }

export default function AdminOrders() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const [filter, setFilter] = useState('pending')
  const [confirm, setConfirm] = useState(null)
  const load = useCallback(() => api('admin/orders').then(setList).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

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
        options={[['pending', `待確認（${(list || []).filter((o) => o.status === 'pending').length}）`], ['paid', '已開通'], ['cancelled', '已取消'], ['all', '全部']]} />
      {!list ? <Loading /> : shown.length === 0 ? <Empty text="沒有訂單" /> : shown.map((o) => (
        <div key={o.id} className="card">
          <div className="row between">
            <b>{o.plan_name}</b>
            <Badge tone={STATUS[o.status][1]}>{STATUS[o.status][0]}</Badge>
          </div>
          <p className="small">{o.user_name} · <a href={`tel:${o.phone}`}>{o.phone}</a></p>
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
