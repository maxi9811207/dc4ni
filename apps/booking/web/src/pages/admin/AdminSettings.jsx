import { useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import ImageInput from '../../components/ImageInput'
import { Field } from '../../components/ui'

export default function AdminSettings() {
  const { venue, loadVenue, handleError, showToast } = useApp()
  const [form, setForm] = useState(() => ({ ...venue, categories: (venue?.categories || []).join('\n') }))
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value })

  const save = async (e) => {
    e.preventDefault()
    try {
      await api('admin/settings', {
        method: 'PUT',
        body: {
          ...form,
          open_days: Number(form.open_days) || 14,
          categories: form.categories.split('\n').map((s) => s.trim()).filter(Boolean),
        },
      })
      await loadVenue()
      showToast('已儲存')
    } catch (err) { handleError(err) }
  }

  return (
    <form className="card form" onSubmit={save}>
      <h3 className="card-title">場館資訊</h3>
      <Field label="場館名稱"><input className="input" value={form.name} onChange={set('name')} required /></Field>
      <Field label="封面圖片" hint="建議 16:9，顯示在前台最上方"><ImageInput value={form.cover_url} onChange={(v) => setForm({ ...form, cover_url: v })} /></Field>
      <Field label="地址"><input className="input" value={form.address} onChange={set('address')} /></Field>
      <div className="grid2">
        <Field label="電話"><input className="input" value={form.phone} onChange={set('phone')} /></Field>
        <Field label="LINE 連結"><input className="input" value={form.line_url} onChange={set('line_url')} placeholder="https://lin.ee/..." /></Field>
      </div>
      <Field label="場館介紹"><textarea className="input" rows={4} value={form.about} onChange={set('about')} /></Field>
      <Field label="場館規範"><textarea className="input" rows={3} value={form.rules} onChange={set('rules')} /></Field>
      <Field label="付款方式說明" hint="學生購買課卡時會看到"><textarea className="input" rows={3} value={form.payment_info} onChange={set('payment_info')} /></Field>

      <h3 className="card-title">預約設定</h3>
      <Field label="課程類別" hint="一行一個"><textarea className="input" rows={3} value={form.categories} onChange={set('categories')} /></Field>
      <Field label="開放預約天數" hint="學生可以看到並預約幾天內的課程">
        <input className="input" type="number" min="1" max="120" value={form.open_days} onChange={set('open_days')} />
      </Field>
      <label className="check"><input type="checkbox" checked={!!form.show_reservation_count} onChange={set('show_reservation_count')} /> 課程列表顯示預約人數（例 5 / 6）；關閉時只在剩 5 位以內顯示「剩餘 N 位」</label>
      <label className="check"><input type="checkbox" checked={!!form.waitlist_enabled} onChange={set('waitlist_enabled')} /> 額滿時開放候補</label>
      <button className="btn btn-block btn-lg">儲存設定</button>
    </form>
  )
}
