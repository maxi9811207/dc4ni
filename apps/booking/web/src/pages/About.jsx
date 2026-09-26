import { useEffect, useState } from 'react'
import { useApp } from '../App'
import { api } from '../api'
import VenueHeader from '../components/VenueHeader'
import ReviewItem from '../components/ReviewItem'
import { Empty, Stars } from '../components/ui'

export default function About() {
  const { venue, handleError } = useApp()
  const [reviews, setReviews] = useState([])
  useEffect(() => { api('reviews').then(setReviews).catch(handleError) }, [handleError])

  return (
    <>
      <VenueHeader />
      <main className="page">
        <section className="card">
          <h3 className="card-title">關於場館</h3>
          {venue?.address && (
            <a className="info-link" target="_blank" rel="noreferrer"
              href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(venue.address)}`}>
              📍 {venue.address}
            </a>
          )}
          {venue?.phone && <a className="info-link" href={`tel:${venue.phone}`}>📞 {venue.phone}</a>}
          {venue?.line_url && <a className="info-link" target="_blank" rel="noreferrer" href={venue.line_url}>💬 LINE 官方帳號</a>}
          {venue?.about && <p className="pre about-text">{venue.about}</p>}
        </section>
        {venue?.rules && (
          <section className="card">
            <h3 className="card-title">場館規範</h3>
            <p className="pre">{venue.rules}</p>
          </section>
        )}
        <section className="card row gap">
          <span className="big-rating">{venue?.rating ?? '—'}</span>
          <div>
            <h3 className="card-title nomargin">評價</h3>
            <Stars value={venue?.rating || 0} size={18} />
            <p className="muted small">（{venue?.review_count || 0} 評價）</p>
          </div>
        </section>
        {reviews.length === 0 ? <Empty text="還沒有評價" /> : reviews.map((r) => <ReviewItem key={r.id} r={r} />)}
      </main>
    </>
  )
}
