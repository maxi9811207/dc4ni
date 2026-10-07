import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api, downloadFile } from '../../api'
import EventBoard, { ScoreModal } from '../../components/EventBoard'
import { AvatarImg, Badge, Confirm, Empty, Field, Loading } from '../../components/ui'
import { rating, showDate } from '../../util'

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
const MIN = { rotating: 4, fixed: 2, singles: 2 }

export default function EventAdmin() {
  const { id } = useParams()
  const { handleError, showToast } = useApp()
  const [d, setD] = useState(null)
  const [groups, setGroups] = useState(null)
  const [picked, setPicked] = useState(null)
  const [busy, setBusy] = useState(false)
  const [scoring, setScoring] = useState(null)
  const [deleting, setDeleting] = useState(false)
  const [withdrawing, setWithdrawing] = useState(null)

  const load = useCallback(() => api(`admin/courses/${id}/event`).then((r) => {
    setD(r)
    setGroups(r.plan)
    setPicked(null)
  }).catch(handleError), [id, handleError])
  useEffect(() => { load() }, [load])

  if (!d) return <Loading />
  const c = d.course
  const people = Object.fromEntries(d.players.map((p) => [p.id, p]))
  const unit = d.format === 'fixed' ? '隊' : '人'

  // 點兩位球員互換位置（跨組、跨隊都可以）
  const pick = (gi, ei, pi) => {
    if (!picked) return setPicked([gi, ei, pi])
    const [g2, e2, p2] = picked
    setPicked(null)
    if (g2 === gi && e2 === ei && p2 === pi) return
    const next = groups.map((g) => g.map((e) => [...e]))
    const t = next[gi][ei][pi]
    next[gi][ei][pi] = next[g2][e2][p2]
    next[g2][e2][p2] = t
    setGroups(next)
  }
  const moveEntry = (gi, ei, to) => {
    const next = groups.map((g) => g.map((e) => [...e]))
    const [entry] = next[gi].splice(ei, 1)
    if (to === next.length) next.push([])
    next[to].push(entry)
    setGroups(next.filter((g) => g.length))
    setPicked(null)
  }
  const generate = async () => {
    setBusy(true)
    try {
      const r = await api(`admin/courses/${id}/event`, { method: 'POST', body: { groups } })
      setD({ ...r, plan: null })
      showToast('賽事已生成，已通知所有球員')
    } catch (e) { handleError(e) } finally { setBusy(false) }
  }
  const saveScore = async (a, b) => {
    try {
      await api(`admin/event-games/${scoring.id}`, { method: 'PUT', body: { score_a: a, score_b: b } })
      setScoring(null)
      showToast('比分已登錄')
      load()
    } catch (e) { handleError(e) }
  }
  const clearScore = async () => {
    try {
      await api(`admin/event-games/${scoring.id}`, { method: 'PUT', body: { clear: true } })
      setScoring(null)
      load()
    } catch (e) { handleError(e) }
  }

  return (
    <>
      <section className="card">
        <Link to={`/admin/courses/${c.id}`} className="muted small">‹ 回名單</Link>
        <h2 className="detail-title">{c.name}</h2>
        <p className="course-meta"><b className="course-time">{showDate(c.date)} {c.start_time}~{c.end_time}</b> · {d.format_name} · 每局打到 {c.games_to} 分</p>
        <p className="muted small">報名 {d.players.length} 人{d.event && ` · 已確認 ${d.event.progress.confirmed} / ${d.event.progress.total} 局`}</p>
        {d.dupr?.enabled && d.dupr.counts.ready + d.dupr.counts.stale > 0 && (
          <button className="btn btn-small" onClick={() => document.getElementById('dupr-review')?.scrollIntoView({ behavior: 'smooth' })}>
            {d.dupr.counts.ready + d.dupr.counts.stale} 局可以上傳 DUPR，前往審核
          </button>
        )}
      </section>

      {d.event ? (
        <>
          <EventBoard event={d.event} mode="owner" onScore={setScoring} dupr={d.dupr} onWithdraw={setWithdrawing} />
          {d.dupr?.enabled && <DuprReview courseId={id} review={d.dupr} onDone={(r) => setD({ ...r, plan: null })} />}
          <button className="btn btn-block btn-light" onClick={() => downloadFile(`admin/courses/${id}/event/export`, `比分_${c.date}_${c.name}.csv`).catch(handleError)}>下載比分（CSV，可整理後上傳 DUPR）</button>
          <button className="btn btn-block btn-light text-danger" onClick={() => setDeleting(true)}>刪除賽事，重新分組</button>
        </>
      ) : d.plan_error ? (
        <Empty text={d.plan_error}><p className="muted small">可以到名單「代為預約」補人，或調整名額後再回來生成。</p></Empty>
      ) : groups && (
        <>
          <section className="card">
            <h3 className="card-title nomargin">建議分組</h3>
            <p className="muted small">依 DUPR {c.dupr_format === 'singles' ? '單打' : '雙打'}分數由高到低分組。點兩位球員可以互換位置{d.format !== 'fixed' && '，也可以把人移到別組'}；確認後按「生成賽事」。每組至少 {MIN[d.format]} {unit}{d.format === 'rotating' && '、最多 7 人'}。</p>
          </section>
          {groups.map((g, gi) => {
            const bad = g.length < MIN[d.format] || (d.format === 'rotating' && g.length > 7)
            return (
              <section key={gi} className={`card plan-group ${bad ? 'bad' : ''}`}>
                <div className="row between">
                  <b>{LETTERS[gi]} 組</b>
                  <span className={`small ${bad ? 'text-danger' : 'muted'}`}>{g.length} {unit}</span>
                </div>
                {g.map((e, ei) => (
                  <div key={ei} className="plan-entry">
                    {d.format === 'fixed' && <span className="muted small">第 {ei + 1} 隊</span>}
                    <div className="plan-players">
                      {e.map((pid, pi) => {
                        const p = people[pid]
                        const on = picked && picked[0] === gi && picked[1] === ei && picked[2] === pi
                        return (
                          <button key={pid} type="button" className={`plan-player ${on ? 'picked' : ''}`} onClick={() => pick(gi, ei, pi)}>
                            <span className="player-avatar"><AvatarImg src={p?.avatar_url} name={p?.name} /></span>
                            <span className="flex1">{p?.name}</span>
                            <span className="small muted">{rating(p?.rating)}{p?.dupr_verified ? ' ✓' : ''}</span>
                          </button>
                        )
                      })}
                    </div>
                    {d.format !== 'fixed' && (
                      <select className="input input-small" value={gi} onChange={(ev) => moveEntry(gi, ei, Number(ev.target.value))} aria-label="移到">
                        {groups.map((_, i) => <option key={i} value={i}>{LETTERS[i]} 組</option>)}
                        <option value={groups.length}>新的一組</option>
                      </select>
                    )}
                  </div>
                ))}
              </section>
            )
          })}
          <div className="row gap">
            <button className="btn btn-light flex1" onClick={load}>還原建議分組</button>
            <button className="btn flex1" disabled={busy} onClick={generate}>{busy ? '生成中…' : '生成賽事'}</button>
          </div>
        </>
      )}

      {scoring && (
        <ScoreModal game={scoring} gamesTo={d.event.games_to} owner uploaded={!!d.dupr?.games?.[scoring.id]?.code} onClose={() => setScoring(null)} onSave={saveScore}
          onClear={scoring.score_a != null ? clearScore : null} />
      )}
      {withdrawing && (
        <Confirm title={`從 DUPR 撤回第 ${withdrawing.round} 局？`} danger okText="撤回" onClose={() => setWithdrawing(null)}
          text="DUPR 會刪除這局並還原它對球員分數的影響。這裡的比分會保留，修改後可以再重新上傳。"
          onOk={async () => {
            try {
              const r = await api(`admin/event-games/${withdrawing.id}/dupr`, { method: 'DELETE' })
              setD({ ...r, plan: null }); setWithdrawing(null); showToast('已從 DUPR 撤回')
            } catch (e) { handleError(e) }
          }} />
      )}
      {deleting && (
        <Confirm title="刪除賽事？" danger okText="刪除" onClose={() => setDeleting(false)}
          text="所有分組與比分都會刪除，之後可以重新分組生成。"
          onOk={async () => {
            try { await api(`admin/courses/${id}/event`, { method: 'DELETE' }); setDeleting(false); showToast('已刪除賽事'); load() } catch (e) { handleError(e) }
          }} />
      )}
    </>
  )
}

