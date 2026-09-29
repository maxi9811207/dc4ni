import { useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api, BASE, getToken } from '../../api'
import BarChart from '../../components/BarChart'
import { Chips, Empty, Field, Loading } from '../../components/ui'
import { addDays, money, PLAN_TYPES, toISO, today } from '../../util'

function range(kind) {
  const t = today()
  const d = new Date()
  if (kind === 'month') return [toISO(new Date(d.getFullYear(), d.getMonth(), 1)), t]
  if (kind === 'last') return [toISO(new Date(d.getFullYear(), d.getMonth() - 1, 1)), toISO(new Date(d.getFullYear(), d.getMonth(), 0))]
  return [addDays(t, -(Number(kind) - 1)), t]
}

const pct = (v) => (v == null ? '—' : `${v}%`)

export default function Reports() {
  const { handleError, showToast } = useApp()
  const [kind, setKind] = useState('month')
  const [custom, setCustom] = useState(range('30'))
  const [data, setData] = useState(null)
  const [downloading, setDownloading] = useState(false)
  const [from, to] = kind === 'custom' ? custom : range(kind)

  useEffect(() => {
    setData(null)
    api(`admin/reports?from=${from}&to=${to}`).then(setData).catch(handleError)
  }, [from, to, handleError])

  const download = async () => {
    setDownloading(true)
    try {
      const res = await fetch(`${BASE}api/admin/reports/export?from=${from}&to=${to}`, { headers: { Authorization: `Bearer ${getToken()}` } })
      if (!res.ok) throw new Error((await res.json().catch(() => ({}))).error || '匯出失敗')
      const url = URL.createObjectURL(await res.blob())
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${from}_${to}.xlsx`
      document.body.appendChild(a)
      a.click()
      a.remove()
      setTimeout(() => URL.revokeObjectURL(url), 1000)
      showToast('已下載 Excel 報表')
    } catch (e) { handleError(e) } finally { setDownloading(false) }
  }

  return (
    <>
      <Chips value={kind} onChange={setKind} options={[['month', '本月'], ['last', '上月'], ['30', '近 30 天'], ['90', '近 90 天'], ['custom', '自訂']]} />
      {kind === 'custom' && (
        <div className="grid2">
          <Field label="從"><input className="input" type="date" value={custom[0]} max={custom[1]} onChange={(e) => setCustom([e.target.value, custom[1]])} /></Field>
          <Field label="到"><input className="input" type="date" value={custom[1]} min={custom[0]} onChange={(e) => setCustom([custom[0], e.target.value])} /></Field>
        </div>
      )}
      <div className="row between">
        <span className="muted small">{from.replaceAll('-', '/')} ～ {to.replaceAll('-', '/')}</span>
        <button className="btn btn-small" disabled={downloading || !data} onClick={download}>{downloading ? '匯出中…' : '⬇ 匯出 Excel'}</button>
      </div>
      {!data ? <Loading /> : <Body d={data} />}
    </>
  )
}

function Body({ d }) {
  const { revenue: rev, classes: cls, cards, members } = d
  return (
    <>
      <div className="stats">
        <div className="stat"><span>營收</span><b>{money(rev.total)}</b><em>{rev.orders} 筆收款</em></div>
        <div className="stat"><span>預約人次</span><b>{cls.booked}</b><em>{cls.sessions} 堂課</em></div>
        <div className="stat"><span>滿班率</span><b>{pct(cls.fill_rate)}</b><em>名額 {cls.capacity}</em></div>
        <div className="stat"><span>出席率</span><b>{pct(cls.attendance_rate)}</b><em>缺席 {cls.absent}</em></div>
        <div className="stat"><span>上課會員</span><b>{members.active}</b><em>新會員 {members.new}</em></div>
        <div className="stat"><span>取消預約</span><b>{cls.cancellations}</b><em>停課 {cls.cancelled_sessions} 堂</em></div>
      </div>

      <section className="card">
        <h3 className="card-title">每日營收</h3>
        {rev.total ? <BarChart data={rev.daily} format={(v) => `$${v.toLocaleString()}`} label="每日營收" /> : <p className="muted small">這段期間沒有收款</p>}
      </section>
      <section className="card">
        <h3 className="card-title">每日預約人次</h3>
        {cls.booked ? <BarChart data={cls.daily} format={(v) => `${v} 人`} label="每日預約人次" /> : <p className="muted small">這段期間沒有預約</p>}
      </section>

      <section className="card">
        <h3 className="card-title">課卡銷售</h3>
        {rev.by_plan.length === 0 ? <p className="muted small">沒有銷售</p> : (
          <Table head={['方案／活動', '筆數', '金額']} rows={rev.by_plan.map((p) => [p.name, p.count, money(p.amount)])} />
        )}
        <div className="stats stats-3 mt">
          <div className="stat"><span>消耗堂數</span><b>{cards.consumed.sessions}</b></div>
          <div className="stat"><span>消耗點數</span><b>{cards.consumed.points}</b></div>
          <div className="stat"><span>無限卡上課</span><b>{cards.consumed.unlimited}</b></div>
        </div>
        <p className="muted small mt">
          目前學員手上未使用：
          {Object.keys(cards.outstanding).length === 0 ? '無' : Object.entries(cards.outstanding).map(([k, v]) =>
            k === 'unlimited' ? `${PLAN_TYPES[k]} ${v.cards} 張` : `${PLAN_TYPES[k]} ${v.remaining} ${k === 'points' ? '點' : '堂'}`).join('、')}
          {cards.manual_grants > 0 && `；期間內場主手動開通 ${cards.manual_grants} 張`}
        </p>
      </section>

      <section className="card">
        <h3 className="card-title">課程排行</h3>
        {d.courses.length === 0 ? <Empty text="這段期間沒有課程" /> : (
          <Table head={['課程', '堂數', '預約', '滿班率']} rows={d.courses.map((c) => [c.name, c.sessions, c.booked, <Meter key={c.name} v={c.fill_rate} />])} />
        )}
      </section>

      <section className="card">
        <h3 className="card-title">老師授課（鐘點計算）</h3>
        {d.teachers.length === 0 ? <p className="muted small">沒有授課紀錄</p> : (
          <Table head={['老師', '堂數', '時數', '學員人次']} rows={d.teachers.map((t) => [t.name, t.sessions, `${t.hours} 小時`, t.booked])} />
        )}
      </section>

      <section className="card">
        <h3 className="card-title">最常上課的會員</h3>
        {members.top.length === 0 ? <p className="muted small">沒有上課紀錄</p> : (
          <Table head={['會員', '預約', '出席', '缺席']} rows={members.top.map((m) => [m.name, m.booked, m.attended, m.absent])} />
        )}
      </section>
      <p className="muted small center">營收以「確認收款」的時間計算；上課數據以課程日期計算，不含停課。</p>
    </>
  )
}

function Table({ head, rows }) {
  const cols = { gridTemplateColumns: `minmax(0, 1fr) repeat(${head.length - 1}, auto)` }
  return (
    <div className="report-table">
      <div className="report-tr head" style={cols}>{head.map((h) => <span key={h}>{h}</span>)}</div>
      {rows.map((r, i) => <div key={i} className="report-tr" style={cols}>{r.map((c, j) => <span key={j}>{c}</span>)}</div>)}
    </div>
  )
}

function Meter({ v }) {
  return (
    <span className="meter-cell">
      <span className="meter-track"><span className="meter-fill" style={{ width: `${Math.min(v || 0, 100)}%` }} /></span>
      <span>{pct(v)}</span>
    </span>
  )
}
