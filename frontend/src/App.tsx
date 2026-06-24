/**
 * App.tsx — Complete file.
 * Fix: removed <Navbar /> from here — Dashboard/pages already render their
 * own Navbar with the correct WebSocket props (connected, holdings, etc.)
 * Adding it here caused the duplicate navbar visible in the screenshot.
 * Home.tsx now renders Navbar itself since it previously had none.
 */
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthProvider }  from './context/AuthContext'

import Home      from './pages/Home'
import Dashboard from './pages/Dashboard'
import Recommend from './pages/Recommend'
import TaxEngine from './pages/TaxEngine'
import Reports   from './pages/Reports'
import Login     from './pages/Login'
import Register  from './pages/Register'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry:               1,
      refetchOnWindowFocus: false,
      staleTime:           30_000,
    },
  },
})

function NotFound() {
  return (
    <div className="min-h-screen bg-gray-950 flex flex-col items-center justify-center text-center px-4">
      <p className="text-7xl font-black text-gray-800 mb-4">404</p>
      <p className="text-white text-xl font-semibold mb-2">Page not found</p>
      <p className="text-gray-500 text-sm mb-6">The page you're looking for doesn't exist.</p>
      <a href="/"
        className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors">
        Go Home
      </a>
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          {/* Outer boundary catches catastrophic render failures */}
          <ErrorBoundary>
            {/*
              NO <Navbar /> here.
              Each page renders its own Navbar with the correct live props.
              Putting one here AND having one inside Dashboard = 2 navbars.
            */}
            <div className="min-h-screen bg-gray-950">
              <Routes>
                <Route path="/"          element={<ErrorBoundary><Home /></ErrorBoundary>} />
                <Route path="/dashboard" element={<ErrorBoundary><Dashboard /></ErrorBoundary>} />
                <Route path="/recommend" element={<ErrorBoundary><Recommend /></ErrorBoundary>} />
                <Route path="/tax"       element={<ErrorBoundary><TaxEngine /></ErrorBoundary>} />
                <Route path="/reports"   element={<ErrorBoundary><Reports /></ErrorBoundary>} />
                <Route path="/login"     element={<ErrorBoundary><Login /></ErrorBoundary>} />
                <Route path="/register"  element={<ErrorBoundary><Register /></ErrorBoundary>} />
                <Route path="*"          element={<ErrorBoundary><NotFound /></ErrorBoundary>} />
              </Routes>
            </div>
          </ErrorBoundary>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
