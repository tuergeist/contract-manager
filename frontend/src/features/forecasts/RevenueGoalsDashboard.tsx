import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useLazyQuery, gql } from '@apollo/client'
import { Loader2, AlertTriangle, ChevronDown, ChevronUp, ExternalLink } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { formatCurrency } from '@/lib/utils'

const REVENUE_GOALS_QUERY = gql`
  query RevenueGoalsAndStreams($year: Int!) {
    revenueGoals(year: $year) {
      id
      year
      revenueType
      targetAmount
    }
    revenueByStream(year: $year) {
      revenueType
      ytdActual
      fullYearForecast
    }
  }
`

const UNCLASSIFIED_ITEMS_QUERY = gql`
  query UnclassifiedRevenueItems {
    unclassifiedRevenueItems {
      itemId
      productName
      description
      isOneOff
      unitPrice
      quantity
      contractId
      contractName
      customerName
      customerId
    }
  }
`

interface RevenueGoal {
  id: number
  year: number
  revenueType: string
  targetAmount: string
}

interface RevenueStreamData {
  revenueType: string
  ytdActual: string
  fullYearForecast: string
}

interface UnclassifiedItem {
  itemId: number
  productName: string | null
  description: string
  isOneOff: boolean
  unitPrice: string
  quantity: number
  contractId: number
  contractName: string
  customerName: string
  customerId: number
}

const STANDARD_STREAMS = [
  { key: 'recurring', i18nKey: 'products.revenueTypes.recurring' },
  { key: 'advanced_development', i18nKey: 'products.revenueTypes.advancedDevelopment' },
  { key: 'training_implementation', i18nKey: 'products.revenueTypes.trainingImplementation' },
] as const

function ProgressBar({ value, overTarget }: { value: number; overTarget: boolean }) {
  const clamped = Math.min(value, 100)
  return (
    <div className="relative h-3 w-full rounded-full bg-gray-200">
      <div
        className={`h-3 rounded-full transition-all ${
          overTarget ? 'bg-emerald-500' : value >= 80 ? 'bg-blue-500' : 'bg-blue-400'
        }`}
        style={{ width: `${clamped}%` }}
      />
      {overTarget && (
        <div className="absolute -right-1 -top-1 h-5 w-5 rounded-full bg-emerald-500 border-2 border-white flex items-center justify-center">
          <span className="text-[10px] text-white font-bold">!</span>
        </div>
      )}
    </div>
  )
}

