import { Stars } from './ui'

export default function ReviewItem({ r }) {
  return (
    <div className="card review">
      <div className="row between">
        <div className="row gap-sm">
          <b className="rating-num">{r.rating}</b>
          <Stars value={r.rating} />
          <span className="strong">{r.user_name}</span>
        </div>
        <span className="muted small">{r.created_at.slice(0, 10).replaceAll('-', '/')}</span>
      </div>
      {r.course_name && <p className="muted small">{r.course_name}{r.teacher_name && ` · ${r.teacher_name}`}</p>}
      {r.comment && <p className="pre">{r.comment}</p>}
    </div>
  )
}
