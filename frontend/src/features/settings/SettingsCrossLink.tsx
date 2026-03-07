import { Link } from 'react-router-dom'
import { ArrowRight, Info } from 'lucide-react'

interface SettingsCrossLinkProps {
  text: string
  to: string
  linkText: string
}

export function SettingsCrossLink({ text, to, linkText }: SettingsCrossLinkProps) {
  return (
    <div className="flex items-center gap-2 rounded-md bg-blue-50 px-4 py-2.5 text-sm text-blue-700 mb-4">
      <Info className="h-4 w-4 flex-shrink-0" />
      <span>{text}</span>
      <Link to={to} className="inline-flex items-center gap-1 font-medium hover:underline">
        {linkText} <ArrowRight className="h-3.5 w-3.5" />
      </Link>
    </div>
  )
}
