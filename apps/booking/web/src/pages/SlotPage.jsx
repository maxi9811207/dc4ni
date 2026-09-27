import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useApp } from '../App'
import { api, asset } from '../api'
import { ShareButton } from '../components/Share'
import { VenueAvatar } from '../components/VenueHeader'
import { Badge, Confirm, Loading, Modal } from '../components/ui'
import { blockUntil, hours, noshowRule, showDate, today } from '../util'

const PAY = (m) => (m.status === 'waitlist' ? ['候補中', 'warn'] : !m.fee ? ['已預約', 'success'] : m.paid ? ['已付款', 'success'] : m.pay_note ? ['預約成功・等對帳', 'success'] : ['未完成・待回填後五碼', 'warn'])

function minutes(s) {
  const t = (x) => Number(x.slice(0, 2)) * 60 + Number(x.slice(3, 5))
  const m = t(s.end_time) - t(s.start_time)
  return m % 60 === 0 ? `${m / 60} 小時` : `${m} 分鐘`
}

// 時段預約頁：/slots/:id（課表點進來）或 /e/:code（分享連結）
export default function SlotPage({ code, header }) {
  const { id } = useParams()
  const { user, venue, refreshUser, handleError } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const [d, setD] = useState(null)
  const [day, setDay] = useState(params.get('date') || '')
  const [pick, setPick] = useState(null)
  const [busy, setBusy] = useState(false)
  const [dialog, setDialog] = useState(null)
  const [missing, setMissing] = useState(false)

  const load = useCallback(() => api(code ? `e/${code}` : `slots/${id}`).then((x) => { setD(x); return x })
    .catch((e) => (e.status === 404 ? setMissing(true) : handleError(e))), [id, code, handleError])
  useEffect(() => { load() }, [load])

  const days = d?.days || []
  const firstOpen = days.find((x) => x.slots.some((s) => ['book', 'waitlist'].includes(s.state)))?.date || days[0]?.date
  const cur = days.find((x) => x.date === day) || days.find((x) => x.date === firstOpen)
  const slot = cur?.slots.find((s) => s.id === pick)
  const maxDate = venue?.open_days ? new Date(Date.now() + venue.open_days * 864e5).toISOString().slice(0, 10) : null

  // 從登入頁回來（?slot=）：自動接著預約剛剛選的時段
  const autoRef = useRef(false)
  useEffect(() => {
    const want = Number(params.get('slot'))
    if (!d || !want || autoRef.current) return
    autoRef.current = true
    const found = days.flatMap((x) => x.slots.map((s) => [x.date, s])).find(([, s]) => s.id === want)
    setParams((p) => { p.delete('slot'); return p }, { replace: true })
    if (!found) return
    setDay(found[0]); setPick(want)
    if (user && ['book', 'waitlist'].includes(found[1].state)) book(found[1])
  })

  if (missing) return <>{header}<main className="page"><section className="card center"><h3 className="card-title">找不到這個活動</h3><p className="muted small">連結可能已失效，請向主辦確認。</p></section></main></>
  if (!d || d.kind !== 'slots') return <>{header}<Loading /></>

  async function book(s) {
    if (!user) {
      navigate('/login', { state: { from: `${location.pathname}?slot=${s.id}`, forEvent: `${d.name} ${showDate(cur?.date || '')} ${s.start_time}` } })
      return
    }
    if (user.suspended) return handleError({ message: 'SUSPENDED' })
    if (d.cost > 0 && d.cards.length === 0) return setDialog({ kind: 'nocard' })
    setBusy(true)
    try {
      const r = await api(`courses/${s.id}/reserve`, { method: 'POST', body: { code: s.share_code, card_id: d.cards[0]?.id } })
      setDialog({ kind: r.result === 'booked' ? 'booked' : 'waitlisted', slot: s })
      setPick(null)
      await Promise.all([load(), refreshUser()])
    } catch (e) { handleError(e) } finally { setBusy(false) }
  }

  const beyond = (date) => maxDate && date > maxDate
  const priceText = d.fee > 0 ? `NT$ ${d.fee.toLocaleString()}` : d.cost > 0 ? '課卡' : '免費'
  const sample = days[0]?.slots[0]
  const ns = user?.noshow

  return (
    <>
      {header}
      <main className="page">
        {ns?.blocked && <p className="alert warn">您因{ns.reason || '缺席次數過多'}，預約暫停{blockUntil(ns)}。已預約的時段不受影響；有疑問請聯絡主辦。</p>}
        {d.cover_url && <img className="event-cover" src={asset(d.cover_url)} alt={d.name} onError={(e) => { e.currentTarget.style.display = 'none' }} />}
        <section className="card ev-head">
          <p className="ev-host"><VenueAvatar venue={venue} /><span><b>{d.teacher?.name || venue?.name}</b> 主辦</span></p>
          <div className="ev-title-row">
            <h2 className="detail-title">{d.name}</h2>
            <ShareButton c={d} />
          </div>
          <div className="row gap-sm wrap"><Badge tone="dupr">選時段預約</Badge>{d.category && <Badge>{d.category}</Badge>}</div>
          <div className="kpis">
            <div className="kpi"><span>每個時段</span><b>{sample ? minutes(sample) : '—'}</b><small>{days.length} 天可選</small></div>
            <div className="kpi"><span>名額</span><b>每段 {d.capacity} 位</b><small>可預約多個時段</small></div>
            <div className="kpi"><span>費用</span><b>{priceText}</b><small>{d.fee > 0 ? '每段・匯款付款' : d.cost > 0 ? '每段扣課卡' : '不用付費'}</small></div>
          </div>
          {d.location && <dl className="ev-meta"><div><dt>地點</dt><dd>{d.location}</dd></div></dl>}
        </section>

        {d.mine.length > 0 && (
          <section className="card">
            <div className="sec-head"><h3>我的預約（{d.mine.length}）</h3><span>點進去可付款回報或取消</span></div>
            <div className="players">
              {d.mine.map((m) => {
                const [label, tone] = PAY(m)
                return (
                  <Link key={m.course_id} to={`/e/${m.share_code}`} className="prow">
                    <span className="flex1"><b>{showDate(m.date).slice(5)}</b> {m.start_time}–{m.end_time}</span>
                    <Badge tone={tone}>{label}</Badge><span className="muted">›</span>
                  </Link>
                )
              })}
            </div>
          </section>
        )}

        <section className="card">
          <div className="sec-head"><h3>選日期</h3>{days.length > 0 && <span>{showDate(days[0].date).slice(5)} 起</span>}</div>
          {days.length === 0 ? <p className="muted small">目前沒有開放的時段，請晚點再來看看。</p> : (
            <div className="dscroll">
              {days.map((x) => {
                const open = x.slots.filter((s) => s.state === 'book').length
                return (
                  <button key={x.date} type="button" disabled={beyond(x.date)}
                    className={`dtile ${x.date === cur?.date ? 'selected' : ''} ${x.date === today() ? 'is-today' : ''}`}
                    onClick={() => { setDay(x.date); setPick(null) }}>
                    <span>{x.date === today() ? '今天' : x.weekday}</span>
                    <b>{Number(x.date.slice(8))}</b>
                    <small>{beyond(x.date) ? '未開放' : open ? `${open} 段` : '已滿'}</small>
                  </button>
                )
              })}
            </div>
          )}
        </section>

        {cur && (
          <section className="card">
            <div className="sec-head"><h3>{showDate(cur.date)} 的時段</h3><span>綠色可預約・灰色已滿或已過</span></div>
            <div className="slot-grid">
              {cur.slots.map((s) => {
                const mine = s.mine && s.mine.status !== 'cancelled'
                const can = ['book', 'waitlist'].includes(s.state) && !beyond(cur.date)
                return (
                  <button key={s.id} type="button" disabled={!can && !mine}
                    className={`slot ${pick === s.id ? 'picked' : ''} ${mine ? 'mine' : ''} ${s.state === 'waitlist' ? 'full' : ''}`}
                    onClick={() => (mine ? navigate(`/e/${s.share_code}`) : setPick(pick === s.id ? null : s.id))}>
                    <b>{s.start_time}</b>
                    <small>{mine ? (s.mine.status === 'waitlist' ? '你在候補' : s.mine.fee && !s.mine.paid && !s.mine.pay_note ? '待回填後五碼' : '你已預約') : s.state === 'book' ? `剩 ${s.remain}` : s.state === 'waitlist' ? '額滿・可候補' : s.button}</small>
                  </button>
                )
              })}
            </div>
          </section>
        )}

        <section className="card">
          <h3 className="card-title">預約須知</h3>
          <ul className="notes">
            <li>{d.booking_deadline_min ? `開始前 ${hours(d.booking_deadline_min)}截止預約。` : '開始前都可以預約。'}</li>
            <li>{d.cancel_deadline_min ? `開始前 ${hours(d.cancel_deadline_min)}內無法自行取消，請聯絡主辦。` : '開始前都可以自行取消。'}</li>
            {d.fee > 0 && <li>預約後依主辦提供的匯款資訊付款，並在該時段頁面回填匯款帳號後五碼，回填後才算預約成功，主辦再對帳確認。{d.pay_hours ? `請在 ${d.pay_hours} 小時內付款，逾期名額會釋出。` : ''}</li>}
            <li>想預約好幾個時段，一個一個選就可以。</li>
            {noshowRule(venue) && <li>{noshowRule(venue).replace('報名', '預約')}</li>}
          </ul>
          {d.description && <p className="pre small mt">{d.description}</p>}
        </section>
      </main>

      <div className="action-bar">
        <button className={`btn btn-block btn-lg ${slot?.state === 'waitlist' ? 'btn-warn' : ''}`} disabled={!slot || busy || ns?.blocked} onClick={() => book(slot)}>
          {busy ? '處理中…' : ns?.blocked ? `暫停預約中（${blockUntil(ns)}）` : !slot ? '請先選一個時段'
            : `${slot.state === 'waitlist' ? '加入候補' : '預約'} ${showDate(cur.date).slice(5)} ${slot.start_time}–${slot.end_time}${slot.state === 'book' && d.fee > 0 ? `（NT$ ${d.fee.toLocaleString()}）` : ''}`}
        </button>
      </div>

      {dialog?.kind === 'booked' && (
        <Modal onClose={() => setDialog(null)}>
          <div className={`dialog-icon ${d.fee > 0 ? 'warn' : 'success'}`}>{d.fee > 0 ? '!' : '✓'}</div>
          <h3 className="dialog-title">{d.fee > 0 ? '時段已保留，還差一步' : '預約成功'}</h3>
          <p className="dialog-text">{d.name}<br />{showDate(cur?.date || '')} {dialog.slot.start_time}–{dialog.slot.end_time}</p>
          {d.fee > 0 && <p className="alert warn small">請匯款 NT$ {d.fee.toLocaleString()}，匯完到這個時段的頁面填「匯款帳號後五碼」，<b>送出後才算預約成功</b>。逾時沒回填，時段會讓給下一位。</p>}
          <button className="btn btn-block" onClick={() => (d.fee > 0 ? navigate(`/e/${dialog.slot.share_code}`) : setDialog(null))}>{d.fee > 0 ? '去付款' : '好'}</button>
          {d.fee > 0 && <button className="btn btn-block btn-light" onClick={() => setDialog(null)}>繼續選其他時段</button>}
        </Modal>
      )}
      {dialog?.kind === 'waitlisted' && (
        <Modal onClose={() => setDialog(null)}>
          <div className="dialog-icon warn">⏳</div>
          <h3 className="dialog-title">已加入候補</h3>
          <p className="dialog-text">有人取消會依順序自動遞補並通知您。</p>
          <button className="btn btn-block" onClick={() => setDialog(null)}>好</button>
        </Modal>
      )}
      {dialog?.kind === 'nocard' && (
        <Confirm title="這個活動要用課卡" text="您目前沒有可用的課卡。購買後主辦確認收款就會開通，再回來預約。" okText="看課卡方案"
          onClose={() => setDialog(null)} onOk={() => navigate('/plans')} />
      )}
    </>
  )
}
