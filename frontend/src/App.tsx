import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { lazy, Suspense } from 'react'
import { AuthProvider } from './context/AuthContext'
import { queryClient } from './services/queryClient'
import Navbar from './components/Navbar'

const Home       = lazy(() => import('./pages/Home'))
const Dashboard  = lazy(() => import('./pages/Dashboard'))
const Recommend  = lazy(() => import('./pages/Recommend'))
const Login      = lazy(() => import('./pages/Login'))
const Register   = lazy(() => import('./pages/Register'))
const TaxEngine  = lazy(() => import('./pages/TaxEngine'))
const ReportsPage = lazy(() => import('./pages/ReportsPage'))


function PageLoader() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-gray-950 text-white">
            <Routes>
              <Route path="/" element={<><Navbar /><Suspense fallback={<PageLoader />}><Home /></Suspense></>} />
              <Route path="/dashboard" element={<Suspense fallback={<PageLoader />}><Dashboard /></Suspense>} />
              <Route path="/recommend" element={<Suspense fallback={<PageLoader />}><Recommend /></Suspense>} />
              <Route path="/tax"       element={<Suspense fallback={<PageLoader />}><TaxEngine /></Suspense>} />
              <Route path="/login"     element={<Suspense fallback={<PageLoader />}><Login /></Suspense>} />
              <Route path="/register"  element={<Suspense fallback={<PageLoader />}><Register /></Suspense>} />
              <Route path="/reports" element={<Suspense fallback={<PageLoader />}><ReportsPage /></Suspense>} />
            </Routes>
          </div>
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}