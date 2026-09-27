import { useEffect } from 'react'
import { useApp } from '../App'
import { BASE } from '../api'
import { showDate } from '../util'

// 活動的分享網址：/e/<代碼> 由後端產生 LINE／FB 預覽，再轉到一頁式活動頁
export function shareUrl(code) {
  return `${BASE}e/${code}`
}

function shareText(c) {
  if (c.kind === 'slots') return `${c.name}\n線上選時段預約${c.location ? `｜${c.location}` : ''}`
  return `${c.name}\n${showDate(c.date)} ${c.start_time}~${c.end_time}${c.location ? `｜${c.location}` : ''}`
}

async function copy(text) {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    // 舊版瀏覽器、非 https 等情況
    const el = document.createElement('textarea')
    el.value = text
    document.body.appendChild(el)
    el.select()
    const ok = document.execCommand('copy')
    el.remove()
    return ok
  }
}

// 分享按鈕（手機叫出系統分享選單，電腦直接複製連結）
export function ShareButton({ c, className = 'btn btn-small btn-light' }) {
  const { showToast } = useApp()
  const url = shareUrl(c.share_code)
  const onClick = async () => {
    if (navigator.share) {
      try { await navigator.share({ title: c.name, text: shareText(c), url }); return } catch (e) { if (e?.name === 'AbortError') return }
    }
    showToast(await copy(url) ? '已複製活動連結' : url)
  }
  return <button type="button" className={className} onClick={onClick}>分享</button>
}

// 後台用：顯示連結、複製、LINE 分享
export function ShareBox({ c }) {
  const { showToast } = useApp()
  const url = shareUrl(c.share_code)
  return (
    <section className="card share-box">
      <div className="row between">
        <h3 className="card-title nomargin">報名連結</h3>
        {!c.listed && <span className="badge badge-warn">只限連結</span>}
      </div>
      <p className="muted small">{c.listed ? '這場也會出現在課表上；' : '這場不會出現在課表，只有拿到連結的人看得到；'}學員打開連結就能直接登入、報名。</p>
      <div className="share-url">
        <input className="input" readOnly value={url} onFocus={(e) => e.target.select()} />
      </div>
      <div className="admin-actions">
        <button type="button" className="btn btn-small" onClick={async () => showToast(await copy(url) ? '已複製連結' : '複製失敗，請長按連結手動複製')}>複製連結</button>
        <a className="btn btn-small btn-line" href={`https://line.me/R/share?text=${encodeURIComponent(`${shareText(c)}\n${url}`)}`} target="_blank" rel="noreferrer">分享到 LINE</a>
        <a className="btn btn-small btn-light" href={`${BASE}#/e/${c.share_code}`} target="_blank" rel="noreferrer">預覽報名頁</a>
      </div>
    </section>
  )
}

// 活動頁的網址列直接顯示分享連結（/e/<代碼>），從網址列複製出去也有 LINE 預覽、不公開的活動也打得開；
// 畫面仍由 hash 路由控制，離開活動頁時網址列恢復原本的路徑
export function useShareAddress(code) {
  useEffect(() => {
    if (!code) return undefined
    const set = (path) => {
      try { window.history.replaceState(window.history.state, '', path + window.location.hash) } catch { /* 部分內嵌瀏覽器不允許 */ }
    }
    set(`${BASE}e/${code}`)
    return () => set(BASE)
  }, [code])
}
