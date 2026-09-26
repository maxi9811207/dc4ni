import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import EventBoard, { ScoreModal } from '../../components/EventBoard'
import { AvatarImg, Confirm, Empty, Loading } from '../../components/ui'
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
      </section>

      {d.event ? (
        <>
          <EventBoard event={d.event} mode="owner" onScore={setScoring} />
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
        <ScoreModal game={scoring} gamesTo={d.event.games_to} owner onClose={() => setScoring(null)} onSave={saveScore}
          onClear={scoring.score_a != null ? clearScore : null} />
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
