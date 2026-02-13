import { useState, useRef, useEffect } from 'react'
import { Play, ChevronDown } from 'lucide-react'
import { useHelpVideoLinks } from '@/lib/helpVideoLinks'
import { useTranslation } from 'react-i18next'

export function HelpVideoButton() {
  const { t } = useTranslation()
  const links = useHelpVideoLinks()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }
    if (open) document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [open])

  if (links.length === 0) return null

  if (links.length === 1) {
    return (
      <button
        onClick={() => window.open(links[0].url, '_blank', 'noopener')}
        className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-green-700"
      >
        <Play className="h-4 w-4" />
        {t('helpVideo.button')}
      </button>
    )
  }

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen(!open)}
        className="inline-flex items-center gap-1.5 rounded-md bg-green-600 px-3 py-1.5 text-sm font-medium text-white shadow-sm hover:bg-green-700"
      >
        <Play className="h-4 w-4" />
        {t('helpVideo.button')}
        <ChevronDown className="h-3.5 w-3.5" />
      </button>
      {open && (
        <div className="absolute right-0 z-50 mt-1 min-w-48 rounded-md border bg-white py-1 shadow-lg">
          {links.map((link, i) => (
            <button
              key={i}
              onClick={() => {
                window.open(link.url, '_blank', 'noopener')
                setOpen(false)
              }}
              className="block w-full px-3 py-2 text-left text-sm text-gray-700 hover:bg-gray-100"
            >
              {link.label || link.url}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
