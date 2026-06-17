/**
 * components/Navbar.tsx — Complete file.
 * Fixed: hardcoded fetch(`${API_BASE}/...`) -> API_BASE
 */
import { useState, useEffect, useCallback, memo } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import {
  BarChart3, Bell, LogOut, User, Menu, X,
  ChevronDown, FileText, Calculator, Sparkles,
  LayoutDashboard, Home
} from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import AlertManager from './AlertManager'
import { API_BASE } from '../config/api'

interface NavProps {
  connected?:    boolean
  lastUpdated?:  string | null
  nextRefresh?:  number
  holdings?:     any[]
}

const MarketBar = memo(function MarketBar({
  connected, lastUpdated, nextRefresh
}: { connected?: boolean; lastUpdated?: string|null; nextRefresh?: number }) {
  const [time, setTime] = useState(new Date())

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000)
    return () => clearInterval(t)
  }, [])

  const ist = time.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false })
  const et  = time.toLocaleTimeString('en-US', { timeZone: 'America/New_York', hour12: false })

  const nseHour = parseInt(time.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', hour: '2-digit', hour12: false
  }))
  const nseMin = time.toLocaleString('en-IN', {
    timeZone: 'Asia/Kolkata', minute: '2-digit'
  })
  const nseOpen = nseHour >= 9 && (nseHour < 15 || (nseHour === 15 && parseInt(nseMin) <= 30))
  const isWeekend = [0, 6].includes(
    new Date(time.toLocaleString('en-US', { timeZone: 'Asia/Kolkata' })).getDay()
  )

  const usHour = parseInt(time.toLocaleString('en-US', {
    timeZone: 'America/New_York', hour: '2-digit', hour12: false
  }))
  const usOpen = !isWeekend && usHour >= 9 && usHour < 16

  return (
    <div className="bg-gray-950 border-b border-gray-800/60 px-4 md:px-6 py-1.5">
      <div className="max-w-7xl mx-auto flex items-center gap-4 text-xs overflow-x-auto">
        <div className={`flex items-center gap-1.5 shrink-0 ${connected ? 'text-green-400' : 'text-red-400'}`}>
          {connected ? (
            <><span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-pulse" />Live</>
          ) : (
            <><span className="relative flex h-1.5 w-1.5"><span className="w-1.5 h-1.5 rounded-full bg-red-500" /></span>Offline</>
          )}
        </div>

        <span className="text-gray-700">|</span>

        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`w-1.5 h-1.5 rounded-full ${!isWeekend && nseOpen ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
          <span className={!isWeekend && nseOpen ? 'text-green-400' : 'text-gray-500'}>
            NSE {!isWeekend && nseOpen ? 'Open' : 'Closed'}
          </span>
          <span className="text-gray-600">{ist}</span>
        </div>

        <span className="text-gray-700">|</span>

        <div className="flex items-center gap-1.5 shrink-0">
          <span className={`w-1.5 h-1.5 rounded-full ${usOpen ? 'bg-green-400 animate-pulse' : 'bg-gray-600'}`} />
          <span className={usOpen ? 'text-green-400' : 'text-gray-500'}>
            US {usOpen ? 'Open' : 'Closed'}
          </span>
          <span className="text-gray-600">{et} ET</span>
        </div>

        {nextRefresh && (
          <>
            <span className="text-gray-700">|</span>
            <span className="text-gray-600 shrink-0">
              Refresh: {nextRefresh >= 60 ? `${Math.floor(nextRefresh/60)}m` : `${nextRefresh}s`}
            </span>
          </>
        )}

        {lastUpdated && (
          <>
            <span className="text-gray-700">|</span>
            <span className="text-gray-600 shrink-0">
              Updated {new Date(lastUpdated).toLocaleTimeString('en-IN', { hour12: false })}
            </span>
          </>
        )}

        {isWeekend && (
          <>
            <span className="text-gray-700">|</span>
            <span className="text-yellow-600/80 shrink-0">Weekend · last close prices</span>
          </>
        )}
      </div>
    </div>
  )
})

function UnreadBadge({ count }: { count: number }) {
  if (count <= 0) return null
  return (
    <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-600 text-white text-[9px] font-bold rounded-full flex items-center justify-center">
      {count > 9 ? '9+' : count}
    </span>
  )
}

const Navbar = memo(function Navbar({
  connected, lastUpdated, nextRefresh, holdings = []
}: NavProps) {
  const location  = useLocation()
  const navigate   = useNavigate()
  const { user, isLoggedIn, logout } = useAuth()

  const [mobileOpen,  setMobileOpen]  = useState(false)
  const [showAlerts,  setShowAlerts]  = useState(false)
  const [showUser,    setShowUser]    = useState(false)
  const [unreadCount, setUnreadCount] = useState(0)

  // Poll unread count every 30s — uses API_BASE, not a hardcoded URL
  useEffect(() => {
    const fetchUnread = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/alerts/unread-count`)
        const d   = await res.json()
        setUnreadCount(d.count || 0)
      } catch { /* silent */ }
    }
    fetchUnread()
    const iv = setInterval(fetchUnread, 30000)
    return () => clearInterval(iv)
  }, [])

  const handleLogout = useCallback(async () => {
    await logout()
    setShowUser(false)
    navigate('/')
  }, [logout, navigate])

  const isActive = (path: string) =>
    location.pathname === path
      ? 'text-white bg-gray-800/80'
      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'

  const LINKS = [
    { path: '/',          label: 'Home',        icon: <Home size={14} /> },
    { path: '/dashboard', label: 'Dashboard',   icon: <LayoutDashboard size={14} /> },
    { path: '/recommend', label: '✨ AI Advisor', icon: <Sparkles size={14} /> },
    { path: '/tax',       label: '🧾 Tax P&L',   icon: <Calculator size={14} /> },
    { path: '/reports',   label: '📄 Reports',   icon: <FileText size={14} /> },
  ]

  return (
    <>
      <MarketBar
        connected={connected}
        lastUpdated={lastUpdated}
        nextRefresh={nextRefresh}
      />

      <nav className="bg-gray-950/95 backdrop-blur-sm border-b border-gray-800/60 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-4 md:px-6">
          <div className="flex items-center justify-between h-14">

            <Link
              to="/"
              className="flex items-center gap-2.5 text-lg font-bold text-white shrink-0"
            >
              <div className="w-8 h-8 bg-blue-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-600/30">
                <BarChart3 size={17} className="text-white" />
              </div>
              <span>Portfolio<span className="text-blue-400">AI</span></span>
            </Link>

            <div className="hidden md:flex items-center gap-1">
              {LINKS.map(link => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${isActive(link.path)}`}
                >
                  {link.label}
                </Link>
              ))}
            </div>

            <div className="flex items-center gap-2">

              <button
                onClick={() => setShowAlerts(true)}
                className="relative p-2 text-gray-400 hover:text-white hover:bg-gray-800/60 rounded-lg transition-all"
                title="Alerts"
              >
                <Bell size={17} />
                <UnreadBadge count={unreadCount} />
              </button>

              {isLoggedIn ? (
                <div className="relative">
                  <button
                    onClick={() => setShowUser(!showUser)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-800/60 hover:bg-gray-700/60 border border-gray-700/60 rounded-xl text-sm text-white transition-all"
                  >
                    <div className="w-6 h-6 bg-blue-600/30 rounded-full flex items-center justify-center">
                      <User size={12} className="text-blue-400" />
                    </div>
                    <span className="hidden sm:block text-gray-300 max-w-20 truncate">
                      {user?.username}
                    </span>
                    <ChevronDown size={13} className={`text-gray-500 transition-transform ${showUser ? 'rotate-180' : ''}`} />
                  </button>

                  {showUser && (
                    <div className="absolute right-0 top-full mt-2 w-52 bg-gray-900 border border-gray-700 rounded-2xl shadow-2xl overflow-hidden z-50">
                      <div className="px-4 py-3 border-b border-gray-800">
                        <p className="text-white font-medium text-sm truncate">{user?.username}</p>
                        <p className="text-gray-500 text-xs truncate">{user?.email}</p>
                      </div>
                      <div className="p-1.5">
                        {[
                          { to: '/dashboard', icon: <LayoutDashboard size={14} />, label: 'Dashboard' },
                          { to: '/tax',       icon: <Calculator size={14} />,      label: 'Tax P&L' },
                          { to: '/reports',   icon: <FileText size={14} />,        label: 'PDF Reports' },
                        ].map(item => (
                          <Link
                            key={item.to}
                            to={item.to}
                            onClick={() => setShowUser(false)}
                            className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors text-sm"
                          >
                            {item.icon}
                            {item.label}
                          </Link>
                        ))}
                        <button
                          onClick={handleLogout}
                          className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-red-400 hover:text-red-300 hover:bg-red-950/20 transition-colors text-sm mt-1"
                        >
                          <LogOut size={14} />
                          Sign Out
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="hidden sm:flex items-center gap-2">
                  <Link
                    to="/login"
                    className="px-3 py-1.5 text-gray-400 hover:text-white text-sm transition-colors"
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/register"
                    className="px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium rounded-xl transition-all shadow-lg shadow-blue-600/20"
                  >
                    Sign Up Free
                  </Link>
                </div>
              )}

              <Link
                to="/dashboard"
                className="hidden lg:flex items-center gap-1.5 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-blue-600/20"
              >
                Analyze Portfolio →
              </Link>

              <button
                onClick={() => setMobileOpen(!mobileOpen)}
                className="md:hidden p-2 text-gray-400 hover:text-white transition-colors"
              >
                {mobileOpen ? <X size={20} /> : <Menu size={20} />}
              </button>
            </div>
          </div>
        </div>

        {mobileOpen && (
          <div className="md:hidden border-t border-gray-800 bg-gray-950 px-4 py-3 space-y-1">
            {LINKS.map(link => (
              <Link
                key={link.path}
                to={link.path}
                onClick={() => setMobileOpen(false)}
                className={`flex items-center gap-2 px-3 py-2.5 rounded-xl text-sm font-medium transition-all ${isActive(link.path)}`}
              >
                {link.icon}
                {link.label}
              </Link>
            ))}
            <div className="pt-2 border-t border-gray-800 mt-2">
              {isLoggedIn ? (
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-2 px-3 py-2.5 text-red-400 text-sm"
                >
                  <LogOut size={14} /> Sign Out
                </button>
              ) : (
                <div className="flex gap-2">
                  <Link to="/login" onClick={() => setMobileOpen(false)}
                    className="flex-1 text-center py-2.5 text-gray-400 border border-gray-700 rounded-xl text-sm">
                    Sign In
                  </Link>
                  <Link to="/register" onClick={() => setMobileOpen(false)}
                    className="flex-1 text-center py-2.5 bg-blue-600 text-white rounded-xl text-sm font-medium">
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>
        )}
      </nav>

      {showAlerts && (
        <AlertManager
          holdings={holdings}
          onClose={() => { setShowAlerts(false); setUnreadCount(0) }}
        />
      )}

      {showUser && (
        <div
          className="fixed inset-0 z-30"
          onClick={() => setShowUser(false)}
        />
      )}
    </>
  )
})

export default Navbar
