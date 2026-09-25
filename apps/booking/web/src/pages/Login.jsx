import { useEffect, useState } from 'react'
import { useLocation, useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../App'
import { api, BASE, setToken } from '../api'
import { Field, Loading, TopBar } from '../components/ui'

export function LineButton({ next = '/', label = '使用 LINE 登入' }) {
  return (
    <a className="btn btn-block btn-lg btn-line" href={`${BASE}api/auth/line/start?next=${encodeURIComponent(next)}`}>
      <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M12 3C6.5 3 2 6.6 2 11c0 3.9 3.5 7.2 8.3 7.9.3.1.8.2.9.5.1.3.1.7 0 1l-.1.9c0 .3-.2 1 .9.5 1.1-.5 5.9-3.5 8-6C21.4 14.3 22 12.7 22 11c0-4.4-4.5-8-10-8zM8.3 13.4H6.4c-.3 0-.5-.2-.5-.5V9.1c0-.3.2-.5.5-.5s.5.2.5.5v3.3h1.4c.3 0 .5.2.5.5s-.2.5-.5.5zm1.9-.5c0 .3-.2.5-.5.5s-.5-.2-.5-.5V9.1c0-.3.2-.5.5-.5s.5.2.5.5v3.8zm4.6 0c0 .2-.1.4-.3.5h-.2c-.2 0-.3-.1-.4-.2l-2-2.7v2.4c0 .3-.2.5-.5.5s-.5-.2-.5-.5V9.1c0-.2.1-.4.3-.5h.2c.2 0 .3.1.4.2l2 2.7V9.1c0-.3.2-.5.5-.5s.5.2.5.5v3.8zm3.1-2.4c.3 0 .5.2.5.5s-.2.5-.5.5h-1.4v.9h1.4c.3 0 .5.2.5.5s-.2.5-.5.5h-1.9c-.3 0-.5-.2-.5-.5V9.1c0-.3.2-.5.5-.5h1.9c.3 0 .5.2.5.5s-.2.5-.5.5h-1.4v.9h1.4z"/></svg>
      {label}
    </a>
  )
}

export default function Login() {
  const { signIn, venue, auth, showToast } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', login: '', email: '', phone: '', password: '' })
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })
  const from = location.state?.from

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const body = mode === 'login'
        ? { login: form.login, password: form.password }
        : { name: form.name, email: form.email, phone: form.phone, password: form.password }
      const r = await api(`auth/${mode}`, { method: 'POST', body })
      signIn(r.token, r.user)
      showToast(mode === 'login' ? '登入成功' : '註冊成功，歡迎加入！')
      navigate(from || (r.user.role === 'owner' ? '/admin' : '/'), { replace: true })
    } catch (err) {
      showToast(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <TopBar title="註冊登入" />
      <main className="page">
        <form className="card login-card" onSubmit={submit}>
          <h2 className="detail-title center">{venue?.name}</h2>
          <p className="muted center small">{mode === 'login' ? '登入帳號以預約課程' : '建立帳號，開始預約課程'}</p>
          {auth.line_enabled && (
            <>
              <LineButton next={from || '/'} label={mode === 'login' ? '使用 LINE 登入' : '使用 LINE 快速註冊'} />
              <div className="or"><span>或使用信箱</span></div>
            </>
          )}
          <div className="seg">
            <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>登入</button>
            <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>註冊</button>
          </div>
          {mode === 'login' ? (
            <Field label="信箱或手機號碼">
              <input className="input" value={form.login} onChange={set('login')} required autoComplete="username" placeholder="you@example.com" />
            </Field>
          ) : (
            <>
              <Field label="姓名"><input className="input" value={form.name} onChange={set('name')} required autoComplete="name" /></Field>
              <Field label="信箱"><input className="input" type="email" value={form.email} onChange={set('email')} required autoComplete="email" placeholder="you@example.com" /></Field>
              <Field label="手機號碼（選填）" hint="方便場館臨時聯絡您">
                <input className="input" type="tel" inputMode="numeric" value={form.phone} onChange={set('phone')} autoComplete="tel" placeholder="09xxxxxxxx" />
              </Field>
            </>
          )}
          <Field label="密碼" hint={mode === 'register' ? '至少 6 碼' : undefined}>
            <input className="input" type="password" value={form.password} onChange={set('password')} required minLength={mode === 'register' ? 6 : 1} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
          </Field>
          <button className="btn btn-block btn-lg" disabled={busy}>{busy ? '處理中…' : mode === 'login' ? '登入' : '註冊'}</button>
          <p className="muted small center">登入即代表您同意本場館的使用者條款與隱私權政策</p>
        </form>
      </main>
    </>
  )
}

// LINE 授權完成後回到這裡：帶著本站 token 或錯誤訊息
export function LineCallback() {
  const [params] = useSearchParams()
  const { refreshUser, showToast } = useApp()
  const navigate = useNavigate()
  useEffect(() => {
    const token = params.get('token')
    if (!token) {
      showToast(params.get('error') || 'LINE 登入失敗')
      navigate('/login', { replace: true })
      return
    }
    setToken(token)
    refreshUser().then((u) => {
      showToast(params.get('linked') ? '已綁定 LINE 帳號' : `歡迎，${u?.name || ''}`)
      navigate(params.get('next') || (u?.role === 'owner' ? '/admin' : '/'), { replace: true })
    })
  }, [params, refreshUser, showToast, navigate])
  return <Loading text="LINE 登入中" />
}
