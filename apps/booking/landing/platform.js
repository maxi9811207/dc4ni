// Digital Court 平台頁共用：API、登入 token、小工具
window.DC = (function () {
  var KEY = 'dc-platform-token'
  function token() { try { return localStorage.getItem(KEY) || '' } catch (e) { return '' } }
  function setToken(t) { try { t ? localStorage.setItem(KEY, t) : localStorage.removeItem(KEY) } catch (e) { /* 無痕模式 */ } }
  function api(path, opts) {
    opts = opts || {}
    var h = { 'Content-Type': 'application/json' }
    if (token()) h.Authorization = 'Bearer ' + token()
    return fetch('/platform/api/' + path, { method: opts.method || 'GET', headers: h, body: opts.body ? JSON.stringify(opts.body) : undefined })
      .then(function (r) {
        return r.json().catch(function () { return {} }).then(function (d) {
          if (!r.ok) { var e = new Error(d.error || d.detail || '發生錯誤，請稍後再試'); e.status = r.status; throw e }
          return d
        })
      })
  }
  function msg(el, text, kind) { el.textContent = text; el.className = 'msg ' + (kind || 'bad'); el.hidden = !text }
  function $(s) { return document.querySelector(s) }
  function money(n) { return 'NT$ ' + Number(n || 0).toLocaleString() }
  function day(s) { return s ? String(s).slice(0, 10).replace(/-/g, '/') : '' }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c] }) }
  var STATUS = { pending: '待付款', trial: '試用中', active: '使用中', past_due: '扣款失敗', suspended: '已暫停', cancelled: '已停止' }
  return { api: api, token: token, setToken: setToken, msg: msg, $: $, money: money, day: day, esc: esc, STATUS: STATUS }
})()
