import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, gql } from '@apollo/client'
import { Loader2, ArrowUpDown, ArrowUp, ArrowDown } from 'lucide-react'

const DEPARTMENT_TIME_ANALYSIS = gql`
  query DepartmentTimeAnalysis($dateFrom: Date!, $dateTo: Date!) {
    departmentTimeAnalysis(dateFrom: $dateFrom, dateTo: $dateTo) {
      totalHours
      distribution {
        departmentName
        hours
        percentage
      }
      userMatrix {
        userName
        totalHours
        departments {
          departmentName
          hours
          percentage
        }
      }
    }
  }
`

const DEPARTMENTS_QUERY = gql`
  query DepartmentsCheck {
    departments { id name }
  }
`

function formatDate(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function lastDayOfMonth(year: number, month: number): Date {
  return new Date(year, month + 1, 0)
}

function getMonthShortcuts(): { label: string; from: string; to: string }[] {
  const now = new Date()
  const shortcuts: { label: string; from: string; to: string }[] = []

  // Last 6 months (most recent first, excluding current month)
  for (let i = 1; i <= 6; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
    const last = lastDayOfMonth(d.getFullYear(), d.getMonth())
    const label = d.toLocaleDateString(undefined, { month: 'short', year: '2-digit' })
    shortcuts.push({ label, from: formatDate(d), to: formatDate(last) })
  }

  return shortcuts
}

const COLORS = [
  'bg-blue-500', 'bg-green-500', 'bg-amber-500', 'bg-purple-500',
  'bg-pink-500', 'bg-cyan-500', 'bg-orange-500', 'bg-teal-500',
  'bg-indigo-500', 'bg-red-400',
]

export function DepartmentAnalysis() {
  const { t, i18n } = useTranslation()
  const now = new Date()
  // Default to last full month
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const lastMonthEnd = lastDayOfMonth(lastMonthStart.getFullYear(), lastMonthStart.getMonth())

  const [dateFrom, setDateFrom] = useState(formatDate(lastMonthStart))
  const [dateTo, setDateTo] = useState(formatDate(lastMonthEnd))
  const [showPercentage, setShowPercentage] = useState(false)
  const [sortBy, setSortBy] = useState<string>('__user')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')

  const monthShortcuts = useMemo(() => getMonthShortcuts(), [])
  const ytdFrom = formatDate(new Date(now.getFullYear(), 0, 1))
  const ytdTo = formatDate(now)
  const ytdLabel = i18n.language === 'de' ? 'JzD' : 'YTD'

  const { data: deptsData } = useQuery(DEPARTMENTS_QUERY)
  const { data, loading } = useQuery(DEPARTMENT_TIME_ANALYSIS, {
    variables: { dateFrom, dateTo },
    skip: !dateFrom || !dateTo,
  })

  const departments = deptsData?.departments || []
  const analysis = data?.departmentTimeAnalysis
  const distribution = analysis?.distribution || []
  const userMatrix = analysis?.userMatrix || []
  const totalHours = analysis?.totalHours || 0

  // Get unique department names from distribution for matrix columns
  const deptNames = distribution.map((d: { departmentName: string }) => d.departmentName)

  type MatrixRow = { userName: string; totalHours: number; departments: { departmentName: string; hours: number; percentage: number }[] }

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder(field === '__user' ? 'asc' : 'desc')
    }
  }

  const SortIcon = ({ field }: { field: string }) => {
    if (sortBy !== field) return <ArrowUpDown className="ml-1 h-4 w-4 text-gray-400" />
    return sortOrder === 'asc' ? <ArrowUp className="ml-1 h-4 w-4" /> : <ArrowDown className="ml-1 h-4 w-4" />
  }

  const sortedMatrix = useMemo(() => {
    if (!userMatrix.length) return []
    return [...userMatrix].sort((a: MatrixRow, b: MatrixRow) => {
      let cmp: number
      if (sortBy === '__user') {
        cmp = a.userName.localeCompare(b.userName)
      } else if (sortBy === '__total') {
        cmp = a.totalHours - b.totalHours
      } else {
        const aVal = a.departments.find((d: { departmentName: string }) => d.departmentName === sortBy)?.hours || 0
        const bVal = b.departments.find((d: { departmentName: string }) => d.departmentName === sortBy)?.hours || 0
        cmp = aVal - bVal
      }
      return sortOrder === 'asc' ? cmp : -cmp
    })
  }, [userMatrix, sortBy, sortOrder])

  if (departments.length === 0 && !loading) {
    return (
      <div>
        <h1 className="text-2xl font-bold">{t('departmentAnalysis.title')}</h1>
        <p className="mt-4 text-gray-500">{t('departmentAnalysis.noDepartments')}</p>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t('departmentAnalysis.title')}</h1>

      {/* Month shortcuts */}
      <div className="mb-3 flex flex-wrap items-center gap-2">
        {monthShortcuts.map((s) => (
          <button
            key={s.from}
            onClick={() => { setDateFrom(s.from); setDateTo(s.to) }}
            className={`rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
              dateFrom === s.from && dateTo === s.to
                ? 'border-blue-500 bg-blue-50 text-blue-700'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            }`}
          >
            {s.label}
          </button>
        ))}
        <button
          onClick={() => { setDateFrom(ytdFrom); setDateTo(ytdTo) }}
          className={`rounded-md border px-3 py-1.5 text-sm font-medium transition-colors ${
            dateFrom === ytdFrom && dateTo === ytdTo
              ? 'border-blue-500 bg-blue-50 text-blue-700'
              : 'border-gray-300 text-gray-600 hover:bg-gray-50'
          }`}
        >
          {ytdLabel}
        </button>
      </div>

      {/* Date range picker */}
      <div className="mb-6 flex items-center gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('departmentAnalysis.dateFrom')}</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('departmentAnalysis.dateTo')}</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="mt-1 rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          {t('departmentAnalysis.loading')}
        </div>
      ) : totalHours === 0 ? (
        <p className="py-12 text-gray-500">{t('departmentAnalysis.noData')}</p>
      ) : (
        <>
          {/* Distribution section */}
          <div className="mb-8 rounded-lg border bg-white p-6">
            <h2 className="mb-4 text-lg font-medium text-gray-900">{t('departmentAnalysis.distribution')}</h2>
            <p className="mb-4 text-sm text-gray-500">
              {t('departmentAnalysis.totalHours')}: <span className="font-semibold text-gray-900">{totalHours.toFixed(1)}</span>
            </p>

            {/* Stacked bar */}
            <div className="mb-4 flex h-8 overflow-hidden rounded-full">
              {distribution.map((d: { departmentName: string; percentage: number }, i: number) => (
                <div
                  key={d.departmentName}
                  className={`${COLORS[i % COLORS.length]} transition-all`}
                  style={{ width: `${d.percentage}%` }}
                  title={`${d.departmentName}: ${d.percentage.toFixed(1)}%`}
                />
              ))}
            </div>

            {/* Legend / table */}
            <div className="space-y-2">
              {distribution.map((d: { departmentName: string; hours: number; percentage: number }, i: number) => (
                <div key={d.departmentName} className="flex items-center gap-3">
                  <div className={`h-3 w-3 rounded-full ${COLORS[i % COLORS.length]}`} />
                  <span className="min-w-[160px] text-sm font-medium text-gray-900">{d.departmentName}</span>
                  <div className="flex-1">
                    <div className="h-2 rounded-full bg-gray-100">
                      <div
                        className={`h-2 rounded-full ${COLORS[i % COLORS.length]} opacity-60`}
                        style={{ width: `${d.percentage}%` }}
                      />
                    </div>
                  </div>
                  <span className="min-w-[60px] text-right text-sm text-gray-600">{d.hours.toFixed(1)}h</span>
                  <span className="min-w-[50px] text-right text-sm font-medium text-gray-900">{d.percentage.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          {/* User x Department matrix */}
          <div className="rounded-lg border bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">{t('departmentAnalysis.userMatrix')}</h2>
              <div className="flex rounded-md border">
                <button
                  onClick={() => setShowPercentage(false)}
                  className={`px-3 py-1 text-sm ${!showPercentage ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  {t('departmentAnalysis.showHours')}
                </button>
                <button
                  onClick={() => setShowPercentage(true)}
                  className={`border-l px-3 py-1 text-sm ${showPercentage ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                >
                  {t('departmentAnalysis.showPercentage')}
                </button>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th
                      className="cursor-pointer px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                      onClick={() => handleSort('__user')}
                    >
                      <div className="flex items-center">
                        {t('departmentAnalysis.user')}
                        <SortIcon field="__user" />
                      </div>
                    </th>
                    {deptNames.map((name: string) => (
                      <th
                        key={name}
                        className="cursor-pointer px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                        onClick={() => handleSort(name)}
                      >
                        <div className="flex items-center justify-end">
                          {name}
                          <SortIcon field={name} />
                        </div>
                      </th>
                    ))}
                    <th
                      className="cursor-pointer px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                      onClick={() => handleSort('__total')}
                    >
                      <div className="flex items-center justify-end">
                        {t('departmentAnalysis.total')}
                        <SortIcon field="__total" />
                      </div>
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 bg-white">
                  {sortedMatrix.map((row: { userName: string; totalHours: number; departments: { departmentName: string; hours: number; percentage: number }[] }) => (
                    <tr key={row.userName}>
                      <td className="px-6 py-3 text-sm font-medium text-gray-900">{row.userName}</td>
                      {deptNames.map((name: string) => {
                        const cell = row.departments.find((d: { departmentName: string }) => d.departmentName === name)
                        const value = cell
                          ? showPercentage
                            ? `${cell.percentage.toFixed(1)}%`
                            : cell.hours.toFixed(1)
                          : showPercentage ? '0.0%' : '0.0'
                        return (
                          <td key={name} className={`px-6 py-3 text-right text-sm ${cell && cell.hours > 0 ? 'text-gray-900' : 'text-gray-300'}`}>
                            {value}
                          </td>
                        )
                      })}
                      <td className="px-6 py-3 text-right text-sm font-semibold text-gray-900">{row.totalHours.toFixed(1)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
