import { useState, useMemo, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Link } from 'react-router-dom'
import { Loader2, TrendingUp, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Checkbox } from '@/components/ui/checkbox'
import { HelpVideoButton } from '@/components/HelpVideoButton'

const REVENUE_FORECAST_QUERY = gql`
  query RevenueForecast($months: Int, $quarters: Int, $view: String, $proRata: Boolean) {
    revenueForecast(months: $months, quarters: $quarters, view: $view, proRata: $proRata) {
      monthColumns
      monthlyTotals {
        month
        amount
      }
      contracts {
        contractId
        contractName
        customerId
        customerName
        months {
          month
          amount
        }
        total
      }
      grandTotal
      error
    }
  }
`

const RECOGNITION_FORECAST_QUERY = gql`
  query RecognitionForecast($months: Int, $quarters: Int, $view: String, $proRata: Boolean) {
    recognitionForecast(months: $months, quarters: $quarters, view: $view, proRata: $proRata) {
      monthColumns
      monthlyTotals {
        month
        amount
      }
      contracts {
        contractId
        contractName
        customerId
        customerName
        months {
          month
          amount
        }
        total
      }
      grandTotal
      error
    }
  }
`

interface RevenueMonthData {
  month: string
  amount: string
}

interface ContractRevenueRow {
  contractId: number
  contractName: string
  customerId: number
  customerName: string
  months: RevenueMonthData[]
  total: string
}

interface RevenueForecastResult {
  monthColumns: string[]
  monthlyTotals: RevenueMonthData[]
  contracts: ContractRevenueRow[]
  grandTotal: string
  error: string | null
}

type ViewType = 'monthly' | 'quarterly'
type ForecastType = 'billing' | 'recognition'
type SortField = 'contract' | 'customer' | null
type SortOrder = 'asc' | 'desc'

