/**
 * pages/Reports.tsx — Complete file.
 * Fixed: both axios.post(localhost:8000) calls -> API_BASE
 */
import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'
import {
  FileText, Download, Loader2, CheckCircle,
  BarChart3, Shield, Calculator, AlertTriangle,
  Eye, Sparkles
} from 'lucide-react'
import { API_BASE } from '../config/api'

interface ReportConfig {
  portfolio_name: string
  include_tax:    boolean
}

interface Props {
  holdings?:        any[]
  summary?:         any
  riskMetrics?:     any
  advancedMetrics?: any
}

const SECTIONS = [
  { icon: <BarChart3 size={16} className="text-blue-400" />,  label: 'Portfolio Summary',      desc: 'Total invested, P&L, returns' },
  { icon: <Shield size={16} className="text-purple-400" />,   label: 'Risk Analytics',         desc: 'Sharpe, VaR, Drawdown, Beta' },
  { icon: <Eye size={16} className="text-green-400" />,       label: 'Visual Charts',          desc: 'Sector allocation + P&L chart' },
  { icon: <FileText size={16} className="text-yellow-400" />, label: 'Holdings Table',         desc: 'All positions with live P&L' },
  { icon: <Calculator size={16} className="text-orange-400"/>,label: 'Tax P&L (optional)',     desc: 'STCG/LTCG + harvest ideas' },
  { icon: <Sparkles size={16} className="text-pink-400" />,   label: 'AI Interpretation',      desc: 'Risk explanations in plain English' },
]

