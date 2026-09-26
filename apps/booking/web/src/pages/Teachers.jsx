import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import VenueHeader from '../components/VenueHeader'
import { Avatar, Empty, Loading, Stars } from '../components/ui'

export default function Teachers() {
  const { handleError } = useApp()
  const [list, setList] = useState(null)
  useEffect(() => { api('teachers').then(setList).catch(handleError) }, [handleError])

  return (
    <>
      <VenueHeader />
      <main className="page">
        {!list ? <Loading /> : list.length === 0 ? <Empty text="師資準備中" /> : list.map((t) => (
          <Link key={t.id} to={`/teachers/${t.id}`} className="card teacher-card">
            <Avatar src={t.photo_url} name={t.name} size={64} />
            <div className="flex1 min0">
              <h2 className="course-name">{t.name}</h2>
              {t.title && <p className="text-brand small strong">{t.title}</p>}
              {t.bio && <p className="muted small clamp2">{t.bio}</p>}
              {t.rating && <p className="small"><Stars value={t.rating} /> {t.rating}（{t.review_count}）</p>}
            </div>
          </Link>
        ))}
      </main>
    </>
  )
}
