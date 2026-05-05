import { useState } from 'react'
import axios from 'axios'
import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react'

interface HoldingImpact {
  symbol: string
  sector: string
  current_value: number
  estimated_loss: number
  estimated_value_after: number
  drop_pct: number
}

interface ScenarioResult {
  scenario: string
  total_portfolio_value: number
  total_loss: number
  total_loss_pct: number
  value_after: number
  holdings: HoldingImpact[]
}

interface Props {
  holdings: any[]
}

export default function ScenarioSimulator({ holdings }: Props) {
  const [results, setResults]   = useState<ScenarioResult[]>([])
  const [loading, setLoading]   = useState(false)
  const [expanded, setExpanded] = useState<string | null>(null)
  const [ran, setRan]           = useState(false)

  const runSimulation = async () => {
    setLoading(true)
    try {
      const res = await axios.post(
        'http://localhost:8000/api/analytics/simulate',
        { holdings }
      )
      setResults(res.data.scenarios || [])
      setRan(true)
    } catch {
      /* silent */
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-white font-semibold text-lg">
            💥 Crash Scenario Simulator
          </h3>
          <p className="text-gray-500 text-sm mt-1">
            What happens to your portfolio under various market crashes?
          </p>
        </div>
        {!ran && (
          <button
            onClick={runSimulation}
            disabled={loading}
            className="bg-red-600/20 hover:bg-red-600/40 border border-red-700 text-red-400 px-4 py-2 rounded-lg text-sm transition-colors disabled:opacity-50"
          >
            {loading ? 'Simulating...' : '⚡ Run Simulation'}
          </button>
        )}
      </div>

      {loading && (
        <div className="text-center py-8">
          <div className="w-8 h-8 border-4 border-red-400 border-t-transparent rounded-full animate-spin mx-auto mb-3" />
          <p className="text-gray-400 text-sm">Running crash scenarios...</p>
        </div>
      )}

      {results.length > 0 && (
        <div className="space-y-3">
          {results.map((scenario) => {
            const isExpanded = expanded === scenario.scenario
            const severity =
              scenario.total_loss_pct > 25 ? 'high' :
              scenario.total_loss_pct > 15 ? 'medium' : 'low'

            const borderColor =
              severity === 'high'   ? 'border-red-800' :
              severity === 'medium' ? 'border-yellow-800' :
              'border-gray-700'

            const bgColor =
              severity === 'high'   ? 'bg-red-950/20' :
              severity === 'medium' ? 'bg-yellow-950/20' :
              'bg-gray-800/20'

            return (
              <div
                key={scenario.scenario}
                className={`border rounded-xl overflow-hidden ${borderColor} ${bgColor}`}
              >
                {/* Header */}
                <button
                  onClick={() => setExpanded(
                    isExpanded ? null : scenario.scenario
                  )}
                  className="w-full flex items-center justify-between px-5 py-4"
                >
                  <div className="flex items-center gap-4">
                    <AlertTriangle
                      size={16}
                      className={
                        severity === 'high'   ? 'text-red-400' :
                        severity === 'medium' ? 'text-yellow-400' :
                        'text-gray-400'
                      }
                    />
                    <span className="text-white font-medium text-sm">
                      {scenario.scenario}
                    </span>
                  </div>
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <p className="text-red-400 font-bold">
                        -₹{scenario.total_loss.toLocaleString()}
                      </p>
                      <p className="text-gray-500 text-xs">
                        -{scenario.total_loss_pct.toFixed(1)}% loss
                      </p>
                    </div>
                    {isExpanded
                      ? <ChevronUp size={16} className="text-gray-400" />
                      : <ChevronDown size={16} className="text-gray-400" />
                    }
                  </div>
                </button>

                {/* Expanded holdings */}
                {isExpanded && (
                  <div className="border-t border-gray-800 px-5 pb-4">
                    <div className="grid grid-cols-2 gap-4 py-4 mb-4">
                      <div>
                        <p className="text-gray-500 text-xs">Current Value</p>
                        <p className="text-white font-semibold">
                          ₹{scenario.total_portfolio_value.toLocaleString()}
                        </p>
                      </div>
                      <div>
                        <p className="text-gray-500 text-xs">Value After Crash</p>
                        <p className="text-red-400 font-semibold">
                          ₹{scenario.value_after.toLocaleString()}
                        </p>
                      </div>
                    </div>

                    <div className="space-y-2">
                      {scenario.holdings.slice(0, 8).map((h) => (
                        <div
                          key={h.symbol}
                          className="flex items-center justify-between text-sm"
                        >
                          <div className="flex items-center gap-2">
                            <span className="text-blue-400 w-28 shrink-0">
                              {h.symbol}
                            </span>
                            <span className="text-gray-500 text-xs">
                              {h.sector}
                            </span>
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="text-red-400 text-xs">
                              -{h.drop_pct}%
                            </span>
                            <span className="text-red-400">
                              -₹{h.estimated_loss.toLocaleString()}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )
          })}

          <button
            onClick={() => { setResults([]); setRan(false) }}
            className="text-xs text-gray-500 hover:text-gray-300 mt-2"
          >
            Reset simulation
          </button>
        </div>
      )}
    </div>
  )
}