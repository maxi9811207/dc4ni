import React from 'react'
import ReactDOM from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import App from './App'
import './styles.css'
import { BASE } from './api'

// 活動網址 <網站>/<代碼>：伺服器直接回這個 App（頁面上已經有活動的文字內容給搜尋引擎），這裡轉成內部路由 #/e/<代碼>
{
  const seg = window.location.href.split('#')[0].slice(BASE.length).split('?')[0]
  if (!window.location.hash && /^[a-z0-9]{4,18}$/i.test(seg)) {
    window.history.replaceState(window.history.state, '', `${BASE}${seg}#/e/${seg.toLowerCase()}`)
  }
}

// 活動頁的網址列是 /e/<代碼>（不帶 hash，見 useShareAddress）；按返回鍵回到那一頁時先把 hash 接回，
// 這個監聽要比路由的早註冊，路由讀到的才會是正確的頁面
window.addEventListener('popstate', () => {
  const hash = window.history.state?.__hash
  if (hash && !window.location.hash) window.history.replaceState(window.history.state, '', window.location.href.split('#')[0] + hash)
})

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <HashRouter>
      <App />
    </HashRouter>
  </React.StrictMode>
)