export default function Reports({
  holdings = [], summary = {}, riskMetrics, advancedMetrics
}: Props) {
  const navigate = useNavigate()

  const [config,    setConfig]    = useState<ReportConfig>({
    portfolio_name: 'My Portfolio',
    include_tax:    false,
  })
  const [loading,   setLoading]   = useState(false)
  const [error,     setError]     = useState<string | null>(null)
  const [generated, setGenerated] = useState(false)

  const hasHoldings = holdings.length > 0

  const generateReport = useCallback(async () => {
    if (!hasHoldings) return

    setLoading(true); setError(null)

    // Optionally compute tax
    let taxData = null
    if (config.include_tax && holdings.length > 0) {
      try {
        const taxRes = await axios.post(
          `${API_BASE}/api/tax/calculate`,
          { holdings },
          { timeout: 20000 }
        )
        taxData = taxRes.data
      } catch { /* tax optional — continue without */ }
    }

    try {
      const res = await axios.post(
        `${API_BASE}/api/reports/generate`,
        {
          holdings,
          summary,
          risk_metrics:     riskMetrics     || null,
          advanced_metrics: advancedMetrics || null,
          tax_data:         taxData,
          portfolio_name:   config.portfolio_name,
        },
        {
          responseType: 'blob',
          timeout:      60000,
        }
      )

      // Trigger browser download
      const url      = URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }))
      const link     = document.createElement('a')
      const filename = `portfolio_report_${new Date().toISOString().slice(0,10)}.pdf`
      link.href      = url
      link.download  = filename
      link.click()
      URL.revokeObjectURL(url)

      setGenerated(true)
      setTimeout(() => setGenerated(false), 5000)

    } catch (e: any) {
      const msg = e.response?.data
        ? new TextDecoder().decode(await e.response.data.arrayBuffer?.() || e.response.data)
        : e.message
      try {
        setError(JSON.parse(msg)?.detail || msg)
      } catch {
        setError(String(msg))
      }
    } finally {
      setLoading(false)
    }
  }, [holdings, summary, riskMetrics, advancedMetrics, config])

  return (
    <div className="min-h-screen bg-gray-950">
      <div className="max-w-3xl mx-auto px-4 py-10">

        <div className="mb-8">
          <button
            onClick={() => navigate('/dashboard')}
            className="text-gray-500 hover:text-white text-sm mb-3 block"
          >
            ← Dashboard
          </button>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-blue-600/20 border border-blue-700/40 rounded-xl flex items-center justify-center">
              <FileText size={20} className="text-blue-400" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-white">PDF Report Generator</h1>
              <p className="text-gray-500 text-sm">
                Institutional-grade portfolio report · A4 PDF · Instant download
              </p>
            </div>
          </div>
        </div>

        <div className="card p-6 mb-6">
          <h2 className="text-white font-semibold text-sm mb-4">
            What's included in your report
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {SECTIONS.map(sec => (
              <div key={sec.label} className="flex items-start gap-3 bg-gray-800/30 rounded-xl p-3">
                <div className="mt-0.5 shrink-0">{sec.icon}</div>
                <div>
                  <p className="text-white text-sm font-medium">{sec.label}</p>
                  <p className="text-gray-500 text-xs mt-0.5">{sec.desc}</p>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="card p-6 mb-6 space-y-4">
          <h2 className="text-white font-semibold text-sm mb-2">Report Options</h2>

          <div>
            <label className="block text-gray-400 text-sm mb-1.5">Portfolio Name</label>
            <input
              type="text"
              value={config.portfolio_name}
              onChange={e => setConfig(p => ({...p, portfolio_name: e.target.value}))}
              className="w-full bg-gray-800 border border-gray-700 focus:border-blue-500 text-white px-4 py-3 rounded-xl outline-none"
              placeholder="My Portfolio"
              maxLength={50}
            />
          </div>

          <label className="flex items-center gap-3 cursor-pointer select-none">
            <div
              onClick={() => setConfig(p => ({...p, include_tax: !p.include_tax}))}
              className={`w-10 h-6 rounded-full transition-colors ${
                config.include_tax ? 'bg-green-600' : 'bg-gray-700'
              }`}
            >
              <div className={`w-5 h-5 bg-white rounded-full mt-0.5 transition-transform shadow ${
                config.include_tax ? 'translate-x-4.5 ml-0.5' : 'ml-0.5'
              }`} />
            </div>
            <div>
              <p className="text-white text-sm font-medium">Include Tax P&L section</p>
              <p className="text-gray-500 text-xs">
                Adds STCG/LTCG estimates and tax harvesting opportunities
              </p>
            </div>
          </label>
        </div>

        {hasHoldings && (
          <div className="card p-4 mb-6">
            <p className="text-gray-500 text-xs font-medium uppercase tracking-wide mb-3">
              Report will include
            </p>
            <div className="flex flex-wrap gap-2">
              {[
                { label: `${holdings.length} Holdings`, color: 'bg-blue-900/30 text-blue-400' },
                riskMetrics && { label: 'Risk Metrics', color: 'bg-purple-900/30 text-purple-400' },
                advancedMetrics && { label: 'Advanced Analytics', color: 'bg-green-900/30 text-green-400' },
                { label: 'Sector Chart', color: 'bg-yellow-900/30 text-yellow-400' },
                { label: 'P&L Chart',    color: 'bg-orange-900/30 text-orange-400' },
                config.include_tax && { label: 'Tax Analysis', color: 'bg-red-900/30 text-red-400' },
              ].filter(Boolean).map((item: any) => (
                <span key={item.label} className={`text-xs px-3 py-1.5 rounded-full font-medium ${item.color}`}>
                  ✓ {item.label}
                </span>
              ))}
            </div>
          </div>
        )}

        {error && (
          <div className="flex items-start gap-2 text-red-400 text-sm bg-red-950/30 border border-red-800 rounded-xl px-4 py-3 mb-4">
            <AlertTriangle size={15} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        {!hasHoldings ? (
          <div className="card p-8 text-center">
            <FileText size={40} className="text-gray-700 mx-auto mb-3" />
            <p className="text-gray-400 font-medium mb-1">No portfolio loaded</p>
            <p className="text-gray-600 text-sm mb-4">
              Upload your portfolio first to generate a report
            </p>
            <button
              onClick={() => navigate('/dashboard')}
              className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-2 rounded-xl text-sm font-medium transition-colors"
            >
              Go to Dashboard →
            </button>
          </div>
        ) : (
          <button
            onClick={generateReport}
            disabled={loading}
            className="w-full flex items-center justify-center gap-3 bg-blue-600 hover:bg-blue-500 disabled:opacity-60 text-white py-4 rounded-xl font-bold text-lg transition-all shadow-2xl shadow-blue-600/20"
          >
            {loading ? (
              <>
                <Loader2 size={20} className="animate-spin" />
                Generating PDF... (10-30s)
              </>
            ) : generated ? (
              <>
                <CheckCircle size={20} className="text-green-300" />
                Downloaded! Generate Another
              </>
            ) : (
              <>
                <Download size={20} />
                Download PDF Report
              </>
            )}
          </button>
        )}

        <div className="mt-4 bg-gray-800/30 border border-gray-700/40 rounded-xl p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle size={13} className="text-yellow-400 shrink-0 mt-0.5" />
            <p className="text-gray-600 text-xs leading-relaxed">
              Report generation takes 10–30 seconds. It fetches risk metrics and builds charts.
              The PDF opens as a download — check your browser's Downloads folder.
              All data is processed locally on your machine.
            </p>
          </div>
        </div>

      </div>
    </div>
  )
}
