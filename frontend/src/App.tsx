import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClientProvider } from '@tanstack/react-query'
import { queryClient } from './services/queryClient'
import { lazy, Suspense } from 'react'
import Navbar from './components/Navbar'

const Home      = lazy(() => import('./pages/Home'))
const Dashboard = lazy(() => import('./pages/Dashboard'))

function PageLoader() {
  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center">
      <div className="w-8 h-8 border-3 border-blue-400 border-t-transparent rounded-full animate-spin" />
    </div>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-950 text-white">
          <Routes>
            <Route path="/" element={
              <><Navbar /><Suspense fallback={<PageLoader />}><Home /></Suspense></>
            } />
            <Route path="/dashboard" element={
              <Suspense fallback={<PageLoader />}><Dashboard /></Suspense>
            } />
          </Routes>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}