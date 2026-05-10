import { useEffect, useRef, useState, memo } from 'react'
import type { ReactNode } from 'react'

interface Props {
  children: ReactNode
  delay?: number
  className?: string
  id?: string
  minHeight?: number
}

const Section = memo(function Section({
  children,
  delay     = 0,
  className = '',
  id,
  minHeight,
}: Props) {
  const [visible,  setVisible]  = useState(delay === 0)
  const ref        = useRef<HTMLDivElement>(null)
  const triggered  = useRef(false)

  useEffect(() => {
    if (triggered.current) return
    const el = ref.current
    if (!el) return

    const rect = el.getBoundingClientRect()
    if (rect.top < window.innerHeight) {
      setTimeout(() => setVisible(true), delay)
      triggered.current = true
      return
    }

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !triggered.current) {
          triggered.current = true
          setTimeout(() => setVisible(true), delay)
          observer.disconnect()
        }
      },
      { threshold: 0.02, rootMargin: '50px' }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [delay])

  return (
    <div
      id={id}
      ref={ref}
      className={`transition-all duration-500 ease-out will-change-transform ${
        visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-3'
      } ${className}`}
      style={minHeight && !visible ? { minHeight } : undefined}
    >
      {children}
    </div>
  )
})

export default Section