import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Download, AlertTriangle, CheckCircle, Users, FileSpreadsheet, RefreshCw } from 'lucide-react'

const VALIDATION_QUERY = gql`
  query AccountingValidation($periodStart: Date!, $periodEnd: Date!) {
    accountingValidation(periodStart: $periodStart, periodEnd: $periodEnd) {
      totalInvoices
      invoicesWithBookings
      invoicesWithoutBookings
      customersWithoutDebitorCount
      unmappedLineItems {
        invoiceNumber
        productName
        amount
        reason
      }
    }
  }
`

const DEBITOR_ACCOUNTS_QUERY = gql`
  query DebitorAccountsForExport($hasNumber: Boolean) {
    debitorAccounts(hasNumber: $hasNumber) {
      id
      customerId
      customerName
      customerNumber
      accountNumber
      notes
    }
  }
`

const EXPORTS_QUERY = gql`
  query AccountingExports {
    accountingExports {
      id
      periodStart
      periodEnd
      exportFormat
      entryCount
      totalAmount
      createdAt
      downloadUrl
    }
  }
`

const GENERATE_BOOKINGS = gql`
  mutation GenerateBookingsForPeriod($periodStart: Date!, $periodEnd: Date!, $regenerate: Boolean) {
    generateBookingsForPeriod(periodStart: $periodStart, periodEnd: $periodEnd, regenerate: $regenerate) {
      created
      skipped
      errors
    }
  }
`

const EXPORT_DATEV = gql`
  mutation ExportDatev($periodStart: Date!, $periodEnd: Date!) {
    exportDatev(periodStart: $periodStart, periodEnd: $periodEnd) {
      id
      periodStart
      periodEnd
      entryCount
      totalAmount
      downloadUrl
    }
  }
`

const BULK_ASSIGN_DEBITORS = gql`
  mutation BulkAssignDebitorAccounts {
    bulkAssignDebitorAccounts {
      assigned
      skipped
      errors
    }
  }
`

const ASSIGN_DEBITOR = gql`
  mutation AssignDebitorAccount($customerId: ID!, $accountNumber: String) {
    assignDebitorAccount(customerId: $customerId, accountNumber: $accountNumber) {
      id
      accountNumber
    }
  }
`

interface ValidationData {
  accountingValidation: {
    totalInvoices: number
    invoicesWithBookings: number
    invoicesWithoutBookings: number
    customersWithoutDebitorCount: number
    unmappedLineItems: {
      invoiceNumber: string
      productName: string
      amount: string
      reason: string
    }[]
  }
}

interface DebitorAccount {
  id: number
  customerId: number
  customerName: string
  customerNumber: string
  accountNumber: string
  notes: string
}

interface ExportRecord {
  id: number
  periodStart: string
  periodEnd: string
  exportFormat: string
  entryCount: number
  totalAmount: string
  createdAt: string
  downloadUrl: string | null
}

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleDateString('de-DE')
}

function formatAmount(amount: string | number) {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR' }).format(Number(amount))
}

