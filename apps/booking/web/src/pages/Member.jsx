import { useCallback, useEffect, useState } from 'react'
import { Link, Navigate, useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import CourseCard from '../components/CourseCard'
import SupportContact from '../components/SupportContact'
import { Avatar, Badge, Chips, Empty, Field, Loading, Modal, Stars, TopBar } from '../components/ui'
import { blockUntil, cardRemain, money, noshowRule, rating, showDate, showDateTime } from '../util'

const TABS = [['reservations', '我的報名'], ['cards', '我的課卡'], ['attendance', '出席紀錄'], ['dupr', 'DUPR'], ['notifications', '通知'], ['account', '帳號']]

// 用 LINE 登入但沒加官方帳號好友：報名成功、候補遞補、開課提醒都傳不到 LINE，提醒一下
function LineFriendNote({ user }) {
  const [info, setInfo] = useState(null)
  useEffect(() => {
    if (!user.line_linked) return
    api('me/line-friend').then(setInfo).catch(() => {})
  }, [user.id, user.line_linked])
  if (!info || info.friend !== false || !info.add_url) return null
  return (
    <div className="alert info line-friend">
      <span>加入 LINE 官方帳號好友，報名成功、候補遞補、開課前一天提醒才會傳到你的 LINE。</span>
      <a className="btn btn-small btn-line" href={info.add_url} target="_blank" rel="noreferrer">加好友</a>
    </div>
  )
}

export default function Member() {
  const { user } = useApp()
  const [params, setParams] = useSearchParams()
  const tab = params.get('tab') || 'reservations'
  if (!user) return <Navigate to="/login" replace state={{ from: '/me' }} />

  return (
    <>
      <TopBar title="會員中心" back="/" />
      <main className="page">
        <section className="card row gap member-head">
          <Avatar src={user.avatar_url} name={user.name} size={52} />
          <div className="flex1">
            <b className="big">{user.name}</b>
            <p className="muted small">{user.email || user.phone || (user.line_linked ? 'LINE 登入' : '')}</p>
            {user.dupr_id && <p className="small"><span className="badge badge-dupr">DUPR</span> 雙打 {rating(user.dupr_doubles)} · 單打 {rating(user.dupr_singles)}</p>}
          </div>
          {user.role === 'owner' && <Link className="btn btn-small" to="/admin">場主後台</Link>}
        </section>
        <LineFriendNote user={user} />
        {user.noshow?.blocked && <div className="alert warn">您因{user.noshow.reason || '缺席次數過多'}，報名暫停{blockUntil(user.noshow)}。已報名的活動不受影響。<Link className="strong" to="/me?tab=attendance"> 看紀錄 ›</Link></div>}
        {user.suspended ? <div className="alert danger">您的帳號已被停權，請聯絡場館管理員。{user.suspend_reason && `原因：${user.suspend_reason}`}</div> : null}
        <Chips value={tab} onChange={(t) => setParams({ tab: t }, { replace: true })}
          options={TABS.map(([k, l]) => [k, k === 'notifications' && user.unread ? `${l}（${user.unread}）` : l])} />
        {tab === 'reservations' && <Reservations />}
        {tab === 'cards' && <Cards />}
        {tab === 'attendance' && <Attendance />}
        {tab === 'dupr' && <Dupr />}
        {tab === 'notifications' && <Notifications />}
        {tab === 'account' && <Account />}
      </main>
    </>
  )
}

function Reservations() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const [view, setView] = useState('upcoming')
  const [reviewing, setReviewing] = useState(null)
  const load = useCallback(() => api('me/reservations').then(setList).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

  if (!list) return <Loading />
  const upcoming = list.filter((x) => !x.ended).reverse()
  const history = list.filter((x) => x.ended)
  const shown = view === 'upcoming' ? upcoming : history

  return (
    <>
      <div className="seg">
        <button className={view === 'upcoming' ? 'active' : ''} onClick={() => setView('upcoming')}>即將到來（{upcoming.length}）</button>
        <button className={view === 'history' ? 'active' : ''} onClick={() => setView('history')}>歷史紀錄</button>
      </div>
      {shown.length === 0 ? <Empty text={view === 'upcoming' ? '目前沒有報名' : '還沒有參加紀錄'}><Link className="btn" to="/">看看有哪些活動</Link></Empty>
        : shown.map(({ reservation: r, course: c, reviewed }) => (
          <div key={r.id}>
            <CourseCard course={c} showDate />
            {r.fee > 0 && r.status === 'booked' && !r.paid && view === 'upcoming' && (
              <Link to={`/course/${c.id}`} className={`history-foot small ${r.pay_note ? 'text-success' : 'text-warn'}`}>
                {r.pay_note ? `已回填後五碼，報名成功・等主辦對帳 ›` : `尚未完成報名：匯款 NT$ ${r.fee.toLocaleString()} 後回填後五碼 ›`}
              </Link>
            )}
            {view === 'history' && (
              <div className="history-foot">
                <span className="muted small">{{ attended: '已出席', absent: '缺席', booked: '未點名', waitlist: '候補未遞補' }[r.status]}</span>
                {['booked', 'attended'].includes(r.status) && (reviewed
                  ? <span className="muted small">已評價</span>
                  : <button className="btn btn-small btn-outline" onClick={() => setReviewing(c)}>給評價</button>)}
              </div>
            )}
          </div>
        ))}
      {reviewing && <ReviewDialog course={reviewing} onClose={() => setReviewing(null)}
        onDone={() => { setReviewing(null); showToast('感謝您的評價！'); load() }} />}
    </>
  )
}

function ReviewDialog({ course, onClose, onDone }) {
  const { handleError } = useApp()
  const [rating, setRating] = useState(5)
  const [comment, setComment] = useState('')
  const quick = ['太棒了！我會推薦朋友來', '很適合新手來體驗！', '十分用心教學的老師，推～', '喜歡上課的氛圍']
  const submit = () => api('reviews', { method: 'POST', body: { course_id: course.id, rating, comment } }).then(onDone).catch(handleError)
  return (
    <Modal onClose={onClose}>
      <h3 className="dialog-title">評價課程</h3>
      <p className="muted center small">{course.name}</p>
      <div className="center"><Stars value={rating} size={34} onChange={setRating} /></div>
      <div className="chips wrap">
        {quick.map((q) => <button key={q} className="chip" onClick={() => setComment((comment ? comment + '\n' : '') + q)}>{q}</button>)}
      </div>
      <textarea className="input" rows={4} value={comment} onChange={(e) => setComment(e.target.value)} placeholder="分享您的上課心得" />
      <button className="btn btn-block" onClick={submit}>送出評價</button>
    </Modal>
  )
}

function Cards() {
  const { handleError } = useApp()
  const [data, setData] = useState(null)
  useEffect(() => { api('me/cards').then(setData).catch(handleError) }, [handleError])
  if (!data) return <Loading />
  const pending = data.orders.filter((o) => o.status === 'pending')
  return (
    <>
      {pending.map((o) => (
        <div key={o.id} className="alert warn">「{o.plan_name}」{money(o.amount)} 等待場館確認收款</div>
      ))}
      {data.cards.length === 0 ? <Empty text="還沒有課卡"><Link className="btn" to="/plans">購買課卡</Link></Empty>
        : data.cards.map((c) => (
          <div key={c.id} className={`card member-card ${c.valid ? '' : 'expired'}`}>
            <div className="row between">
              <b>{c.name}</b>
              {c.valid ? <Badge tone="success">使用中</Badge> : <Badge tone="gray">{c.expires_on < new Date().toISOString().slice(0, 10) ? '已過期' : '已用完'}</Badge>}
            </div>
            <p className="plan-amount">{cardRemain(c)}</p>
            <p className="muted small">有效期間 {c.starts_on} ~ {c.expires_on}</p>
          </div>
        ))}
      {data.orders.length > 0 && (
        <section className="card">
          <h3 className="card-title">購買紀錄</h3>
          {data.orders.map((o) => (
            <div key={o.id} className="row between list-row">
              <div><b>{o.plan_name}</b><p className="muted small">{showDateTime(o.created_at)}</p></div>
              <div className="right">
                <span>{money(o.amount)}</span><br />
                <span className={`small ${o.status === 'paid' ? 'text-success' : o.status === 'pending' ? 'text-warn' : 'muted'}`}>
                  {{ paid: '已開通', pending: '待確認', cancelled: '已取消' }[o.status]}
                </span>
              </div>
            </div>
          ))}
        </section>
      )}
    </>
  )
}

function Notifications() {
  const { handleError, refreshUser } = useApp()
  const [list, setList] = useState(null)
  useEffect(() => { api('me/notifications').then((l) => { setList(l); refreshUser() }).catch(handleError) }, [handleError, refreshUser])
  if (!list) return <Loading />
  if (list.length === 0) return <Empty text="沒有通知" />
  return (
    <section className="card">
      {list.map((n) => (
        <div key={n.id} className={`notice ${n.read ? '' : 'unread'}`}>
          <p>{n.text}</p>
          <span className="muted small">{showDateTime(n.created_at)}</span>
        </div>
      ))}
    </section>
  )
}

function Account() {
  const { user, auth, refreshUser, signOut, showToast, handleError } = useApp()
  const navigate = useNavigate()
  const [form, setForm] = useState({ name: user.name, email: user.email || '', phone: user.phone || '', password: '', new_password: '' })
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const [uploading, setUploading] = useState(false)
  const uploadAvatar = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    const data = new FormData()
    data.append('file', file)
    setUploading(true)
    try {
      await api('me/avatar', { method: 'POST', form: data })
      await refreshUser()
      showToast('已更新大頭照')
    } catch (err) { handleError(err) } finally { setUploading(false) }
  }
  const save = async (e) => {
    e.preventDefault()
    try {
      await api('me', { method: 'PUT', body: form })
      await refreshUser()
      setForm({ ...form, password: '', new_password: '' })
      showToast('已更新')
    } catch (err) { handleError(err) }
  }
  const linkLine = async () => {
    try { window.location.href = (await api('auth/line/link', { method: 'POST' })).url } catch (err) { handleError(err) }
  }
  const unlinkLine = async () => {
    try { await api('me/line', { method: 'DELETE' }); await refreshUser(); showToast('已解除 LINE 綁定') } catch (err) { handleError(err) }
  }
  return (
    <>
      <section className="card row gap">
        <Avatar src={user.avatar_url} name={user.name} size={64} />
        <div className="flex1">
          <b>大頭照</b>
          <p className="muted small">{user.avatar_source === 'line' ? '目前使用 LINE 頭像，' : ''}會顯示在您報名的課程中，讓球友認識您</p>
        </div>
        <label className="btn btn-small btn-light upload-btn">
          {uploading ? '上傳中…' : user.avatar_url ? '更換' : '上傳'}
          <input type="file" accept="image/*" hidden onChange={uploadAvatar} />
        </label>
      </section>
      {auth.line_enabled && (
        <section className="card row gap">
          <span className="line-dot" aria-hidden="true">LINE</span>
          <div className="flex1">
            <b>LINE 帳號</b>
            <p className="muted small">{user.line_linked ? '已綁定，可直接用 LINE 登入' : '綁定後可用 LINE 一鍵登入，並使用 LINE 頭像'}</p>
          </div>
          {user.line_linked
            ? <button className="btn btn-small btn-light" onClick={unlinkLine}>解除</button>
            : <button className="btn btn-small btn-line" onClick={linkLine}>綁定</button>}
        </section>
      )}
      <form className="card form" onSubmit={save}>
        <Field label="姓名"><input className="input" value={form.name} onChange={set('name')} required /></Field>
        <Field label="信箱" hint={user.line_linked && !user.email ? '設定信箱與密碼後，也可以用信箱登入' : undefined}>
          <input className="input" type="email" value={form.email} onChange={set('email')} autoComplete="email" />
        </Field>
        <Field label="手機號碼（選填）"><input className="input" type="tel" value={form.phone} onChange={set('phone')} autoComplete="tel" /></Field>
        {user.has_password && (
          <Field label="原密碼" hint="要修改密碼才需要填寫"><input className="input" type="password" value={form.password} onChange={set('password')} autoComplete="current-password" /></Field>
        )}
        <Field label={user.has_password ? '新密碼' : '設定密碼'}><input className="input" type="password" value={form.new_password} onChange={set('new_password')} minLength={6} autoComplete="new-password" /></Field>
        <button className="btn btn-block">儲存</button>
      </form>
      <button className="btn btn-block btn-light" onClick={async () => { await signOut(); navigate('/') }}>登出</button>
    </>
  )
}

