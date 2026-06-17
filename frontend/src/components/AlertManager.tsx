/**
 * components/AlertManager.tsx — Complete file.
 * Fixed: hardcoded axios calls to localhost:8000 -> API_BASE
 * Fixed: unused 'memo' import, unused 'loading'/'setLoading' state
 */
import { useState, useEffect } from 'react'
import axios from 'axios'
import { Bell, Plus, Trash2, X, Check, AlertTriangle, TrendingDown } from 'lucide-react'
import { API_BASE } from '../config/api'

interface AlertRule {
  id: number; symbol: string; alert_type: string
  threshold: number; is_active: number; triggered_count: number
  last_triggered: string | null
}
interface AlertHistoryItem {
  id: number; symbol: string; alert_type: string
  message: string; value: number; severity: string
  is_read: number; created_at: string
}

const ALERT_TYPES = [
  { value: 'price_above',    label: 'Price above',     unit: '₹' },
  { value: 'price_below',    label: 'Price below',     unit: '₹' },
  { value: 'price_up_pct',   label: 'Up % from buy',   unit: '%' },
  { value: 'price_down_pct', label: 'Down % from buy', unit: '%' },
]

const SEVERITY_COLOR: Record<string, string> = {
  high:   'text-red-400 bg-red-950/30 border-red-800/40',
  medium: 'text-yellow-400 bg-yellow-950/30 border-yellow-800/40',
  low:    'text-green-400 bg-green-950/30 border-green-800/40',
}

interface Props {
  holdings: any[]
  onClose:  () => void
}