export function DatevExportPage() {
  const { t } = useTranslation()
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth()) // previous month by default
  const [step, setStep] = useState<'validate' | 'debitors' | 'export'>('validate')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const periodStart = `${year}-${String(month + 1).padStart(2, '0')}-01`
  const lastDay = new Date(year, month + 1, 0).getDate()
  const periodEnd = `${year}-${String(month + 1).padStart(2, '0')}-${String(lastDay).padStart(2, '0')}`

  const { data: validationData, loading: validating, refetch: refetchValidation } = useQuery<ValidationData>(VALIDATION_QUERY, {
    variables: { periodStart, periodEnd },
  })

  const { data: debitorsData, refetch: refetchDebitors } = useQuery(DEBITOR_ACCOUNTS_QUERY, {
    variables: { hasNumber: false },
  })

  const { data: exportsData, refetch: refetchExports } = useQuery(EXPORTS_QUERY)

  const [generateBookings, { loading: generating }] = useMutation(GENERATE_BOOKINGS)
  const [exportDatev, { loading: exporting }] = useMutation(EXPORT_DATEV)
  const [bulkAssign, { loading: assigning }] = useMutation(BULK_ASSIGN_DEBITORS)
  const [assignDebitor] = useMutation(ASSIGN_DEBITOR)

  const validation = validationData?.accountingValidation
  const unassignedDebitors: DebitorAccount[] = debitorsData?.debitorAccounts || []
  const exports: ExportRecord[] = exportsData?.accountingExports || []

  const handleGenerateBookings = async () => {
    setMessage(null)
    try {
      const { data } = await generateBookings({
        variables: { periodStart, periodEnd, regenerate: false },
      })
      const result = data?.generateBookingsForPeriod
      setMessage({
        type: 'success',
        text: t('datevExport.bookingsGenerated', {
          created: result?.created || 0,
          skipped: result?.skipped || 0,
        }),
      })
      await refetchValidation()
    } catch {
      setMessage({ type: 'error', text: t('datevExport.bookingsGenerateFailed') })
    }
  }

  const handleBulkAssign = async () => {
    setMessage(null)
    try {
      const { data } = await bulkAssign()
      const result = data?.bulkAssignDebitorAccounts
      setMessage({
        type: 'success',
        text: t('datevExport.debitorsAssigned', { count: result?.assigned || 0 }),
      })
      await refetchDebitors()
      await refetchValidation()
    } catch {
      setMessage({ type: 'error', text: t('datevExport.debitorsAssignFailed') })
    }
  }

  const handleAssignSingle = async (customerId: number, accountNumber: string) => {
    try {
      await assignDebitor({ variables: { customerId: String(customerId), accountNumber } })
      await refetchDebitors()
      await refetchValidation()
    } catch {
      setMessage({ type: 'error', text: t('datevExport.debitorsAssignFailed') })
    }
  }

  const handleExport = async () => {
    setMessage(null)
    try {
      const { data } = await exportDatev({ variables: { periodStart, periodEnd } })
      const result = data?.exportDatev
      if (result?.downloadUrl) {
        window.open(result.downloadUrl, '_blank')
      }
      setMessage({
        type: 'success',
        text: t('datevExport.exportSuccess', {
          count: result?.entryCount || 0,
          total: formatAmount(result?.totalAmount || '0'),
        }),
      })
      await refetchExports()
    } catch {
      setMessage({ type: 'error', text: t('datevExport.exportFailed') })
    }
  }

  const months = Array.from({ length: 12 }, (_, i) => i)
  const years = Array.from({ length: 5 }, (_, i) => now.getFullYear() - i)

  const canExport = validation &&
    validation.customersWithoutDebitorCount === 0 &&
    validation.unmappedLineItems.length === 0 &&
    validation.invoicesWithBookings > 0

  return (
    <div>
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('datevExport.title')}</h1>
      </div>

      {/* Period Selector */}
      <div className="mt-4 flex items-center gap-4">
        <div className="flex items-center gap-2">
          <select
            value={month}
            onChange={(e) => { setMonth(parseInt(e.target.value)); setStep('validate') }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {months.map((m) => (
              <option key={m} value={m}>
                {new Date(2000, m).toLocaleDateString('de-DE', { month: 'long' })}
              </option>
            ))}
          </select>
          <select
            value={year}
            onChange={(e) => { setYear(parseInt(e.target.value)); setStep('validate') }}
            className="rounded-md border border-gray-300 px-3 py-2 text-sm"
          >
            {years.map((y) => (
              <option key={y} value={y}>{y}</option>
            ))}
          </select>
        </div>
        <span className="text-sm text-gray-500">
          {formatDate(periodStart)} – {formatDate(periodEnd)}
        </span>
      </div>

      {message && (
        <div className={`mt-4 rounded-md p-3 text-sm ${message.type === 'success' ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'}`}>
          {message.text}
        </div>
      )}

      {/* Step Navigation */}
      <div className="mt-6 flex gap-2 border-b border-gray-200">
        {(['validate', 'debitors', 'export'] as const).map((s) => (
          <button
            key={s}
            onClick={() => setStep(s)}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              step === s
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            {t(`datevExport.steps.${s}`)}
          </button>
        ))}
      </div>

      {/* Step: Validate */}
      {step === 'validate' && (
        <div className="mt-6 space-y-4">
          {validating ? (
            <div className="flex items-center gap-2 py-8 text-gray-500">
              <Loader2 className="h-5 w-5 animate-spin" />
              {t('datevExport.validating')}
            </div>
          ) : validation ? (
            <>
              {/* Summary Cards */}
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
                <div className="rounded-lg border bg-white p-4">
                  <p className="text-sm text-gray-500">{t('datevExport.totalInvoices')}</p>
                  <p className="mt-1 text-2xl font-semibold">{validation.totalInvoices}</p>
                </div>
                <div className="rounded-lg border bg-white p-4">
                  <p className="text-sm text-gray-500">{t('datevExport.withBookings')}</p>
                  <p className="mt-1 text-2xl font-semibold text-green-600">{validation.invoicesWithBookings}</p>
                </div>
                <div className="rounded-lg border bg-white p-4">
                  <p className="text-sm text-gray-500">{t('datevExport.withoutBookings')}</p>
                  <p className="mt-1 text-2xl font-semibold text-amber-600">{validation.invoicesWithoutBookings}</p>
                </div>
                <div className="rounded-lg border bg-white p-4">
                  <p className="text-sm text-gray-500">{t('datevExport.missingDebitors')}</p>
                  <p className="mt-1 text-2xl font-semibold text-red-600">{validation.customersWithoutDebitorCount}</p>
                </div>
              </div>

              {/* Generate Bookings */}
              {validation.invoicesWithoutBookings > 0 && (
                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-amber-500" />
                    <p className="text-sm font-medium text-amber-800">
                      {t('datevExport.bookingsMissing', { count: validation.invoicesWithoutBookings })}
                    </p>
                  </div>
                  <button
                    onClick={handleGenerateBookings}
                    disabled={generating}
                    className="mt-2 inline-flex items-center gap-2 rounded-md bg-amber-600 px-3 py-2 text-sm font-medium text-white hover:bg-amber-700 disabled:opacity-50"
                  >
                    {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
                    {t('datevExport.generateBookings')}
                  </button>
                </div>
              )}

              {/* Unmapped Items */}
              {validation.unmappedLineItems.length > 0 && (
                <div className="rounded-lg border border-red-200 bg-red-50 p-4">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="h-5 w-5 text-red-500" />
                    <p className="text-sm font-medium text-red-800">
                      {t('datevExport.unmappedItems', { count: validation.unmappedLineItems.length })}
                    </p>
                  </div>
                  <table className="mt-2 min-w-full text-sm">
                    <thead>
                      <tr>
                        <th className="px-2 py-1 text-left text-xs font-medium text-red-600">{t('datevExport.invoiceNumber')}</th>
                        <th className="px-2 py-1 text-left text-xs font-medium text-red-600">{t('datevExport.product')}</th>
                        <th className="px-2 py-1 text-left text-xs font-medium text-red-600">{t('datevExport.amount')}</th>
                        <th className="px-2 py-1 text-left text-xs font-medium text-red-600">{t('datevExport.reason')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {validation.unmappedLineItems.map((item, i) => (
                        <tr key={i}>
                          <td className="px-2 py-1 text-red-800">{item.invoiceNumber}</td>
                          <td className="px-2 py-1 text-red-800">{item.productName}</td>
                          <td className="px-2 py-1 text-red-800">{item.amount}</td>
                          <td className="px-2 py-1 text-red-800">{item.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {/* All Good */}
              {validation.invoicesWithoutBookings === 0 && validation.unmappedLineItems.length === 0 && validation.invoicesWithBookings > 0 && (
                <div className="rounded-lg border border-green-200 bg-green-50 p-4 flex items-center gap-2">
                  <CheckCircle className="h-5 w-5 text-green-500" />
                  <p className="text-sm font-medium text-green-800">{t('datevExport.validationOk')}</p>
                </div>
              )}
            </>
          ) : null}
        </div>
      )}

      {/* Step: Debitors */}
      {step === 'debitors' && (
        <div className="mt-6 space-y-4">
          {unassignedDebitors.length === 0 ? (
            <div className="rounded-lg border border-green-200 bg-green-50 p-4 flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <p className="text-sm font-medium text-green-800">{t('datevExport.allDebitorsAssigned')}</p>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-5 w-5 text-gray-400" />
                  <p className="text-sm text-gray-700">
                    {t('datevExport.unassignedDebitors', { count: unassignedDebitors.length })}
                  </p>
                </div>
                <button
                  onClick={handleBulkAssign}
                  disabled={assigning}
                  className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-3 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                >
                  {assigning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Users className="h-4 w-4" />}
                  {t('datevExport.bulkAssign')}
                </button>
              </div>
              <div className="rounded-lg border">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.customerName')}</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.customerNumber')}</th>
                      <th className="px-4 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.debitorNumber')}</th>
                      <th className="px-4 py-2 text-right text-xs font-medium uppercase text-gray-500">{t('common.actions')}</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200 bg-white">
                    {unassignedDebitors.map((d) => (
                      <DebitorRow key={d.id} debitor={d} onAssign={handleAssignSingle} />
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {/* Step: Export */}
      {step === 'export' && (
        <div className="mt-6 space-y-4">
          <div className="rounded-lg border bg-white p-6">
            <div className="flex items-center gap-3">
              <FileSpreadsheet className="h-8 w-8 text-blue-500" />
              <div>
                <h3 className="text-lg font-medium">{t('datevExport.exportTitle')}</h3>
                <p className="text-sm text-gray-500">{t('datevExport.exportDescription')}</p>
              </div>
            </div>
            <div className="mt-4">
              <button
                onClick={handleExport}
                disabled={exporting || !canExport}
                className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {exporting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Download className="h-4 w-4" />}
                {t('datevExport.downloadCsv')}
              </button>
              {!canExport && (
                <p className="mt-2 text-xs text-amber-600">{t('datevExport.cannotExportHint')}</p>
              )}
            </div>
          </div>

          {/* Previous Exports */}
          {exports.length > 0 && (
            <div className="rounded-lg border bg-white p-6">
              <h3 className="text-sm font-medium text-gray-700">{t('datevExport.previousExports')}</h3>
              <table className="mt-3 min-w-full divide-y divide-gray-200 text-sm">
                <thead>
                  <tr>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.period')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.entries')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.total')}</th>
                    <th className="px-3 py-2 text-left text-xs font-medium uppercase text-gray-500">{t('datevExport.exportedAt')}</th>
                    <th className="px-3 py-2 text-right text-xs font-medium uppercase text-gray-500"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {exports.map((exp) => (
                    <tr key={exp.id}>
                      <td className="px-3 py-2">{formatDate(exp.periodStart)} – {formatDate(exp.periodEnd)}</td>
                      <td className="px-3 py-2">{exp.entryCount}</td>
                      <td className="px-3 py-2">{formatAmount(exp.totalAmount)}</td>
                      <td className="px-3 py-2 text-gray-500">{formatDate(exp.createdAt)}</td>
                      <td className="px-3 py-2 text-right">
                        {exp.downloadUrl && (
                          <a
                            href={exp.downloadUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-blue-600 hover:text-blue-800"
                          >
                            <Download className="h-4 w-4" />
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function DebitorRow({ debitor, onAssign }: { debitor: DebitorAccount; onAssign: (customerId: number, accountNumber: string) => void }) {
  const { t } = useTranslation()
  const [manualNumber, setManualNumber] = useState('')

  return (
    <tr>
      <td className="px-4 py-2 text-sm">{debitor.customerName}</td>
      <td className="px-4 py-2 text-sm text-gray-500">{debitor.customerNumber || '–'}</td>
      <td className="px-4 py-2">
        <input
          type="text"
          value={manualNumber}
          onChange={(e) => setManualNumber(e.target.value)}
          placeholder={t('datevExport.enterNumber')}
          className="w-32 rounded-md border border-gray-300 px-2 py-1 text-sm"
        />
      </td>
      <td className="px-4 py-2 text-right">
        <button
          onClick={() => onAssign(debitor.customerId, manualNumber || '')}
          className="text-sm text-blue-600 hover:text-blue-800"
        >
          {manualNumber ? t('datevExport.assignManual') : t('datevExport.assignAuto')}
        </button>
      </td>
    </tr>
  )
}
