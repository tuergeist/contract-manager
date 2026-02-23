import { Info } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip'
import { formatCurrency, formatNumber } from '@/lib/utils'

interface KPICardProps {
  title: string
  value: string | number
  subtitle?: string
  explanation: string
  isCurrency?: boolean
}

export function KPICard({ title, value, subtitle, explanation, isCurrency = false }: KPICardProps) {
  const displayValue = typeof value === 'number'
    ? (isCurrency ? formatCurrency(value, { minimumFractionDigits: 0, maximumFractionDigits: 0 }) : formatNumber(value))
    : value

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <TooltipProvider>
          <Tooltip>
            <TooltipTrigger asChild>
              <button className="text-muted-foreground hover:text-foreground transition-colors">
                <Info className="h-4 w-4" />
              </button>
            </TooltipTrigger>
            <TooltipContent className="max-w-xs">
              <p>{explanation}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{displayValue}</div>
        {subtitle && subtitle.split('\n').map((line, i) => (
          <p key={i} className="text-xs text-muted-foreground mt-1">{line}</p>
        ))}
      </CardContent>
    </Card>
  )
}