// 場主審核：核對比分與每位球員的 DUPR ID，選比賽類型後上傳；改過比分的一併同步
function DuprReview({ courseId, review, onDone }) {
  const { handleError, showToast } = useApp()
  const [form, setForm] = useState({ play_type: review.play_type, match_type: review.match_type })
  const [checked, setChecked] = useState(false)
  const [busy, setBusy] = useState(false)
  const n = review.counts
  const todo = n.ready + n.stale
  const missing = review.players.filter((p) => !p.dupr_id)
  const unchecked = review.players.filter((p) => p.dupr_id && !p.checked)

  const upload = async () => {
    setBusy(true)
    try {
      const r = await api(`admin/courses/${courseId}/event/dupr`, { method: 'POST', body: form })
      const x = r.result
      const parts = [x.created && `新上傳 ${x.created} 局`, x.updated && `同步 ${x.updated} 局`].filter(Boolean)
      showToast(x.error ? `${parts.join('、') || '沒有成功的'}，${x.error} 局失敗（原因標在該局）` : `已${parts.join('、')}`)
      setChecked(false)
      onDone(r)
    } catch (e) { handleError(e) } finally { setBusy(false) }
  }

  return (
    <section className="card form dupr-review" id="dupr-review">
      <div className="row between">
        <h3 className="card-title nomargin">審核並上傳 DUPR</h3>
        <span className="badge badge-dupr">DUPR</span>
      </div>
      <div className="stats stats-3">
        <div className="stat"><span>已上傳</span><b>{n.uploaded}</b></div>
        <div className="stat"><span>可上傳{n.stale ? `／待同步` : ''}</span><b>{n.ready}{n.stale ? ` / ${n.stale}` : ''}</b></div>
        <div className="stat"><span>比分未確認</span><b>{n.waiting}</b></div>
      </div>
      {n.waiting > 0 && <p className="muted small">還有 {n.waiting} 局比分沒確認，確認後才能上傳（可以先上傳已確認的）。</p>}

      <div>
        <p className="field-label">核對球員的 DUPR ID</p>
        {missing.length > 0 && <p className="alert danger small">{missing.map((p) => p.name).join('、')} 還沒綁 DUPR，他們的比賽無法上傳。請對方到會員中心綁定。</p>}
        <ul className="dupr-players">
          {review.players.map((p) => (
            <li key={p.id} className="row between">
              <span>{p.name}{p.dupr_name && p.dupr_name !== p.name && <span className="muted small">（DUPR：{p.dupr_name}）</span>}</span>
              <span className="row gap-sm">
                {p.dupr_id ? <code className="small">{p.dupr_id}</code> : <Badge tone="danger">未綁定</Badge>}
                {p.dupr_id && review.sso && !p.sso && <Badge tone="danger">需用 DUPR 登入綁定</Badge>}
                {p.dupr_id && !review.sso && !p.checked && <Badge tone="warn">未核對</Badge>}
              </span>
            </li>
          ))}
        </ul>
        {!review.sso && unchecked.length > 0 && <p className="muted small">「未核對」是球友自己填的 DUPR ID，上傳前請確認是本人，填錯會記到別人的 DUPR 上。</p>}
      </div>

      <div className="grid2">
        <Field label="比賽類型">
          <select className="input" value={form.play_type} onChange={(e) => setForm({ ...form, play_type: e.target.value })}>
            {Object.entries(review.play_types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
        <Field label="計分制">
          <select className="input" value={form.match_type} onChange={(e) => setForm({ ...form, match_type: e.target.value })}>
            {Object.entries(review.match_types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
          </select>
        </Field>
      </div>
      {todo > 0 ? (
        <>
          <label className="check small"><input type="checkbox" checked={checked} onChange={(e) => setChecked(e.target.checked)} /> 我已核對比分與每位球員的 DUPR ID，資料正確</label>
          <button className="btn btn-block" disabled={!checked || busy} onClick={upload}>
            {busy ? '上傳中…' : `上傳 ${todo} 局到 DUPR${n.stale ? `（含同步 ${n.stale} 局修改）` : ''}`}
          </button>
        </>
      ) : n.uploaded > 0 && n.waiting === 0 && n.blocked === 0 ? (
        <p className="alert info small">全部比賽都已上傳 DUPR。之後如果修改比分，記得回來同步。</p>
      ) : null}
    </section>
  )
}
