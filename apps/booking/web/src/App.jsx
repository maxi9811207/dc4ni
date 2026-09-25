import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { api, getToken, setToken } from './api'
import { Modal } from './components/ui'
import Courses from './pages/Courses'
import CourseDetail from './pages/CourseDetail'
import Teachers from './pages/Teachers'
import TeacherDetail from './pages/TeacherDetail'
import Plans from './pages/Plans'
import About from './pages/About'
import Login from './pages/Login'
import Member from './pages/Member'
import AdminLayout from './pages/admin/AdminLayout'
import Dashboard from './pages/admin/Dashboard'
import AdminCourses from './pages/admin/AdminCourses'
import CourseForm from './pages/admin/CourseForm'
import Roster from './pages/admin/Roster'
import AdminTeachers from './pages/admin/AdminTeachers'
import AdminPlans from './pages/admin/AdminPlans'
import AdminOrders from './pages/admin/AdminOrders'
import AdminMembers from './pages/admin/AdminMembers'
import AdminReviews from './pages/admin/AdminReviews'
import AdminSettings from './pages/admin/AdminSettings'
import AdminCalendar from './pages/admin/AdminCalendar'
import Attendance from './pages/admin/Attendance'
import AdminNotifications from './pages/admin/AdminNotifications'
import AdminTemplates from './pages/admin/AdminTemplates'
import Reports from './pages/admin/Reports'

const AppContext = createContext(null)
export const useApp = () => useContext(AppContext)

export default function App() {
  const [venue, setVenue] = useState(null)
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)
  const [toast, setToast] = useState('')
  const [dialog, setDialog] = useState(null)

  const loadVenue = useCallback(() => api('venue').then(setVenue).catch(() => {}), [])

  const refreshUser = useCallback(async () => {
    if (!getToken()) { setUser(null); return null }
    try {
      const me = await api('me')
      setUser(me)
      return me
    } catch (e) {
      if (e.status === 401) setToken('')
      setUser(null)
      return null
    }
  }, [])

  useEffect(() => {
    Promise.all([loadVenue(), refreshUser()]).finally(() => setReady(true))
  }, [loadVenue, refreshUser])

  useEffect(() => {
    if (venue?.name) document.title = `${venue.name} | 約課系統`
  }, [venue])

  const showToast = useCallback((text) => {
    setToast(text)
    clearTimeout(showToast.timer)
    showToast.timer = setTimeout(() => setToast(''), 2400)
  }, [])

  const signIn = (token, u) => { setToken(token); setUser(u) }
  const signOut = async () => {
    await api('auth/logout', { method: 'POST' }).catch(() => {})
    setToken('')
    setUser(null)
  }

  // 統一處理 API 錯誤：停權顯示專用視窗，其餘顯示提示
  const handleError = useCallback((e) => {
    if (e.message === 'SUSPENDED') setDialog({ kind: 'suspended' })
    else showToast(e.message)
  }, [showToast])

  const ctx = { venue, loadVenue, user, refreshUser, signIn, signOut, showToast, setDialog, handleError }

  if (!ready) return <div className="boot"><div className="spinner" /></div>

  return (
    <AppContext.Provider value={ctx}>
      <div className="shell">
        <Routes>
          <Route path="/" element={<Courses />} />
          <Route path="/course/:id" element={<CourseDetail />} />
          <Route path="/teachers" element={<Teachers />} />
          <Route path="/teachers/:id" element={<TeacherDetail />} />
          <Route path="/plans" element={<Plans />} />
          <Route path="/about" element={<About />} />
          <Route path="/login" element={<Login />} />
          <Route path="/me" element={<Member />} />
          <Route path="/admin" element={<AdminLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="calendar" element={<AdminCalendar />} />
            <Route path="templates" element={<AdminTemplates />} />
            <Route path="templates/new" element={<CourseForm template />} />
            <Route path="templates/:id/edit" element={<CourseForm template />} />
            <Route path="reports" element={<Reports />} />
            <Route path="attendance" element={<Attendance />} />
            <Route path="notifications" element={<AdminNotifications />} />
            <Route path="courses" element={<AdminCourses />} />
            <Route path="courses/new" element={<CourseForm />} />
            <Route path="courses/:id/edit" element={<CourseForm />} />
            <Route path="courses/:id" element={<Roster />} />
            <Route path="teachers" element={<AdminTeachers />} />
            <Route path="plans" element={<AdminPlans />} />
            <Route path="orders" element={<AdminOrders />} />
            <Route path="members" element={<AdminMembers />} />
            <Route path="reviews" element={<AdminReviews />} />
            <Route path="settings" element={<AdminSettings />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <footer className="footer">© {new Date().getFullYear()} {venue?.name || '約課系統'}</footer>
      </div>

      {toast && <div className="toast">{toast}</div>}

      {dialog?.kind === 'suspended' && (
        <Modal onClose={() => setDialog(null)}>
          <div className="dialog-icon danger">!</div>
          <p className="dialog-text">看起來您的帳號已被<b className="text-danger">停權</b>，<br />請聯絡場館管理員了解具體原因。</p>
          {user?.suspend_reason && <p className="muted center small">原因：{user.suspend_reason}</p>}
          <button className="btn btn-block" onClick={() => setDialog(null)}>我知道了</button>
        </Modal>
      )}
    </AppContext.Provider>
  )
}
