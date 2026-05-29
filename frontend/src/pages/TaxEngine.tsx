import { useState, memo } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  Calculator, TrendingDown, TrendingUp,
  AlertTriangle, CheckCircle, Info,
  ChevronDown, ChevronUp, ArrowRight
} from 'lucide-react'

interface TaxResult {
  fy: string
  total_stcg: number; total_ltcg: number
  ltcg_exempt: number; ltcg_taxable: number
  stcg_tax: number; ltcg_tax: number
  total_tax: number; total_tax_with_cess: number
  tax_rates: Record<string, string>
  unrealised_gains: UnrealisedGain[]
  harvest_suggestions: HarvestSuggestion[]
  summary_text: string
}

interface UnrealisedGain {
  symbol: string; quantity: number
  avg_buy_price: number; current_price: number
  invested: number; current_value: number
  unrealised_gain: number; unrealised_pct: number
  estimated_tax_if_sold: { stcg: number; ltcg: number; saving: number }
  note: string
}

interface HarvestSuggestion {
  symbol: string; action: string
  unrealised_loss?: number; unrealised_gain?: number
  offsets_against: string; tax_saved: number
  explanation: string; buy_back_note: string
}

const fmt = (n: number) => `₹${n.toLocaleString('en-IN')}`
const fmtPct = (n: number) => `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`

function TaxCard({
  label, value, sub, color = 'text-white', highlight = false
}: {
  label: string; value: string; sub?: string
  color?: string; highlight?: boolean
}) {
  return (
    <div className={`card p-4 ${highlight ? 'border-blue-800/60 bg-blue-950/20' : ''}`}>
      <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">{label}</p>
      <p className={`text-2xl font-bold tabular-nums ${color}`}>{value}</p>
      {sub && <p className="text-gray-600 text-xs mt-1">{sub}</p>}
    </div>
  )
}

const HarvestCard = memo(function HarvestCard({ h }: { h: HarvestSuggestion }) {
  const [open, setOpen] = useState(false)
  const isLoss = h.action.includes("harvest loss")

  return (
    <div className={`border rounded-xl overflow-hidden ${
      isLoss ? 'border-green-800/40 bg-green-950/10' : 'border-blue-800/40 bg-blue-950/10'
    }`}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 p-4 text-left hover:bg-white/[0.02] transition-colors"
      >
        <div className={`w-8 h-8 rounded-lg flex items-center justify-center shrink-0 ${
          isLoss ? 'bg-green-900/40' : 'bg-blue-900/40'
        }`}>
          {isLoss ? <TrendingDown size={15} className="text-green-400" /> : <TrendingUp size={15} className="text-blue-400" />}
        </div>
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-white font-semibold text-sm">{h.symbol}</span>
            <span className={`text-xs px-2 py-0.5 rounded-full ${
              isLoss ? 'bg-green-900/40 text-green-400' : 'bg-blue-900/40 text-blue-400'
            }`}>{h.offsets_against}</span>
          </div>
          <p className="text-gray-400 text-xs mt-0.5">{h.action}</p>
        </div>
        {h.tax_saved > 0 && (
          <div className="text-right shrink-0">
            <p className="text-green-400 font-bold text-sm">{fmt(h.tax_saved)}</p>
            <p className="text-gray-600 text-xs">tax saved</p>
          </div>
        )}
        {open ? <ChevronUp size={13} className="text-gray-500 shrink-0" /> : <ChevronDown size={13} className="text-gray-500 shrink-0" />}
      </button>

      {open && (
        <div className="border-t border-white/[0.04] px-4 pb-4 pt-3 space-y-2">
          <p className="text-gray-300 text-sm leading-relaxed">{h.explanation}</p>
          <div className="bg-yellow-950/20 border border-yellow-800/40 rounded-lg px-3 py-2">
            <p className="text-yellow-300 text-xs">💡 {h.buy_back_note}</p>
          </div>
        </div>
      )}
    </div>
  )
})

