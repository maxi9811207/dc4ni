const WEEKDAYS = ['日', '一', '二', '三', '四', '五', '六']

export function toISO(d) {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

export function fromISO(s) {
  const [y, m, d] = s.split('-').map(Number)
  return new Date(y, m - 1, d)
}

export function addDays(iso, n) {
  const d = fromISO(iso)
  d.setDate(d.getDate() + n)
  return toISO(d)
}

export function today() {
  return toISO(new Date())
}

// 該日所在週的週一
export function mondayOf(iso) {
  const d = fromISO(iso)
  const offset = (d.getDay() + 6) % 7
  d.setDate(d.getDate() - offset)
  return toISO(d)
}

export function weekdayOf(iso) {
  return WEEKDAYS[fromISO(iso).getDay()]
}

export function showDate(iso) {
  return `${iso.replaceAll('-', '/')}(${weekdayOf(iso)})`
}

export function showDateTime(ts) {
  if (!ts) return ''
  return ts.slice(0, 16).replace('T', ' ').replaceAll('-', '/')
}

export const PLAN_TYPES = {
  points: '點數課卡',
  sessions: '堂數課卡',
  unlimited: '無限課卡',
  fee: '單次報名費',
}

export function planAmount(p) {
  if (p.type === 'unlimited') return `${p.valid_days} 天無限次`
  if (p.type === 'points') return `${p.quantity} 點`
  return `${p.quantity} 堂`
}

export function cardRemain(c) {
  if (c.type === 'unlimited') return '無限次'
  if (c.type === 'points') return `剩 ${c.remaining} / ${c.total} 點`
  return `剩 ${c.remaining} / ${c.total} 堂`
}

export function money(n) {
  return 'NT$ ' + Number(n || 0).toLocaleString()
}

export function hours(min) {
  const h = min / 60
  return Number.isInteger(h) ? `${h} 小時` : `${min} 分鐘`
}

export function rating(v) {
  return v === null || v === undefined ? '尚無分數' : Number(v).toFixed(3)
}

// 例：DUPR 雙打 3.000–4.000
export function duprRange(c, short = false) {
  const fmt = c.dupr_format === 'singles' ? '單打' : '雙打'
  const lo = c.dupr_min != null ? Number(c.dupr_min).toFixed(short ? 1 : 3) : ''
  const hi = c.dupr_max != null ? Number(c.dupr_max).toFixed(short ? 1 : 3) : ''
  const range = lo && hi ? `${lo}–${hi}` : lo ? `${lo}+` : hi ? `≤${hi}` : '不限分數'
  return short ? `DUPR ${range}` : `DUPR ${fmt} ${range}`
}

// 點名標記缺席後給場主的提示（到上限已自動暫停／差 1 次）
export function noshowMessage(ns, name) {
  if (!ns) return ''
  if (ns.blocked) return `${name} ${ns.reason}，已自動暫停報名${ns.forever ? '直到您解除' : `到 ${ns.blocked_until.slice(5).replace('-', '/')}`}，已通知他`
  if (ns.limit && ns.count === ns.limit - 1) return `${name} 已缺席 ${ns.count} 次，再 1 次會暫停報名（已提醒他）`
  return ''
}

// 缺席規則（報名須知、會員中心用）；沒開啟回傳空字串
export function noshowRule(v) {
  if (!v || v.noshow_enabled === false) return ''
  const period = Number(v.noshow_days) ? `最近 ${v.noshow_days} 天內` : '累計'
  const length = Number(v.noshow_block_days) ? ` ${v.noshow_block_days} 天` : '，直到主辦解除'
  return `報名後沒到會記一次缺席；${period}缺席 ${v.noshow_limit} 次會暫停報名${length}。不能來請提早取消。`
}

export function blockUntil(ns) {
  return ns.forever ? '直到主辦解除' : `到 ${ns.blocked_until.slice(5).replace('-', '/')}`
}

// 平台方案：目前場館能用哪些功能（沒有平台資訊時＝單場館安裝，全部可用）
export const PLAN_NAMES = { lite: '輕量', standard: '標準', pro: '專業', advanced: '進階', enterprise: '企業' }
export const FEATURE_NAMES = {
  fee: '收費對帳', cards: '課卡方案', reminder: '開課前一天提醒', noshow: '缺席管理',
  push: 'LINE 推播通知', export: '名單下載 Excel', dupr: 'DUPR 活動', slots: '時段預約', reports: '營收與出席報表',
  staff: '多位管理員與教練帳號', domain: '自訂網域', multisite: '多館管理', support: '優先客服與協助搬家', app: '場館專屬 App',
}
export function planOf(venue) {
  const p = venue?.platform
  const has = (f) => !p || p.features.includes(f)
  const needs = (f) => PLAN_NAMES[p?.feature_plans?.[f] || 'standard']
  return { ...(p || {}), has, needs, paused: p && ['suspended', 'cancelled'].includes(p.status) }
}
