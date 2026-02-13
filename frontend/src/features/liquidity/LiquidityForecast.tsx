import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, RefreshCw, TrendingUp, TrendingDown, ChevronDown, ChevronRight, Check, X, Pause, Play, Pencil, ArrowUpDown, ArrowUp, ArrowDown, Search } from 'lucide-react'
import { formatCurrency, formatDate } from '@/lib/utils'
import { ForecastChart } from './ForecastChart'
import { EditPatternModal } from './EditPatternModal'
import { HelpVideoButton } from '@/components/HelpVideoButton'

const LIQUIDITY_FORECAST_QUERY = gql`
  query LiquidityForecast($months: Int!) {
    liquidityForecast(months: $months) {
      currentBalance
      balanceAsOf
      months {
        month
        startingBalance
        projectedCosts
        projectedIncome
        endingBalance
        transactions {
          patternId
          counterparty {
            id
            name
            iban
            bic
          }
          amount
          projectedDate
          isConfirmed
        }
      }
    }
    recurringPatterns(includeIgnored: false) {
      id
      counterparty {
        id
        name
        iban
        bic
      }
      averageAmount
      frequency
      dayOfMonth
      confidenceScore
      isConfirmed
      isIgnored
      isPaused
      lastOccurrence
      projectedNextDate
      sourceTransactionCount
    }
  }
`

const DETECT_PATTERNS = gql`
  mutation DetectPatterns {
    detectPatterns {
      success
      error
      detectedCount
    }
  }
`

const CONFIRM_PATTERN = gql`
  mutation ConfirmPattern($patternId: Int!) {
    confirmPattern(patternId: $patternId) {
      success
      error
    }
  }
`

const IGNORE_PATTERN = gql`
  mutation IgnorePattern($patternId: Int!) {
    ignorePattern(patternId: $patternId) {
      success
      error
    }
  }
`

const PAUSE_PATTERN = gql`
  mutation PausePattern($patternId: Int!) {
    pausePattern(patternId: $patternId) {
      success
      error
    }
  }
`

const RESUME_PATTERN = gql`
  mutation ResumePattern($patternId: Int!) {
    resumePattern(patternId: $patternId) {
      success
      error
    }
  }
`

interface Counterparty {
  id: string
  name: string
  iban: string
  bic: string
}

interface RecurringPattern {
  id: number
  counterparty: Counterparty
  averageAmount: number
  frequency: string
  dayOfMonth: number | null
  confidenceScore: number
  isConfirmed: boolean
  isIgnored: boolean
  isPaused: boolean
  lastOccurrence: string | null
  projectedNextDate: string | null
  sourceTransactionCount: number
}

interface ProjectedTransaction {
  patternId: number
  counterparty: Counterparty
  amount: number
  projectedDate: string
  isConfirmed: boolean
}

interface MonthlyForecast {
  month: string
  startingBalance: number
  projectedCosts: number
  projectedIncome: number
  endingBalance: number
  transactions: ProjectedTransaction[]
}

type SortColumn = 'counterparty' | 'amount' | 'frequency' | 'confidence'
type SortDirection = 'asc' | 'desc'

interface FilteredMonth extends MonthlyForecast {
  filteredCosts: number
  filteredIncome: number
  endBalance: number
  filteredTransactions: ProjectedTransaction[]
}

const FREQUENCY_ORDER: Record<string, number> = {
  monthly: 1,
  quarterly: 2,
  semi_annual: 3,
  annual: 4,
  irregular: 5,
}

