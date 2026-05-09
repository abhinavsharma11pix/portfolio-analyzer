import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Menu, X } from 'lucide-react'
import { useState, memo } from 'react'
import MarketStatusBar from './MarketStatusBar'

interface Props {
  connected?: boolean
  lastUpdated?: Date | null
  nextRefresh?: number
}

const Navbar = memo(function Navbar({ connected, lastUpdated, nextRefresh }: Props) {
  const location  = useLocation()
  const [open, setOpen] = useState(false)

  const isActive = (path: string) => location.pathname === path

  const links = [
    { path: '/',          label: 'Home' },
    { path: '/dashboard', label: 'Dashboard' },
  ]

  return (
    <div className="sticky top-0 z-40">
      <nav className="bg-gray-950/95 backdrop-blur-md border-b border-gray-800/50 px-6 py-4">
        <div className="max-w-7xl mx-auto flex items-center justify-between">

          <Link to="/" className="flex items-center gap-2.5 text-xl font-bold text-white hover:opacity-90 transition-opacity">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center shrink-0">
              <BarChart3 size={18} className="text-white" />
            </div>
            <span>Portfolio<span className="text-blue-400">AI</span></span>
          </Link>

          {/* Desktop */}
          <div className="hidden md:flex items-center gap-1">
            {links.map(l => (
              <Link
                key={l.path}
                to={l.path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                  isActive(l.path)
                    ? 'bg-blue-600/20 text-blue-400'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {l.label}
              </Link>
            ))}
          </div>

          <div className="hidden md:flex">
            <Link
              to="/dashboard"
              className="bg-blue-600 hover:bg-blue-500 text-white px-4 py-2 rounded-lg text-sm font-medium transition-colors shadow-lg shadow-blue-600/20"
            >
              Analyze Portfolio →
            </Link>
          </div>

          <button
            onClick={() => setOpen(!open)}
            className="md:hidden text-gray-400 hover:text-white p-2"
          >
            {open ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>

        {open && (
          <div className="md:hidden mt-3 pb-2 border-t border-gray-800 pt-3 space-y-1">
            {links.map(l => (
              <Link
                key={l.path}
                to={l.path}
                onClick={() => setOpen(false)}
                className={`block px-4 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive(l.path)
                    ? 'bg-blue-600/20 text-blue-400'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                }`}
              >
                {l.label}
              </Link>
            ))}
            <Link
              to="/dashboard"
              onClick={() => setOpen(false)}
              className="block mt-2 bg-blue-600 text-white px-4 py-2.5 rounded-lg text-sm font-medium text-center"
            >
              Analyze Portfolio →
            </Link>
          </div>
        )}
      </nav>

      <MarketStatusBar
        connected={connected}
        lastUpdated={lastUpdated}
        nextRefresh={nextRefresh}
      />
    </div>
  )
})

export default Navbar