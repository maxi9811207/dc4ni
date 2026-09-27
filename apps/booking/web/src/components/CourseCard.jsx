import { Link } from 'react-router-dom'
import { useApp } from '../App'
import { Avatar, AvatarStack } from './ui'
import { duprRange } from '../util'

function duration(c) {
  const [h1, m1] = c.start_time.split(':').map(Number)
  const [h2, m2] = c.end_time.split(':').map(Number)
  const min = h2 * 60 + m2 - (h1 * 60 + m1)
  if (min <= 0) return ''
  return min % 60 === 0 ? `${min / 60} 小時` : min > 60 ? `${(min / 60).toFixed(1)} 小時` : `${min} 分鐘`
}

// 右側名額標籤：大字是名額或狀態，小字是下一步提示
export function capInfo(c, showCount, admin) {
  const count = `${c.booked_count}/${c.capacity}`
  if (admin) return { tone: c.remain <= 0 ? 'full' : c.remain <= 3 ? 'near' : '', big: count, small: '名單 ›' }
  switch (c.state) {
    case 'booked': return { tone: 'mine', big: '已報名', small: showCount ? count : '' }
    case 'waiting': return { tone: 'wait', big: '候補中', small: c.waitlist_position ? `第 ${c.waitlist_position} 位` : '' }
    case 'waitlist': return { tone: 'full', big: showCount ? count : '額滿', small: '可候補' }
    case 'book':
      return {
        tone: c.remain <= 3 ? 'near' : '',
        big: showCount ? count : c.remain <= 5 ? `剩 ${c.remain}` : '可報名',
        small: showCount ? `剩 ${c.remain}` : c.remain <= 5 ? '名額' : '',
      }
    default: return { tone: 'full', big: c.button, small: '' }
  }
}

export default function CourseCard({ course: c, showCount = true, showDate, to, admin }) {
  const { venue } = useApp()
  const cap = capInfo(c, showCount, admin)
  const org = c.teacher?.name ? `${c.teacher.name}${c.substitute ? '（代課）' : ''}` : venue?.name || ''
  const dur = duration(c)
  const chips = [
    showDate && `${c.date.slice(5).replace('-', '/')}（${c.weekday}）`,
    dur ? `${dur} · 到 ${c.end_time}` : `到 ${c.end_time}`,
    c.category && c.category !== 'DUPR 場' && c.category,
    c.location,
    c.fee > 0 && `NT$ ${c.fee.toLocaleString()}`,
  ].filter(Boolean)
  return (
    <Link to={to || `/course/${c.id}`} className="card ccard">
      <Avatar src={c.teacher?.photo_url} name={org} size={34} />
      <div className="ccard-main">
        {org && <p className="ccard-org">{org}</p>}
        <h2 className="ccard-title"><time>{c.start_time}</time>{c.name}</h2>
        <div className="ccard-chips">
          {c.dupr_required && <span className="cchip dupr">{duprRange(c, true)}</span>}
          {c.beginner && <span className="cchip beginner">新手友善</span>}
          {chips.map((t, i) => <span key={i} className="cchip">{t}</span>)}
        </div>
        {c.attendees?.length > 0 && (
          <div className="ccard-people">
            <AvatarStack people={c.attendees.slice(0, 5)} total={c.booked_count} size={20} />
            {(showCount || admin) && <span>{c.booked_count} 位球友報名</span>}
          </div>
        )}
      </div>
      <div className={`cap ${cap.tone}`}>
        <b>{cap.big}</b>
        {cap.small && <small>{cap.small}</small>}
      </div>
    </Link>
  )
}
