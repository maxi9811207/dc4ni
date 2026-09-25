import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Badge, Empty, Loading, Stars } from '../../components/ui'

export default function AdminReviews() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const load = useCallback(() => api('admin/reviews').then(setList).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

  const toggle = async (r) => {
    try {
      await api(`admin/reviews/${r.id}`, { method: 'PUT', body: { hidden: !r.hidden } })
      showToast(r.hidden ? '已重新顯示' : '已隱藏')
      load()
    } catch (e) { handleError(e) }
  }

  if (!list) return <Loading />
  const avg = list.length ? (list.reduce((s, r) => s + r.rating, 0) / list.length).toFixed(1) : '—'
  return (
    <>
      <div className="card row gap">
        <span className="big-rating">{avg}</span>
        <div><Stars value={Number(avg) || 0} size={18} /><p className="muted small">共 {list.length} 則評價（含已隱藏）</p></div>
      </div>
      {list.length === 0 ? <Empty text="還沒有評價" /> : list.map((r) => (
        <div key={r.id} className={`card review ${r.hidden ? 'dim' : ''}`}>
          <div className="row between">
            <div className="row gap-sm"><Stars value={r.rating} /><b>{r.user_name}</b>{r.hidden ? <Badge tone="gray">已隱藏</Badge> : null}</div>
            <span className="muted small">{r.created_at.slice(0, 10)}</span>
          </div>
          <p className="muted small">{r.course_name} {r.course_date}{r.teacher_name && ` · ${r.teacher_name}`}</p>
          {r.comment && <p className="pre">{r.comment}</p>}
          <div className="admin-actions">
            <button className="btn btn-small btn-light" onClick={() => toggle(r)}>{r.hidden ? '重新顯示' : '隱藏此評價'}</button>
          </div>
        </div>
      ))}
    </>
  )
}
