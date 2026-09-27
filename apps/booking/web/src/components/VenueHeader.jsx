import { NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import { AvatarImg } from './ui'

const TABS = [
  ['/', '課程報名'],
  ['/teachers', '師資陣容'],
  ['/plans', '課卡方案'],
  ['/about', '關於場館'],
]

// 副標：地址裡的行政區＋評價（沒有就不顯示）
export function venueSubtitle(venue) {
  const parts = []
  const area = venue?.address?.match(/[^\s\d市縣]{1,3}[區鄉鎮]/)?.[0]
  if (area) parts.push(area)
  if (venue?.review_count > 0) parts.push(`★ ${venue.rating} · ${venue.review_count} 則評價`)
  return parts.join(' · ')
}

export function VenueAvatar({ venue }) {
  return (
    <span className="vbar-avatar">
      <AvatarImg src={venue?.cover_url} name={venue?.name || '約'} />
    </span>
  )
}

export default function VenueHeader() {
  const { venue, user } = useApp()
  const navigate = useNavigate()
  const sub = venueSubtitle(venue)
  return (
    <header className="vhead">
      <div className="vbar">
        <VenueAvatar venue={venue} />
        <div className="vbar-text">
          <h1 className="vbar-name">{venue?.name}</h1>
          {sub && <p className="vbar-sub">{sub}</p>}
        </div>
        <button
          className="member-btn"
          aria-label={user ? '會員中心' : '登入/註冊'}
          onClick={() => navigate(user ? '/me' : '/login')}
        >
          {user
            ? <span className="member-initial"><AvatarImg src={user.avatar_url} name={user.name} />{user.unread > 0 && <i className="dot" />}</span>
            : <span className="member-login">登入</span>}
        </button>
      </div>
      <nav className="tabs">
        {TABS.map(([to, label]) => (
          <NavLink key={to} to={to} end className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>{label}</NavLink>
        ))}
      </nav>
    </header>
  )
}
