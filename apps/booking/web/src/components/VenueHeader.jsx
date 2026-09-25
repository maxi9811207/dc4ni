import { NavLink, useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import { asset } from '../api'
import { AvatarImg, RatingPill } from './ui'

const TABS = [
  ['/', '課程預約'],
  ['/teachers', '師資陣容'],
  ['/plans', '課卡方案'],
  ['/about', '關於場館'],
]

export default function VenueHeader() {
  const { venue, user } = useApp()
  const navigate = useNavigate()
  return (
    <>
      <div className="cover">
        {venue?.cover_url
          ? <img src={asset(venue.cover_url)} alt={venue.name} />
          : <div className="cover-placeholder"><span>{(venue?.name || '約').slice(0, 1)}</span></div>}
        <button
          className="member-btn"
          aria-label={user ? '會員中心' : '登入/註冊'}
          onClick={() => navigate(user ? '/me' : '/login')}
        >
          {user
            ? <span className="member-initial"><AvatarImg src={user.avatar_url} name={user.name} />{user.unread > 0 && <i className="dot" />}</span>
            : <span className="member-login">登入/註冊</span>}
        </button>
      </div>
      <div className="venue-head">
        <h1 className="venue-name">{venue?.name}</h1>
        <RatingPill rating={venue?.rating} count={venue?.review_count} />
      </div>
      <nav className="tabs">
        {TABS.map(([to, label]) => (
          <NavLink key={to} to={to} end className={({ isActive }) => `tab ${isActive ? 'active' : ''}`}>{label}</NavLink>
        ))}
      </nav>
    </>
  )
}