function Dupr() {
  const { user, refreshUser, handleError, showToast } = useApp()
  const [config, setConfig] = useState(null)
  const [editing, setEditing] = useState(!user.dupr_id)
  const [form, setForm] = useState({ dupr_id: user.dupr_id, doubles: user.dupr_doubles ?? '', singles: user.dupr_singles ?? '', optin: !!user.dupr_optin })
  const [busy, setBusy] = useState(false)
  useEffect(() => { api('dupr/config').then(setConfig).catch(handleError) }, [handleError])
  if (!config) return <Loading />

  const run = async (fn, msg) => {
    setBusy(true)
    try { await fn(); await refreshUser(); showToast(msg); setEditing(false) } catch (e) { handleError(e) } finally { setBusy(false) }
  }
  const save = (e) => {
    e.preventDefault()
    run(() => api('me/dupr', { method: 'PUT', body: form }), '已綁定 DUPR 帳號')
  }
  const status = user.dupr_source === 'sso' ? ['DUPR 帳號登入', 'success'] : user.dupr_verified ? ['已驗證', 'success'] : user.dupr_source === 'api' ? ['DUPR 官方資料', 'brand'] : ['待場館核對', 'warn']
  const ents = user.dupr_entitlements || []
  if (config.sso) return <DuprSso config={config} user={user} status={status} ents={ents} busy={busy} run={run} />

  return (
    <>
      {user.dupr_id && !editing && (
        <section className="card dupr-card">
          <div className="row between">
            <b className="big">DUPR 帳號</b>
            <Badge tone={status[1]}>{status[0]}</Badge>
          </div>
          <p className="muted small">DUPR ID：<b className="text-brand">{user.dupr_id}</b>{user.dupr_name && ` · ${user.dupr_name}`}</p>
          <div className="stats stats-2">
            <div className="stat"><span>雙打分數</span><b>{rating(user.dupr_doubles)}</b></div>
            <div className="stat"><span>單打分數</span><b>{rating(user.dupr_singles)}</b></div>
          </div>
          <p className="muted small">更新時間 {showDateTime(user.dupr_synced_at)}</p>
          <div className="admin-actions">
            {config.api_enabled && <button className="btn btn-small" disabled={busy} onClick={() => run(() => api('me/dupr/refresh', { method: 'POST' }), '已從 DUPR 更新分數')}>從 DUPR 更新分數</button>}
            <button className="btn btn-small btn-light" onClick={() => setEditing(true)}>{config.api_enabled ? '更換帳號' : '修改'}</button>
            <button className="btn btn-small btn-light text-danger" disabled={busy} onClick={() => run(() => api('me/dupr', { method: 'PUT', body: { dupr_id: '' } }), '已解除綁定')}>解除綁定</button>
          </div>
        </section>
      )}
      {!editing && <DuprOptin />}
      {editing && (
        <form className="card form" onSubmit={save}>
          <h3 className="card-title nomargin">綁定 DUPR 帳號</h3>
          <p className="muted small">綁定後即可報名「DUPR 場」，系統會依您的 DUPR 分數判斷是否符合該場的分數範圍。</p>
          <Field label="DUPR ID" hint="打開 DUPR App → 個人頁面，名字下方的 8 碼英數字（例如 GB0NV05E）">
            <input className="input" value={form.dupr_id} onChange={(e) => setForm({ ...form, dupr_id: e.target.value.toUpperCase() })} required placeholder="GB0NV05E" autoCapitalize="characters" />
          </Field>
          {config.api_enabled ? (
            <p className="pay-info small">送出後會向 DUPR 取得您的姓名與最新單打、雙打分數。</p>
          ) : (
            <>
              <div className="grid2">
                <Field label="雙打分數"><input className="input" type="number" step="0.001" min="1" max="8" value={form.doubles} onChange={(e) => setForm({ ...form, doubles: e.target.value })} placeholder="3.500" /></Field>
                <Field label="單打分數"><input className="input" type="number" step="0.001" min="1" max="8" value={form.singles} onChange={(e) => setForm({ ...form, singles: e.target.value })} placeholder="沒有請留空" /></Field>
              </div>
              <p className="alert warn small">請填寫 DUPR App 上顯示的分數，場館會核對您的 DUPR 帳號與分數。</p>
            </>
          )}
          <label className="check small"><input type="checkbox" checked={form.optin} onChange={(e) => setForm({ ...form, optin: e.target.checked })} /> {DUPR_OPTIN_TEXT}</label>
          <div className="row gap">
            {user.dupr_id && <button type="button" className="btn btn-light flex1" onClick={() => setEditing(false)}>取消</button>}
            <button className="btn flex1" disabled={busy}>{busy ? '處理中…' : '綁定'}</button>
          </div>
        </form>
      )}
    </>
  )
}

