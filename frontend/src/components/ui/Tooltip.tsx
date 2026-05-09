import { useState } from 'react'
import { HelpCircle } from 'lucide-react'

interface Props {
  content: string
  children?: React.ReactNode
  showIcon?: boolean
}

export default function Tooltip({ content, children, showIcon = false }: Props) {
  const [visible, setVisible] = useState(false)

  return (
    <div
      className="relative inline-flex items-center gap-1"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
    >
      {children}
      {showIcon && (
        <HelpCircle size={12} className="text-gray-600 hover:text-gray-400 cursor-help shrink-0" />
      )}
      {visible && (
        <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-60 pointer-events-none">
          <div className="bg-gray-800 border border-gray-700 text-gray-200 text-xs rounded-lg px-3 py-2 shadow-xl leading-relaxed">
            {content}
          </div>
          <div className="w-2 h-2 bg-gray-800 border-r border-b border-gray-700 rotate-45 mx-auto -mt-1" />
        </div>
      )}
    </div>
  )
}