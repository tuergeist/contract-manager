import { useState, useMemo } from 'react'
import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { useQuery, gql } from '@apollo/client'
import { Loader2, ArrowUpDown, ArrowUp, ArrowDown, Download, Info, ShieldAlert } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import { AbsenceReport } from './AbsenceReport'

const DEPARTMENT_TIME_ANALYSIS = gql`
  query DepartmentTimeAnalysis($dateFrom: Date!, $dateTo: Date!) {
    departmentTimeAnalysis(dateFrom: $dateFrom, dateTo: $dateTo) {
      totalHours
      totalHoursFilled
      distribution {
        departmentName
        hours
        percentage
      }
      distributionFilled {
        departmentName
        hours
        percentage
      }
      userMatrix {
        userName
        totalHours
        absenceDays
        sickDays
        sickCertificateDays
        sickChildDays
        departments {
          departmentName
          hours
          percentage
        }
      }
      userMatrixFilled {
        userName
        totalHours
        absenceDays
        sickDays
        sickCertificateDays
        sickChildDays
        departments {
          departmentName
          hours
          percentage
        }
      }
      costDistribution {
        departmentName
        cost
        percentage
        ftes
      }
      totalCost
    }
  }
`

const DEPARTMENTS_QUERY = gql`
  query DepartmentsCheck {
    departments { id name }
  }
`

