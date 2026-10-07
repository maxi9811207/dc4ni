import { useApp } from '../App'

// 比分有爭議時找得到主辦（DUPR 規定：球員要有明確的客服管道）
export default function SupportContact({ topic = 'match' }) {
  const { venue } = useApp()
  const ways = [
    venue?.line_url && { href: venue.line_url, label: '用 LINE 聯絡主辦', external: true },
    venue?.phone && { href: `tel:${venue.phone}`, label: `致電 ${venue.phone}` },
  ].filter(Boolean)
  if (!ways.length) return null
  return (
    <section className="card support-contact">
      <b className="small">{topic === 'match' ? '比分有問題？' : '需要協助？'}</b>
      <p className="muted small">
        {topic === 'match'
          ? '比分登錄錯誤、對手沒回報，或已上傳 DUPR 的成績有爭議，請聯絡主辦處理。'
          : 'DUPR 綁定或分數有問題，請聯絡主辦。'}
      </p>
      <div className="admin-actions">
        {ways.map((w) => (
          <a key={w.label} className="btn btn-small btn-light" href={w.href}
            {...(w.external ? { target: '_blank', rel: 'noreferrer' } : {})}>{w.label}</a>
        ))}
      </div>
    </section>
  )
}
