import { useState, useMemo, Fragment } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation } from '@apollo/client'
import { gql } from '@apollo/client'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'
import { FileDown, FileSpreadsheet, Files, ChevronDown, ChevronRight, AlertTriangle, CheckCircle, XCircle, Loader2 } from 'lucide-react'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

const INVOICES_FOR_MONTH = gql`
  query InvoicesForMonth($year: Int!, $month: Int!) {
    invoicesForMonth(year: $year, month: $month) {
      contractId
      contractName
      customerId
      customerName
      customerAddress
      billingDate
      billingPeriodStart
      billingPeriodEnd
      totalAmount
      lineItemCount
      lineItems {
        itemId
        productName
        description
        quantity
        unitPrice
        amount
        isProrated
        prorateFactor
        isOneOff
      }
    }
  }
`

const INVOICE_RECORDS_FOR_MONTH = gql`
  query InvoiceRecordsForMonth($year: Int!, $month: Int!) {
    invoiceRecordsForMonth(year: $year, month: $month) {
      id
      invoiceNumber
      contractId
      contractName
      customerName
      billingDate
      totalNet
      taxRate
      taxAmount
      totalGross
      status
    }
  }
`

const CHECK_LEGAL_DATA = gql`
  query CheckLegalDataComplete {
    checkLegalDataComplete {
      isComplete
      missingFields
    }
  }
`

const GENERATE_INVOICES = gql`
  mutation GenerateInvoices($year: Int!, $month: Int!) {
    generateInvoices(year: $year, month: $month) {
      success
      error
      count
    }
  }
`

interface InvoiceLineItem {
  itemId: number
  productName: string
  description: string
  quantity: number
  unitPrice: number
  amount: number
  isProrated: boolean
  prorateFactor: number | null
  isOneOff: boolean
}

interface Invoice {
  contractId: number
  contractName: string
  customerId: number
  customerName: string
  customerAddress: Record<string, string>
  billingDate: string
  billingPeriodStart: string
  billingPeriodEnd: string
  totalAmount: number
  lineItemCount: number
  lineItems: InvoiceLineItem[]
}

interface InvoiceRecord {
  id: number
  invoiceNumber: string
  contractId: number
  contractName: string
  customerName: string
  billingDate: string
  totalNet: number
  taxRate: number
  taxAmount: number
  totalGross: number
  status: string
}

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation()
  switch (status) {
    case 'finalized':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-green-50 px-2 py-0.5 text-xs font-medium text-green-700">
          <CheckCircle className="h-3 w-3" />
          {t('invoices.statusFinalized')}
        </span>
      )
    case 'cancelled':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
          <XCircle className="h-3 w-3" />
          {t('invoices.statusCancelled')}
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
          {t('invoices.statusNotGenerated')}
        </span>
      )
  }
}