// DUPR 官方登入（SSO）：DUPR 規定球員只能這樣連結帳號，不能手動輸入 ID
function DuprSso({ config, user, status, ents, busy, run }) {
  const { refreshUser, handleError, showToast } = useApp()
  const [open, setOpen] = useState(false)
  const [optin, setOptin] = useState(!!user.dupr_optin)
  const [saving, setSaving] = useState(false)
  const legacy = user.dupr_id && user.dupr_source !== 'sso'

  useEffect(() => {
    if (!open) return
    const onMessage = async (e) => {
      if (e.origin !== config.sso_origin) return
      let d = e.data
      if (typeof d === 'string') { try { d = JSON.parse(d) } catch { return } }
      if (d?.error === 'consent_denied') { setOpen(false); showToast('您沒有同意授權，尚未綁定 DUPR'); return }
      const token = d?.userToken || d?.accessToken
      if (!token) return  // DUPR 頁面也會送其他訊息（例如操作紀錄），只處理登入結果
      setOpen(false)
      setSaving(true)
      try {
        await api('me/dupr/sso', { method: 'POST', body: { userToken: token, refreshToken: d.refreshToken || '', optin } })
        await refreshUser()
        showToast('已用 DUPR 帳號綁定')
      } catch (err) { handleError(err) } finally { setSaving(false) }
    }
    window.addEventListener('message', onMessage)
    return () => window.removeEventListener('message', onMessage)
  }, [open, optin, config.sso_origin, refreshUser, handleError, showToast])

  return (
    <>
      {user.dupr_id && !legacy ? (
        <section className="card dupr-card">
          <div className="row between">
            <b className="big">DUPR 帳號</b>
            <span className="row gap-sm">{ents.includes('PREMIUM_L1') && <Badge tone="dupr">DUPR+</Badge>}<Badge tone={status[1]}>{status[0]}</Badge></span>
          </div>
          <p className="muted small">DUPR ID：<b className="text-brand">{user.dupr_id}</b>{user.dupr_name && ` · ${user.dupr_name}`}</p>
          <div className="stats stats-2">
            <div className="stat"><span>雙打分數</span><b>{rating(user.dupr_doubles)}</b></div>
            <div className="stat"><span>單打分數</span><b>{rating(user.dupr_singles)}</b></div>
          </div>
          {!ents.includes('BASIC_L1') && <p className="alert warn small">DUPR 顯示您的帳號目前不能參加計分比賽，或授權已失效。請按「重新登入 DUPR」，若仍無法使用請到 DUPR App 確認帳號狀態。</p>}
          <p className="muted small">更新時間 {showDateTime(user.dupr_synced_at)}</p>
          <div className="admin-actions">
            <button className="btn btn-small" disabled={busy} onClick={() => run(() => api('me/dupr/refresh', { method: 'POST' }), '已從 DUPR 更新')}>從 DUPR 更新</button>
            <button className="btn btn-small btn-light" onClick={() => setOpen(true)}>重新登入 DUPR</button>
            <button className="btn btn-small btn-light text-danger" disabled={busy} onClick={() => run(() => api('me/dupr', { method: 'PUT', body: { dupr_id: '' } }), '已解除綁定')}>解除綁定</button>
          </div>
        </section>
      ) : (
        <section className="card form">
          <h3 className="card-title nomargin">綁定 DUPR 帳號</h3>
          {legacy && <p className="alert warn small">您之前手動填的 DUPR ID（{user.dupr_id}）已停用。DUPR 規定要用 DUPR 帳號登入綁定，綁好才能報名 DUPR 場。</p>}
          <p className="muted small">用您的 DUPR 帳號登入並同意授權，系統會自動取得 DUPR ID 與最新分數。還沒有 DUPR 帳號可以在登入畫面直接註冊。</p>
          <label className="check small"><input type="checkbox" checked={optin} onChange={(e) => setOptin(e.target.checked)} /> {DUPR_OPTIN_TEXT}</label>
          <button className="btn btn-block" disabled={saving} onClick={() => setOpen(true)}>{saving ? '綁定中…' : '用 DUPR 帳號登入'}</button>
        </section>
      )}
      {user.dupr_id && !legacy && <DuprOptin />}
      <SupportContact topic="dupr" />
      {open && (
        <Modal onClose={() => setOpen(false)}>
          <div className="dupr-sso">
            <iframe src={config.sso_url} title="DUPR 登入" allow="payment" />
          </div>
          <button className="btn btn-block btn-light" onClick={() => setOpen(false)}>取消</button>
        </Modal>
      )}
    </>
  )
}

