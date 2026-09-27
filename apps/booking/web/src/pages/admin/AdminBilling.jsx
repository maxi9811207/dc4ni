import { useApp } from '../../App'
import { Badge } from '../../components/ui'
import { FEATURE_NAMES, PLAN_NAMES, planOf } from '../../util'

const STATUS = {
  active: ['使用中', 'success'], past_due: ['扣款失敗（寬限期）', 'warn'], suspended: ['已暫停', 'danger'], cancelled: ['已停止', 'gray'],
}
const ORDER = ['basic', 'standard', 'advanced']
const PRICE = { basic: [490, 5390], standard: [1500, 16500], advanced: [4900, 53900] }
const PLAN_FEATURES = {
  basic: ['建立、查看單次活動', '球友線上報名、額滿候補'],
  standard: ['基本方案全部功能', '收費對帳（匯款回填後五碼）', '課卡方案', 'LINE 推播、開課前一天提醒', '缺席管理', '名單下載 Excel'],
  advanced: ['標準方案全部功能', 'DUPR 活動（分組、記分、匯出）', '時段預約（私人課、場地租借）', '營收與出席報表', '自訂網域'],
}

function day(iso) {
  return iso ? iso.slice(0, 10).replaceAll('-', '/') : ''
}

// 場館後台「方案與帳單」：目前方案、狀態、各方案差異；付款與變更方案在平台帳號頁（Polar 顧客入口）
export default function AdminBilling() {
  const { venue } = useApp()
  const p = planOf(venue)
  if (!venue?.platform) return <section className="card"><p className="muted">這個場館沒有連結平台訂閱。</p></section>
  const [label, tone] = STATUS[p.status] || [p.status, 'gray']
  return (
    <>
      <section className="card">
        <div className="row between">
          <h3 className="card-title nomargin">目前方案：{p.plan_name}方案</h3>
          <Badge tone={tone}>{label}</Badge>
        </div>
        {p.comp ? <p className="muted small mt">這個場館由 Digital Court 提供，不需付費。</p> : (
          <p className="small mt">
            {p.billing_cycle === 'year' ? '年繳' : '月繳'} NT$ {PRICE[p.plan]?.[p.billing_cycle === 'year' ? 1 : 0].toLocaleString()}
            {p.period_end && (p.cancel_at_period_end ? `・將於 ${day(p.period_end)} 停止` : `・下次扣款 ${day(p.period_end)}`)}
          </p>
        )}
        {p.status === 'past_due' && <p className="alert warn small mt">這期扣款沒有成功，請在 {day(p.grace_until)} 前更新付款方式，逾期場館會暫停服務。</p>}
        {p.paused && <p className="alert danger small mt">場館目前暫停服務：球友不能報名，後台只能查看與匯出。續訂後馬上恢復，資料都還在。</p>}
        {!p.comp && <a className="btn btn-block mt" href={p.account_url} target="_blank" rel="noreferrer">{p.paused ? '續訂' : '管理訂閱（升級、付款方式、收據）'}</a>}
      </section>

      <div className="plan-compare">
        {ORDER.map((k) => (
          <section key={k} className={`card plan-col ${k === p.plan ? 'on' : ''}`}>
            <div className="row between"><b>{PLAN_NAMES[k]}</b>{k === p.plan && <Badge tone="success">目前方案</Badge>}</div>
            <p className="plan-price">NT$ {PRICE[k][0].toLocaleString()}<span>／月</span></p>
            <p className="muted small">年繳 NT$ {PRICE[k][1].toLocaleString()}（送一個月）</p>
            <ul>{PLAN_FEATURES[k].map((f) => <li key={f}>{f}</li>)}</ul>
          </section>
        ))}
      </div>
      <section className="card">
        <h3 className="card-title">目前可用的功能</h3>
        <div className="feature-list">
          {Object.entries(FEATURE_NAMES).map(([k, n]) => (
            <span key={k} className={p.has(k) ? 'ok' : 'off'}>{p.has(k) ? '✓' : '🔒'} {n}{!p.has(k) && `（${p.needs(k)}方案）`}</span>
          ))}
        </div>
      </section>
    </>
  )
}
