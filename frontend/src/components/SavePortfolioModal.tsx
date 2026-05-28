import { useState, useEffect } from 'react'
import { Save, X, Check, Plus } from 'lucide-react'
import { portfolioService } from '../services/auth'
import { useAuth } from '../context/AuthContext'
import { Link } from 'react-router-dom'

interface Props {
  holdings: any[]; summary: any
  onClose: () => void; onSaved: (id: number, name: string) => void
}

export default function SavePortfolioModal({ holdings, summary, onClose, onSaved }: Props) {
  const { isLoggedIn } = useAuth()
  const [portfolios, setPortfolios] = useState<any[]>([])
  const [loading,    setLoading]    = useState(false)
  const [saving,     setSaving]     = useState(false)
  const [saved,      setSaved]      = useState(false)
  const [selected,   setSelected]   = useState<number | null>(null)
  const [newName,    setNewName]     = useState('')
  const [mode,       setMode]        = useState<'select'|'new'>('select')
  const [error,      setError]       = useState<string|null>(null)

  useEffect(() => {
    if (!isLoggedIn) return
    setLoading(true)
    portfolioService.list()
      .then(r => setPortfolios(r.data.portfolios || []))
      .catch(() => setError('Could not load portfolios'))
      .finally(() => setLoading(false))
  }, [isLoggedIn])

  const save = async () => {
    setSaving(true); setError(null)
    try {
      let pid: number; let name: string
      if (mode === 'new') {
        if (!newName.trim()) { setError('Enter a name'); return }
        const r = await portfolioService.create(newName.trim())
        pid = r.data.id; name = newName.trim()
      } else {
        if (!selected) { setError('Select a portfolio'); return }
        pid = selected
        name = portfolios.find(p => p.id === selected)?.name ?? ''
      }
      await portfolioService.saveHoldings(pid, holdings, summary)
      setSaved(true)
      setTimeout(() => { onSaved(pid, name); onClose() }, 900)
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Save failed')
    } finally { setSaving(false) }
  }

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center px-4">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-md shadow-2xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-800">
          <h2 className="text-white font-semibold flex items-center gap-2">
            <Save size={15} className="text-blue-400" /> Save Portfolio
          </h2>
          <button onClick={onClose} className="text-gray-500 hover:text-white"><X size={17} /></button>
        </div>

        <div className="p-6 space-y-4">
          {!isLoggedIn ? (
            <div className="text-center py-6">
              <p className="text-gray-400 text-sm mb-4">Sign in to save your portfolio</p>
              <Link to="/login" className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-xl text-sm font-medium">
                Sign In
              </Link>
            </div>
          ) : (
            <>
              <div className="flex gap-1 p-1 bg-gray-800 rounded-xl">
                {(['select','new'] as const).map(m => (
                  <button key={m} onClick={() => setMode(m)}
                    className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors ${mode===m ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'}`}>
                    {m === 'select' ? 'Existing' : '+ New'}
                  </button>
                ))}
              </div>

              {mode === 'select' && (
                <div className="space-y-2 max-h-52 overflow-y-auto">
                  {loading ? (
                    <p className="text-gray-500 text-sm text-center py-4">Loading...</p>
                  ) : portfolios.length === 0 ? (
                    <div className="text-center py-4">
                      <p className="text-gray-500 text-sm">No saved portfolios yet</p>
                      <button onClick={() => setMode('new')} className="text-blue-400 text-sm mt-1 flex items-center gap-1 mx-auto">
                        <Plus size={12} /> Create first portfolio
                      </button>
                    </div>
                  ) : portfolios.map(p => (
                    <button key={p.id} onClick={() => setSelected(p.id)}
                      className={`w-full flex items-center justify-between px-4 py-3 rounded-xl border transition-colors ${selected===p.id ? 'border-blue-600 bg-blue-950/30' : 'border-gray-700 hover:border-gray-600'}`}>
                      <div className="text-left">
                        <p className="text-white text-sm font-medium">{p.name}</p>
                        <p className="text-gray-500 text-xs">{p.holdings_count} holdings</p>
                      </div>
                      {selected===p.id && <Check size={15} className="text-blue-400" />}
                    </button>
                  ))}
                </div>
              )}

              {mode === 'new' && (
                <div>
                  <label className="block text-gray-400 text-sm mb-1.5">Portfolio Name</label>
                  <input value={newName} onChange={e => setNewName(e.target.value)}
                    placeholder="e.g. Long Term Growth"
                    className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 rounded-xl outline-none"
                    maxLength={50} />
                </div>
              )}

              {error && <p className="text-red-400 text-sm bg-red-950/20 border border-red-800 rounded-xl px-3 py-2">{error}</p>}

              <button onClick={save}
                disabled={saving || saved || (mode==='select' && !selected) || (mode==='new' && !newName.trim())}
                className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-3 rounded-xl font-semibold transition-all">
                {saved ? (
                  <span className="flex items-center justify-center gap-2 text-green-300"><Check size={15} /> Saved!</span>
                ) : saving ? (
                  <span className="flex items-center justify-center gap-2"><span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Saving...</span>
                ) : (
                  <span className="flex items-center justify-center gap-2"><Save size={14} /> Save {holdings.length} Holdings</span>
                )}
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  )
}