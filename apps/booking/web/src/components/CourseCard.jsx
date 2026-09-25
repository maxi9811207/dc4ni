import { Link } from 'react-router-dom'
import { Avatar, AvatarStack } from './ui'
import { duprRange } from '../util'

const BUTTON_CLASS = {
  book: 'btn',
  waitlist: 'btn btn-warn',
  booked: 'btn btn-outline',
  waiting: 'btn btn-outline-warn',
  disabled: 'btn btn-muted',
}

export function countInfo(c, showCount) {
  if (!['book', 'booked', 'waitlist', 'waiting'].includes(c.state)) return ''
  if (showCount) return `${c.booked_count} / ${c.capacity}`
  if (c.remain > 0 && c.remain <= 5) return `剩餘 ${c.remain} 位`
  return ''
}

export default function CourseCard({ course: c, showCount = true, showDate, to }) {
  const info = countInfo(c, showCount)
  return (
    <Link to={to || `/course/${c.id}`} className="card course-card">
      <Avatar src={c.teacher?.photo_url} name={c.teacher?.name} />
      <div className="course-main">
        <h2 className="course-name">
          {c.name}
          {c.dupr_required && <span className="badge badge-dupr">{duprRange(c, true)}</span>}
          {c.beginner && <span className="badge badge-danger">新手友善</span>}
        </h2>
        <p className="course-meta">
          <b className="course-time">
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" aria-hidden="true"><circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.4" /><path d="M12 7v5l3 2" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" /></svg>
            {showDate && `${c.date.slice(5).replace('-', '/')}(${c.weekday}) `}{c.start_time}~{c.end_time}
          </b>
          {c.category && <span> · {c.category}</span>}
        </p>
        <div className="course-foot">
          {c.attendees?.length > 0 && <AvatarStack people={c.attendees.slice(0, 4)} total={c.booked_count} size={22} />}
          <span className="course-teacher">{c.teacher?.name || '未指定老師'}{c.substitute && ' (代課)'}</span>
          {info && <span className="course-count">{info}</span>}
          <span className={`${BUTTON_CLASS[c.state]} btn-small`}>{c.button}</span>
        </div>
      </div>
    </Link>
  )
}