export default function TaxEngine() {
  const navigate   = useNavigate()
  const [holdings, setHoldings] = useState<any[]>([])
  const [result,   setResult]   = useState<TaxResult | null>(null)
  const [loading,  setLoading]  = useState(false)
  const [error,    setError]    = useState<string | null>(null)
  const [inputJson, setInputJson] = useState('')
  const [mode,     setMode]     = useState<'paste' | 'result'>('paste')

  const calculate = async () => {
    let parsed: any[]
    try {
      parsed = JSON.parse(inputJson)
      if (!Array.isArray(parsed)) throw new Error("Must be array")
    } catch {
      setError('Invalid JSON. Paste your holdings as a JSON array.')
      return
    }

    setLoading(true); setError(null)
    try {
      const res = await axios.post('http://localhost:8000/api/tax/calculate', {
        holdings: parsed,
      }, { timeout: 30000 })
      setResult(res.data)
      setMode('result')
    } catch (e: any) {
      setError(e.response?.data?.detail || 'Calculation failed')
    } finally {
      setLoading(false) }
  }

  const EXAMPLE = JSON.stringify([
    { symbol: "RELIANCE.NS", quantity: 10, avg_buy_price: 2500, current_price: 2900 },
    { symbol: "INFY.NS",     quantity: 20, avg_buy_price: 1400, current_price: 1200 },
    { symbol: "TCS.NS",      quantity: 5,  avg_buy_price: 3200, current_price: 3800 },
  ], null, 2)

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-5xl mx-auto px-4 py-10">

        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-2 mb-2">
            <button onClick={() => navigate('/dashboard')} className="text-gray-500 hover:text-white text-sm">
              ← Dashboard
            </button>
          </div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-green-600/20 border border-green-700/40 rounded-xl flex items-center justify-center">
              <Calculator size={20} className="text-green-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">Tax P&L Calculator</h1>
              <p className="text-gray-500 text-sm">India Capital Gains — FY 2024-25 · Budget 2024 rates</p>
            </div>
          </div>
        </div>

        {/* Tax rates banner */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-8">
          {[
            { label: 'STCG Rate', value: '20%', sub: 'Held < 12 months', color: 'text-red-400' },
            { label: 'LTCG Rate', value: '12.5%', sub: 'Held ≥ 12 months', color: 'text-yellow-400' },
            { label: 'LTCG Exemption', value: '₹1.25L', sub: 'Per financial year', color: 'text-green-400' },
          ].map(r => (
            <div key={r.label} className="card p-4 text-center">
              <p className="text-gray-500 text-xs uppercase tracking-wide mb-1">{r.label}</p>
              <p className={`text-xl font-bold ${r.color}`}>{r.value}</p>
              <p className="text-gray-600 text-xs">{r.sub}</p>
            </div>
          ))}
        </div>

        {mode === 'paste' && (
          <div className="card p-6">
            <h2 className="text-white font-semibold mb-2">Enter Your Holdings</h2>
            <p className="text-gray-500 text-sm mb-4">
              Paste as JSON array with symbol, quantity, avg_buy_price, current_price
            </p>

            <div className="mb-3 flex justify-end">
              <button
                onClick={() => setInputJson(EXAMPLE)}
                className="text-xs text-blue-400 hover:text-blue-300 bg-blue-950/20 border border-blue-800/40 px-3 py-1.5 rounded-lg transition-colors"
              >
                Load Example
              </button>
            </div>

            <textarea
              value={inputJson}
              onChange={e => setInputJson(e.target.value)}
              className="w-full h-64 bg-gray-800 border border-gray-700 focus:border-blue-500 text-green-400 font-mono text-sm px-4 py-3 rounded-xl outline-none resize-none"
              placeholder={EXAMPLE}
            />

            {error && (
              <div className="mt-3 flex items-center gap-2 text-red-400 text-sm bg-red-950/20 border border-red-800 rounded-xl px-4 py-2.5">
                <AlertTriangle size={14} className="shrink-0" /> {error}
              </div>
            )}

            <button
              onClick={calculate}
              disabled={loading || !inputJson.trim()}
              className="mt-4 flex items-center gap-2 bg-green-600 hover:bg-green-500 disabled:opacity-50 text-white px-6 py-3 rounded-xl font-semibold transition-all"
            >
              {loading ? (
                <><div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />Calculating...</>
              ) : (
                <><Calculator size={16} /> Calculate Tax</>
              )}
            </button>

            {/* Info */}
            <div className="mt-6 bg-blue-950/20 border border-blue-800/30 rounded-xl p-4">
              <div className="flex items-start gap-2">
                <Info size={14} className="text-blue-400 shrink-0 mt-0.5" />
                <div className="text-xs text-gray-400 space-y-1">
                  <p>• FIFO method used for lot matching per CBDT guidelines</p>
                  <p>• Budget 2024 rates: STCG 20% (from Jul 23), LTCG 12.5%, exemption ₹1.25L</p>
                  <p>• 4% cess included in final computation</p>
                  <p>• This is an estimate — consult a CA for filing</p>
                </div>
              </div>
            </div>
          </div>
        )}

        {mode === 'result' && result && (
          <div className="space-y-6">

            {/* Back + FY */}
            <div className="flex items-center justify-between">
              <button onClick={() => setMode('paste')} className="text-gray-500 hover:text-white text-sm flex items-center gap-1">
                ← Recalculate
              </button>
              <span className="text-xs bg-gray-800 text-gray-400 px-3 py-1 rounded-full">{result.fy}</span>
            </div>

            {/* Summary text */}
            <div className="card p-5 border-l-4 border-blue-600">
              <p className="text-gray-300 text-sm leading-relaxed">{result.summary_text}</p>
            </div>

            {/* Tax cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <TaxCard label="STCG"        value={fmt(result.total_stcg)}          color="text-orange-400" />
              <TaxCard label="LTCG"        value={fmt(result.total_ltcg)}          color="text-yellow-400" />
              <TaxCard label="LTCG Exempt" value={fmt(result.ltcg_exempt)}         color="text-green-400" />
              <TaxCard
                label="Total Tax (+ Cess)"
                value={fmt(result.total_tax_with_cess)}
                color={result.total_tax_with_cess > 0 ? 'text-red-400' : 'text-green-400'}
                highlight
              />
            </div>

            {/* Tax breakdown */}
            <div className="card p-5">
              <h3 className="text-white font-semibold text-sm mb-4">Tax Breakdown</h3>
              <div className="space-y-2">
                {[
                  { label: `STCG Tax (${result.tax_rates.stcg})`,        value: result.stcg_tax,             color: 'text-orange-400' },
                  { label: `LTCG Tax (${result.tax_rates.ltcg})`,        value: result.ltcg_tax,             color: 'text-yellow-400' },
                  { label: `LTCG Exemption`,                              value: -result.ltcg_exempt,         color: 'text-green-400' },
                  { label: `4% Cess`,                                     value: result.total_tax_with_cess - result.total_tax, color: 'text-gray-400' },
                  { label: `Total Tax Liability`,                         value: result.total_tax_with_cess,  color: 'text-white', bold: true },
                ].map((row, i) => (
                  <div key={i} className={`flex items-center justify-between py-2 border-b border-white/[0.04] ${(row as any).bold ? 'font-bold' : ''}`}>
                    <span className="text-gray-400 text-sm">{row.label}</span>
                    <span className={`tabular-nums text-sm ${row.color}`}>
                      {row.value < 0 ? `-${fmt(-row.value)}` : fmt(row.value)}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* Unrealised P&L */}
            {result.unrealised_gains.length > 0 && (
              <div className="card p-5">
                <h3 className="text-white font-semibold text-sm mb-1">Unrealised Positions</h3>
                <p className="text-gray-600 text-xs mb-4">Tax owed only when you sell</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm min-w-[600px]">
                    <thead>
                      <tr className="border-b border-white/[0.06]">
                        {['Symbol','Qty','Avg Price','CMP','Unrealised P&L','If Sold Now (STCG)','If Held 12m (LTCG)','Saving'].map(h => (
                          <th key={h} className="text-left text-gray-600 text-xs py-2 pr-4 font-medium">{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {result.unrealised_gains.map(u => (
                        <tr key={u.symbol} className="border-b border-white/[0.03] hover:bg-white/[0.02]">
                          <td className="py-2.5 pr-4 text-blue-400 font-semibold">{u.symbol}</td>
                          <td className="py-2.5 pr-4 text-gray-400 tabular-nums">{u.quantity}</td>
                          <td className="py-2.5 pr-4 text-gray-400 tabular-nums">{fmt(u.avg_buy_price)}</td>
                          <td className="py-2.5 pr-4 text-gray-300 tabular-nums">{fmt(u.current_price)}</td>
                          <td className={`py-2.5 pr-4 font-medium tabular-nums ${u.unrealised_gain >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {fmt(u.unrealised_gain)} ({fmtPct(u.unrealised_pct)})
                          </td>
                          <td className="py-2.5 pr-4 text-orange-400 tabular-nums">
                            {fmt(u.estimated_tax_if_sold.stcg)}
                          </td>
                          <td className="py-2.5 pr-4 text-yellow-400 tabular-nums">
                            {fmt(u.estimated_tax_if_sold.ltcg)}
                          </td>
                          <td className="py-2.5 text-green-400 font-medium tabular-nums">
                            {fmt(u.estimated_tax_if_sold.saving)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Tax harvesting */}
            {result.harvest_suggestions.length > 0 && (
              <div>
                <div className="flex items-center gap-2 mb-4">
                  <h3 className="text-white font-semibold">🌱 Tax Harvesting Opportunities</h3>
                  <span className="text-xs bg-green-900/30 text-green-400 px-2 py-0.5 rounded-full">
                    {result.harvest_suggestions.length} suggestion{result.harvest_suggestions.length > 1 ? 's' : ''}
                  </span>
                </div>
                <div className="space-y-3">
                  {result.harvest_suggestions.map((h, i) => (
                    <HarvestCard key={i} h={h} />
                  ))}
                </div>
              </div>
            )}

            {result.harvest_suggestions.length === 0 && (
              <div className="card p-5 flex items-center gap-3">
                <CheckCircle size={20} className="text-green-400 shrink-0" />
                <div>
                  <p className="text-white font-medium text-sm">No harvesting needed</p>
                  <p className="text-gray-500 text-xs">Your portfolio is already optimized for tax efficiency.</p>
                </div>
              </div>
            )}

            {/* Disclaimer */}
            <div className="bg-yellow-950/20 border border-yellow-800/30 rounded-xl p-4">
              <div className="flex items-start gap-2">
                <AlertTriangle size={14} className="text-yellow-400 shrink-0 mt-0.5" />
                <p className="text-yellow-300/70 text-xs leading-relaxed">
                  This calculator provides estimates based on Budget 2024 rates for listed equity with STT paid.
                  Results are for educational purposes only. Please consult a Chartered Accountant for actual
                  ITR filing. Tax laws may change — always verify with official CBDT notifications.
                </p>
              </div>
            </div>

          </div>
        )}
      </div>
    </div>
  )
}