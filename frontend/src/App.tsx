/**
 * App.tsx — Complete file.
 * All routes + ErrorBoundary wrapping every page.
 * React Query provider included.
 * ErrorBoundary catches React render crashes and shows
 * a recovery screen instead of a blank white page.
 */

import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import {
  QueryClient,
  QueryClientProvider,
} from '@tanstack/react-query'

import { ErrorBoundary } from './components/ErrorBoundary'
import { AuthProvider } from './context/AuthContext'
import Navbar from './components/Navbar'

// Pages
import Home from './pages/Home'
import Dashboard from './pages/Dashboard'
import Recommend from './pages/Recommend'
import TaxEngine from './pages/TaxEngine'
import Reports from './pages/Reports'
import Login from './pages/Login'
import Register from './pages/Register'

// React Query client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 2,
      refetchOnWindowFocus: false,
      staleTime: 60_000, // 1 min
      gcTime: 300_000, // 5 min
    },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AuthProvider>
          {/* Global crash protection */}
          <ErrorBoundary>
            <div className="min-h-screen bg-gray-950">
              {/* Navbar remains visible even if a page crashes */}
              <Navbar />

              <Routes>
                <Route
                  path="/"
                  element={
                    <ErrorBoundary>
                      <Home />
                    </ErrorBoundary>
                  }
                />

                <Route
                  path="/dashboard"
                  element={
                    <ErrorBoundary>
                      <Dashboard />
                    </ErrorBoundary>
                  }
                />

                <Route
                  path="/recommend"
                  element={
                    <ErrorBoundary>
                      <Recommend />
                    </ErrorBoundary>
                  }
                />

                <Route
                  path="/tax"
                  element={
                    <ErrorBoundary>
                      <TaxEngine />
                    </ErrorBoundary>
                  }
                />

                <Route
                  path="/reports"
                  element={
                    <ErrorBoundary>
                      <Reports />
                    </ErrorBoundary>
                  }
                />

                <Route
                  path="/login"
                  element={
                    <ErrorBoundary>
                      <Login />
                    </ErrorBoundary>
                  }
                />

                <Route
                  path="/register"
                  element={
                    <ErrorBoundary>
                      <Register />
                    </ErrorBoundary>
                  }
                />

                {/* 404 Fallback */}
                <Route
                  path="*"
                  element={
                    <div className="min-h-[60vh] flex flex-col items-center justify-center text-center px-4">
                      <p className="text-6xl font-black text-gray-800 mb-4">
                        404
                      </p>

                      <p className="text-white text-xl font-semibold mb-2">
                        Page not found
                      </p>

                      <p className="text-gray-500 text-sm mb-6">
                        The page you're looking for doesn't exist.
                      </p>

                      <Link
                        to="/"
                        className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2.5 rounded-xl text-sm font-medium transition-colors"
                      >
                        Go Home
                      </Link>
                    </div>
                  }
                />
              </Routes>
            </div>
          </ErrorBoundary>
        </AuthProvider>
      </BrowserRouter>
    </QueryClientProvider>
  )
}