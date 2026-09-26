import { useCallback, useEffect, useState } from 'react'
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom'
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
    : <TopBar title="課程資訊" back={-1} right={c?.share_code && <ShareButton c={c} className="icon-btn share-btn" />} />
  if (missing) return <>{header}<main className="page"><section className="card center"><h3 className="card-title">找不到這個活動</h3><p className="muted small">連結可能已失效，請向主辦單位確認。</p></section></main></>
  if (!c) return <>{header}<Loading /></>

  const requireLogin = () => {
    if (user) return false
    navigate('/login', { state: { from: location.pathname } })
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
    showToast(c.state === 'waiting' ? '已取消候補' : '已取消預約，課卡已退還')
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
      return setDialog('full')
    }
    if (c.state === 'booked' || c.state === 'waiting') {
      if (!c.can_cancel) return showToast(c.has_event && c.state === 'booked' ? '團主已生成賽事，無法自行取消，請聯絡團主' : '已超過可自行取消的時間，請聯絡場館')
      return setDialog('cancel')
    }
  }

  const primaryLabel = {
    book: c.cost === 0 ? '立即預約（免費）' : '立即預約',
    waitlist: '額滿，加入候補',
    booked: c.has_event ? '已排入賽事' : '取消預約',
    waiting: `取消候補（第 ${c.waitlist_position} 位）`,
  }[c.state] || c.button

  const costText = c.cost === 0 ? '免費' : `堂數卡扣 1 堂／點數卡扣 ${c.cost} 點`

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
            <div><dt>扣卡</dt><dd>{costText}</dd></div>
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
              <li>需先在會員中心綁定 DUPR 帳號{c.dupr_verified_only && '，且須經場館驗證'}。</li>
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
            <h3 className="card-title">課程介紹</h3>
            <p className="pre">{c.description}</p>
          </section>
        )}

        <section className="card">
          <h3 className="card-title">預約須知</h3>
          <ul className="notes">
            <li>課程開始前 {hours(c.booking_deadline_min)}截止預約。</li>
            <li>課程開始前 {hours(c.cancel_deadline_min)}內無法自行取消，請聯絡場館。</li>
            <li>額滿時可加入候補，有名額釋出會依順序自動遞補並扣卡、通知您。</li>
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
                  <p className="muted small">{cardRemain(card)} · 到期 {card.expires_on}</p>
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
                      {a.dupr == null ? 'NR' : Number(a.dupr).toFixed(3)}{a.dupr_verified && ' ✓'}
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
        <button
          className={`btn btn-block btn-lg ${c.state === 'waitlist' ? 'btn-warn' : ''} ${['booked', 'waiting'].includes(c.state) && !(c.has_event && c.state === 'booked') ? 'btn-outline-danger' : ''}`}
          disabled={busy || c.state === 'disabled' || (c.has_event && c.state === 'booked')}
          onClick={onPrimary}
        >
          {busy ? '處理中…' : primaryLabel}
        </button>
      </div>

      {dialog === 'booked' && (
        <Modal onClose={() => setDialog(null)}>
          <div className="dialog-icon success">✓</div>
          <h3 className="dialog-title">預約成功</h3>
          <p className="dialog-text">{showDate(c.date)} {c.start_time}<br />{c.name}</p>
          {standalone
            ? <button className="btn btn-block" onClick={() => setDialog(null)}>好</button>
            : <button className="btn btn-block" onClick={() => navigate('/me')}>查看預約紀錄</button>}
        </Modal>
      )}
      {dialog === 'waitlisted' && (
        <Modal onClose={() => setDialog(null)}>
          <div className="dialog-icon warn">⏳</div>
          <h3 className="dialog-title">已加入候補</h3>
          <p className="dialog-text">您目前是候補第 {c.waitlist_position} 位，<br />釋出名額會自動遞補並通知您。</p>
          {standalone
            ? <button className="btn btn-block" onClick={() => setDialog(null)}>好</button>
            : <button className="btn btn-block" onClick={() => navigate('/me')}>查看預約紀錄</button>}
        </Modal>
      )}
      {dialog === 'full' && (
        <Confirm title="預約人數已額滿" text="請加入候補名單，釋出名額會通知您" okText="加入候補"
          onClose={() => setDialog(null)} onOk={() => { setDialog(null); reserve() }} />
      )}
      {dialog === 'cancel' && (
        <Confirm title={c.state === 'waiting' ? '取消候補' : '取消預約'} danger okText="確定取消"
          text={c.state === 'waiting' ? '確定要取消這堂課的候補嗎？' : '取消後課卡會退還，確定要取消嗎？'}
          onClose={() => setDialog(null)} onOk={cancel} />
      )}
      {dialog === 'dupr' && (
        <Confirm title="不符合 DUPR 報名條件" text={c.dupr_problem} okText={user?.dupr_id ? '查看我的 DUPR' : '前往綁定'}
          onClose={() => setDialog(null)} onOk={() => navigate('/me?tab=dupr')} />
      )}
      {dialog === 'nocard' && (
        <Confirm title="沒有可用的課卡" text="這堂課需要使用課卡，請先購買課卡方案。" okText="前往購買"
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
      await api(`event-games/${g.id}/confirm`, { method: 'POST' })
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
        <p className="small">{FORMAT_TEXT[c.match_format]}；每局打到 {c.games_to} 分、領先 2 分獲勝。</p>
        {!event && <p className="muted small">報名人數到齊後，團主會依 DUPR 分數分組並生成賽程，屆時會通知您。</p>}
        {event?.is_player && <p className="muted small">打完後由任一方回報比分，對手按「確認比分」才算數。</p>}
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
