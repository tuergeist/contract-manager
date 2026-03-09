import { useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from 'recharts'
import { formatCurrency, formatMonthShort } from '@/lib/utils'

const LIQUIDITY_ANALYSIS_QUERY = gql`
  query LiquidityAnalysis($year: Int!) {
    liquidityAnalysis(year: $year) {
      year
      currentBalance
      balanceAsOf
      months {
        month
        actualCosts
        actualIncome
        projectedCosts
        projectedIncome
        totalCosts
        totalIncome
        net
        cumulativeBalance
        isPast
      }
    }
  }
`

interface LiquidityMonth {
  month: string
  actualCosts: number
  actualIncome: number
  projectedCosts: number
  projectedIncome: number
  totalCosts: number
  totalIncome: number
  net: number
  cumulativeBalance: number
  isPast: boolean
}

export function LiquidityAnalysis() {
  const { t } = useTranslation()
  const currentYear = new Date().getFullYear()

  const { data, loading } = useQuery(LIQUIDITY_ANALYSIS_QUERY, {
    variables: { year: currentYear },
  })

  const analysis = data?.liquidityAnalysis
  const months: LiquidityMonth[] = analysis?.months || []

  const chartData = useMemo(() => {
    return months.map((m) => ({
      month: formatMonthShort(m.month),
      rawMonth: m.month,
      actualIncome: Math.round(m.actualIncome * 100) / 100,
      projectedIncome: Math.round(m.projectedIncome * 100) / 100,
      actualCosts: Math.round(m.actualCosts * 100) / 100,
      projectedCosts: Math.round(m.projectedCosts * 100) / 100,
      balance: Math.round(m.cumulativeBalance * 100) / 100,
      isPast: m.isPast,
    }))
  }, [months])

  const currentMonthIdx = useMemo(() => {
    const now = new Date()
    return months.findIndex((m) => {
      const d = new Date(m.month)
      return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear()
    })
  }, [months])

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (!analysis) return null

  // Year totals
  const totals = months.reduce(
    (acc, m) => ({
      actualCosts: acc.actualCosts + m.actualCosts,
      projectedCosts: acc.projectedCosts + m.projectedCosts,
      totalCosts: acc.totalCosts + m.totalCosts,
      actualIncome: acc.actualIncome + m.actualIncome,
      projectedIncome: acc.projectedIncome + m.projectedIncome,
      totalIncome: acc.totalIncome + m.totalIncome,
      net: acc.net + m.net,
    }),
    {
      actualCosts: 0,
      projectedCosts: 0,
      totalCosts: 0,
      actualIncome: 0,
      projectedIncome: 0,
      totalIncome: 0,
      net: 0,
    }
  )

  const formatTooltipValue = (value: number | undefined) => value != null ? formatCurrency(value) : ''

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-medium">{t('forecasts.liquidity.title', { year: currentYear })}</h2>
        {analysis.balanceAsOf && (
          <span className="text-sm text-gray-500">
            {t('forecasts.liquidity.balance')}: {formatCurrency(analysis.currentBalance)}
          </span>
        )}
      </div>

      {/* Chart */}
      <div className="rounded-lg border bg-white p-6">
        <ResponsiveContainer width="100%" height={350}>
          <ComposedChart data={chartData} stackOffset="sign">
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 12 }} />
            <YAxis
              tick={{ fontSize: 12 }}
              tickFormatter={(v: number) => `${Math.round(v / 1000)}k`}
            />
            <Tooltip
              formatter={formatTooltipValue}
              labelFormatter={(label) => String(label)}
            />
            <Legend />
            <ReferenceLine y={0} stroke="#000" strokeWidth={1} />
            <Bar
              dataKey="actualIncome"
              name={t('forecasts.liquidity.actualIncome')}
              fill="#22c55e"
              stackId="income"
            />
            <Bar
              dataKey="projectedIncome"
              name={t('forecasts.liquidity.projectedIncome')}
              fill="#86efac"
              stackId="income"
            />
            <Bar
              dataKey="actualCosts"
              name={t('forecasts.liquidity.actualCosts')}
              fill="#ef4444"
              stackId="costs"
            />
            <Bar
              dataKey="projectedCosts"
              name={t('forecasts.liquidity.projectedCosts')}
              fill="#fca5a5"
              stackId="costs"
            />
            <Line
              type="monotone"
              dataKey="balance"
              name={t('forecasts.liquidity.cumulative')}
              stroke="#3b82f6"
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>

      {/* Summary Table */}
      <div className="rounded-lg border bg-white overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200 text-sm">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-3 text-left font-medium text-gray-500">
                  {t('forecasts.liquidity.month')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.actualCosts')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.projectedCosts')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.totalCosts')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.actualIncome')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.projectedIncome')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.totalIncome')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.net')}
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-500">
                  {t('forecasts.liquidity.cumulative')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {months.map((m, idx) => (
                <tr
                  key={m.month}
                  className={idx === currentMonthIdx ? 'bg-blue-50' : ''}
                >
                  <td className="px-4 py-2 font-medium whitespace-nowrap">
                    {formatMonthShort(m.month)}
                  </td>
                  <td className={`px-4 py-2 text-right ${m.actualCosts < 0 ? 'text-red-600' : ''}`}>
                    {formatCurrency(m.actualCosts)}
                  </td>
                  <td className={`px-4 py-2 text-right ${m.projectedCosts < 0 ? 'text-red-600' : ''}`}>
                    {formatCurrency(m.projectedCosts)}
                  </td>
                  <td className={`px-4 py-2 text-right font-medium ${m.totalCosts < 0 ? 'text-red-600' : ''}`}>
                    {formatCurrency(m.totalCosts)}
                  </td>
                  <td className="px-4 py-2 text-right text-green-600">
                    {formatCurrency(m.actualIncome)}
                  </td>
                  <td className="px-4 py-2 text-right text-green-600">
                    {formatCurrency(m.projectedIncome)}
                  </td>
                  <td className="px-4 py-2 text-right font-medium text-green-600">
                    {formatCurrency(m.totalIncome)}
                  </td>
                  <td className={`px-4 py-2 text-right font-medium ${m.net < 0 ? 'text-red-600' : 'text-green-600'}`}>
                    {formatCurrency(m.net)}
                  </td>
                  <td className={`px-4 py-2 text-right font-medium ${m.cumulativeBalance < 0 ? 'text-red-600' : ''}`}>
                    {formatCurrency(m.cumulativeBalance)}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot className="bg-gray-50 font-medium">
              <tr>
                <td className="px-4 py-3">{t('forecasts.liquidity.total')}</td>
                <td className={`px-4 py-3 text-right ${totals.actualCosts < 0 ? 'text-red-600' : ''}`}>
                  {formatCurrency(totals.actualCosts)}
                </td>
                <td className={`px-4 py-3 text-right ${totals.projectedCosts < 0 ? 'text-red-600' : ''}`}>
                  {formatCurrency(totals.projectedCosts)}
                </td>
                <td className={`px-4 py-3 text-right ${totals.totalCosts < 0 ? 'text-red-600' : ''}`}>
                  {formatCurrency(totals.totalCosts)}
                </td>
                <td className="px-4 py-3 text-right text-green-600">
                  {formatCurrency(totals.actualIncome)}
                </td>
                <td className="px-4 py-3 text-right text-green-600">
                  {formatCurrency(totals.projectedIncome)}
                </td>
                <td className="px-4 py-3 text-right text-green-600">
                  {formatCurrency(totals.totalIncome)}
                </td>
                <td className={`px-4 py-3 text-right ${totals.net < 0 ? 'text-red-600' : 'text-green-600'}`}>
                  {formatCurrency(totals.net)}
                </td>
                <td className="px-4 py-3 text-right">-</td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>
    </div>
  )
}