export function RevenueGoalsDashboard() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const currentYear = new Date().getFullYear()
  const [selectedYear, setSelectedYear] = useState(currentYear)
  const [showUnclassified, setShowUnclassified] = useState(false)

  const { data, loading } = useQuery<{
    revenueGoals: RevenueGoal[]
    revenueByStream: RevenueStreamData[]
  }>(REVENUE_GOALS_QUERY, { variables: { year: selectedYear } })

  const [fetchUnclassified, { data: unclassifiedData, loading: loadingUnclassified }] =
    useLazyQuery<{ unclassifiedRevenueItems: UnclassifiedItem[] }>(UNCLASSIFIED_ITEMS_QUERY)

  const handleToggleUnclassified = () => {
    if (!showUnclassified && !unclassifiedData) {
      fetchUnclassified()
    }
    setShowUnclassified(!showUnclassified)
  }

  const years = Array.from({ length: 5 }, (_, i) => currentYear - 1 + i)

  const goalMap: Record<string, number> = {}
  for (const g of data?.revenueGoals || []) {
    goalMap[g.revenueType] = parseFloat(g.targetAmount)
  }

  const streamMap: Record<string, { ytd: number; forecast: number }> = {}
  for (const s of data?.revenueByStream || []) {
    streamMap[s.revenueType] = {
      ytd: parseFloat(s.ytdActual),
      forecast: parseFloat(s.fullYearForecast),
    }
  }

  const unclassified = streamMap['unclassified']
  const hasUnclassified = unclassified && (unclassified.ytd !== 0 || unclassified.forecast !== 0)

  // Calculate totals
  let totalTarget = 0
  let totalYtd = 0
  let totalForecast = 0
  for (const stream of STANDARD_STREAMS) {
    totalTarget += goalMap[stream.key] || 0
    totalYtd += streamMap[stream.key]?.ytd || 0
    totalForecast += streamMap[stream.key]?.forecast || 0
  }

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <select
          value={selectedYear}
          onChange={(e) => setSelectedYear(parseInt(e.target.value))}
          className="rounded-md border border-gray-300 py-1.5 px-3 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
        >
          {years.map((y) => (
            <option key={y} value={y}>{y}</option>
          ))}
        </select>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        </div>
      ) : (
        <>
          {hasUnclassified && (
            <div className="rounded-lg border border-yellow-200 bg-yellow-50">
              <button
                onClick={handleToggleUnclassified}
                className="flex w-full items-center gap-2 px-4 py-3 text-left"
              >
                <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0" />
                <p className="flex-1 text-sm text-yellow-800">
                  {t('forecasts.goals.unclassifiedWarning')} ({formatCurrency(unclassified.forecast.toString())})
                </p>
                {showUnclassified
                  ? <ChevronUp className="h-4 w-4 text-yellow-600" />
                  : <ChevronDown className="h-4 w-4 text-yellow-600" />
                }
              </button>
              {showUnclassified && (
                <div className="border-t border-yellow-200 px-4 py-3">
                  {loadingUnclassified ? (
                    <div className="flex items-center gap-2 py-2">
                      <Loader2 className="h-4 w-4 animate-spin text-yellow-600" />
                    </div>
                  ) : (unclassifiedData?.unclassifiedRevenueItems?.length ?? 0) === 0 ? (
                    <p className="text-sm text-yellow-700">{t('forecasts.goals.noUnclassifiedItems')}</p>
                  ) : (
                    <table className="min-w-full text-sm">
                      <thead>
                        <tr className="text-left text-xs font-medium uppercase text-yellow-700">
                          <th className="pb-2 pr-4">{t('forecast.customer')}</th>
                          <th className="pb-2 pr-4">{t('forecast.contract')}</th>
                          <th className="pb-2 pr-4">{t('products.name')}</th>
                          <th className="pb-2 pr-4 text-right">{t('products.price')}</th>
                          <th className="pb-2"></th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-yellow-100">
                        {unclassifiedData!.unclassifiedRevenueItems.map((item) => (
                          <tr key={item.itemId}>
                            <td className="py-2 pr-4 text-yellow-900">{item.customerName}</td>
                            <td className="py-2 pr-4 text-yellow-900">{item.contractName}</td>
                            <td className="py-2 pr-4 text-yellow-900">
                              {item.productName || item.description || '-'}
                              {item.isOneOff && (
                                <span className="ml-1 text-xs text-yellow-600">(one-off)</span>
                              )}
                            </td>
                            <td className="py-2 pr-4 text-right text-yellow-900">
                              {formatCurrency(item.unitPrice)} x {item.quantity}
                            </td>
                            <td className="py-2">
                              <button
                                onClick={() => navigate(`/contracts/${item.contractId}`)}
                                className="text-yellow-700 hover:text-yellow-900"
                                title={t('forecasts.goals.openContract')}
                              >
                                <ExternalLink className="h-3.5 w-3.5" />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                </div>
              )}
            </div>
          )}

          <div className="overflow-hidden rounded-lg border">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('forecasts.goals.stream')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('forecasts.goals.target')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('forecasts.goals.ytdActual')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('forecasts.goals.forecast')}
                  </th>
                  <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                    {t('forecasts.goals.difference')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 w-48">
                    {t('forecasts.goals.progress')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {STANDARD_STREAMS.map((stream) => {
                  const target = goalMap[stream.key]
                  const ytd = streamMap[stream.key]?.ytd || 0
                  const forecast = streamMap[stream.key]?.forecast || 0
                  const progress = target ? (forecast / target) * 100 : null
                  const overTarget = progress !== null && progress > 100

                  return (
                    <tr key={stream.key}>
                      <td className="px-6 py-4 text-sm font-medium text-gray-900">
                        {t(stream.i18nKey)}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-900">
                        {target ? formatCurrency(target.toString()) : (
                          <span className="text-gray-400">{t('forecasts.goals.noTarget')}</span>
                        )}
                      </td>
                      <td className="px-6 py-4 text-sm text-right text-gray-900">
                        {formatCurrency(ytd.toString())}
                      </td>
                      <td className="px-6 py-4 text-sm text-right font-medium text-gray-900">
                        {formatCurrency(forecast.toString())}
                      </td>
                      <td className="px-6 py-4 text-sm text-right">
                        {target ? (
                          <span className={forecast - target >= 0 ? 'text-emerald-600 font-medium' : 'text-red-600 font-medium'}>
                            {forecast - target >= 0 ? '+' : ''}{formatCurrency((forecast - target).toString())}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="px-6 py-4">
                        {progress !== null ? (
                          <div className="flex items-center gap-2">
                            <div className="flex-1">
                              <ProgressBar value={progress} overTarget={overTarget} />
                            </div>
                            <span className={`text-xs font-medium whitespace-nowrap ${
                              overTarget ? 'text-emerald-600' : 'text-gray-600'
                            }`}>
                              {Math.round(progress)}%
                            </span>
                          </div>
                        ) : (
                          <a
                            href="/settings/general/revenue-goals"
                            className="text-xs text-blue-600 hover:underline"
                          >
                            {t('forecasts.goals.setGoals')}
                          </a>
                        )}
                      </td>
                    </tr>
                  )
                })}

                {/* Total row */}
                <tr className="bg-gray-50 font-medium">
                  <td className="px-6 py-4 text-sm font-bold text-gray-900">
                    {t('forecasts.goals.total')}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-bold text-gray-900">
                    {totalTarget > 0 ? formatCurrency(totalTarget.toString()) : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-bold text-gray-900">
                    {formatCurrency(totalYtd.toString())}
                  </td>
                  <td className="px-6 py-4 text-sm text-right font-bold text-gray-900">
                    {formatCurrency(totalForecast.toString())}
                  </td>
                  <td className="px-6 py-4 text-sm text-right">
                    {totalTarget > 0 ? (
                      <span className={`font-bold ${totalForecast - totalTarget >= 0 ? 'text-emerald-600' : 'text-red-600'}`}>
                        {totalForecast - totalTarget >= 0 ? '+' : ''}{formatCurrency((totalForecast - totalTarget).toString())}
                      </span>
                    ) : '-'}
                  </td>
                  <td className="px-6 py-4">
                    {totalTarget > 0 ? (
                      <div className="flex items-center gap-2">
                        <div className="flex-1">
                          <ProgressBar
                            value={(totalForecast / totalTarget) * 100}
                            overTarget={totalForecast > totalTarget}
                          />
                        </div>
                        <span className={`text-xs font-medium whitespace-nowrap ${
                          totalForecast > totalTarget ? 'text-emerald-600' : 'text-gray-600'
                        }`}>
                          {Math.round((totalForecast / totalTarget) * 100)}%
                        </span>
                      </div>
                    ) : null}
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
