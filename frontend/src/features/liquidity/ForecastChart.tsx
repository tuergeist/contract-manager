import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { formatCurrency } from '@/lib/utils'

interface MonthlyForecast {
  month: string
  startingBalance: number
  projectedCosts: number
  projectedIncome: number
  endingBalance: number
}

interface ForecastChartProps {
  months: MonthlyForecast[]
  referenceDate: string
  referenceAmount: number
  showIncome?: boolean
  showCosts?: boolean
}

export function ForecastChart({ months, referenceDate, referenceAmount, showIncome = true, showCosts = true }: ForecastChartProps) {
  const { t } = useTranslation()

  const chartData = useMemo(() => {
    const currentYear = new Date().getFullYear()
    const refDate = new Date(referenceDate)
    const refMonthKey = refDate.getFullYear() * 12 + refDate.getMonth()

    // Build data for all 12 months of current year (Jan-Dec)
    const allMonths: { monthKey: number; label: string; netChange: number; costs: number; income: number }[] = []

    for (let m = 0; m < 12; m++) {
      const monthKey = currentYear * 12 + m
      const monthDate = new Date(currentYear, m, 1)
      const label = monthDate.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })

      // Find matching month from backend data
      const backendMonth = months.find((bm) => {
        const bmDate = new Date(bm.month)
        return bmDate.getFullYear() === currentYear && bmDate.getMonth() === m
      })

      const costs = backendMonth ? parseFloat(String(backendMonth.projectedCosts)) || 0 : 0
      const income = backendMonth ? parseFloat(String(backendMonth.projectedIncome)) || 0 : 0
      const filteredCosts = showCosts ? costs : 0
      const filteredIncome = showIncome ? income : 0

      allMonths.push({
        monthKey,
        label,
        netChange: filteredCosts + filteredIncome,
        costs: Math.abs(filteredCosts),
        income: filteredIncome,
      })
    }

    // Find reference month index
    let refIndex = allMonths.findIndex((m) => m.monthKey >= refMonthKey)
    if (refIndex === -1) refIndex = allMonths.length - 1

    // Calculate balances from reference point
    const balances: number[] = new Array(12)
    balances[refIndex] = referenceAmount

    // Work backwards
    for (let i = refIndex - 1; i >= 0; i--) {
      balances[i] = balances[i + 1] - allMonths[i + 1].netChange
    }

    // Work forwards
    for (let i = refIndex + 1; i < 12; i++) {
      balances[i] = balances[i - 1] + allMonths[i].netChange
    }

    return allMonths.map((m, i) => ({
      month: m.label,
      balance: balances[i],
      costs: m.costs,
      income: m.income,
    }))
  }, [months, referenceDate, referenceAmount, showIncome, showCosts])

  const balances = chartData.map((d) => d.balance)
  const minBalance = balances.length > 0 ? Math.min(...balances) : 0
  const maxBalance = balances.length > 0 ? Math.max(...balances) : 0
  const hasNegative = minBalance < 0

  // Calculate Y-axis domain with proper padding
  const yMin = hasNegative ? Math.floor(minBalance * 1.1) : 0
  const yMax = Math.ceil(maxBalance * 1.1) || 1000 // fallback if maxBalance is 0

  // Current month label for vertical reference line
  const currentMonthLabel = new Date().toLocaleDateString(undefined, {
    month: 'short',
    year: '2-digit',
  })

  if (chartData.length === 0) {
    return <div className="h-80 flex items-center justify-center text-gray-400">No data</div>
  }

  return (
    <div className="h-80">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
          <XAxis dataKey="month" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis
            tickFormatter={(value) => formatCurrency(value, { compact: true })}
            tick={{ fontSize: 12 }}
            stroke="#9ca3af"
            domain={[yMin, yMax]}
          />
          <Tooltip
            formatter={(value, name) => [
              formatCurrency(value as number),
              name === 'balance'
                ? t('liquidity.balance')
                : name === 'costs'
                  ? t('liquidity.costs')
                  : t('liquidity.income'),
            ]}
            labelStyle={{ fontWeight: 'bold' }}
            contentStyle={{
              backgroundColor: 'white',
              border: '1px solid #e5e7eb',
              borderRadius: '8px',
            }}
          />
          {hasNegative && (
            <ReferenceLine y={0} stroke="#ef4444" strokeDasharray="5 5" />
          )}
          {/* Vertical line at current date */}
          <ReferenceLine
            x={currentMonthLabel}
            stroke="#6b7280"
            strokeDasharray="3 3"
            label={{ value: t('liquidity.today'), position: 'top', fontSize: 11, fill: '#6b7280' }}
          />
          <Line
            type="monotone"
            dataKey="balance"
            stroke="#3b82f6"
            strokeWidth={2}
            dot={{ fill: '#3b82f6', strokeWidth: 2 }}
            activeDot={{ r: 6 }}
          />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
