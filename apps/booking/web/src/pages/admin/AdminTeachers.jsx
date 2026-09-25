import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../../App'
import { api } from '../../api'
import ImageInput from '../../components/ImageInput'
import { Avatar, Badge, Empty, Field, Loading, Modal } from '../../components/ui'

const EMPTY = { name: '', title: '', bio: '', photo_url: '', active: 1, sort: 0 }

export default function AdminTeachers() {
  const { handleError, showToast } = useApp()
  const [list, setList] = useState(null)
  const [editing, setEditing] = useState(null)
  const load = useCallback(() => api('admin/teachers').then(setList).catch(handleError), [handleError])
  useEffect(() => { load() }, [load])

  const save = async (e) => {
    e.preventDefault()
    try {
      if (editing.id) await api(`admin/teachers/${editing.id}`, { method: 'PUT', body: editing })
      else await api('admin/teachers', { method: 'POST', body: editing })
      setEditing(null)
      showToast('已儲存')
      load()
    } catch (err) { handleError(err) }
  }
  const set = (k) => (e) => setEditing({ ...editing, [k]: e.target.type === 'checkbox' ? (e.target.checked ? 1 : 0) : e.target.value })

  return (
    <>
      <div className="row between section-head">
        <h3 className="date-title">老師（{list?.length ?? 0}）</h3>
        <button className="btn btn-small" onClick={() => setEditing({ ...EMPTY, sort: list?.length || 0 })}>＋ 新增老師</button>
      </div>
      {!list ? <Loading /> : list.length === 0 ? <Empty text="還沒有老師" /> : list.map((t) => (
        <button key={t.id} className={`card teacher-card text-left ${t.active ? '' : 'dim'}`} onClick={() => setEditing(t)}>
          <Avatar src={t.photo_url} name={t.name} size={56} />
          <div className="flex1 min0">
            <h2 className="course-name">{t.name}{!t.active && <Badge tone="gray">已隱藏</Badge>}</h2>
            <p className="text-brand small">{t.title}</p>
            <p className="muted small clamp2">{t.bio}</p>
          </div>
          <span className="muted">編輯 ›</span>
        </button>
      ))}
      {editing && (
        <Modal onClose={() => setEditing(null)}>
          <form className="form" onSubmit={save}>
            <h3 className="dialog-title">{editing.id ? '編輯老師' : '新增老師'}</h3>
            <Field label="照片"><ImageInput round value={editing.photo_url} onChange={(v) => setEditing({ ...editing, photo_url: v })} /></Field>
            <Field label="姓名"><input className="input" value={editing.name} onChange={set('name')} required /></Field>
            <Field label="頭銜"><input className="input" value={editing.title} onChange={set('title')} placeholder="例：USAPA 認證教練" /></Field>
            <Field label="介紹"><textarea className="input" rows={4} value={editing.bio} onChange={set('bio')} /></Field>
            <Field label="排序" hint="數字小的排前面"><input className="input" type="number" value={editing.sort} onChange={set('sort')} /></Field>
            <label className="check"><input type="checkbox" checked={!!editing.active} onChange={set('active')} /> 在「師資陣容」顯示</label>
            <button className="btn btn-block">儲存</button>
          </form>
        </Modal>
      )}
    </>
  )
}
