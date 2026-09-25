import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { asset } from '../api'

export function Modal({ onClose, children }) {
  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" role="dialog" aria-modal="true" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" aria-label="關閉" onClick={onClose}>×</button>
        {children}
      </div>
    </div>
  )
}

export function Confirm({ title, text, okText = '確定', danger, onOk, onClose, children }) {
  return (
    <Modal onClose={onClose}>
      {title && <h3 className="dialog-title">{title}</h3>}
      {text && <p className="dialog-text">{text}</p>}
      {children}
      <div className="row gap">
        <button className="btn btn-light flex1" onClick={onClose}>取消</button>
        <button className={`btn flex1 ${danger ? 'btn-danger' : ''}`} onClick={onOk}>{okText}</button>
      </div>
    </Modal>
  )
}

export function TopBar({ title, back = -1, right }) {
  const navigate = useNavigate()
  return (
    <header className="topbar">
      <button className="icon-btn" aria-label="返回" onClick={() => navigate(back)}>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none"><path d="M15 5l-7 7 7 7" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </button>
      <h1 className="topbar-title">{title}</h1>
      <div className="topbar-right">{right}</div>
    </header>
  )
}

export function Avatar({ src, name, size = 44 }) {
  return (
    <div className="avatar" style={{ width: size, height: size, fontSize: size * 0.42 }}>
      {src ? <img src={asset(src)} alt={name} /> : <span>{(name || '?').slice(0, 1)}</span>}
    </div>
  )
}

export function Stars({ value = 0, size = 14, onChange }) {
  return (
    <span className="stars" style={{ fontSize: size }}>
      {[1, 2, 3, 4, 5].map((n) => (
        <span
          key={n}
          className={n <= Math.round(value) ? 'on' : ''}
          onClick={onChange ? () => onChange(n) : undefined}
          role={onChange ? 'button' : undefined}
          aria-label={onChange ? `${n} 顆星` : undefined}
        >★</span>
      ))}
    </span>
  )
}

export function RatingPill({ rating, count }) {
  return (
    <div className="rating-line">
      <span className="rating-pill">{rating ?? '—'}</span>
      <span className="muted small">{count || 0} 則評價</span>
    </div>
  )
}

export function Loading({ text = '載入中' }) {
  return (
    <div className="empty">
      <div className="spinner" />
      <p>{text}</p>
    </div>
  )
}

export function Empty({ text, children }) {
  return (
    <div className="empty">
      <svg width="96" height="96" viewBox="0 0 96 96" fill="none" aria-hidden="true">
        <rect x="18" y="22" width="60" height="56" rx="10" fill="var(--brand-soft)" />
        <rect x="18" y="22" width="60" height="14" rx="7" fill="var(--brand-200)" />
        <circle cx="34" cy="18" r="4" fill="var(--brand)" /><circle cx="62" cy="18" r="4" fill="var(--brand)" />
        <path d="M36 56h24M36 64h14" stroke="var(--brand-300)" strokeWidth="4" strokeLinecap="round" />
      </svg>
      <p>{text}</p>
      {children}
    </div>
  )
}

export function Chips({ options, value, onChange }) {
  return (
    <div className="chips">
      {options.map(([v, label]) => (
        <button key={v} className={`chip ${value === v ? 'active' : ''}`} onClick={() => onChange(v)}>{label}</button>
      ))}
    </div>
  )
}

export function Field({ label, hint, children }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
      {hint && <span className="field-hint">{hint}</span>}
    </label>
  )
}

export function Badge({ tone = 'brand', children }) {
  return <span className={`badge badge-${tone}`}>{children}</span>
}
