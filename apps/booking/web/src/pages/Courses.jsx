import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import VenueHeader from '../components/VenueHeader'
import WeekPicker from '../components/WeekPicker'
import CourseCard from '../components/CourseCard'
import { Chips, Empty, Loading } from '../components/ui'
import { addDays, showDate, today } from '../util'

export default function Courses() {
  const { venue, handleError } = useApp()
  const [params, setParams] = useSearchParams()
  const date = /^\d{4}-\d{2}-\d{2}$/.test(params.get('date') || '') ? params.get('date') : today()
  const [data, setData] = useState(null)
  const [kind, setKind] = useState('all')

  useEffect(() => {
    let alive = true
    setData(null)
    api(`courses?date=${date}`).then((d) => alive && setData(d)).catch(handleError)
    return () => { alive = false }
  }, [date, handleError])

  const shown = (data?.courses || []).filter((c) => kind === 'all' || (kind === 'dupr') === c.dupr_required)
  const maxDate = venue?.open_days ? addDays(today(), venue.open_days) : undefined

  return (
    <>
      <VenueHeader />
      <main className="page">
        <WeekPicker value={date} maxDate={maxDate} onChange={(d) => setParams({ date: d }, { replace: true })} />
        <h3 className="date-title">{showDate(date)}</h3>
        {data?.courses.some((c) => c.dupr_required) && (
          <Chips value={kind} onChange={setKind} options={[['all', '全部'], ['dupr', 'DUPR 場'], ['normal', '一般場']]} />
        )}
        {!data ? <Loading text="課程查詢中" />
          : shown.length === 0 ? <Empty text="目前沒有課程" />
            : shown.map((c) => <CourseCard key={c.id} course={c} showCount={data.show_reservation_count} />)}
      </main>
    </>
  )
}
