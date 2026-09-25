import { Link, Navigate, NavLink, Outlet } from 'react-router-dom'
import { useApp } from '../../App'

const TABS = [
  ['/admin', '總覽'],
  ['/admin/courses', '課程'],
  ['/admin/orders', '訂單'],
  ['/admin/members', '會員'],
  ['/admin/plans', '課卡方案'],
  ['/admin/teachers', '老師'],
  ['/admin/reviews', '評價'],
  ['/admin/settings', '場館設定'],
]

export default function AdminLayout() {
  const { user, venue } = useApp()
  if (!user) return <Navigate to="/login" replace state={{ from: '/admin' }} />
  if (user.role !== 'owner') return <Navigate to="/" replace />
  return (
    <>
      <header className="admin-head">
        <div>
          <p className="admin-kicker">場主後台</p>
          <h1 className="admin-title">{venue?.name}</h1>
        </div>
        <Link to="/" className="btn btn-small btn-ghost-light">查看前台 ›</Link>
      </header>
      <nav className="tabs tabs-scroll">
        {TABS.map(([to, label]) => (
          <NavLink key={to} to={to} end={to === '/admin'} className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>{label}</NavLink>
        ))}
      </nav>
      <main className="page">
        <Outlet />
      </main>
    </>
  )
}