const DUPR_OPTIN_TEXT = '我同意 Digital Court 將我的 Email 提供給 DUPR，用來寄送 DUPR 的賽事與推廣資訊（可隨時取消）'

// 是否同意 DUPR 寄推廣資訊：預設不勾，球友自己決定；取消後不再列入提供給 DUPR 的名單
function DuprOptin() {
  const { user, refreshUser, handleError, showToast } = useApp()
  const [busy, setBusy] = useState(false)
  const toggle = async (e) => {
    const optin = e.target.checked
    setBusy(true)
    try {
      await api('me/dupr/optin', { method: 'PUT', body: { optin } })
      await refreshUser()
      showToast(optin ? '已同意接收 DUPR 資訊' : '已取消，之後不會再提供您的 Email 給 DUPR')
    } catch (err) { handleError(err) } finally { setBusy(false) }
  }
  return (
    <section className="card form">
      <h3 className="card-title nomargin">DUPR 最新消息</h3>
      <label className="check small"><input type="checkbox" checked={!!user.dupr_optin} disabled={busy} onChange={toggle} /> {DUPR_OPTIN_TEXT}</label>
      {!!user.dupr_optin && !user.email && <p className="alert warn small">您的帳號還沒有 Email，DUPR 無法寄信給您。請到「帳號」分頁填寫信箱。</p>}
      {!!user.dupr_optin && user.dupr_optin_at && <p className="muted small">同意時間 {showDateTime(user.dupr_optin_at)}</p>}
      <p className="muted small">我們每季會把同意者的 Email 提供給 DUPR；已提供出去的名單由 DUPR 依其隱私權政策處理，退訂也可以直接點 DUPR 信件裡的取消訂閱。</p>
    </section>
  )
}

