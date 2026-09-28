// 以目前頁面所在路徑為基準，打包後可掛在任何子路徑下
export const BASE = new URL('.', window.location.href.split('#')[0]).href

// 同一個網域底下有很多場館（digital-court.cc/<代碼>/），localStorage 是整個網域共用的，
// 登入 token 要依場館路徑分開存，否則在 B 館登入會把 A 館的登入蓋掉。
const tokenKey = (base) => 'booking-token:' + new URL(base).pathname
const TOKEN_KEY = tokenKey(BASE)
// 分開存之前只有一個場館（/active/ 或自訂網域根目錄），沿用舊的 key 讓已登入的人不用重登
const LEGACY_KEY = 'booking-token'
const LEGACY_PATHS = ['/', '/active/']

export function getToken() {
  try {
    const t = localStorage.getItem(TOKEN_KEY)
    if (t) return t
    if (LEGACY_PATHS.includes(new URL(BASE).pathname)) {
      const old = localStorage.getItem(LEGACY_KEY) || ''
      if (old) localStorage.setItem(TOKEN_KEY, old)
      return old
    }
    return ''
  } catch { return '' }
}

// 場主改了場館網址：把登入帶到新網址，轉過去之後不用重新登入
export function carryTokenTo(newBase) {
  try {
    const t = getToken()
    if (t) localStorage.setItem(tokenKey(newBase), t)
  } catch { /* 無痕模式：轉過去後重新登入即可 */ }
}

export function setToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch { /* 無痕模式等情況下仍可使用，只是不會記住登入 */ }
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

export async function api(path, { method = 'GET', body, form } = {}) {
  const headers = {}
  const token = getToken()
  if (token) headers.Authorization = `Bearer ${token}`
  let payload
  if (form) payload = form
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }
  const res = await fetch(BASE + 'api/' + path.replace(/^\//, ''), { method, headers, body: payload })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) throw new ApiError(data.error || '發生錯誤，請稍後再試', res.status)
  return data
}

export function asset(url) {
  if (!url) return ''
  return /^(https?:|data:)/.test(url) ? url : BASE + url
}

export async function uploadImage(file) {
  const form = new FormData()
  form.append('file', file)
  const { url } = await api('admin/upload', { method: 'POST', form })
  return url
}

// 後台下載（Excel／CSV）：帶登入憑證取檔再存檔
export async function downloadFile(path, filename) {
  const res = await fetch(BASE + 'api/' + path.replace(/^\//, ''), { headers: { Authorization: `Bearer ${getToken()}` } })
  if (!res.ok) throw new ApiError((await res.json().catch(() => ({}))).error || '下載失敗', res.status)
  const url = URL.createObjectURL(await res.blob())
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
