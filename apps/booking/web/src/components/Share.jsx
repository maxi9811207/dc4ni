import { useEffect, useState } from 'react'
import { useApp } from '../App'
import { BASE, api } from '../api'
import { showDate } from '../util'

// 活動的分享網址：/e/<代碼> 由後端產生 LINE／FB 預覽，再轉到一頁式活動頁
export function shareUrl(code) {
  return `${BASE}${code}`
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

// 後台用：顯示連結、複製、LINE 分享、自訂網址（saveUrl：PUT 的 API 路徑）
export function ShareBox({ c, saveUrl, onSaved }) {
  const { showToast, handleError } = useApp()
  const url = shareUrl(c.share_code)
  const [editing, setEditing] = useState(false)
  const [code, setCode] = useState(c.share_code)
  const save = async (e) => {
    e.preventDefault()
    if (!/^[a-z0-9]{4,18}$/.test(code)) return showToast('自訂網址只能用英文或數字，長度 4～18 碼')
    try {
      await api(saveUrl, { method: 'PUT', body: { share_code: code } })
      showToast('已更新網址，舊網址也還打得開')
      setEditing(false)
      onSaved?.()
    } catch (err) { handleError(err) }
  }
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
        {saveUrl && !editing && <button type="button" className="btn btn-small btn-light" onClick={() => { setCode(c.share_code); setEditing(true) }}>自訂網址</button>}
      </div>
      {editing && (
        <form className="form mt" onSubmit={save}>
          <div className="url-input">
            <span>{BASE.replace(/^https?:\/\//, '')}</span>
            <input className="input" value={code} autoFocus autoCapitalize="off" spellCheck={false}
              onChange={(e) => setCode(e.target.value.replace(/[^a-zA-Z0-9]/g, '').slice(0, 18).toLowerCase())} />
          </div>
          <p className="field-hint">4～18 碼英文或數字；改了之後舊網址還是打得開</p>
          <div className="row gap">
            <button type="button" className="btn btn-small btn-light" onClick={() => setEditing(false)}>取消</button>
            <button className="btn btn-small" disabled={code === c.share_code || code.length < 4}>儲存</button>
          </div>
        </form>
      )}
    </section>
  )
}

// 活動頁的網址列只顯示分享連結 <網站>/<代碼>（不帶 #/course/…），從網址列複製出去也有 LINE 預覽、不公開的活動也打得開。
// 畫面仍由 hash 路由控制：原本的 hash 記在 history.state.__hash，按返回鍵回到這頁時由 main.jsx 接回；離開活動頁恢復原路徑。
export function useShareAddress(code, inApp = true) {
  useEffect(() => {
    if (!code) return undefined
    if (inApp) markInApp(code)
    const replace = (url, extra = {}) => {
      try { window.history.replaceState({ ...(window.history.state || {}), ...extra }, '', url) } catch { /* 部分內嵌瀏覽器不允許 */ }
    }
    replace(`${BASE}${code}`, { __hash: window.location.hash || window.history.state?.__hash || '' })
    return () => {
      const hash = window.location.hash || window.history.state?.__hash || ''
      replace(BASE + hash, { __hash: undefined })
    }
  }, [code])
}

// 從前台點進活動頁時記下來：重新整理（伺服器會轉到 /e/<代碼>）後仍顯示返回箭頭與前台版面；
// 別人第一次從分享連結打開則是一頁式活動頁
const IN_APP_KEY = 'booking-in-app-events'

function markInApp(code) {
  try {
    const list = JSON.parse(sessionStorage.getItem(IN_APP_KEY) || '[]').filter((x) => x !== code)
    sessionStorage.setItem(IN_APP_KEY, JSON.stringify([...list, code].slice(-50)))
  } catch { /* 無痕模式等情況 */ }
}

export function openedInApp(code) {
  try { return JSON.parse(sessionStorage.getItem(IN_APP_KEY) || '[]').includes(code) } catch { return false }
}
