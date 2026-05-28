import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { BarChart3, Eye, EyeOff, AlertCircle } from 'lucide-react'

export default function Login() {
  const { login }    = useAuth()
  const navigate     = useNavigate()
  const [form,    setF] = useState({ email: '', password: '' })
  const [show,    setShow]    = useState(false)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault(); setError(null); setLoading(true)
    try { await login(form.email, form.password); navigate('/dashboard') }
    catch (err: any) { setError(err.response?.data?.detail || 'Invalid credentials') }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 text-xl font-bold text-white mb-4">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
              <BarChart3 size={20} />
            </div>
            Portfolio<span className="text-blue-400">AI</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Welcome back</h1>
          <p className="text-gray-500 text-sm mt-1">Sign in to access your portfolios</p>
        </div>

        <div className="card p-8">
          <form onSubmit={submit} className="space-y-5">
            <div>
              <label className="block text-gray-400 text-sm mb-1.5">Email</label>
              <input type="email" required value={form.email}
                onChange={e => setF(p => ({ ...p, email: e.target.value }))}
                className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 rounded-xl outline-none"
                placeholder="you@example.com" />
            </div>
            <div>
              <label className="block text-gray-400 text-sm mb-1.5">Password</label>
              <div className="relative">
                <input type={show ? 'text' : 'password'} required value={form.password}
                  onChange={e => setF(p => ({ ...p, password: e.target.value }))}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 pr-11 rounded-xl outline-none"
                  placeholder="••••••••" />
                <button type="button" onClick={() => setShow(!show)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>
            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-xl px-4 py-3">
                <AlertCircle size={14} className="shrink-0" /> {error}
              </div>
            )}
            <button type="submit" disabled={loading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white py-3 rounded-xl font-semibold transition-all">
              {loading
                ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Signing in...</span>
                : 'Sign In'}
            </button>
          </form>
          <p className="text-center text-gray-500 text-sm mt-6">
            No account?{' '}
            <Link to="/register" className="text-blue-400 hover:text-blue-300 font-medium">Create one free</Link>
          </p>
        </div>
      </div>
    </div>
  )
}