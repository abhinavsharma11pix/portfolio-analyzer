import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Menu, X } from 'lucide-react'
import { useState, memo } from 'react'
import MarketStatusBar from './MarketStatusBar'

interface Props {
  connected?: boolean; lastUpdated?: Date | null; nextRefresh?: number
}

const Navbar = memo(function Navbar({ connected, lastUpdated, nextRefresh }: Props) {
  const { pathname } = useLocation()
  const [open, setOpen] = useState(false)

  const links = [
    { path: '/',          label: 'Home' },
    { path: '/dashboard', label: 'Dashboard' },
    { path: '/recommend', label: '✨ AI Advisor' },

  ]

  return (
    <div className="sticky top-0 z-40">
      <nav className="glass border-b border-white/[0.06] px-4 md:px-6 py-3.5">
        <div className="max-w-7xl mx-auto flex items-center justify-between">

          <Link to="/" className="flex items-center gap-2.5 font-bold text-white hover:opacity-85 transition-opacity">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-600/30">
              <BarChart3 size={17} className="text-white" />
            </div>
            <span className="text-lg">Portfolio<span className="text-blue-400">AI</span></span>
          </Link>

          <div className="hidden md:flex items-center gap-0.5">
            {links.map(l => (
              <Link
                key={l.path}
                to={l.path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  pathname === l.path
                    ? 'bg-blue-600/15 text-blue-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex items-center gap-3">
            <Link
              to="/dashboard"
              className="bg-blue-600 hover:bg-blue-500 active:scale-95 text-white px-4 py-2 rounded-lg text-sm font-semibold transition-all shadow-md shadow-blue-600/20"
            >
              Analyze Portfolio →
            </Link>
          </div>

          <button onClick={() => setOpen(!open)} className="md:hidden text-gray-400 hover:text-white p-2 rounded-lg hover:bg-white/5">
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {open && (
          <div className="md:hidden mt-3 pt-3 border-t border-white/[0.06] space-y-1 animate-fade-in">
            {links.map(l => (
              <Link
                key={l.path}
                to={l.path}
                onClick={() => setOpen(false)}
                className={`block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  pathname === l.path
                    ? 'bg-blue-600/15 text-blue-400'
                    : 'text-gray-400 hover:text-white hover:bg-white/5'
                }`}
              >
                {l.label}
              </Link>
            ))}
            <Link
              to="/dashboard"
              onClick={() => setOpen(false)}
              className="block mt-1 bg-blue-600 text-white px-4 py-2.5 rounded-lg text-sm font-semibold text-center"
            >
              Analyze Portfolio →
            </Link>
          </div>
        )}
      </nav>

      <MarketStatusBar connected={connected} lastUpdated={lastUpdated} nextRefresh={nextRefresh} />
    </div>
  )
})

export default Navbar