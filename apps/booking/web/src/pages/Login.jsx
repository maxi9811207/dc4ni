import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import { Field, TopBar } from '../components/ui'

export default function Login() {
  const { signIn, venue, showToast } = useApp()
  const navigate = useNavigate()
  const location = useLocation()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ name: '', phone: '', password: '' })
  const [busy, setBusy] = useState(false)
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    try {
      const r = await api(`auth/${mode}`, { method: 'POST', body: form })
      signIn(r.token, r.user)
      showToast(mode === 'login' ? '登入成功' : '註冊成功，歡迎加入！')
      navigate(location.state?.from || (r.user.role === 'owner' ? '/admin' : '/'), { replace: true })
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
          <div className="seg">
            <button type="button" className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>登入</button>
            <button type="button" className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>註冊</button>
          </div>
          {mode === 'register' && (
            <Field label="姓名"><input className="input" value={form.name} onChange={set('name')} required autoComplete="name" /></Field>
          )}
          <Field label="手機號碼">
            <input className="input" type="tel" inputMode="numeric" value={form.phone} onChange={set('phone')} required autoComplete="tel" placeholder="09xxxxxxxx" />
          </Field>
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
