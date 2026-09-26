import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import CourseCard from '../../components/CourseCard'
import { Empty, Loading } from '../../components/ui'
import { money, showDate, today } from '../../util'

export default function Dashboard() {
  const { handleError } = useApp()
  const [d, setD] = useState(null)
  useEffect(() => { api('admin/dashboard').then(setD).catch(handleError) }, [handleError])
  if (!d) return <Loading />
  return (
    <>
      <div className="stats">
        <Link to="/admin/orders" className={`stat ${d.pending_orders ? 'alert-stat' : ''}`}><span>待確認訂單</span><b>{d.pending_orders}</b></Link>
        <div className="stat"><span>本月營收</span><b>{money(d.month_revenue)}</b>{d.unpaid_fees > 0 && <small className="stat-sub text-warn">{d.unpaid_fees} 筆報名費待收</small>}</div>
        <div className="stat"><span>7 日內預約</span><b>{d.week_bookings}</b></div>
        <Link to="/admin/members" className="stat"><span>學生人數</span><b>{d.members}</b></Link>
      </div>
      <div className="row between section-head">
        <h3 className="date-title">今日課程 · {showDate(today())}</h3>
        <Link to="/admin/courses/new" className="btn btn-small">＋ 新增課程</Link>
      </div>
      {d.today.length === 0 ? <Empty text="今天沒有課程" />
        : d.today.map((c) => <CourseCard key={c.id} course={{ ...c, button: '名單', state: 'booked' }} to={`/admin/courses/${c.id}`} />)}
    </>
  )
}
