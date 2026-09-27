import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApp } from '../App'
import { api } from '../api'
import VenueHeader from '../components/VenueHeader'
import WeekPicker from '../components/WeekPicker'
import CourseCard, { SlotSetCard } from '../components/CourseCard'
import { Chips, Empty, Loading } from '../components/ui'
import { addDays, showDate, today } from '../util'

const PERIODS = [
  ['上午', (h) => h < 12],
  ['下午', (h) => h >= 12 && h < 18],
  ['晚上', (h) => h >= 18],
]

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

  const shown = [
    ...(data?.courses || []).filter((c) => kind === 'all' || (kind === 'dupr') === c.dupr_required),
    ...(kind === 'dupr' ? [] : (data?.slot_sets || []).map((x) => ({ ...x, slotSet: true }))),
  ].sort((a, b) => a.start_time.localeCompare(b.start_time))
  const maxDate = venue?.open_days ? addDays(today(), venue.open_days) : undefined

  return (
    <>
      <VenueHeader />
      <main className="page">
        <WeekPicker value={date} maxDate={maxDate} onChange={(d) => setParams({ date: d }, { replace: true })} />
        <div className="filter-row">
          <h3 className="date-title">{showDate(date)}</h3>
          {data?.courses.some((c) => c.dupr_required) && (
            <Chips value={kind} onChange={setKind} options={[['all', '全部'], ['dupr', 'DUPR'], ['normal', '一般']]} />
          )}
        </div>
        {!data ? <Loading text="課程查詢中" />
          : shown.length === 0 ? <Empty text="這天沒有課程" />
            : PERIODS.map(([label, test]) => {
              const list = shown.filter((c) => test(Number(c.start_time.slice(0, 2))))
              if (!list.length) return null
              return (
                <section key={label} className="tgroup-wrap">
                  <h3 className="tgroup">{label}<span>{list.length} 場</span></h3>
                  {list.map((c) => (c.slotSet ? <SlotSetCard key={`s${c.id}`} s={c} /> : <CourseCard key={c.id} course={c} showCount={data.show_reservation_count} />))}
                </section>
              )
            })}
      </main>
    </>
  )
}
