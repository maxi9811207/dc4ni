import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import CourseCard from '../components/CourseCard'
import ReviewItem from '../components/ReviewItem'
import { Avatar, Chips, Empty, Loading, Stars, TopBar } from '../components/ui'

export default function TeacherDetail() {
  const { id } = useParams()
  const { handleError } = useApp()
  const [t, setT] = useState(null)
  const [tab, setTab] = useState('courses')
  useEffect(() => { api(`teachers/${id}`).then(setT).catch(handleError) }, [id, handleError])

  if (!t) return <><TopBar title="師資介紹" /><Loading /></>
  const avg = t.reviews.length ? t.reviews.reduce((s, r) => s + r.rating, 0) / t.reviews.length : 0

  return (
    <>
      <TopBar title="師資介紹" />
      <main className="page">
        <section className="card center teacher-profile">
          <Avatar src={t.photo_url} name={t.name} size={96} />
          <h2 className="detail-title">{t.name}</h2>
          {t.title && <p className="text-brand strong">{t.title}</p>}
          {t.bio && <p className="pre left">{t.bio}</p>}
        </section>
        <Chips value={tab} onChange={setTab} options={[['courses', '課程'], ['reviews', `評價（${t.reviews.length}）`]]} />
        {tab === 'courses' ? (
          t.courses.length === 0 ? <Empty text="近期沒有課程" />
            : t.courses.map((c) => <CourseCard key={c.id} course={c} showDate />)
        ) : (
          <>
            {t.reviews.length > 0 && (
              <div className="card row gap">
                <span className="big-rating">{avg.toFixed(1)}</span>
                <div><Stars value={avg} size={18} /><p className="muted small">{t.reviews.length} 則評價</p></div>
              </div>
            )}
            {t.reviews.length === 0 ? <Empty text="還沒有評價" /> : t.reviews.map((r) => <ReviewItem key={r.id} r={r} />)}
          </>
        )}
      </main>
    </>
  )
}
