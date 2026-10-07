import { api } from './api'

// 只有在 LINE App 內開啟時才載入 LIFF SDK；一般瀏覽器不受影響
export async function liffLogin(liffId) {
  if (!/Line\//i.test(navigator.userAgent)) return null
  await new Promise((resolve, reject) => {
    const s = document.createElement('script')
    s.src = 'https://static.line-scdn.net/liff/edge/2/sdk.js'
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
  const liff = window.liff
  await liff.init({ liffId })
  if (!liff.isLoggedIn()) {
    liff.login({ redirectUri: window.location.href })
    return null
  }
  const idToken = liff.getIDToken()
  if (!idToken) return null
  return api('auth/line/idtoken', { method: 'POST', body: { id_token: idToken } })
}
