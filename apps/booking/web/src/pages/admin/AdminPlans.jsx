import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import { Badge, Empty, Field, Loading, Modal } from '../../components/ui'
import { money, PLAN_TYPES, planAmount } from '../../util'

const EMPTY = { name: '', type: 'sessions', quantity: 10, valid_days: 90, price: 0, description: '', active: 1, sort: 0 }

export default function AdminPlans() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const [editing, setEditing] = useState(null)
  const load = useCallback(() => api('admin/plans').then(setList).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

  const save = async (e) => {
    e.preventDefault()
    try {
      if (editing.id) await api(`admin/plans/${editing.id}`, { method: 'PUT', body: editing })
      else await api('admin/plans', { method: 'POST', body: editing })
      setEditing(null)
      showToast('已儲存')
      load()
    } catch (err) { handleError(err) }
  }
  const set = (k) => (e) => setEditing({ ...editing, [k]: e.target.type === 'checkbox' ? (e.target.checked ? 1 : 0) : e.target.value })

  return (
    <>
      <div className="row between section-head">
        <h3 className="date-title">課卡方案（{list?.length ?? 0}）</h3>
        <button className="btn btn-small" onClick={() => setEditing({ ...EMPTY, sort: list?.length || 0 })}>＋ 新增方案</button>
      </div>
      {!list ? <Loading /> : list.length === 0 ? <Empty text="還沒有課卡方案" /> : list.map((p) => (
        <button key={p.id} className={`card plan-card text-left ${p.active ? '' : 'dim'}`} onClick={() => setEditing(p)}>
          <div className="row between">
            <Badge>{PLAN_TYPES[p.type]}</Badge>
            {!p.active && <Badge tone="gray">已下架</Badge>}
          </div>
          <h2 className="plan-name">{p.name}</h2>
          <p className="muted small">{planAmount(p)} · 效期 {p.valid_days} 天</p>
          <div className="row between plan-foot"><span className="price">{money(p.price)}</span><span className="muted">編輯 ›</span></div>
        </button>
      ))}
      {editing && (
        <Modal onClose={() => setEditing(null)}>
          <form className="form" onSubmit={save}>
            <h3 className="dialog-title">{editing.id ? '編輯方案' : '新增方案'}</h3>
            <Field label="方案名稱"><input className="input" value={editing.name} onChange={set('name')} required /></Field>
            <Field label="類型">
              <select className="input" value={editing.type} onChange={set('type')}>
                {Object.entries(PLAN_TYPES).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </Field>
            <div className="grid2">
              {editing.type !== 'unlimited' && (
                <Field label={editing.type === 'points' ? '點數' : '堂數'}><input className="input" type="number" min="1" value={editing.quantity} onChange={set('quantity')} required /></Field>
              )}
              <Field label="效期（天）"><input className="input" type="number" min="1" value={editing.valid_days} onChange={set('valid_days')} required /></Field>
            </div>
            <Field label="售價（NT$）"><input className="input" type="number" min="0" value={editing.price} onChange={set('price')} required /></Field>
            <Field label="說明"><textarea className="input" rows={3} value={editing.description} onChange={set('description')} /></Field>
            <Field label="排序"><input className="input" type="number" value={editing.sort} onChange={set('sort')} /></Field>
            <label className="check"><input type="checkbox" checked={!!editing.active} onChange={set('active')} /> 上架販售</label>
            {editing.id && <p className="muted small">修改方案不影響已售出的課卡。</p>}
            <button className="btn btn-block">儲存</button>
          </form>
        </Modal>
      )}
    </>
  )
}