export default function AlertManager({ holdings, onClose }: Props) {
  const [tab,       setTab]       = useState<'rules'|'history'>('rules')
  const [rules,     setRules]     = useState<AlertRule[]>([])
  const [history,   setHistory]   = useState<AlertHistoryItem[]>([])
  const [unread,    setUnread]    = useState(0)
  const [form,      setForm]      = useState({ symbol:'', alert_type:'price_below', threshold:'' })
  const [adding,    setAdding]    = useState(false)
  const [showForm,  setShowForm]  = useState(false)

  useEffect(() => {
    loadRules()
    loadHistory()
  }, [])

  const loadRules = () => {
    axios.get(`${API_BASE}/api/alerts/rules`)
      .then(r => setRules(r.data.rules || []))
      .catch(() => {})
  }

  const loadHistory = () => {
    axios.get(`${API_BASE}/api/alerts/history?limit=30`)
      .then(r => {
        setHistory(r.data.alerts || [])
        setUnread(r.data.unread_count || 0)
      })
      .catch(() => {})
  }

  const addRule = async () => {
    if (!form.symbol || !form.threshold) return
    setAdding(true)
    try {
      await axios.post(`${API_BASE}/api/alerts/rules`, {
        symbol:     form.symbol.toUpperCase(),
        alert_type: form.alert_type,
        threshold:  Number(form.threshold),
      })
      setForm({ symbol:'', alert_type:'price_below', threshold:'' })
      setShowForm(false)
      loadRules()
    } catch { }
    finally { setAdding(false) }
  }

  const deleteRule = async (id: number) => {
    try {
      await axios.delete(`${API_BASE}/api/alerts/rules/${id}`)
      loadRules()
    } catch {}
  }

  const markAllRead = async () => {
    await axios.post(`${API_BASE}/api/alerts/mark-read`, { all: true })
    loadHistory()
  }

  const symbols = holdings.map(h => h.symbol)

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-start justify-end">
      <div className="bg-gray-900 border-l border-gray-700 w-full max-w-md h-full overflow-y-auto shadow-2xl">

        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-800 sticky top-0 bg-gray-900 z-10">
          <div className="flex items-center gap-2">
            <Bell size={17} className="text-blue-400" />
            <h2 className="text-white font-semibold">Price Alerts</h2>
            {unread > 0 && (
              <span className="bg-red-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                {unread}
              </span>
            )}
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-white">
            <X size={18} />
          </button>
        </div>

        <div className="flex gap-1 p-3 bg-gray-800/50">
          {(['rules','history'] as const).map(t => (
            <button key={t} onClick={() => setTab(t)}
              className={`flex-1 py-2 rounded-lg text-sm font-medium transition-colors capitalize ${
                tab === t ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
              }`}>
              {t}
              {t === 'history' && unread > 0 && (
                <span className="ml-1.5 bg-red-600 text-white text-xs px-1.5 py-0.5 rounded-full">
                  {unread}
                </span>
              )}
            </button>
          ))}
        </div>

        <div className="p-4 space-y-4">

          {tab === 'rules' && (
            <>
              <button
                onClick={() => setShowForm(!showForm)}
                className="w-full flex items-center justify-center gap-2 border border-dashed border-blue-700/60 text-blue-400 hover:bg-blue-950/20 py-3 rounded-xl text-sm transition-colors"
              >
                <Plus size={15} /> Add Alert Rule
              </button>

              {showForm && (
                <div className="card p-4 space-y-3">
                  <div>
                    <label className="block text-gray-400 text-xs mb-1">Symbol</label>
                    <select
                      value={form.symbol}
                      onChange={e => setForm(p => ({...p, symbol: e.target.value}))}
                      className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm outline-none"
                    >
                      <option value="">Select holding...</option>
                      {symbols.map(s => (
                        <option key={s} value={s}>{s}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-gray-400 text-xs mb-1">Alert Type</label>
                    <select
                      value={form.alert_type}
                      onChange={e => setForm(p => ({...p, alert_type: e.target.value}))}
                      className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm outline-none"
                    >
                      {ALERT_TYPES.map(t => (
                        <option key={t.value} value={t.value}>{t.label}</option>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="block text-gray-400 text-xs mb-1">
                      Threshold ({ALERT_TYPES.find(t => t.value === form.alert_type)?.unit ?? ''})
                    </label>
                    <input
                      type="number"
                      value={form.threshold}
                      onChange={e => setForm(p => ({...p, threshold: e.target.value}))}
                      className="w-full bg-gray-800 border border-gray-700 text-white px-3 py-2 rounded-lg text-sm outline-none"
                      placeholder="e.g. 2500"
                    />
                  </div>

                  <div className="flex gap-2">
                    <button onClick={() => setShowForm(false)}
                      className="flex-1 text-gray-400 border border-gray-700 py-2 rounded-lg text-sm">
                      Cancel
                    </button>
                    <button onClick={addRule} disabled={adding || !form.symbol || !form.threshold}
                      className="flex-1 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white py-2 rounded-lg text-sm font-medium">
                      {adding ? 'Adding...' : 'Add Alert'}
                    </button>
                  </div>
                </div>
              )}

              {rules.length === 0 ? (
                <div className="text-center py-8">
                  <Bell size={32} className="text-gray-700 mx-auto mb-2" />
                  <p className="text-gray-500 text-sm">No alert rules yet</p>
                  <p className="text-gray-600 text-xs mt-1">Add a rule to get notified on price moves</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {rules.map(r => {
                    const typeInfo = ALERT_TYPES.find(t => t.value === r.alert_type)
                    return (
                      <div key={r.id} className="flex items-center justify-between bg-gray-800/50 border border-gray-700/60 rounded-xl px-4 py-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="text-white font-semibold text-sm">{r.symbol}</span>
                            <span className="text-xs bg-gray-700 text-gray-300 px-2 py-0.5 rounded">
                              {typeInfo?.label ?? r.alert_type}
                            </span>
                          </div>
                          <p className="text-gray-500 text-xs mt-0.5">
                            Threshold: {typeInfo?.unit}{r.threshold.toLocaleString()}
                            {r.triggered_count > 0 && ` · Triggered ${r.triggered_count}×`}
                          </p>
                        </div>
                        <button onClick={() => deleteRule(r.id)}
                          className="text-gray-600 hover:text-red-400 transition-colors ml-3">
                          <Trash2 size={14} />
                        </button>
                      </div>
                    )
                  })}
                </div>
              )}
            </>
          )}

          {tab === 'history' && (
            <>
              {unread > 0 && (
                <button onClick={markAllRead}
                  className="w-full flex items-center justify-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 border border-blue-800/40 bg-blue-950/10 py-2 rounded-lg transition-colors">
                  <Check size={12} /> Mark all as read
                </button>
              )}

              {history.length === 0 ? (
                <div className="text-center py-8">
                  <AlertTriangle size={32} className="text-gray-700 mx-auto mb-2" />
                  <p className="text-gray-500 text-sm">No alerts triggered yet</p>
                  <p className="text-gray-600 text-xs mt-1">Alerts appear here when thresholds are hit</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {history.map(a => (
                    <div key={a.id} className={`border rounded-xl px-4 py-3 ${
                      SEVERITY_COLOR[a.severity] ?? 'text-gray-400 bg-gray-800 border-gray-700'
                    } ${!a.is_read ? 'opacity-100' : 'opacity-60'}`}>
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          <div className="flex items-center gap-2 mb-0.5">
                            <span className="font-semibold text-sm">{a.symbol}</span>
                            {!a.is_read && (
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                            )}
                          </div>
                          <p className="text-xs opacity-80 leading-relaxed">{a.message}</p>
                          <p className="text-xs opacity-50 mt-1">
                            {new Date(a.created_at).toLocaleString('en-IN')}
                          </p>
                        </div>
                        {a.severity === 'high' && (
                          <TrendingDown size={16} className="shrink-0 mt-0.5" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
