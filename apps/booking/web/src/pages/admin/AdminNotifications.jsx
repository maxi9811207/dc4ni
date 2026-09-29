import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '../../App'
import { api } from '../../api'
import { Empty, Loading } from '../../components/ui'
import { showDateTime } from '../../util'

const KIND = {
  booking: ['預約', 'brand'],
  waitlist: ['候補', 'warn'],
  cancel: ['取消', 'danger'],
  promote: ['遞補', 'success'],
  order: ['付款', 'warn'],
  member: ['會員', 'gray'],
  review: ['評價', 'brand'],
}

export default function AdminNotifications() {
  const { handleError, refreshUser } = useApp()
  const [list, setList] = useState(null)
  useEffect(() => {
    api('admin/notifications').then((l) => { setList(l); refreshUser() }).catch(handleError)
  }, [handleError, refreshUser])

  if (!list) return <Loading />
  if (list.length === 0) return <Empty text="目前沒有通知" />
  return (
    <section className="card">
      {list.map((n) => {
        const [label, tone] = KIND[n.kind] || ['通知', 'gray']
        const body = (
          <>
            <span className={`badge badge-${tone}`}>{label}</span>
            <div className="flex1 min0">
              <p className={n.read ? '' : 'strong'}>{n.text}</p>
              <span className="muted small">{showDateTime(n.created_at)}</span>
            </div>
            {n.link && <span className="muted">›</span>}
          </>
        )
        return n.link
          ? <Link key={n.id} to={n.link} className={`admin-notice ${n.read ? '' : 'unread'}`}>{body}</Link>
          : <div key={n.id} className={`admin-notice ${n.read ? '' : 'unread'}`}>{body}</div>
      })}
    </section>
  )
}
