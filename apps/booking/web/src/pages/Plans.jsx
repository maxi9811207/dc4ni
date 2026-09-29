import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import VenueHeader from '../components/VenueHeader'
import { Badge, Chips, Empty, Loading, Modal } from '../components/ui'
import { money, PLAN_TYPES, planAmount } from '../util'

export default function Plans() {
  const { user, venue, handleError, refreshUser } = useApp()
  const navigate = useNavigate()
  const [list, setList] = useState(null)
  const [type, setType] = useState('all')
  const [buying, setBuying] = useState(null)
  const [done, setDone] = useState(false)
  const [busy, setBusy] = useState(false)

  useEffect(() => { api('plans').then(setList).catch(handleError) }, [handleError])

  const shown = (list || []).filter((p) => type === 'all' || p.type === type)

  const buy = (p) => {
    if (!user) return navigate('/login', { state: { from: '/plans' } })
    if (user.suspended) return handleError({ message: 'SUSPENDED' })
    setDone(false)
    setBuying(p)
  }

  const submit = async () => {
    setBusy(true)
    try {
      await api(`plans/${buying.id}/order`, { method: 'POST' })
      setDone(true)
      refreshUser()
    } catch (e) { handleError(e) } finally { setBusy(false) }
  }

  return (
    <>
      <VenueHeader />
      <main className="page">
        <Chips value={type} onChange={setType} options={[['all', '全部'], ...Object.entries(PLAN_TYPES)]} />
        {!list ? <Loading text="課卡載入中" /> : shown.length === 0 ? <Empty text="目前沒有此類課卡" /> : shown.map((p) => (
          <div key={p.id} className="card plan-card">
            <div className="row between">
              <Badge>{PLAN_TYPES[p.type]}</Badge>
              <span className="muted small">效期 {p.valid_days} 天</span>
            </div>
            <h2 className="plan-name">{p.name}</h2>
            <p className="plan-amount">{planAmount(p)}</p>
            {p.description && <p className="muted small pre">{p.description}</p>}
            <div className="row between plan-foot">
              <span className="price">{money(p.price)}</span>
              <button className="btn" onClick={() => buy(p)}>購買</button>
            </div>
          </div>
        ))}
      </main>

      {buying && (
        <Modal onClose={() => setBuying(null)}>
          {done ? (
            <>
              <div className="dialog-icon success">✓</div>
              <h3 className="dialog-title">已送出購買申請</h3>
              <p className="dialog-text">場館確認收款後會開通課卡並通知您。</p>
              {venue?.payment_info && <p className="pay-info pre">{venue.payment_info}</p>}
              <button className="btn btn-block" onClick={() => navigate('/me?tab=cards')}>查看我的課卡</button>
            </>
          ) : (
            <>
              <h3 className="dialog-title">購買課卡</h3>
              <div className="summary">
                <div className="row between"><span className="muted">方案</span><b>{buying.name}</b></div>
                <div className="row between"><span className="muted">內容</span><span>{planAmount(buying)}</span></div>
                <div className="row between"><span className="muted">效期</span><span>開通後 {buying.valid_days} 天</span></div>
                <div className="row between"><span className="muted">金額</span><b className="price">{money(buying.price)}</b></div>
              </div>
              {venue?.payment_info && <p className="pay-info pre">{venue.payment_info}</p>}
              <button className="btn btn-block" disabled={busy} onClick={submit}>{busy ? '送出中…' : '確認購買'}</button>
            </>
          )}
        </Modal>
      )}
    </>
  )
}
