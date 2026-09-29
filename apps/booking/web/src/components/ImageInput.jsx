import { useState } from 'react'
import { useApp } from '../App'
import { asset, uploadImage } from '../api'

// 圖片欄位：可上傳檔案或直接貼網址
export default function ImageInput({ value, onChange, round }) {
  const { handleError } = useApp()
  const [busy, setBusy] = useState(false)
  const pick = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    try { onChange(await uploadImage(file)) } catch (err) { handleError(err) } finally { setBusy(false) }
  }
  return (
    <div className="image-input">
      {value && <img src={asset(value)} alt="" className={round ? 'round' : ''} />}
      <div className="flex1">
        <input className="input" value={value || ''} onChange={(e) => onChange(e.target.value)} placeholder="貼上圖片網址，或上傳" />
        <label className="btn btn-small btn-light upload-btn">
          {busy ? '上傳中…' : '上傳圖片'}
          <input type="file" accept="image/*" hidden onChange={pick} />
        </label>
        {value && <button type="button" className="btn btn-small btn-light" onClick={() => onChange('')}>移除</button>}
      </div>
    </div>
  )
}