export function InvoiceExportPage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.language === 'de' ? de : enUS

  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [expandedInvoices, setExpandedInvoices] = useState<Set<number>>(new Set())
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const { data, loading, error } = useQuery<{ invoicesForMonth: Invoice[] }>(
    INVOICES_FOR_MONTH,
    { variables: { year, month } }
  )

  const { data: recordsData, refetch: refetchRecords } = useQuery<{ invoiceRecordsForMonth: InvoiceRecord[] }>(
    INVOICE_RECORDS_FOR_MONTH,
    { variables: { year, month } }
  )

  const { data: legalData } = useQuery(CHECK_LEGAL_DATA)

  const [generateInvoices, { loading: generating }] = useMutation(GENERATE_INVOICES)

  const invoices = data?.invoicesForMonth ?? []
  const records = recordsData?.invoiceRecordsForMonth ?? []
  const legalDataComplete = legalData?.checkLegalDataComplete?.isComplete ?? false

  // Build a map of contractId -> record for quick lookup
  const recordByContract = useMemo(() => {
    const map = new Map<number, InvoiceRecord>()
    for (const r of records) {
      if (r.contractId) map.set(r.contractId, r)
    }
    return map
  }, [records])

  // Count ungenerated invoices
  const ungeneratedCount = useMemo(() => {
    return invoices.filter(inv => !recordByContract.has(inv.contractId)).length
  }, [invoices, recordByContract])

  // Calculate totals including tax
  const totals = useMemo(() => {
    let totalNet = 0
    let totalTax = 0
    let totalGross = 0
    for (const inv of invoices) {
      const record = recordByContract.get(inv.contractId)
      if (record) {
        totalNet += Number(record.totalNet) || 0
        totalTax += Number(record.taxAmount) || 0
        totalGross += Number(record.totalGross) || 0
      } else {
        totalNet += Number(inv.totalAmount) || 0
      }
    }
    return { count: invoices.length, totalNet, totalTax, totalGross }
  }, [invoices, recordByContract])

  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear()
    return Array.from({ length: 5 }, (_, i) => currentYear - 2 + i)
  }, [])

  const monthOptions = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => ({
      value: i + 1,
      label: format(new Date(2000, i, 1), 'MMMM', { locale }),
    }))
  }, [locale])

  const toggleExpand = (contractId: number) => {
    setExpandedInvoices((prev) => {
      const next = new Set(prev)
      if (next.has(contractId)) next.delete(contractId)
      else next.add(contractId)
      return next
    })
  }

  const handleGenerate = async () => {
    setShowConfirm(false)
    try {
      const { data: result } = await generateInvoices({
        variables: { year, month },
      })
      if (result?.generateInvoices?.success) {
        setToast({ type: 'success', message: t('invoices.generateSuccess', { count: result.generateInvoices.count }) })
        refetchRecords()
      } else {
        setToast({ type: 'error', message: result?.generateInvoices?.error || t('invoices.generateFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('invoices.generateFailed') })
    }
    setTimeout(() => setToast(null), 4000)
  }

  const handleExport = async (exportFormat: 'pdf' | 'pdf-individual' | 'excel') => {
    setExportingFormat(exportFormat)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(
        `/api/invoices/export/?year=${year}&month=${month}&format=${exportFormat}&language=${i18n.language}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Export failed')
      }
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `invoices-${year}-${String(month).padStart(2, '0')}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/)
        if (match) filename = match[1]
      } else {
        if (exportFormat === 'pdf') filename += '.pdf'
        else if (exportFormat === 'pdf-individual') filename += '.zip'
        else filename += '.xlsx'
      }
      const blob = await response.blob()
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (err) {
      console.error('Export error:', err)
    } finally {
      setExportingFormat(null)
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat(i18n.language, {
      style: 'currency',
      currency: 'EUR',
    }).format(amount)
  }

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'dd.MM.yyyy', { locale })
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold" data-testid="invoice-export-title">
          {t('invoices.export.title')}
        </h1>
      </div>

      {/* Toast */}
      {toast && (
        <div className={`rounded-lg px-4 py-3 text-sm ${toast.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {toast.message}
        </div>
      )}

      {/* Legal Data Warning */}
      {!legalDataComplete && (
        <div className="flex items-center gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertTriangle className="h-5 w-5 text-amber-600 shrink-0" />
          <div className="flex-1 text-sm text-amber-800">{t('invoices.legalDataIncomplete')}</div>
          <Link to="/settings/invoices" className="text-sm font-medium text-amber-700 hover:text-amber-900 whitespace-nowrap">
            {t('invoices.goToSettings')} &rarr;
          </Link>
        </div>
      )}

      {/* Month/Year Selector */}
      <Card>
        <CardHeader>
          <CardTitle>{t('invoices.export.selectPeriod')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Select value={String(month)} onValueChange={(value) => setMonth(parseInt(value))}>
              <SelectTrigger className="w-40" data-testid="month-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {monthOptions.map((opt) => (
                  <SelectItem key={opt.value} value={String(opt.value)}>{opt.label}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={String(year)} onValueChange={(value) => setYear(parseInt(value))}>
              <SelectTrigger className="w-28" data-testid="year-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {yearOptions.map((y) => (
                  <SelectItem key={y} value={String(y)}>{y}</SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Totals Summary */}
      {!loading && invoices.length > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex gap-8">
              <div>
                <p className="text-sm text-muted-foreground">{t('invoices.export.totalInvoices')}</p>
                <p className="text-2xl font-bold" data-testid="total-count">{totals.count}</p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">{t('invoices.netTotal')}</p>
                <p className="text-2xl font-bold" data-testid="total-net">{formatCurrency(totals.totalNet)}</p>
              </div>
              {totals.totalTax > 0 && (
                <>
                  <div>
                    <p className="text-sm text-muted-foreground">{t('invoices.taxAmount')}</p>
                    <p className="text-lg font-semibold text-gray-600">{formatCurrency(totals.totalTax)}</p>
                  </div>
                  <div>
                    <p className="text-sm text-muted-foreground">{t('invoices.grossTotal')}</p>
                    <p className="text-2xl font-bold" data-testid="total-gross">{formatCurrency(totals.totalGross)}</p>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 flex-wrap">
        {/* Generate button */}
        {ungeneratedCount > 0 && legalDataComplete && (
          <>
            {showConfirm ? (
              <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2">
                <p className="text-sm text-blue-800">{t('invoices.generateConfirm', { count: ungeneratedCount })}</p>
                <Button size="sm" onClick={handleGenerate} disabled={generating}>
                  {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  {generating ? t('invoices.generating') : t('common.save')}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowConfirm(false)}>
                  {t('common.cancel')}
                </Button>
              </div>
            ) : (
              <Button onClick={() => setShowConfirm(true)} data-testid="generate-invoices-button">
                <CheckCircle className="mr-2 h-4 w-4" />
                {t('invoices.generateInvoices')} ({ungeneratedCount})
              </Button>
            )}
          </>
        )}

        <Button
          onClick={() => handleExport('pdf')}
          disabled={invoices.length === 0 || exportingFormat !== null}
          variant={ungeneratedCount > 0 ? 'outline' : 'default'}
          data-testid="export-pdf-button"
        >
          <FileDown className="mr-2 h-4 w-4" />
          {exportingFormat === 'pdf' ? t('invoices.export.exporting') : t('invoices.export.exportPdf')}
        </Button>
        <Button
          variant="outline"
          onClick={() => handleExport('pdf-individual')}
          disabled={invoices.length === 0 || exportingFormat !== null}
          data-testid="export-individual-pdfs-button"
        >
          <Files className="mr-2 h-4 w-4" />
          {exportingFormat === 'pdf-individual' ? t('invoices.export.exporting') : t('invoices.export.exportIndividualPdfs')}
        </Button>
        <Button
          variant="outline"
          onClick={() => handleExport('excel')}
          disabled={invoices.length === 0 || exportingFormat !== null}
          data-testid="export-excel-button"
        >
          <FileSpreadsheet className="mr-2 h-4 w-4" />
          {exportingFormat === 'excel' ? t('invoices.export.exporting') : t('invoices.export.exportExcel')}
        </Button>
      </div>

      {/* Invoice Preview Table */}
      <Card>
        <CardHeader>
          <CardTitle>{t('invoices.export.preview')}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-muted-foreground">{t('common.loading')}</div>
          ) : error ? (
            <div className="py-8 text-center text-destructive">{t('common.error')}: {error.message}</div>
          ) : invoices.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground" data-testid="no-invoices">
              {t('invoices.export.noInvoices')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>{t('invoices.invoiceNo')}</TableHead>
                  <TableHead>{t('invoices.status')}</TableHead>
                  <TableHead>{t('invoices.customer')}</TableHead>
                  <TableHead>{t('invoices.contract')}</TableHead>
                  <TableHead>{t('invoices.billingDate')}</TableHead>
                  <TableHead className="text-right">{t('invoices.netTotal')}</TableHead>
                  <TableHead className="text-right">{t('invoices.taxAmount')}</TableHead>
                  <TableHead className="text-right">{t('invoices.grossTotal')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => {
                  const record = recordByContract.get(invoice.contractId)
                  return (
                    <Fragment key={invoice.contractId}>
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleExpand(invoice.contractId)}
                        data-testid={`invoice-row-${invoice.contractId}`}
                      >
                        <TableCell>
                          {expandedInvoices.has(invoice.contractId) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {record?.invoiceNumber || '—'}
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={record?.status || ''} />
                        </TableCell>
                        <TableCell className="font-medium">
                          <Link
                            to={`/customers/${invoice.customerId}`}
                            className="text-blue-600 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {invoice.customerName}
                          </Link>
                        </TableCell>
                        <TableCell>
                          <Link
                            to={`/contracts/${invoice.contractId}`}
                            className="text-blue-600 hover:underline"
                            onClick={(e) => e.stopPropagation()}
                          >
                            {invoice.contractName}
                          </Link>
                        </TableCell>
                        <TableCell>{formatDate(invoice.billingDate)}</TableCell>
                        <TableCell className="text-right">
                          {formatCurrency(record ? Number(record.totalNet) : Number(invoice.totalAmount))}
                        </TableCell>
                        <TableCell className="text-right text-muted-foreground">
                          {record ? formatCurrency(Number(record.taxAmount)) : '—'}
                        </TableCell>
                        <TableCell className="text-right font-medium">
                          {record ? formatCurrency(Number(record.totalGross)) : '—'}
                        </TableCell>
                      </TableRow>
                      {expandedInvoices.has(invoice.contractId) && (
                        <TableRow>
                          <TableCell colSpan={9} className="bg-muted/30 p-0">
                            <Table>
                              <TableHeader>
                                <TableRow>
                                  <TableHead className="pl-12">{t('invoices.product')}</TableHead>
                                  <TableHead className="text-center">{t('invoices.quantity')}</TableHead>
                                  <TableHead className="text-right">{t('invoices.unitPrice')}</TableHead>
                                  <TableHead className="text-right">{t('invoices.amount')}</TableHead>
                                </TableRow>
                              </TableHeader>
                              <TableBody>
                                {invoice.lineItems.map((item) => (
                                  <TableRow key={item.itemId}>
                                    <TableCell className="pl-12">
                                      {item.productName}
                                      {item.isProrated && (
                                        <span className="ml-2 text-xs text-muted-foreground">({t('invoices.prorated')})</span>
                                      )}
                                      {item.isOneOff && (
                                        <span className="ml-2 text-xs text-muted-foreground">({t('invoices.oneOff')})</span>
                                      )}
                                    </TableCell>
                                    <TableCell className="text-center">{item.quantity}</TableCell>
                                    <TableCell className="text-right">{formatCurrency(item.unitPrice)}</TableCell>
                                    <TableCell className="text-right">{formatCurrency(item.amount)}</TableCell>
                                  </TableRow>
                                ))}
                              </TableBody>
                            </Table>
                          </TableCell>
                        </TableRow>
                      )}
                    </Fragment>
                  )
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