// 出席紀錄：目前計入的缺席次數、規則、每筆缺席
function Attendance() {
  const { venue, handleError } = useApp()
  const [d, setD] = useState(null)
  useEffect(() => { api('me/attendance').then(setD).catch(handleError) }, [handleError])
  if (!d) return <Loading />
  const s = d.status
  return (
    <>
      <section className="card">
        <div className="sec-head"><h3>缺席次數</h3>{s.enabled && <span>{s.days ? `最近 ${s.days} 天` : '累計'}</span>}</div>
        {!s.enabled ? <p className="muted small">這個場館沒有缺席限制。</p> : s.blocked ? (
          <p className="text-warn strong">暫停報名中，{blockUntil(s)}（{s.reason}）</p>
        ) : (
          <>
            <div className="noshow-meter" aria-label={`缺席 ${s.count} 次，上限 ${s.limit} 次`}>
              {Array.from({ length: s.limit }, (_, i) => <span key={i} className={i < s.count ? 'on' : ''} />)}
            </div>
            <p className="small">{s.count === 0 ? '目前沒有缺席，繼續保持！' : s.count >= s.limit - 1 ? <b className="text-warn">已缺席 {s.count} 次，再 1 次會暫停報名</b> : `已缺席 ${s.count} 次，滿 ${s.limit} 次會暫停報名`}</p>
          </>
        )}
        {noshowRule(venue) && <p className="muted small mt">{noshowRule(venue)}</p>}
      </section>
      <section className="card">
        <h3 className="card-title">缺席紀錄</h3>
        {d.absences.length === 0 ? <p className="muted small">沒有缺席紀錄</p> : d.absences.map((a) => (
          <div key={a.id} className="row between list-row">
            <span className={`small ${a.noshow_cleared ? 'muted' : ''}`}><b>{showDate(a.date).slice(5)} {a.start_time}</b> {a.name}</span>
            {a.noshow_cleared === 1 ? <Badge tone="gray">主辦免記</Badge> : a.noshow_cleared === 2 ? <Badge tone="gray">已計入暫停</Badge> : <Badge tone="warn">計入</Badge>}
          </div>
        ))}
      </section>
    </>
  )
}
