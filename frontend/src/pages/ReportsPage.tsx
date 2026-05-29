import { useEffect, useState } from 'react'
import Reports from './Reports'

export default function ReportsPage() {
  const [data, setData] = useState<any>({
    holdings:        [],
    summary:         {},
    riskMetrics:     null,
    advancedMetrics: null,
  })

  useEffect(() => {
    // Try to load portfolio data from sessionStorage
    // (Dashboard writes here when user navigates to reports)
    try {
      const raw = sessionStorage.getItem('pa_portfolio')
      if (raw) {
        setData(JSON.parse(raw))
      }
    } catch { /* silent */ }
  }, [])

  return (
    <Reports
      holdings={data.holdings}
      summary={data.summary}
      riskMetrics={data.riskMetrics}
      advancedMetrics={data.advancedMetrics}
    />
  )
}