const REPORT_SCHEDULES_DEPT_QUERY = gql`
  query ReportSchedulesDept {
    reportSchedules {
      reportType
      enabled
    }
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
  const year = now.getFullYear()

  // All months of current year up to and including current month (most recent first)
  for (let m = now.getMonth(); m >= 0; m--) {
    const d = new Date(year, m, 1)
    const last = lastDayOfMonth(year, m)
    const label = d.toLocaleDateString(undefined, { month: 'short' })
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
  const { t } = useTranslation()
  const { hasPermission } = useAuth()

  if (!hasPermission('department_analysis', 'read')) {
    return (
      <div className="max-w-2xl">
        <h1 className="text-2xl font-bold">{t('departmentAnalysis.title')}</h1>
        <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 p-6">
          <div className="flex items-start gap-3">
            <ShieldAlert className="h-5 w-5 shrink-0 text-amber-600 mt-0.5" />
            <div>
              <h2 className="font-medium text-amber-900">
                {t('departmentAnalysis.permissionDenied.title', 'Keine Berechtigung')}
              </h2>
              <p className="mt-1 text-sm text-amber-800">
                {t('departmentAnalysis.permissionDenied.body',
                  'Für die Abteilungs-Auswertung wird die Berechtigung "department_analysis.read" benötigt. Bitte wende dich an einen Administrator deines Tenants, falls du Zugriff brauchst.')}
              </p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return <DepartmentAnalysisContent />
}

function DepartmentAnalysisContent() {
  const { t, i18n } = useTranslation()
  const now = new Date()
  // Default to last full month
  const lastMonthStart = new Date(now.getFullYear(), now.getMonth() - 1, 1)
  const lastMonthEnd = lastDayOfMonth(lastMonthStart.getFullYear(), lastMonthStart.getMonth())

  const [dateFrom, setDateFrom] = useState(formatDate(lastMonthStart))
  const [dateTo, setDateTo] = useState(formatDate(lastMonthEnd))
  const [showPercentage, setShowPercentage] = useState(false)
  const [chartView, setChartView] = useState<'hours' | 'costs'>('hours')
  const [costViewMode, setCostViewMode] = useState<'chart' | 'table'>('chart')
  const [showFilled, setShowFilled] = useState(false)
  const [sortBy, setSortBy] = useState<string>('__user')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc')
  const [activeTab, setActiveTab] = useState<'allocation' | 'absences'>('allocation')

  const monthShortcuts = useMemo(() => getMonthShortcuts(), [])
  const ytdFrom = formatDate(new Date(now.getFullYear(), 0, 1))
  const ytdTo = formatDate(now)
  const ytdLabel = i18n.language === 'de' ? 'JzD' : 'YTD'

  const { data: deptsData } = useQuery(DEPARTMENTS_QUERY)
  const { data: schedulesData } = useQuery(REPORT_SCHEDULES_DEPT_QUERY)
  const deptSchedule = schedulesData?.reportSchedules?.find(
    (s: { reportType: string }) => s.reportType === 'department_time'
  )
  const isDeptAutoReportActive = deptSchedule?.enabled === true

  const { data, loading } = useQuery(DEPARTMENT_TIME_ANALYSIS, {
    variables: { dateFrom, dateTo },
    skip: !dateFrom || !dateTo,
  })

  const departments = deptsData?.departments || []
  const analysis = data?.departmentTimeAnalysis
  const distributionRaw = analysis?.distribution || []
  const distributionFilled = analysis?.distributionFilled || null
  const userMatrix = analysis?.userMatrix || []
  const totalHoursRaw = analysis?.totalHours || 0
  const totalHoursFilled = analysis?.totalHoursFilled || null
  const userMatrixFilled = analysis?.userMatrixFilled || null
  const costDistribution = analysis?.costDistribution || []
  const totalCost = analysis?.totalCost || 0

  const distribution = showFilled && distributionFilled ? distributionFilled : distributionRaw
  const totalHours = showFilled && totalHoursFilled != null ? totalHoursFilled : totalHoursRaw

  // Get unique department names from distribution for matrix columns
  const deptNames = distribution.map((d: { departmentName: string }) => d.departmentName)

  type MatrixRow = { userName: string; totalHours: number; absenceDays: number | null; sickDays: number | null; sickCertificateDays: number | null; sickChildDays: number | null; departments: { departmentName: string; hours: number; percentage: number }[] }

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

  const activeMatrix = showFilled && userMatrixFilled ? userMatrixFilled : userMatrix
  const hasAbsenceData = activeMatrix.some((r: MatrixRow) => r.absenceDays != null && r.absenceDays > 0)

  const sortedMatrix = useMemo(() => {
    if (!activeMatrix.length) return []
    return [...activeMatrix].sort((a: MatrixRow, b: MatrixRow) => {
      let cmp: number
      if (sortBy === '__user') {
        cmp = a.userName.localeCompare(b.userName)
      } else if (sortBy === '__absence') {
        cmp = (a.absenceDays || 0) - (b.absenceDays || 0)
      } else if (sortBy === '__sick') {
        cmp = (a.sickDays || 0) - (b.sickDays || 0)
      } else if (sortBy === '__sickCert') {
        cmp = (a.sickCertificateDays || 0) - (b.sickCertificateDays || 0)
      } else if (sortBy === '__sickChild') {
        cmp = (a.sickChildDays || 0) - (b.sickChildDays || 0)
      } else if (sortBy === '__total') {
        cmp = a.totalHours - b.totalHours
      } else {
        const aVal = a.departments.find((d: { departmentName: string }) => d.departmentName === sortBy)?.hours || 0
        const bVal = b.departments.find((d: { departmentName: string }) => d.departmentName === sortBy)?.hours || 0
        cmp = aVal - bVal
      }
      return sortOrder === 'asc' ? cmp : -cmp
    })
  }, [activeMatrix, sortBy, sortOrder])

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
      <h1 className="text-2xl font-bold mb-4">{t('departmentAnalysis.title')}</h1>

      {/* Tab switcher */}
      <div className="mb-6 flex gap-1 border-b">
        <button
          onClick={() => setActiveTab('allocation')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'allocation'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          {t('departmentAnalysis.allocationTab')}
        </button>
        <button
          onClick={() => setActiveTab('absences')}
          className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors ${
            activeTab === 'absences'
              ? 'border-blue-500 text-blue-600'
              : 'border-transparent text-gray-500 hover:text-gray-700'
          }`}
        >
          {t('departmentAnalysis.absencesTab')}
        </button>
      </div>

      {activeTab === 'absences' && <AbsenceReport />}

      {activeTab === 'allocation' && <>
      {/* Auto-report banner */}
      {isDeptAutoReportActive && (
        <div className="mb-4 flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm text-blue-800">
          <Info className="h-4 w-4 shrink-0" />
          <span>{t('settings.reports.autoReportActive')}</span>
          <Link to="/settings/general/reports" className="ml-1 underline">{t('settings.reports.openSettings')}</Link>
        </div>
      )}

      {/* Month shortcuts + date range picker */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
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
        <div className="ml-auto flex items-center gap-2">
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <span className="text-gray-400">–</span>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 py-12 text-gray-500">
          <Loader2 className="h-5 w-5 animate-spin" />
          {t('departmentAnalysis.loading')}
        </div>
      ) : totalHoursRaw === 0 ? (
        <p className="py-12 text-gray-500">{t('departmentAnalysis.noData')}</p>
      ) : (
        <>
          {/* Distribution section */}
          <div className="mb-8 rounded-lg border bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">
                {chartView === 'hours' ? t('departmentAnalysis.distribution') : t('departmentAnalysis.costDistribution')}
              </h2>
              <div className="flex items-center gap-3">
                {distributionFilled && (
                  <div className="flex rounded-md border">
                    <button
                      onClick={() => setShowFilled(false)}
                      className={`px-3 py-1 text-sm ${!showFilled ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                    >
                      {t('departmentAnalysis.logged')}
                    </button>
                    <button
                      onClick={() => setShowFilled(true)}
                      className={`border-l px-3 py-1 text-sm ${showFilled ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                    >
                      {t('departmentAnalysis.filled')}
                    </button>
                  </div>
                )}
                {costDistribution.length > 0 && totalCost > 0 && (
                  <div className="flex rounded-md border">
                    <button
                      onClick={() => setChartView('hours')}
                      className={`px-3 py-1 text-sm ${chartView === 'hours' ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                    >
                      {t('departmentAnalysis.showHours')}
                    </button>
                    <button
                      onClick={() => setChartView('costs')}
                      className={`border-l px-3 py-1 text-sm ${chartView === 'costs' ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                    >
                      {t('departmentAnalysis.ftes')}
                    </button>
                  </div>
                )}
              </div>
            </div>

            {chartView === 'hours' ? (
              <>
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
                  {(() => {
                    const maxPct = Math.max(...distribution.map((d: { percentage: number }) => d.percentage))
                    const barMax = maxPct > 40 ? Math.min(100, maxPct + 5) : 40
                    return distribution.map((d: { departmentName: string; hours: number; percentage: number }, i: number) => (
                      <div key={d.departmentName} className="flex items-center gap-3">
                        <div className={`h-3 w-3 rounded-full ${COLORS[i % COLORS.length]}`} />
                        <span className="min-w-[160px] text-sm font-medium text-gray-900">{d.departmentName}</span>
                        <div className="flex-1">
                          <div className="h-2 rounded-full bg-gray-100">
                            <div
                              className={`h-2 rounded-full ${COLORS[i % COLORS.length]} opacity-60`}
                              style={{ width: `${(d.percentage / barMax) * 100}%` }}
                            />
                          </div>
                        </div>
                        <span className="min-w-[60px] text-right text-sm text-gray-600">{d.hours.toFixed(1)}h</span>
                        <span className="min-w-[50px] text-right text-sm font-medium text-gray-900">{d.percentage.toFixed(1)}%</span>
                      </div>
                    ))
                  })()}
                </div>
              </>
            ) : (
              <>
                <div className="mb-4 flex items-center gap-3">
                  <p className="text-sm text-gray-500">
                    {t('departmentAnalysis.ftes')}: <span className="font-semibold text-gray-900">{costDistribution.reduce((sum: number, d: { ftes: number }) => sum + d.ftes, 0).toFixed(2)}</span>
                  </p>
                  <div className="ml-auto flex items-center gap-2">
                    <div className="flex rounded-md border">
                      <button
                        onClick={() => setCostViewMode('chart')}
                        className={`px-3 py-1 text-sm ${costViewMode === 'chart' ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                      >
                        {t('departmentAnalysis.chart')}
                      </button>
                      <button
                        onClick={() => setCostViewMode('table')}
                        className={`border-l px-3 py-1 text-sm ${costViewMode === 'table' ? 'bg-blue-50 font-medium text-blue-700' : 'text-gray-600 hover:bg-gray-50'}`}
                      >
                        {t('departmentAnalysis.table')}
                      </button>
                    </div>
                    <button
                      onClick={() => {
                        const header = [t('departmentAnalysis.department'), t('departmentAnalysis.ftes'), '%'].join(';')
                        const rows = costDistribution.map((d: { departmentName: string; percentage: number; ftes: number }) =>
                          [d.departmentName, d.ftes.toFixed(2), d.percentage.toFixed(1)].join(';')
                        )
                        const totalFtes = costDistribution.reduce((sum: number, d: { ftes: number }) => sum + d.ftes, 0)
                        rows.push([t('departmentAnalysis.total'), totalFtes.toFixed(2), '100.0'].join(';'))
                        const csv = [header, ...rows].join('\n')
                        const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
                        const url = URL.createObjectURL(blob)
                        const a = document.createElement('a')
                        a.href = url
                        a.download = `fte-distribution-${dateFrom}-${dateTo}.csv`
                        a.click()
                        URL.revokeObjectURL(url)
                      }}
                      className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1 text-sm text-gray-600 hover:bg-gray-50"
                      title={t('departmentAnalysis.export')}
                    >
                      <Download className="h-4 w-4" />
                    </button>
                  </div>
                </div>

                {costViewMode === 'chart' ? (
                  <>
                    {/* Stacked bar */}
                    <div className="mb-4 flex h-8 overflow-hidden rounded-full">
                      {costDistribution.map((d: { departmentName: string; percentage: number }, i: number) => (
                        <div
                          key={d.departmentName}
                          className={`${COLORS[i % COLORS.length]} transition-all`}
                          style={{ width: `${d.percentage}%` }}
                          title={`${d.departmentName}: ${d.percentage.toFixed(1)}%`}
                        />
                      ))}
                    </div>

                    {/* Legend / bars */}
                    <div className="space-y-2">
                      {(() => {
                        const maxPct = Math.max(...costDistribution.map((d: { percentage: number }) => d.percentage))
                        const barMax = maxPct > 40 ? Math.min(100, maxPct + 5) : 40
                        return costDistribution.map((d: { departmentName: string; percentage: number; ftes: number }, i: number) => (
                          <div key={d.departmentName} className="flex items-center gap-3">
                            <div className={`h-3 w-3 rounded-full ${COLORS[i % COLORS.length]}`} />
                            <span className="min-w-[160px] text-sm font-medium text-gray-900">{d.departmentName}</span>
                            <div className="flex-1">
                              <div className="h-2 rounded-full bg-gray-100">
                                <div
                                  className={`h-2 rounded-full ${COLORS[i % COLORS.length]} opacity-60`}
                                  style={{ width: `${(d.percentage / barMax) * 100}%` }}
                                />
                              </div>
                            </div>
                            <span className="min-w-[60px] text-right text-sm text-gray-600">{d.ftes.toFixed(2)}</span>
                            <span className="min-w-[50px] text-right text-sm font-medium text-gray-900">{d.percentage.toFixed(1)}%</span>
                          </div>
                        ))
                      })()}
                    </div>
                  </>
                ) : (
                  <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                      <thead className="bg-gray-50">
                        <tr>
                          <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">{t('departmentAnalysis.department')}</th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">{t('departmentAnalysis.ftes')}</th>
                          <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">%</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-200 bg-white">
                        {costDistribution.map((d: { departmentName: string; percentage: number; ftes: number }) => (
                          <tr key={d.departmentName}>
                            <td className="px-6 py-3 text-sm font-medium text-gray-900">{d.departmentName}</td>
                            <td className="px-6 py-3 text-right text-sm text-gray-900">{d.ftes.toFixed(2)}</td>
                            <td className="px-6 py-3 text-right text-sm font-medium text-gray-900">{d.percentage.toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                      <tfoot className="bg-gray-50">
                        <tr>
                          <td className="px-6 py-3 text-sm font-semibold text-gray-900">{t('departmentAnalysis.total')}</td>
                          <td className="px-6 py-3 text-right text-sm font-semibold text-gray-900">
                            {costDistribution.reduce((sum: number, d: { ftes: number }) => sum + d.ftes, 0).toFixed(2)}
                          </td>
                          <td className="px-6 py-3 text-right text-sm font-semibold text-gray-900">100.0%</td>
                        </tr>
                      </tfoot>
                    </table>
                  </div>
                )}
              </>
            )}
          </div>

          {/* User x Department matrix */}
          <div className="rounded-lg border bg-white p-6">
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-lg font-medium text-gray-900">{t('departmentAnalysis.userMatrix')}</h2>
              <div className="flex items-center gap-2">
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
                <button
                  onClick={() => {
                    const header = [
                      t('departmentAnalysis.user'),
                      t('departmentAnalysis.absenceDays'),
                      t('departmentAnalysis.sickDays'),
                      t('departmentAnalysis.sickCertificateDays'),
                      t('departmentAnalysis.sickChildDays'),
                      ...deptNames,
                      t('departmentAnalysis.total'),
                    ].join(';')
                    const rows = sortedMatrix.map((row: MatrixRow) => {
                      const cells = [
                        row.userName,
                        row.absenceDays != null ? row.absenceDays.toFixed(1) : '',
                        row.sickDays != null ? row.sickDays.toFixed(1) : '',
                        row.sickCertificateDays != null ? row.sickCertificateDays.toFixed(1) : '',
                        row.sickChildDays != null ? row.sickChildDays.toFixed(1) : '',
                        ...deptNames.map((name: string) => {
                          const cell = row.departments.find((d: { departmentName: string }) => d.departmentName === name)
                          if (!cell) return showPercentage ? '0.0' : '0.0'
                          return showPercentage ? cell.percentage.toFixed(1) : cell.hours.toFixed(1)
                        }),
                        row.totalHours.toFixed(1),
                      ]
                      return cells.join(';')
                    })
                    const csv = [header, ...rows].join('\n')
                    const blob = new Blob(['﻿' + csv], { type: 'text/csv;charset=utf-8;' })
                    const url = URL.createObjectURL(blob)
                    const a = document.createElement('a')
                    a.href = url
                    a.download = `user-matrix-${dateFrom}-${dateTo}.csv`
                    a.click()
                    URL.revokeObjectURL(url)
                  }}
                  className="inline-flex items-center gap-1 rounded-md border border-gray-300 px-3 py-1 text-sm text-gray-600 hover:bg-gray-50"
                  title={t('departmentAnalysis.exportUserMatrix', 'User-Matrix exportieren')}
                >
                  <Download className="h-4 w-4" />
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
                    {hasAbsenceData && (
                      <>
                        <th
                          className="cursor-pointer px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                          onClick={() => handleSort('__absence')}
                          title={t('departmentAnalysis.absenceDaysHint', 'Gesamt-Abwesenheitstage')}
                        >
                          <div className="flex items-center justify-end">
                            {t('departmentAnalysis.absenceDays')}
                            <SortIcon field="__absence" />
                          </div>
                        </th>
                        <th
                          className="cursor-pointer px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                          onClick={() => handleSort('__sick')}
                          title={t('departmentAnalysis.sickDaysHint', 'Krank ohne Krankenschein')}
                        >
                          <div className="flex items-center justify-end">
                            {t('departmentAnalysis.sickDays')}
                            <SortIcon field="__sick" />
                          </div>
                        </th>
                        <th
                          className="cursor-pointer px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                          onClick={() => handleSort('__sickCert')}
                          title={t('departmentAnalysis.sickCertificateDaysHint', 'Krank mit Krankenschein (AU)')}
                        >
                          <div className="flex items-center justify-end">
                            {t('departmentAnalysis.sickCertificateDays')}
                            <SortIcon field="__sickCert" />
                          </div>
                        </th>
                        <th
                          className="cursor-pointer px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500 hover:bg-gray-100"
                          onClick={() => handleSort('__sickChild')}
                          title={t('departmentAnalysis.sickChildDaysHint', 'Kind krank')}
                        >
                          <div className="flex items-center justify-end">
                            {t('departmentAnalysis.sickChildDays')}
                            <SortIcon field="__sickChild" />
                          </div>
                        </th>
                      </>
                    )}
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
                  {sortedMatrix.map((row: MatrixRow) => (
                    <tr key={row.userName}>
                      <td className="px-6 py-3 text-sm font-medium text-gray-900">{row.userName}</td>
                      {hasAbsenceData && (
                        <>
                          <td className={`px-6 py-3 text-right text-sm ${row.absenceDays && row.absenceDays > 0 ? 'text-orange-600 font-medium' : 'text-gray-300'}`}>
                            {row.absenceDays != null ? row.absenceDays.toFixed(1) : '-'}
                          </td>
                          <td className={`px-6 py-3 text-right text-sm ${row.sickDays && row.sickDays > 0 ? 'text-red-600' : 'text-gray-300'}`}>
                            {row.sickDays != null && row.sickDays > 0 ? row.sickDays.toFixed(1) : '-'}
                          </td>
                          <td className={`px-6 py-3 text-right text-sm ${row.sickCertificateDays && row.sickCertificateDays > 0 ? 'text-red-700 font-medium' : 'text-gray-300'}`}>
                            {row.sickCertificateDays != null && row.sickCertificateDays > 0 ? row.sickCertificateDays.toFixed(1) : '-'}
                          </td>
                          <td className={`px-6 py-3 text-right text-sm ${row.sickChildDays && row.sickChildDays > 0 ? 'text-amber-600' : 'text-gray-300'}`}>
                            {row.sickChildDays != null && row.sickChildDays > 0 ? row.sickChildDays.toFixed(1) : '-'}
                          </td>
                        </>
                      )}
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
      </>}
    </div>
  )
}
