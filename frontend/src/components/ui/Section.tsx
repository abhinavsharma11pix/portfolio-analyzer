import { useEffect, useRef, useState, memo } from 'react'

interface Props {
  children: React.ReactNode
  className?: string
  delay?: number
  id?: string
}

const Section = memo(function Section({ children, className = '', delay = 0, id }: Props) {
  const [visible, setVisible] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const observed = useRef(false)

  useEffect(() => {
    if (observed.current) return
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !observed.current) {
          observed.current = true
          setTimeout(() => setVisible(true), delay)
          observer.disconnect()
        }
      },
      { threshold: 0.02 }
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
    >
      {children}
    </div>
  )
})

export default Section