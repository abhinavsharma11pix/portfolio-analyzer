import { useState, useRef, memo } from 'react'
import type { ReactNode } from 'react'
import { HelpCircle } from 'lucide-react'

interface Props {
  content: string
  children?: ReactNode
  showIcon?: boolean
  side?: 'top' | 'bottom'
}

const Tooltip = memo(function Tooltip({
  content,
  children,
  showIcon = false,
  side = 'top',
}: Props) {
  const [visible, setVisible] = useState(false)
  const timeout = useRef<ReturnType<typeof setTimeout> | null>(null)

  const show = () => {
    if (timeout.current) clearTimeout(timeout.current)
    setVisible(true)
  }
  const hide = () => {
    timeout.current = setTimeout(() => setVisible(false), 80)
  }

  return (
    <div
      className="relative inline-flex items-center gap-1"
      onMouseEnter={show}
      onMouseLeave={hide}
    >
      {children}
      {showIcon && (
        <HelpCircle
          size={12}
          className="text-gray-600 hover:text-gray-400 cursor-help shrink-0"
        />
      )}
      {visible && (
        <div
          className={`absolute ${
            side === 'top' ? 'bottom-full mb-2' : 'top-full mt-2'
          } left-1/2 -translate-x-1/2 z-50 w-56 pointer-events-none`}
        >
          <div className="bg-gray-800 border border-gray-700 text-gray-200 text-xs rounded-lg px-3 py-2 shadow-xl leading-relaxed">
            {content}
          </div>
        </div>
      )}
    </div>
  )
})

export default Tooltip