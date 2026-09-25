// 以目前頁面所在路徑為基準，打包後可掛在任何子路徑下
export const BASE = new URL('.', window.location.href.split('#')[0]).href

const TOKEN_KEY = 'booking-token'

export function getToken() {
  try { return localStorage.getItem(TOKEN_KEY) || '' } catch { return '' }
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
