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
  return v === null || v === undefined ? 'NR' : Number(v).toFixed(3)
}

// 例：DUPR 雙打 3.000–4.000
export function duprRange(c, short = false) {
  const fmt = c.dupr_format === 'singles' ? '單打' : '雙打'
  const lo = c.dupr_min != null ? Number(c.dupr_min).toFixed(short ? 1 : 3) : ''
  const hi = c.dupr_max != null ? Number(c.dupr_max).toFixed(short ? 1 : 3) : ''
  const range = lo && hi ? `${lo}–${hi}` : lo ? `${lo}+` : hi ? `≤${hi}` : '不限分數'
  return short ? `DUPR ${range}` : `DUPR ${fmt} ${range}`
}