export function LiquidityForecast() {
  const { t } = useTranslation()
  const [expandedMonth, setExpandedMonth] = useState<string | null>(null)
  const [editingPattern, setEditingPattern] = useState<RecurringPattern | null>(null)

  // Filter state - independent toggles
  const [showIncome, setShowIncome] = useState(true)
  const [showCosts, setShowCosts] = useState(true)

  // Reference point state (known balance at a specific date)
  const currentYear = new Date().getFullYear()
  const janFirst = `${currentYear}-01-01`
  const [referenceDate, setReferenceDate] = useState(janFirst)
  const [referenceAmount, setReferenceAmount] = useState('0')

  // Sort state
  const [sortColumn, setSortColumn] = useState<SortColumn>('amount')
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc')

  // Search state
  const [searchQuery, setSearchQuery] = useState('')

  // Always show full calendar year (12 months)
  const { data, loading, refetch } = useQuery(LIQUIDITY_FORECAST_QUERY, {
    variables: { months: 12 },
  })

  const [detectPatterns, { loading: detecting }] = useMutation(DETECT_PATTERNS, {
    onCompleted: () => refetch(),
  })
  const [confirmPattern] = useMutation(CONFIRM_PATTERN, { onCompleted: () => refetch() })
  const [ignorePattern] = useMutation(IGNORE_PATTERN, { onCompleted: () => refetch() })
  const [pausePattern] = useMutation(PAUSE_PATTERN, { onCompleted: () => refetch() })
  const [resumePattern] = useMutation(RESUME_PATTERN, { onCompleted: () => refetch() })

  const forecast = data?.liquidityForecast
  const patterns: RecurringPattern[] = data?.recurringPatterns || []

  // Filter and sort patterns
  const filteredPatterns = useMemo(() => {
    let result = patterns.filter((p) => {
      // Type filter
      const isIncome = p.averageAmount > 0
      const isCost = p.averageAmount < 0
      if (isIncome && !showIncome) return false
      if (isCost && !showCosts) return false

      // Search filter
      if (searchQuery) {
        const query = searchQuery.toLowerCase()
        if (!p.counterparty.name.toLowerCase().includes(query)) return false
      }

      return true
    })

    // Sort
    result.sort((a, b) => {
      let cmp = 0
      switch (sortColumn) {
        case 'counterparty':
          cmp = a.counterparty.name.localeCompare(b.counterparty.name)
          break
        case 'amount':
          cmp = Math.abs(a.averageAmount) - Math.abs(b.averageAmount)
          break
        case 'frequency':
          cmp = (FREQUENCY_ORDER[a.frequency] || 99) - (FREQUENCY_ORDER[b.frequency] || 99)
          break
        case 'confidence':
          cmp = a.confidenceScore - b.confidenceScore
          break
      }
      return sortDirection === 'asc' ? cmp : -cmp
    })

    return result
  }, [patterns, showIncome, showCosts, searchQuery, sortColumn, sortDirection])

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc')
    } else {
      setSortColumn(column)
      setSortDirection('desc')
    }
  }

  const SortIcon = ({ column }: { column: SortColumn }) => {
    if (sortColumn !== column) return <ArrowUpDown className="h-3 w-3" />
    return sortDirection === 'asc' ? <ArrowUp className="h-3 w-3" /> : <ArrowDown className="h-3 w-3" />
  }

  // Calculate filtered projection with running balance based on reference point
  const filteredProjection: FilteredMonth[] = useMemo(() => {
    const refAmount = parseFloat(referenceAmount) || 0
    const refDate = new Date(referenceDate)
    const refMonthKey = refDate.getFullYear() * 12 + refDate.getMonth()

    // Build data for all 12 months of current year (Jan-Dec)
    interface MonthDataItem {
      monthKey: number
      monthStr: string
      filteredCosts: number
      filteredIncome: number
      netChange: number
      transactions: ProjectedTransaction[]
    }

    const allMonths: MonthDataItem[] = []

    for (let m = 0; m < 12; m++) {
      const monthKey = currentYear * 12 + m
      const monthStr = `${currentYear}-${String(m + 1).padStart(2, '0')}-01`

      // Find matching month from backend data
      const backendMonth = forecast?.months?.find((bm: MonthlyForecast) => {
        const bmDate = new Date(bm.month)
        return bmDate.getFullYear() === currentYear && bmDate.getMonth() === m
      })

      const costs = backendMonth ? parseFloat(String(backendMonth.projectedCosts)) || 0 : 0
      const income = backendMonth ? parseFloat(String(backendMonth.projectedIncome)) || 0 : 0
      const filteredCosts = showCosts ? costs : 0
      const filteredIncome = showIncome ? income : 0
      const transactions = backendMonth?.transactions || []

      allMonths.push({
        monthKey,
        monthStr,
        filteredCosts,
        filteredIncome,
        netChange: filteredCosts + filteredIncome,
        transactions,
      })
    }

    // Find reference month index
    let refIndex = allMonths.findIndex((m) => m.monthKey >= refMonthKey)
    if (refIndex === -1) refIndex = allMonths.length - 1

    // Calculate balances from reference point
    const balances: number[] = new Array(12)
    balances[refIndex] = refAmount

    // Work backwards
    for (let i = refIndex - 1; i >= 0; i--) {
      balances[i] = balances[i + 1] - allMonths[i + 1].netChange
    }

    // Work forwards
    for (let i = refIndex + 1; i < 12; i++) {
      balances[i] = balances[i - 1] + allMonths[i].netChange
    }

    return allMonths.map((m, i): FilteredMonth => {
      const filteredTransactions = m.transactions.filter((txn: ProjectedTransaction) => {
        if (txn.amount > 0 && !showIncome) return false
        if (txn.amount < 0 && !showCosts) return false
        return true
      })

      return {
        month: m.monthStr,
        startingBalance: 0,
        projectedCosts: m.filteredCosts,
        projectedIncome: m.filteredIncome,
        endingBalance: balances[i],
        transactions: m.transactions,
        filteredCosts: m.filteredCosts,
        filteredIncome: m.filteredIncome,
        endBalance: balances[i],
        filteredTransactions,
      }
    })
  }, [forecast, showIncome, showCosts, referenceAmount, referenceDate, currentYear])

  const formatFrequency = (freq: string) => {
    const key = `liquidity.frequency.${freq}`
    return t(key)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('liquidity.title')}</h1>
        <div className="flex items-center gap-2">
          <HelpVideoButton />
          <button
            onClick={() => detectPatterns()}
            disabled={detecting}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {detecting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
            {t('liquidity.detectPatterns')}
          </button>
        </div>
      </div>

      {/* Info Note and Account Offset */}
      <div className="grid gap-4 md:grid-cols-2">
        {/* Info Note */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
          {t('liquidity.infoNote')}
        </div>

        {/* Reference Point */}
        <div className="rounded-lg border bg-white p-4">
          <h3 className="mb-3 text-sm font-medium text-gray-700">{t('liquidity.referencePoint')}</h3>
          <div className="flex items-end gap-4">
            <div className="flex-1">
              <label className="mb-1 block text-xs text-gray-500">{t('liquidity.referenceDate')}</label>
              <input
                type="date"
                value={referenceDate}
                onChange={(e) => setReferenceDate(e.target.value)}
                className="w-full rounded-md border border-gray-300 px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            <div className="flex-1">
              <label className="mb-1 block text-xs text-gray-500">{t('liquidity.referenceAmount')}</label>
              <div className="relative">
                <input
                  type="number"
                  step="0.01"
                  value={referenceAmount}
                  onChange={(e) => setReferenceAmount(e.target.value)}
                  className="w-full rounded-md border border-gray-300 px-3 py-1.5 pr-10 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
                <span className="absolute right-3 top-1/2 -translate-y-1/2 text-sm text-gray-400">EUR</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Forecast Chart */}
      {forecast && forecast.months.length > 0 && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-medium">{t('liquidity.forecastChart')}</h2>
          <ForecastChart
            months={forecast.months}
            referenceDate={referenceDate}
            referenceAmount={parseFloat(referenceAmount) || 0}
            showIncome={showIncome}
            showCosts={showCosts}
          />
        </div>
      )}

      {/* Recurring Patterns */}
      <div className="rounded-lg border bg-white p-6">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-medium">{t('liquidity.patterns')}</h2>
          <div className="flex items-center gap-4">
            {/* Search */}
            <div className="relative">
              <Search className="absolute left-2.5 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder={t('liquidity.searchPlaceholder')}
                className="w-48 rounded-md border border-gray-300 py-1.5 pl-8 pr-3 text-sm placeholder:text-gray-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
            </div>
            {/* Toggle buttons */}
            <div className="flex gap-1">
              <button
                onClick={() => setShowCosts(!showCosts)}
                className={`rounded-md px-3 py-1 text-sm font-medium ${
                  showCosts
                    ? 'bg-red-100 text-red-700'
                    : 'text-gray-400 hover:bg-gray-100'
                }`}
              >
                {t('liquidity.filter.costs')}
              </button>
              <button
                onClick={() => setShowIncome(!showIncome)}
                className={`rounded-md px-3 py-1 text-sm font-medium ${
                  showIncome
                    ? 'bg-green-100 text-green-700'
                    : 'text-gray-400 hover:bg-gray-100'
                }`}
              >
                {t('liquidity.filter.income')}
              </button>
            </div>
          </div>
        </div>

        {/* Sort headers */}
        <div className="mt-4 flex items-center gap-4 border-b pb-2 text-xs font-medium text-gray-500">
          <button
            onClick={() => handleSort('counterparty')}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            {t('liquidity.sortCounterparty')} <SortIcon column="counterparty" />
          </button>
          <button
            onClick={() => handleSort('amount')}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            {t('liquidity.sortAmount')} <SortIcon column="amount" />
          </button>
          <button
            onClick={() => handleSort('frequency')}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            {t('liquidity.sortFrequency')} <SortIcon column="frequency" />
          </button>
          <button
            onClick={() => handleSort('confidence')}
            className="flex items-center gap-1 hover:text-gray-900"
          >
            {t('liquidity.sortConfidence')} <SortIcon column="confidence" />
          </button>
        </div>

        {!showIncome && !showCosts ? (
          <div className="mt-6 text-center text-gray-500">
            <p>{t('liquidity.noFiltersHint')}</p>
          </div>
        ) : filteredPatterns.length === 0 ? (
          <div className="mt-6 text-center text-gray-500">
            <p>{t('liquidity.noPatterns')}</p>
            <p className="mt-2 text-sm">{t('liquidity.noPatternsHint')}</p>
          </div>
        ) : (
          <div className="mt-4 space-y-2">
            {filteredPatterns.map((pattern) => (
              <div
                key={pattern.id}
                className={`rounded-lg border p-4 ${
                  pattern.isPaused ? 'bg-gray-50 opacity-60' : ''
                }`}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    {pattern.averageAmount < 0 ? (
                      <TrendingDown className="h-5 w-5 text-red-500" />
                    ) : (
                      <TrendingUp className="h-5 w-5 text-green-500" />
                    )}
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{pattern.counterparty.name}</span>
                        {pattern.isConfirmed && (
                          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs text-green-700">
                            {t('liquidity.confirmed')}
                          </span>
                        )}
                        {pattern.isPaused && (
                          <span className="rounded-full bg-yellow-100 px-2 py-0.5 text-xs text-yellow-700">
                            {t('liquidity.paused')}
                          </span>
                        )}
                      </div>
                      <div className="text-sm text-gray-500">
                        {formatFrequency(pattern.frequency)}
                        {pattern.dayOfMonth && ` • ${t('liquidity.dayOfMonth', { day: pattern.dayOfMonth })}`}
                        {pattern.projectedNextDate && (
                          <span>
                            {' '}
                            • {t('liquidity.nextDate')}: {formatDate(pattern.projectedNextDate)}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <div className="text-right">
                      <div
                        className={`font-medium ${
                          pattern.averageAmount < 0 ? 'text-red-600' : 'text-green-600'
                        }`}
                      >
                        {formatCurrency(pattern.averageAmount)}
                      </div>
                      <div className="text-xs text-gray-500">
                        {Math.round(pattern.confidenceScore * 100)}% {t('liquidity.confidence')}
                      </div>
                    </div>
                    <div className="flex gap-1">
                      {!pattern.isConfirmed && (
                        <button
                          onClick={() => confirmPattern({ variables: { patternId: pattern.id } })}
                          className="rounded p-1.5 text-gray-400 hover:bg-green-50 hover:text-green-600"
                          title={t('liquidity.confirm')}
                        >
                          <Check className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => ignorePattern({ variables: { patternId: pattern.id } })}
                        className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                        title={t('liquidity.ignore')}
                      >
                        <X className="h-4 w-4" />
                      </button>
                      {pattern.isPaused ? (
                        <button
                          onClick={() => resumePattern({ variables: { patternId: pattern.id } })}
                          className="rounded p-1.5 text-gray-400 hover:bg-blue-50 hover:text-blue-600"
                          title={t('liquidity.resume')}
                        >
                          <Play className="h-4 w-4" />
                        </button>
                      ) : (
                        <button
                          onClick={() => pausePattern({ variables: { patternId: pattern.id } })}
                          className="rounded p-1.5 text-gray-400 hover:bg-yellow-50 hover:text-yellow-600"
                          title={t('liquidity.pause')}
                        >
                          <Pause className="h-4 w-4" />
                        </button>
                      )}
                      <button
                        onClick={() => setEditingPattern(pattern)}
                        className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        title={t('common.edit')}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Projection Table */}
      {filteredProjection.length > 0 && (
        <div className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-medium">{t('liquidity.projectionTable')}</h2>
          <div className="space-y-1">
            {filteredProjection.map((month) => (
              <div key={month.month} className="border rounded-lg">
                <button
                  onClick={() =>
                    setExpandedMonth(expandedMonth === month.month ? null : month.month)
                  }
                  className="flex w-full items-center justify-between px-4 py-3 hover:bg-gray-50"
                >
                  <div className="flex items-center gap-2">
                    {expandedMonth === month.month ? (
                      <ChevronDown className="h-4 w-4 text-gray-400" />
                    ) : (
                      <ChevronRight className="h-4 w-4 text-gray-400" />
                    )}
                    <span className="font-medium">
                      {new Date(month.month).toLocaleDateString(undefined, {
                        month: 'long',
                        year: 'numeric',
                      })}
                    </span>
                  </div>
                  <div className="flex items-center gap-6 text-sm">
                    {showCosts && (
                      <span className="text-red-600">
                        {formatCurrency(month.filteredCosts)}
                      </span>
                    )}
                    {showIncome && (
                      <span className="text-green-600">
                        +{formatCurrency(month.filteredIncome)}
                      </span>
                    )}
                    <span className="font-medium">
                      = {formatCurrency(month.endBalance)}
                    </span>
                  </div>
                </button>
                {expandedMonth === month.month && month.filteredTransactions.length > 0 && (
                  <div className="border-t px-4 py-2">
                    {month.filteredTransactions.map((txn, idx) => (
                        <div
                          key={idx}
                          className="flex items-center justify-between py-2 text-sm"
                        >
                          <div className="flex items-center gap-2">
                            <span
                              className={
                                txn.isConfirmed ? 'text-gray-900' : 'text-gray-500 italic'
                              }
                            >
                              {txn.counterparty.name}
                            </span>
                            {!txn.isConfirmed && (
                              <span className="text-xs text-gray-400">
                                ({t('liquidity.autoDetected')})
                              </span>
                            )}
                          </div>
                          <div className="flex items-center gap-4">
                            <span className="text-gray-500">
                              {formatDate(txn.projectedDate)}
                            </span>
                            <span
                              className={
                                txn.amount < 0 ? 'text-red-600' : 'text-green-600'
                              }
                            >
                              {formatCurrency(txn.amount)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
          </div>
        </div>
      )}

      {/* Edit Pattern Modal */}
      {editingPattern && (
        <EditPatternModal
          pattern={editingPattern}
          onClose={() => setEditingPattern(null)}
          onSave={() => {
            setEditingPattern(null)
            refetch()
          }}
        />
      )}
    </div>
  )
}
