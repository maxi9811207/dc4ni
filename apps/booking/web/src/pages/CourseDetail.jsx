import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import EventBoard, { ScoreModal } from '../components/EventBoard'
import { ShareButton } from '../components/Share'
import { Avatar, AvatarImg, Badge, Confirm, Field, Loading, Modal, TopBar } from '../components/ui'
import { cardRemain, duprRange, hours, rating, showDate } from '../util'

// /course/:id 是課表裡的課程頁；/e/:code 是分享出去的一頁式活動頁（沒有場館導覽，只有報名）
export default function CourseDetail() {
  const { id, code } = useParams()
  const standalone = Boolean(code)
  const { user, venue, refreshUser, handleError, showToast } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [params, setParams] = useSearchParams()
  const [c, setC] = useState(null)
  const [cardId, setCardId] = useState(null)
  const [dialog, setDialog] = useState(null)
  const [busy, setBusy] = useState(false)

  const [missing, setMissing] = useState(false)
  const load = useCallback(() => api(code ? `e/${code}` : `courses/${id}`).then((d) => {
    setC(d)
    setCardId(d.cards[0]?.id ?? null)
  }).catch((e) => (e.status === 404 ? setMissing(true) : handleError(e))), [id, code, handleError])

  useEffect(() => { load() }, [load])
  useEffect(() => {
    if (standalone && c) document.title = `${c.name}｜${venue?.name || '報名'}`
  }, [standalone, c, venue])

  const header = standalone
    ? <StandaloneBar />
    : <TopBar title="活動資訊" back={-1} right={c?.share_code && <ShareButton c={c} className="icon-btn share-btn" />} />
  // 從登入頁回來（?book=1）：自動接著報名，不用再按一次
  const autoBook = params.get('book') === '1'
  useEffect(() => {
    if (!autoBook || !c || !user) return
    setParams((p) => { p.delete('book'); return p }, { replace: true })
    if (['book', 'waitlist'].includes(c.state)) onPrimaryRef.current?.()
  }, [autoBook, c, user, setParams])
  const onPrimaryRef = useRef(null)

  if (missing) return <>{header}<main className="page"><section className="card center"><h3 className="card-title">找不到這個活動</h3><p className="muted small">連結可能已失效，請向主辦單位確認。</p></section></main></>
  if (!c) return <>{header}<Loading /></>

  const requireLogin = () => {
    if (user) return false
    navigate('/login', { state: { from: `${location.pathname}?book=1`, forEvent: c.name } })
    return true
  }

  const act = async (fn) => {
    setBusy(true)
    try { await fn() } catch (e) { handleError(e) } finally { setBusy(false) }
  }

  const reserve = () => act(async () => {
    const r = await api(`courses/${c.id}/reserve`, { method: 'POST', body: { card_id: cardId, code: c.share_code } })
    setDialog(r.result === 'booked' ? 'booked' : 'waitlisted')
    await Promise.all([load(), refreshUser()])
  })

  const cancel = () => act(async () => {
    await api(`courses/${c.id}/cancel`, { method: 'POST' })
    setDialog(null)
    showToast(c.state === 'waiting' ? '已取消候補'
      : c.fee > 0 ? (c.my_reservation?.paid ? '已取消報名，已付的費用主辦會另外退還' : '已取消報名')
        : c.cost > 0 ? '已取消報名，課卡已退還' : '已取消報名')
    await Promise.all([load(), refreshUser()])
  })

  const onPrimary = () => {
    if (requireLogin()) return
    if (user.suspended) return handleError({ message: 'SUSPENDED' })
    if (['book', 'waitlist'].includes(c.state) && c.dupr_problem) return setDialog('dupr')
    if (c.state === 'book') {
      if (c.cost > 0 && c.cards.length === 0) return setDialog('nocard')
      return reserve()
    }
    if (c.state === 'waitlist') {
      if (c.cost > 0 && c.cards.length === 0) return setDialog('nocard')
      return reserve()  // 按鈕已寫「額滿，加入候補」，不再多問一次
    }
    if (needsPay) return document.querySelector('.pay-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
  onPrimaryRef.current = onPrimary
  const askCancel = () => {
    if (!c.can_cancel) return showToast(c.has_event && c.state === 'booked' ? '主辦已排好賽程，無法自行取消，請聯絡主辦' : '已超過可自行取消的時間，請聯絡主辦')
    setDialog('cancel')
  }

  const mine = c.my_reservation
  const needsPay = c.fee > 0 && c.state === 'booked' && mine && !mine.paid
  const bestCard = c.cards.find((x) => x.id === cardId) || c.cards[0]
  const primaryLabel = {
    book: c.fee > 0 ? `立即報名（NT$ ${c.fee.toLocaleString()}）` : c.cost === 0 ? '立即報名（免費）' : '立即報名',
    waitlist: '額滿，加入候補',
  }[c.state] || (needsPay ? `付款回報（NT$ ${c.fee.toLocaleString()}）` : c.button)
  // 已報名／候補：主按鈕換成狀態，取消退到下面的文字連結
  const statusLine = c.state === 'booked' ? (c.has_event ? '✓ 已排入賽事' : mine?.paid || !c.fee ? '✓ 已報名' : null)
    : c.state === 'waiting' ? `候補第 ${c.waitlist_position} 位，有名額會自動遞補並通知您` : null

  const costText = c.fee > 0 ? `NT$ ${c.fee.toLocaleString()}（報名後付款，不需課卡）`
    : c.cost === 0 ? '免費'
      : bestCard?.value > 0 ? `用課卡，這堂約 NT$ ${bestCard.value.toLocaleString()}（${bestCard.type === 'points' ? `扣 ${c.cost} 點` : bestCard.type === 'unlimited' ? '無限卡' : '扣 1 堂'}）`
        : `用課卡（堂數卡扣 1 堂／點數卡扣 ${c.cost} 點）`

  return (
    <>
      {header}
      <main className="page">
        <section className="card detail-card">
          <div className="row gap-sm wrap">
            {c.category && <Badge>{c.category}</Badge>}
            {c.dupr_required && c.category !== 'DUPR 場' && <Badge tone="dupr">DUPR 場</Badge>}
            {c.beginner && <Badge tone="danger">新手友善</Badge>}
            {c.status === 'cancelled' && <Badge tone="gray">已停課</Badge>}
          </div>
          <div className="row between gap">
            <h2 className="detail-title">{c.name}</h2>
            {standalone && <ShareButton c={c} />}
          </div>
          <dl className="info-list">
            <div><dt>日期</dt><dd>{showDate(c.date)}</dd></div>
            <div><dt>時間</dt><dd className="text-brand strong">{c.start_time} ~ {c.end_time}</dd></div>
            {c.location && <div><dt>地點</dt><dd>{c.location}</dd></div>}
            <div><dt>人數</dt><dd>{c.booked_count} / {c.capacity}{c.waitlist_count > 0 && `（候補 ${c.waitlist_count} 人）`}</dd></div>
            <div><dt>費用</dt><dd className={c.fee > 0 ? 'strong' : ''}>{costText}</dd></div>
          </dl>
        </section>

        {c.teacher && (
          <Link to={`/teachers/${c.teacher.id}`} className="card row gap teacher-row">
            <Avatar src={c.teacher.photo_url} name={c.teacher.name} />
            <div className="flex1">
              <b>{c.teacher.name}{c.substitute && '（代課）'}</b>
              <p className="muted small">{c.teacher.title}</p>
            </div>
            <span className="muted">›</span>
          </Link>
        )}

        {c.dupr_required && (
          <section className="card dupr-card">
            <h3 className="card-title">DUPR 報名條件</h3>
            <p className="dupr-range">{duprRange(c)}</p>
            <ul className="notes">
              <li>需先在會員中心綁定 DUPR 帳號{c.dupr_verified_only && '，且須經主辦驗證'}。</li>
              <li>以綁定時取得的 DUPR {c.dupr_format === 'singles' ? '單打' : '雙打'}分數判斷資格。</li>
            </ul>
            {user && (
              user.dupr_id
                ? <p className={`small ${c.dupr_problem ? 'text-danger' : 'text-success'}`}>
                    您的 DUPR：{c.dupr_format === 'singles' ? '單打' : '雙打'} {rating(user[`dupr_${c.dupr_format}`])}
                    {c.dupr_problem ? `（${c.dupr_problem}）` : '，符合資格 ✓'}
                  </p>
                : <Link className="btn btn-small btn-outline" to="/me?tab=dupr">綁定 DUPR 帳號</Link>
            )}
          </section>
        )}

        {c.fee > 0 && ['booked', 'attended', 'absent'].includes(c.my_reservation?.status) && <PaymentBox c={c} onSaved={load} />}

        {c.dupr_required && <EventSection c={c} />}

        {standalone && venue && (venue.address || venue.phone || venue.line_url) && (
          <section className="card">
            <h3 className="card-title">主辦單位</h3>
            <p><b>{venue.name}</b></p>
            {venue.address && <p className="small"><a href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(venue.address)}`} target="_blank" rel="noreferrer">{venue.address}</a></p>}
            {venue.phone && <p className="small"><a href={`tel:${venue.phone}`}>{venue.phone}</a></p>}
            {venue.line_url && <p className="small"><a href={venue.line_url} target="_blank" rel="noreferrer">LINE 聯絡主辦</a></p>}
          </section>
        )}

        {c.description && (
          <section className="card">
            <h3 className="card-title">活動介紹</h3>
            <p className="pre">{c.description}</p>
          </section>
        )}

        <section className="card">
          <h3 className="card-title">報名須知</h3>
          <ul className="notes">
            <li>{c.booking_deadline_min ? `開始前 ${hours(c.booking_deadline_min)}截止報名。` : '開始前都可以報名。'}</li>
            <li>{c.cancel_deadline_min ? `開始前 ${hours(c.cancel_deadline_min)}內無法自行取消，請聯絡主辦。` : '開始前都可以自行取消。'}</li>
            <li>額滿時可加入候補，有名額釋出會依順序自動遞補{c.cost > 0 ? '並扣卡' : ''}、通知您{c.fee > 0 ? '，遞補後再付款' : ''}。</li>
            {c.fee > 0 && <li>已付款後取消，請聯絡主辦辦理退費。</li>}
          </ul>
        </section>

        {user && ['book', 'waitlist'].includes(c.state) && c.cost > 0 && c.cards.length > 1 && (
          <section className="card">
            <h3 className="card-title">使用課卡</h3>
            {c.cards.map((card) => (
              <label key={card.id} className={`select-card ${cardId === card.id ? 'active' : ''}`}>
                <input type="radio" name="card" checked={cardId === card.id} onChange={() => setCardId(card.id)} />
                <div className="flex1">
                  <b>{card.name}</b>
                  <p className="muted small">{cardRemain(card)} · 到期 {card.expires_on}{card.value > 0 && ` · 這堂約 NT$ ${card.value}`}</p>
                </div>
              </label>
            ))}
          </section>
        )}

        {c.attendees.length > 0 && (
          <section className="card">
            <h3 className="card-title">已報名（{c.attendees.length}）</h3>
            <div className="attendee-grid">
              {c.attendees.map((a, i) => (
                <div key={i} className="attendee-cell">
                  <Avatar src={a.avatar_url} name={a.name} size={48} />
                  <span className="attendee-name">{a.name}</span>
                  {c.dupr_required && (
                    <span className={`dupr-chip ${a.dupr_verified ? 'verified' : ''}`} title={a.dupr_verified ? '場館已驗證' : '未驗證'}>
                      {a.dupr == null ? '尚無分數' : Number(a.dupr).toFixed(3)}{a.dupr_verified && ' ✓'}
                    </span>
                  )}
                </div>
              ))}
            </div>
            {c.dupr_required && c.attendees.length > 1 && (
              <p className="muted small">平均 DUPR {c.dupr_format === 'singles' ? '單打' : '雙打'}：{(c.attendees.filter((a) => a.dupr != null).reduce((s, a) => s + a.dupr, 0) / Math.max(c.attendees.filter((a) => a.dupr != null).length, 1)).toFixed(3)}</p>
            )}
          </section>
        )}
      </main>

      <div className="action-bar">
        {statusLine ? (
          <div className="status-bar">
            <b className={c.state === 'waiting' ? 'text-warn' : 'text-success'}>{statusLine}</b>
            {(c.can_cancel || !c.has_event) && (
              <button type="button" className="link-btn" onClick={askCancel}>{c.state === 'waiting' ? '取消候補' : '取消報名'}</button>
            )}
          </div>
        ) : (
          <>
            <button
              className={`btn btn-block btn-lg ${c.state === 'waitlist' ? 'btn-warn' : ''}`}
              disabled={busy || c.state === 'disabled'}
              onClick={onPrimary}
            >
              {busy ? '處理中…' : primaryLabel}
            </button>
            {needsPay && <button type="button" className="link-btn center-link" onClick={askCancel}>取消報名</button>}
          </>
        )}
      </div>

      {dialog === 'booked' && (
        <Modal onClose={() => setDialog(null)}>
          <div className="dialog-icon success">✓</div>
          <h3 className="dialog-title">報名成功</h3>
          <p className="dialog-text">{showDate(c.date)} {c.start_time}<br />{c.name}</p>
          {c.fee > 0 && <p className="alert warn small">名額已保留。請付報名費 NT$ {c.fee.toLocaleString()}，付完在頁面上「付款回報」填末五碼。</p>}
          <button className="btn btn-block" onClick={() => { setDialog(null); if (c.fee > 0) setTimeout(() => document.querySelector('.pay-card')?.scrollIntoView({ behavior: 'smooth', block: 'center' }), 50) }}>
            {c.fee > 0 ? '去付款' : '好'}
          </button>
          {!standalone && <button className="btn btn-block btn-light" onClick={() => navigate('/me')}>查看我的報名</button>}
        </Modal>
      )}
      {dialog === 'waitlisted' && (
        <Modal onClose={() => setDialog(null)}>
          <div className="dialog-icon warn">⏳</div>
          <h3 className="dialog-title">已加入候補</h3>
          <p className="dialog-text">您目前是候補第 {c.waitlist_position} 位，<br />釋出名額會自動遞補並通知您。</p>
          <button className="btn btn-block" onClick={() => setDialog(null)}>好</button>
        </Modal>
      )}
      {dialog === 'cancel' && (
        <Confirm title={c.state === 'waiting' ? '取消候補' : '取消報名'} danger okText="確定取消"
          text={c.state === 'waiting' ? '確定要取消候補嗎？'
            : c.fee > 0 ? (mine?.paid ? '已付的報名費需聯絡主辦退還，確定要取消嗎？' : '確定要取消報名嗎？')
              : c.cost > 0 ? '取消後課卡會退還，確定要取消嗎？' : '確定要取消報名嗎？'}
          onClose={() => setDialog(null)} onOk={cancel} />
      )}
      {dialog === 'dupr' && (
        <Confirm title="不符合 DUPR 報名條件" text={c.dupr_problem} okText={user?.dupr_id ? '查看我的 DUPR' : '前往綁定'}
          onClose={() => setDialog(null)} onOk={() => navigate('/me?tab=dupr')} />
      )}
      {dialog === 'nocard' && (
        <Confirm title="這堂需要課卡" text="您目前沒有可用的課卡。購買後主辦確認收款就會開通，開通後再回來報名。" okText="看課卡方案"
          onClose={() => setDialog(null)} onOk={() => navigate('/plans')} />
      )}
    </>
  )
}

const FORMAT_TEXT = {
  rotating: '輪換搭檔：每組 4～7 人一面場，每局換搭檔，和同組每個人盡量都搭檔一次',
  fixed: '固定搭檔：兩人一隊，同組隊伍互打一輪',
  singles: '單打循環賽：同組每人互打一場',
}

function EventSection({ c }) {
  const { user, handleError, showToast } = useApp()
  const [event, setEvent] = useState(undefined)
  const [scoring, setScoring] = useState(null)
  const load = useCallback(() => api(`courses/${c.id}/event?code=${c.share_code}`).then((d) => setEvent(d.event)).catch(handleError), [c.id, c.share_code, handleError])
  useEffect(() => { load() }, [load])
  if (event === undefined) return null
  const booked = ['booked', 'attended', 'absent'].includes(c.my_reservation?.status)

  const report = async (a, b) => {
    try {
      await api(`event-games/${scoring.id}/report`, { method: 'POST', body: { score_a: a, score_b: b } })
      setScoring(null)
      showToast('已送出，等待對手確認')
      load()
    } catch (e) { handleError(e) }
  }
  const confirm = async (g) => {
    try {
      await api(`event-games/${g.id}/confirm`, { method: 'POST', body: { score_a: g.score_a, score_b: g.score_b } })
      showToast('比分已確認')
      load()
    } catch (e) { handleError(e) }
  }

  return (
    <>
      <section className="card">
        <div className="row between">
          <h3 className="card-title nomargin">賽事</h3>
          {event && <span className="muted small">已確認 {event.progress.confirmed} / {event.progress.total} 局</span>}
        </div>
        <p className="small">{FORMAT_TEXT[c.match_format]}。每局打到 {c.games_to} 分、領先 2 分獲勝。</p>
        {!event && <p className="muted small">人到齊後，主辦會依 DUPR 分數分組並排好賽程，排好會通知您。</p>}
        {event?.is_player && <p className="muted small">打完由任一方回報比分，對手確認才算數；對手一直沒確認就請主辦裁定。</p>}
        {!event && c.match_format === 'fixed' && booked && user && <PartnerBox courseId={c.id} />}
      </section>
      {event && <EventBoard event={event} me={user?.id} onScore={setScoring} onConfirm={confirm} />}
      {scoring && <ScoreModal game={scoring} gamesTo={event.games_to} onClose={() => setScoring(null)} onSave={report} />}
    </>
  )
}

function PartnerBox({ courseId }) {
  const { handleError, showToast } = useApp()
  const [info, setInfo] = useState(null)
  const [contact, setContact] = useState('')
  const load = useCallback(() => api(`courses/${courseId}/partner`).then(setInfo).catch(handleError), [courseId, handleError])
  useEffect(() => { load() }, [load])
  if (!info) return null
  const save = async (value) => {
    try {
      const r = await api(`courses/${courseId}/partner`, { method: 'PUT', body: { contact: value } })
      showToast(r.partner ? `已指定隊友：${r.partner.name}` : '已取消指定隊友')
      setContact('')
      load()
    } catch (e) { handleError(e) }
  }
  return (
    <div className="partner-box">
      {info.partner ? (
        <div className="row between">
          <span className="small">我的隊友：<b>{info.partner.name}</b></span>
          <button className="btn btn-small btn-light" onClick={() => save('')}>取消指定</button>
        </div>
      ) : (
        <form className="row gap" onSubmit={(e) => { e.preventDefault(); save(contact) }}>
          <Field label="指定隊友（選填）" hint="輸入對方註冊的手機或信箱，對方也要報名這場；沒指定的由團主依分數配對">
            <input className="input" value={contact} onChange={(e) => setContact(e.target.value)} placeholder="手機或信箱" />
          </Field>
          <button className="btn btn-small" disabled={!contact.trim()}>指定</button>
        </form>
      )}
      {info.chosen_by.length > 0 && <p className="small text-brand">{info.chosen_by.map((u) => u.name).join('、')} 指定您為隊友</p>}
    </div>
  )
}

// 一頁式活動頁的頂列：主辦名稱＋登入狀態（沒有返回與場館導覽）
function StandaloneBar() {
  const { venue, user } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  return (
    <header className="topbar standalone-bar">
      <span className="standalone-venue">{venue?.name || ''}</span>
      <div className="topbar-right">
        {user
          ? <span className="standalone-user"><span className="player-avatar"><AvatarImg src={user.avatar_url} name={user.name} /></span>{user.name}</span>
          : <button className="btn btn-small" onClick={() => navigate('/login', { state: { from: location.pathname } })}>登入</button>}
      </div>
    </header>
  )
}

// 單次報名費：付款說明、回報匯款資訊、收款狀態
function PaymentBox({ c, onSaved }) {
  const { venue, handleError, showToast } = useApp()
  const r = c.my_reservation
  const [note, setNote] = useState(r.pay_note || '')
  const save = async (e) => {
    e.preventDefault()
    try {
      await api(`courses/${c.id}/payment`, { method: 'PUT', body: { note } })
      showToast('已送出，場館核對後會通知您')
      onSaved()
    } catch (err) { handleError(err) }
  }
  return (
    <section className={`card pay-card ${r.paid ? 'paid' : ''}`}>
      <div className="row between">
        <h3 className="card-title nomargin">報名費 NT$ {r.fee.toLocaleString()}</h3>
        {r.paid ? <Badge tone="success">已付款</Badge> : <Badge tone="warn">待付款</Badge>}
      </div>
      {r.paid ? (
        <p className="small text-success">場館已確認收款，當天直接到場即可。</p>
      ) : (
        <>
          <p className="pre small pay-info">{venue?.payment_ready ? venue.payment_info : '付款方式請直接詢問主辦。'}</p>
          {r.pay_due && <p className="small text-warn">請在 {r.pay_due.slice(5, 16).replace('-', '/').replace('T', ' ')} 前付款，逾期名額會讓給候補。</p>}
          <form className="row gap" onSubmit={save}>
            <Field label="付款回報" hint="例如匯款帳號末五碼、轉帳時間，或「現場付款」">
              <input className="input" value={note} onChange={(e) => setNote(e.target.value)} maxLength={100} placeholder="末五碼 12345" />
            </Field>
            <button className="btn btn-small" disabled={note === (r.pay_note || '')}>送出</button>
          </form>
          {r.pay_note && <p className="muted small">已回報：{r.pay_note}，等待場館確認</p>}
        </>
      )}
    </section>
  )
}
