import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { BarChart3, Eye, EyeOff, AlertCircle, CheckCircle } from 'lucide-react'

export default function Register() {
  const { register } = useAuth()
  const navigate     = useNavigate()
  const [form,    setF] = useState({ email:'', username:'', password:'', confirm:'' })
  const [show,    setShow]    = useState(false)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState<string | null>(null)

  const pwOk  = form.password.length >= 8
  const cfOk  = form.password === form.confirm && form.confirm.length > 0

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!cfOk) { setError('Passwords do not match'); return }
    setError(null); setLoading(true)
    try { await register(form.email, form.username, form.password); navigate('/dashboard') }
    catch (err: any) { setError(err.response?.data?.detail || 'Registration failed') }
    finally { setLoading(false) }
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="inline-flex items-center gap-2 text-xl font-bold text-white mb-4">
            <div className="w-9 h-9 bg-blue-600 rounded-xl flex items-center justify-center">
              <BarChart3 size={20} />
            </div>
            Portfolio<span className="text-blue-400">AI</span>
          </Link>
          <h1 className="text-2xl font-bold text-white">Create your account</h1>
          <p className="text-gray-500 text-sm mt-1">Free forever · No credit card needed</p>
        </div>

        <div className="card p-8">
          <form onSubmit={submit} className="space-y-4">
            {[
              { label:'Email', type:'email', field:'email', placeholder:'you@example.com' },
              { label:'Username', type:'text', field:'username', placeholder:'yourname' },
            ].map(f => (
              <div key={f.field}>
                <label className="block text-gray-400 text-sm mb-1.5">{f.label}</label>
                <input type={f.type} required value={form[f.field as keyof typeof form]}
                  onChange={e => setF(p => ({...p, [f.field]: e.target.value}))}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 rounded-xl outline-none"
                  placeholder={f.placeholder} />
              </div>
            ))}

            <div>
              <label className="block text-gray-400 text-sm mb-1.5">Password</label>
              <div className="relative">
                <input type={show ? 'text' : 'password'} required value={form.password}
                  onChange={e => setF(p => ({...p, password: e.target.value}))}
                  className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 pr-11 rounded-xl outline-none"
                  placeholder="Min 8 characters" />
                <button type="button" onClick={() => setShow(!show)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 hover:text-gray-300">
                  {show ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
              {form.password.length > 0 && (
                <p className={`text-xs mt-1 flex items-center gap-1 ${pwOk ? 'text-green-400' : 'text-red-400'}`}>
                  {pwOk ? <CheckCircle size={10} /> : <AlertCircle size={10} />}
                  {pwOk ? 'Strong enough' : 'Min 8 characters'}
                </p>
              )}
            </div>

            <div>
              <label className="block text-gray-400 text-sm mb-1.5">Confirm Password</label>
              <input type="password" required value={form.confirm}
                onChange={e => setF(p => ({...p, confirm: e.target.value}))}
                className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 rounded-xl outline-none"
                placeholder="Repeat password" />
              {form.confirm.length > 0 && (
                <p className={`text-xs mt-1 flex items-center gap-1 ${cfOk ? 'text-green-400' : 'text-red-400'}`}>
                  {cfOk ? <CheckCircle size={10} /> : <AlertCircle size={10} />}
                  {cfOk ? 'Passwords match' : 'Do not match'}
                </p>
              )}
            </div>

            {error && (
              <div className="flex items-center gap-2 text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-xl px-4 py-3">
                <AlertCircle size={14} className="shrink-0" /> {error}
              </div>
            )}

            <button type="submit" disabled={loading || !pwOk || !cfOk}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-all mt-2">
              {loading
                ? <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Creating...</span>
                : 'Create Account →'}
            </button>
          </form>
          <p className="text-center text-gray-500 text-sm mt-6">
            Have an account? <Link to="/login" className="text-blue-400 hover:text-blue-300 font-medium">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}