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
          reminder_hour: Number(form.reminder_hour ?? 20),
          noshow_limit: Math.max(Number(form.noshow_limit) || 3, 1),
          noshow_days: Number(form.noshow_days ?? 90),
          noshow_block_days: Number(form.noshow_block_days ?? 14),
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

      <h3 className="card-title">開課前一天提醒</h3>
      <label className="check"><input type="checkbox" checked={form.reminder_enabled !== false} onChange={set('reminder_enabled')} /> 前一天提醒已報名的學員（網站通知＋有綁 LINE 的推到 LINE；未付款的會一併提醒付款）</label>
      {form.reminder_enabled !== false && (
        <Field label="提醒時間" hint="您也會在同一時間收到「明天有幾堂、幾個人」的總覽">
          <select className="input" value={form.reminder_hour ?? 20} onChange={set('reminder_hour')}>
            {[...new Set([8, 12, 18, 19, 20, 21, 22, Number(form.reminder_hour ?? 20)])].sort((a, b) => a - b).map((h) => <option key={h} value={h}>前一天 {h}:00</option>)}
          </select>
        </Field>
      )}
      <h3 className="card-title">缺席（No-show）管理</h3>
      <label className="check"><input type="checkbox" checked={form.noshow_enabled !== false} onChange={set('noshow_enabled')} /> 報名後沒到（點名標「缺席」）累計太多次，自動暫停報名</label>
      {form.noshow_enabled !== false && (
        <>
          <div className="grid2">
            <Field label="計算期間">
              <select className="input" value={form.noshow_days ?? 90} onChange={set('noshow_days')}>
                {[[30, '最近 30 天'], [60, '最近 60 天'], [90, '最近 90 天'], [180, '最近 180 天'], [0, '不限（全部累計）']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </Field>
            <Field label="缺席幾次">
              <select className="input" value={form.noshow_limit ?? 3} onChange={set('noshow_limit')}>
                {[1, 2, 3, 4, 5, 6, 8, 10].map((n) => <option key={n} value={n}>{n} 次</option>)}
              </select>
            </Field>
          </div>
          <Field label="暫停報名多久" hint="暫停後缺席次數歸零重算；已經報名的活動不受影響">
            <select className="input" value={form.noshow_block_days ?? 14} onChange={set('noshow_block_days')}>
              {[[7, '7 天'], [14, '14 天'], [30, '30 天'], [60, '60 天'], [0, '直到我手動解除']].map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </Field>
          <p className="muted small">差 1 次到上限時會先提醒學員。個別缺席可以在「會員管理」免記（例如生病有先說），也可以手動解除或暫停。</p>
        </>
      )}
      <button className="btn btn-block btn-lg">儲存設定</button>
    </form>
  )
}
