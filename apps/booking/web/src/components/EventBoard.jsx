import { useState } from 'react'
import { AvatarImg, Badge, Chips, Modal } from './ui'

const STATUS = { pending: ['未打', 'gray'], reported: ['待確認', 'warn'], confirmed: ['已確認', 'success'] }

export function Names({ people, me }) {
  return people.map((p, i) => (
    <span key={p.id} className={`player ${p.id === me ? 'me' : ''}`}>
      {i > 0 && <span className="muted"> / </span>}
      <span className="player-avatar"><AvatarImg src={p.avatar_url} name={p.name} /></span>
      {p.name}
    </span>
  ))
}

// 賽事看板：各組排名＋對戰；mode = player（球員回報／確認）或 owner（團主登錄比分）
export default function EventBoard({ event, me, mode = 'player', onScore, onConfirm }) {
  const mineGroup = event.groups.findIndex((g) => g.entries.some((e) => e.some((p) => p.id === me)))
  const [tab, setTab] = useState(mineGroup >= 0 ? mineGroup : 0)
  const [onlyMine, setOnlyMine] = useState(mode === 'player' && mineGroup >= 0)
  const group = event.groups[tab] || event.groups[0]
  const games = onlyMine ? group.games.filter((g) => g.mine) : group.games
  // 球員最需要的一件事：我的下一局（要確認的優先，其次是還沒打的）
  const myGames = mode === 'player' ? event.groups.flatMap((g) => g.games.filter((x) => x.mine)) : []
  const next = myGames.find((g) => g.can_confirm) || myGames.find((g) => g.status === 'pending') || myGames.find((g) => g.status === 'reported')

  return (
    <div className="event-board">
      {next && (
        <section className="card next-game">
          <div className="row between">
            <b>{next.can_confirm ? '請確認比分' : next.status === 'pending' ? `你的下一局：第 ${next.round} 局` : `第 ${next.round} 局等待對手確認`}</b>
            <span className="muted small">{myGames.filter((g) => g.status === 'confirmed').length} / {myGames.length} 局完成</span>
          </div>
          <p className="next-vs"><Names people={next.a} me={me} /> <span className="muted">vs</span> <Names people={next.b} me={me} /></p>
          {next.score_a != null && <p className="small">回報比分 <b>{next.score_a} : {next.score_b}</b>{next.reported_by && `（${next.reported_by}）`}</p>}
          <div className="admin-actions">
            {next.can_confirm && <button className="btn" onClick={() => onConfirm(next)}>比分正確，確認</button>}
            {next.can_report && <button className={`btn ${next.can_confirm ? 'btn-light' : ''}`} onClick={() => onScore(next)}>{next.status === 'pending' ? '打完了，回報比分' : next.can_confirm ? '比分不對，改報' : '修改回報'}</button>}
          </div>
        </section>
      )}
      {event.groups.length > 1 && (
        <Chips options={event.groups.map((g, i) => [i, `${g.name}${i === mineGroup ? '（我）' : ''}`])} value={tab} onChange={(v) => { setTab(v); setOnlyMine(v === mineGroup && mode === 'player') }} />
      )}

      <section className="card">
        <div className="row between">
          <h3 className="card-title nomargin">{group.name} 排名</h3>
          <span className="muted small">只計已確認的比分</span>
        </div>
        <table className="standings">
          <thead><tr><th>#</th><th className="left">{event.format === 'fixed' ? '隊伍' : '球員'}</th><th>勝</th><th>負</th><th>得失分</th></tr></thead>
          <tbody>
            {group.standings.map((r) => (
              <tr key={r.players.map((p) => p.id).join('-')} className={r.players.some((p) => p.id === me) ? 'me' : ''}>
                <td>{r.rank}</td>
                <td className="left"><Names people={r.players} me={me} /></td>
                <td>{r.won}</td>
                <td>{r.lost}</td>
                <td className={r.diff > 0 ? 'text-success' : r.diff < 0 ? 'text-danger' : ''}>{r.diff > 0 ? `+${r.diff}` : r.diff}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="row between section-head">
        <h3 className="date-title">對戰</h3>
        {mode === 'player' && tab === mineGroup && (
          <button className="btn btn-small btn-light" onClick={() => setOnlyMine(!onlyMine)}>{onlyMine ? '看全部' : '只看我的'}</button>
        )}
      </div>
      {games.map((g) => {
        const [label, tone] = STATUS[g.status]
        const won = g.score_a != null ? (g.score_a > g.score_b ? 'a' : 'b') : null
        return (
          <section key={g.id} className={`card game-card ${g.mine ? 'mine' : ''}`}>
            <div className="row between">
              <b className="small">第 {g.round} 局</b>
              <Badge tone={tone}>{label}</Badge>
            </div>
            <div className="game-sides">
              <div className={`game-side ${won === 'a' ? 'won' : ''}`}>
                <div className="game-names"><Names people={g.a} me={me} /></div>
                <b className="game-score">{g.score_a ?? '–'}</b>
              </div>
              <div className={`game-side ${won === 'b' ? 'won' : ''}`}>
                <div className="game-names"><Names people={g.b} me={me} /></div>
                <b className="game-score">{g.score_b ?? '–'}</b>
              </div>
            </div>
            {g.bye.length > 0 && <p className="muted small">輪空：{g.bye.map((p) => p.name).join('、')}</p>}
            {g.status === 'reported' && g.reported_by && <p className="muted small">{g.reported_by} 回報，等待對手確認</p>}
            <div className="admin-actions">
              {mode === 'owner' && <button className="btn btn-small" onClick={() => onScore(g)}>{g.score_a == null ? '登錄比分' : '修改比分'}</button>}
              {mode === 'player' && g.can_confirm && <button className="btn btn-small" onClick={() => onConfirm(g)}>確認比分</button>}
              {mode === 'player' && g.can_report && (
                <button className="btn btn-small btn-light" onClick={() => onScore(g)}>{g.status === 'pending' ? '回報比分' : g.can_confirm ? '比分有誤，改報' : '修改回報'}</button>
              )}
            </div>
          </section>
        )
      })}
      {games.length === 0 && <p className="muted center small">這組沒有您的比賽</p>}
    </div>
  )
}

export function ScoreModal({ game, gamesTo, owner, onClose, onSave, onClear }) {
  const [a, setA] = useState(game.score_a ?? '')
  const [b, setB] = useState(game.score_b ?? '')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  // 和伺服器同一套規則：打到 N 分、領先 2 分（團主登錄只擋平手）
  const problem = () => {
    const x = Number(a), y = Number(b), hi = Math.max(x, y), lo = Math.min(x, y)
    if (a === '' || b === '') return '請填寫雙方分數'
    if (x === y) return '比分不能平手'
    if (owner) return ''
    if (hi < gamesTo) return `勝方要打到 ${gamesTo} 分`
    if (hi - lo < 2 || (hi > gamesTo && hi - lo !== 2)) return `要領先 2 分才算贏（例如 ${gamesTo}:${gamesTo - 2}、${gamesTo + 1}:${gamesTo - 1}）`
    return ''
  }
  const submit = async (e) => {
    e.preventDefault()
    const p = problem()
    if (p) return setErr(p)
    setBusy(true)
    try { await onSave(Number(a), Number(b)) } finally { setBusy(false) }
  }
  return (
    <Modal onClose={onClose}>
      <form className="form" onSubmit={submit}>
        <h3 className="dialog-title">第 {game.round} 局比分</h3>
        <p className="muted center small">打到 {gamesTo} 分、領先 2 分獲勝{owner ? '（團主登錄後直接確認）' : '；送出後由對手確認'}</p>
        {[['a', a, setA], ['b', b, setB]].map(([side, v, set]) => (
          <label key={side} className="score-row">
            <span className="flex1"><Names people={game[side]} /></span>
            <input className="input score-input" type="number" inputMode="numeric" min="0" max="99" required value={v} onChange={(e) => { setErr(''); set(e.target.value) }} aria-label="分數" />
          </label>
        ))}
        {err && <p className="alert danger small" role="alert">{err}</p>}
        <div className="row gap">
          <button type="button" className="btn btn-light flex1" onClick={onClose}>取消</button>
          <button className="btn flex1" disabled={busy}>{busy ? '送出中…' : '送出'}</button>
        </div>
        {onClear && <button type="button" className="btn btn-block btn-light text-danger" onClick={onClear}>清除這局比分</button>}
      </form>
    </Modal>
  )
}
