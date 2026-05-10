import React, { memo } from 'react'

/* Base skeleton */

type SkeletonProps = React.HTMLAttributes<HTMLDivElement>

export const Skeleton = memo(function Skeleton({
  className = '',
  ...props
}: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      aria-hidden
      {...props}
    />
  )
})

/* Metric card skeleton — fixed height prevents CLS */

export const MetricCardSkeleton = memo(function MetricCardSkeleton() {
  return (
    <div className="card p-5 h-[100px] flex flex-col justify-between">
      <Skeleton className="h-3 w-20" />
      <Skeleton className="h-7 w-28" />
      <Skeleton className="h-3 w-36" />
    </div>
  )
})

/* Chart skeleton — fixed height */

export const ChartSkeleton = memo(function ChartSkeleton({
  height = 280,
}: {
  height?: number
}) {
  return (
    <div
      className="card p-6"
      style={{ minHeight: height + 60 }}
    >
      <Skeleton className="h-4 w-40 mb-6" />

      <Skeleton
        style={{ height }}
        className="w-full rounded-xl"
      />
    </div>
  )
})

/* Table row skeleton */

export const TableRowSkeleton = memo(function TableRowSkeleton() {
  const widths = [
    'w-24',
    'w-20',
    'w-16',
    'w-12',
    'w-20',
    'w-20',
    'w-20',
    'w-20',
    'w-16',
    'w-14',
  ]

  return (
    <tr className="border-b border-gray-800/40">
      {widths.map((width, i) => (
        <td key={i} className="py-3 pr-4">
          <Skeleton className={`h-3.5 ${width}`} />
        </td>
      ))}
    </tr>
  )
})

/* ── Composed page-level skeletons ── */

export const SummaryCardsSkeleton = memo(function SummaryCardsSkeleton() {
  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-5">
        <Skeleton className="h-4 w-32" />
        <Skeleton className="h-5 w-12 rounded-full" />
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="space-y-2">
            <Skeleton className="h-3 w-20" />
            <Skeleton className="h-6 w-28" />
            <Skeleton className="h-3 w-16" />
          </div>
        ))}
      </div>
    </div>
  )
})

export const TodayDashboardSkeleton = memo(function TodayDashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 min-h-[220px]">
      {/* Score card */}

      <div className="card p-6 flex flex-col items-center justify-center gap-3">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-16 w-16 rounded-full" />
        <Skeleton className="h-4 w-20" />

        <div className="flex gap-2 w-full justify-center">
          <Skeleton className="h-6 w-16 rounded-full" />
          <Skeleton className="h-6 w-16 rounded-full" />
        </div>
      </div>

      {/* Explanation card */}

      <div className="lg:col-span-2 card p-6 space-y-4">
        <div className="flex items-center gap-2">
          <Skeleton className="h-5 w-5 rounded" />
          <Skeleton className="h-4 w-48" />
        </div>

        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/5" />

        <div className="pt-2 space-y-2">
          <Skeleton className="h-10 w-full rounded-xl" />
          <Skeleton className="h-10 w-full rounded-xl" />
        </div>
      </div>
    </div>
  )
})

export const RiskMetricsSkeleton = memo(function RiskMetricsSkeleton() {
  return (
    <div className="space-y-5">
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <MetricCardSkeleton key={i} />
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
        <div className="card p-5 h-48 space-y-3">
          <Skeleton className="h-4 w-32" />

          {[...Array(4)].map((_, i) => (
            <div
              key={i}
              className="flex items-center gap-3"
            >
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-2 flex-1" />
              <Skeleton className="h-3 w-8" />
            </div>
          ))}
        </div>

        <div className="card p-5 h-48 space-y-3">
          <Skeleton className="h-4 w-28" />
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-3 w-full" />
        </div>
      </div>
    </div>
  )
})