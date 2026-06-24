/**
 * components/Skeletons.tsx — Complete file. (NEW — Day 3)
 * Reusable loading skeleton components.
 * Prevents the empty flash when dashboard is loading.
 *
 * Usage:
 *   import { CardSkeleton, TableSkeleton, ChartSkeleton } from './components/Skeletons'
 *   {loading ? <CardSkeleton /> : <ActualComponent />}
 */
function Pulse({ className }: { className: string }) {
  return <div className={`animate-pulse bg-gray-800/60 rounded-lg ${className}`} />
}

/** 4 stat cards in a row */
export function StatCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      {[...Array(4)].map((_, i) => (
        <div key={i} className="card p-5">
          <Pulse className="h-3 w-20 mb-3" />
          <Pulse className="h-7 w-28 mb-2" />
          <Pulse className="h-3 w-16" />
        </div>
      ))}
    </div>
  )
}

/** Holdings table rows */
export function TableSkeleton({ rows = 5 }: { rows?: number }) {
  return (
    <div className="card overflow-hidden">
      <div className="px-5 py-4 border-b border-white/[0.04]">
        <Pulse className="h-4 w-32" />
      </div>
      <div className="divide-y divide-white/[0.04]">
        {[...Array(rows)].map((_, i) => (
          <div key={i} className="flex items-center gap-4 px-5 py-3.5">
            <Pulse className="h-4 w-24" />
            <Pulse className="h-4 w-16 hidden md:block" />
            <Pulse className="h-4 w-12 hidden md:block" />
            <div className="ml-auto flex items-center gap-3">
              <Pulse className="h-4 w-16" />
              <Pulse className="h-4 w-16" />
              <Pulse className="h-5 w-14 rounded-full" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

/** Chart area */
export function ChartSkeleton({ height = 'h-52' }: { height?: string }) {
  return (
    <div className={`card p-5 ${height}`}>
      <div className="flex items-center justify-between mb-4">
        <Pulse className="h-4 w-32" />
        <Pulse className="h-6 w-24 rounded-full" />
      </div>
      <div className="flex items-end gap-1 h-32">
        {[40, 65, 45, 80, 55, 70, 50, 90, 60, 75, 85, 65].map((h, i) => (
          <div
            key={i}
            className="flex-1 bg-gray-800/60 rounded-sm animate-pulse"
            style={{ height: `${h}%`, animationDelay: `${i * 50}ms` }}
          />
        ))}
      </div>
    </div>
  )
}

/** Risk metric cards */
export function RiskCardsSkeleton() {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
      {[...Array(6)].map((_, i) => (
        <div key={i} className="card p-4">
          <Pulse className="h-3 w-20 mb-2" />
          <Pulse className="h-6 w-24 mb-1" />
          <Pulse className="h-2 w-full rounded-full" />
        </div>
      ))}
    </div>
  )
}

/** Single card placeholder */
export function CardSkeleton({ className = '' }: { className?: string }) {
  return (
    <div className={`card p-5 ${className}`}>
      <Pulse className="h-4 w-32 mb-4" />
      <Pulse className="h-3 w-full mb-2" />
      <Pulse className="h-3 w-4/5 mb-2" />
      <Pulse className="h-3 w-3/5" />
    </div>
  )
}

/** Full dashboard skeleton — shown on first load before any data */
export function DashboardSkeleton() {
  return (
    <div className="space-y-6 p-6 max-w-7xl mx-auto">
      <div className="flex items-center justify-between">
        <div>
          <Pulse className="h-7 w-48 mb-2" />
          <Pulse className="h-4 w-32" />
        </div>
        <Pulse className="h-9 w-36 rounded-xl" />
      </div>
      <StatCardsSkeleton />
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <ChartSkeleton height="h-64" />
        <ChartSkeleton height="h-64" />
      </div>
      <TableSkeleton rows={5} />
      <RiskCardsSkeleton />
    </div>
  )
}
