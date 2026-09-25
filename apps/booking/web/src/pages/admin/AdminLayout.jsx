import { useEffect, useState } from 'react'
import { Link, Navigate, NavLink, Outlet, useLocation } from 'react-router-dom'
import { useApp } from '../../App'

const I = {
  dashboard: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  attendance: 'M9 11l2 2 4-4M5 4h14v16H5z',
  calendar: 'M4 6h16v14H4zM4 10h16M8 3v4M16 3v4',
  courses: 'M4 5h16v11H4zM8 20h8M12 16v4',
  plans: 'M3 7h18v10H3zM3 11h18',
  members: 'M16 20v-2a4 4 0 0 0-8 0v2M12 12a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7z',
  teachers: 'M9 11a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM3 20v-1a5 5 0 0 1 10 0v1M16 5a3 3 0 0 1 0 6M21 20v-1a5 5 0 0 0-3-4.6',
  orders: 'M12 3v18M16 7H10a2.5 2.5 0 0 0 0 5h4a2.5 2.5 0 0 1 0 5H7',
  reports: 'M3 3v18h18M7 15l4-4 3 3 5-6',
  reviews: 'M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1-4.4-4.3 6.1-.9z',
  settings: 'M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6zM19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-2.9 1.2V21a2 2 0 1 1-4 0v-.1a1.7 1.7 0 0 0-2.9-1.2l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1A1.7 1.7 0 0 0 3 14H3a2 2 0 1 1 0-4h.1a1.7 1.7 0 0 0 1.2-2.9l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1A1.7 1.7 0 0 0 10 3.1V3a2 2 0 1 1 4 0v.1a1.7 1.7 0 0 0 2.9 1.2l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0 1.2 2.9h.1a2 2 0 1 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z',
}

export const MENU = [
  { title: '', items: [
    ['/admin', '營運總覽', 'dashboard'],
    ['/admin/attendance', '出席管理', 'attendance'],
    ['/admin/calendar', '課表行事曆', 'calendar'],
    ['/admin/templates', '課程管理', 'courses'],
    ['/admin/plans', '課卡方案', 'plans'],
    ['/admin/members', '會員管理', 'members'],
    ['/admin/teachers', '師資團隊', 'teachers'],
    ['/admin/orders', '付款審核', 'orders'],
    ['/admin/reports', '分析與報表', 'reports'],
    ['/admin/reviews', '評價管理', 'reviews'],
  ] },
  { title: '系統設定', items: [
    ['/admin/settings', '場館設定', 'settings'],
  ] },
]

function Icon({ name }) {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={I[name]} />
    </svg>
  )
}

function pageTitle(pathname) {
  if (pathname === '/admin/notifications') return '通知'
  if (/^\/admin\/courses\/new/.test(pathname)) return '新增課程'
  if (/^\/admin\/courses\/\d+\/edit/.test(pathname)) return '編輯課程'
  if (/^\/admin\/courses\/\d+/.test(pathname)) return '名單點名'
  if (pathname === '/admin/courses') return '課程管理'
  if (pathname === '/admin/templates/new') return '新增課程範本'
  if (/^\/admin\/templates\/\d+/.test(pathname)) return '編輯課程範本'
  const item = MENU.flatMap((g) => g.items).filter(([to]) => pathname === to || pathname.startsWith(to + '/'))
    .sort((a, b) => b[0].length - a[0].length)[0]
  return item ? item[1] : '場主後台'
}

export default function AdminLayout() {
  const { user, venue, refreshUser } = useApp()
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  useEffect(() => { setOpen(false); refreshUser() }, [pathname, refreshUser])
  // 定期更新通知數量
  useEffect(() => {
    const t = setInterval(() => refreshUser(), 60000)
    return () => clearInterval(t)
  }, [refreshUser])

  if (!user) return <Navigate to="/login" replace state={{ from: pathname }} />
  if (user.role !== 'owner') return <Navigate to="/" replace />
  const unread = user.admin_unread || 0

  return (
    <>
      <header className="admin-bar">
        <button className="icon-btn" aria-label="選單" onClick={() => setOpen(true)}>
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><path d="M4 6h16M4 12h16M4 18h16" /></svg>
        </button>
        <div className="admin-bar-title">
          <span className="admin-kicker">{venue?.name}</span>
          <b>{pageTitle(pathname)}</b>
        </div>
        <Link to="/admin/notifications" className="icon-btn bell" aria-label={`通知，${unread} 則未讀`}>
          <svg width="23" height="23" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" strokeLinejoin="round"><path d="M18 8a6 6 0 1 0-12 0c0 7-3 9-3 9h18s-3-2-3-9M13.7 21a2 2 0 0 1-3.4 0" /></svg>
          {unread > 0 && <span className="bell-count">{unread > 9 ? '9+' : unread}</span>}
        </Link>
      </header>

      {open && <div className="drawer-backdrop" onClick={() => setOpen(false)} />}
      <aside className={`drawer ${open ? 'open' : ''}`} aria-hidden={!open}>
        <div className="drawer-head">
          <p className="drawer-venue">{venue?.name}</p>
          <p className="drawer-user">{user.name}</p>
        </div>
        <nav>
          {MENU.map((g) => (
            <div key={g.title || 'main'}>
              {g.title && <p className="drawer-group">{g.title}</p>}
              {g.items.map(([to, label, icon]) => (
                <NavLink key={to} to={to} end={to === '/admin'} className={({ isActive }) => `drawer-link ${isActive ? 'active' : ''}`}>
                  <Icon name={icon} />{label}
                </NavLink>
              ))}
            </div>
          ))}
          <Link to="/" className="drawer-link drawer-front">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round"><path d="M15 3h6v6M10 14L21 3M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" /></svg>
            查看前台
          </Link>
        </nav>
      </aside>

      <main className="page">
        <Outlet />
      </main>
    </>
  )
}