export function RevenueForecast() {
  const { t, i18n } = useTranslation()
  const [forecastType, setForecastType] = useState<ForecastType>('billing')
  const [view, setView] = useState<ViewType>('monthly')
  const [periods, setPeriods] = useState('13')
  const [proRata, setProRata] = useState(false)
  const [sortField, setSortField] = useState<SortField>(null)
  const [sortOrder, setSortOrder] = useState<SortOrder>('asc')

  // Adjust periods when switching views
  const handleViewChange = (newView: ViewType) => {
    setView(newView)
    if (newView === 'quarterly') {
      setPeriods('6')
    } else {
      setPeriods('13')
    }
  }

  const { data, loading, error } = useQuery(
    forecastType === 'billing' ? REVENUE_FORECAST_QUERY : RECOGNITION_FORECAST_QUERY,
    {
      variables: {
        months: view === 'monthly' ? parseInt(periods) : null,
        quarters: view === 'quarterly' ? parseInt(periods) : null,
        view,
        proRata,
      },
    }
  )

  const forecast = (forecastType === 'billing'
    ? data?.revenueForecast
    : data?.recognitionForecast) as RevenueForecastResult | undefined

  // Sort contracts
  const sortedContracts = useMemo(() => {
    if (!forecast?.contracts) return []
    if (!sortField) return forecast.contracts

    return [...forecast.contracts].sort((a, b) => {
      let comparison = 0
      if (sortField === 'contract') {
        comparison = a.contractName.localeCompare(b.contractName, i18n.language)
      } else if (sortField === 'customer') {
        comparison = a.customerName.localeCompare(b.customerName, i18n.language)
      }
      return sortOrder === 'asc' ? comparison : -comparison
    })
  }, [forecast?.contracts, sortField, sortOrder, i18n.language])

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      // Toggle order or clear
      if (sortOrder === 'asc') {
        setSortOrder('desc')
      } else {
        setSortField(null)
        setSortOrder('asc')
      }
    } else {
      setSortField(field)
      setSortOrder('asc')
    }
  }

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) {
      return <ArrowUpDown className="ml-1 inline h-3 w-3 opacity-50" />
    }
    return sortOrder === 'asc' ? (
      <ArrowUp className="ml-1 inline h-3 w-3" />
    ) : (
      <ArrowDown className="ml-1 inline h-3 w-3" />
    )
  }

  const formatPeriod = (periodStr: string) => {
    if (periodStr.includes('Q')) {
      // Quarter format: "2026-Q1" -> "Q1/26"
      const [year, quarter] = periodStr.split('-')
      return `${quarter}/${year.slice(2)}`
    }
    // Month format: "2026-01" -> "01/26"
    const [year, month] = periodStr.split('-')
    return `${month}/${year.slice(2)}`
  }

  // Memoize currency formatters to avoid creating new Intl.NumberFormat instances on every render
  const currencyFormatter = useMemo(
    () =>
      new Intl.NumberFormat(i18n.language, {
        style: 'currency',
        currency: 'EUR',
        minimumFractionDigits: 0,
        maximumFractionDigits: 0,
      }),
    [i18n.language]
  )

  const currencyFormatterFull = useMemo(
    () =>
      new Intl.NumberFormat(i18n.language, {
        style: 'currency',
        currency: 'EUR',
      }),
    [i18n.language]
  )

  const formatCurrency = useCallback(
    (value: string) => {
      const num = parseFloat(value)
      if (num === 0) return '-'
      return currencyFormatter.format(num)
    },
    [currencyFormatter]
  )

  const formatCurrencyFull = useCallback(
    (value: string) => {
      return currencyFormatterFull.format(parseFloat(value))
    },
    [currencyFormatterFull]
  )

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  if (error || forecast?.error) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-4">
        <p className="text-red-600">{error?.message || forecast?.error}</p>
      </div>
    )
  }

  return (
    <div>
      {/* Header */}
      <div className="mb-6 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingUp className="h-8 w-8 text-blue-600" />
          <h1 className="text-2xl font-bold">
            {forecastType === 'billing' ? t('forecast.title') : t('forecast.recognitionTitle')}
          </h1>
        </div>
        <div className="flex items-center gap-4">
          {/* Forecast Type Toggle */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">{t('forecast.forecastType')}:</label>
            <Select value={forecastType} onValueChange={(v) => setForecastType(v as ForecastType)}>
              <SelectTrigger className="w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="billing">{t('forecast.billing')}</SelectItem>
                <SelectItem value="recognition">{t('forecast.recognition')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {/* View Toggle */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">{t('forecast.view')}:</label>
            <Select value={view} onValueChange={(v) => handleViewChange(v as ViewType)}>
              <SelectTrigger className="w-32">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="monthly">{t('forecast.monthly')}</SelectItem>
                <SelectItem value="quarterly">{t('forecast.quarterly')}</SelectItem>
              </SelectContent>
            </Select>
          </div>
          {/* Period Selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-medium">
              {view === 'monthly' ? t('forecast.months') : t('forecast.quarters')}:
            </label>
            <Select value={periods} onValueChange={setPeriods}>
              <SelectTrigger className="w-20">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {view === 'monthly' ? (
                  <>
                    <SelectItem value="6">6</SelectItem>
                    <SelectItem value="12">12</SelectItem>
                    <SelectItem value="13">13</SelectItem>
                    <SelectItem value="24">24</SelectItem>
                  </>
                ) : (
                  <>
                    <SelectItem value="4">4</SelectItem>
                    <SelectItem value="6">6</SelectItem>
                    <SelectItem value="8">8</SelectItem>
                    <SelectItem value="12">12</SelectItem>
                  </>
                )}
              </SelectContent>
            </Select>
          </div>
          {/* Pro-rata Toggle */}
          <div className="flex items-center gap-2">
            <Checkbox
              id="proRata"
              checked={proRata}
              onCheckedChange={(checked) => setProRata(checked === true)}
            />
            <label htmlFor="proRata" className="text-sm font-medium cursor-pointer">
              {t('forecast.proRata')}
            </label>
          </div>
          <HelpVideoButton />
        </div>
      </div>

      {/* Forecast Table */}
      {!forecast?.contracts || forecast.contracts.length === 0 ? (
        <div className="rounded-lg border bg-white p-8 text-center">
          <TrendingUp className="mx-auto h-12 w-12 text-gray-400" />
          <p className="mt-2 text-gray-600">{t('forecast.noData')}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border bg-white">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th
                  className="sticky left-0 z-10 min-w-[220px] cursor-pointer bg-gray-50 px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                  onClick={() => handleSort('contract')}
                >
                  {t('forecast.contract')}
                  {getSortIcon('contract')}
                </th>
                <th
                  className="min-w-[180px] cursor-pointer px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                  onClick={() => handleSort('customer')}
                >
                  {t('forecast.customer')}
                  {getSortIcon('customer')}
                </th>
                {forecast.monthColumns.map((period) => (
                  <th
                    key={period}
                    className="whitespace-nowrap px-3 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500"
                  >
                    {formatPeriod(period)}
                  </th>
                ))}
                <th className="whitespace-nowrap px-4 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
                  {t('forecast.total')}
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {/* Period Totals Row */}
              <tr className="bg-blue-50 font-semibold">
                <td
                  colSpan={2}
                  className="sticky left-0 z-10 bg-blue-50 px-4 py-3 text-sm text-blue-900"
                >
                  {view === 'monthly' ? t('forecast.monthlyTotal') : t('forecast.quarterlyTotal')}
                </td>
                {forecast.monthlyTotals.map((periodData) => (
                  <td
                    key={periodData.month}
                    className="whitespace-nowrap px-3 py-3 text-right text-sm text-blue-900"
                  >
                    {formatCurrency(periodData.amount)}
                  </td>
                ))}
                <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-bold text-blue-900">
                  {formatCurrencyFull(forecast.grandTotal)}
                </td>
              </tr>

              {/* Contract Rows */}
              {sortedContracts.map((contract) => (
                <tr key={contract.contractId} className="hover:bg-gray-50">
                  <td className="sticky left-0 z-10 min-w-[220px] bg-white px-4 py-3 text-sm group-hover:bg-gray-50">
                    <Link
                      to={`/contracts/${contract.contractId}`}
                      className="font-medium text-blue-600 hover:underline"
                    >
                      {contract.contractName}
                    </Link>
                  </td>
                  <td className="min-w-[180px] px-4 py-3 text-sm">
                    <Link
                      to={`/customers/${contract.customerId}`}
                      className="text-blue-600 hover:underline"
                    >
                      {contract.customerName}
                    </Link>
                  </td>
                  {contract.months.map((periodData) => (
                    <td
                      key={periodData.month}
                      className="whitespace-nowrap px-3 py-3 text-right text-sm text-gray-900"
                    >
                      {formatCurrency(periodData.amount)}
                    </td>
                  ))}
                  <td className="whitespace-nowrap px-4 py-3 text-right text-sm font-medium text-gray-900">
                    {formatCurrencyFull(contract.total)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
