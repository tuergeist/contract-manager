import { useState, useMemo, useEffect, Fragment } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation } from '@apollo/client'
import { gql } from '@apollo/client'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'
import { FileDown, Files, ChevronDown, ChevronRight, AlertTriangle, CheckCircle, XCircle, Loader2, Eye } from 'lucide-react'

import { formatCurrency } from '@/lib/utils'
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
import { Checkbox } from '@/components/ui/checkbox'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { HelpVideoButton } from '@/components/HelpVideoButton'

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
  mutation GenerateInvoices($year: Int!, $month: Int!, $contractIds: [Int!]) {
    generateInvoices(year: $year, month: $month, contractIds: $contractIds) {
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
    case 'voided':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2 py-0.5 text-xs font-medium text-red-700">
          <XCircle className="h-3 w-3" />
          {t('invoices.statusVoided')}
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

// Unique key for invoice previews (a contract can have multiple billing events per month)
function invoiceKey(inv: { contractId: number; billingDate: string }): string {
  return `${inv.contractId}-${inv.billingDate}`
}

export function InvoiceExportPage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.language === 'de' ? de : enUS

  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [expandedInvoices, setExpandedInvoices] = useState<Set<string>>(new Set())
  const [selectedForGeneration, setSelectedForGeneration] = useState<Set<string>>(new Set())
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [showConfirm, setShowConfirm] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [previewLoading, setPreviewLoading] = useState(false)
  const [previewOpen, setPreviewOpen] = useState(false)

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

  // Build a map of invoiceKey -> record for quick lookup
  const recordByKey = useMemo(() => {
    const map = new Map<string, InvoiceRecord>()
    for (const r of records) {
      if (r.contractId && r.billingDate) {
        map.set(`${r.contractId}-${r.billingDate}`, r)
      }
    }
    return map
  }, [records])

  // Ungenerated invoice keys
  const ungeneratedKeys = useMemo(() => {
    return invoices
      .filter(inv => !recordByKey.has(invoiceKey(inv)))
      .map(inv => invoiceKey(inv))
  }, [invoices, recordByKey])

  // Default all ungenerated invoices to selected
  useEffect(() => {
    setSelectedForGeneration(new Set(ungeneratedKeys))
  }, [ungeneratedKeys])

  const ungeneratedCount = ungeneratedKeys.length

  // Calculate totals including tax
  const totals = useMemo(() => {
    let totalNet = 0
    let totalTax = 0
    let totalGross = 0
    for (const inv of invoices) {
      const record = recordByKey.get(invoiceKey(inv))
      if (record) {
        totalNet += Number(record.totalNet) || 0
        totalTax += Number(record.taxAmount) || 0
        totalGross += Number(record.totalGross) || 0
      } else {
        totalNet += Number(inv.totalAmount) || 0
      }
    }
    return { count: invoices.length, totalNet, totalTax, totalGross }
  }, [invoices, recordByKey])

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

  const toggleExpand = (key: string) => {
    setExpandedInvoices((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  const handleGenerate = async () => {
    setShowConfirm(false)
    try {
      // Extract unique contractIds from the selected keys (key format: "contractId-billingDate")
      const contractIds = [...new Set([...selectedForGeneration].map(key => parseInt(key.split('-')[0])))]
      const { data: result } = await generateInvoices({
        variables: { year, month, contractIds },
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

  const handleExport = async (exportFormat: 'pdf' | 'pdf-individual' | 'zugferd') => {
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
        else filename += '.zip'
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

  const handlePreview = async (contractId: number) => {
    setPreviewLoading(true)
    setPreviewOpen(true)
    setPreviewHtml(null)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(
        `/api/invoices/preview-html/?year=${year}&month=${month}&contract_id=${contractId}`,
        { headers: { Authorization: `Bearer ${token}` } }
      )
      if (!response.ok) throw new Error('Preview failed')
      const html = await response.text()
      setPreviewHtml(html)
    } catch (err) {
      console.error('Preview error:', err)
      setPreviewOpen(false)
    } finally {
      setPreviewLoading(false)
    }
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
        <HelpVideoButton />
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

      {/* Description */}
      <p className="text-sm text-muted-foreground">
        {t('invoices.export.description')}
      </p>

      {/* Action Buttons */}
      <div className="flex gap-3 flex-wrap">
        {/* Generate & Finalize button */}
        {ungeneratedCount > 0 && legalDataComplete && (
          <>
            {showConfirm ? (
              <div className="flex items-center gap-2 rounded-lg border border-blue-200 bg-blue-50 px-4 py-2">
                <p className="text-sm text-blue-800">{t('invoices.generateConfirm', { count: selectedForGeneration.size })}</p>
                <Button size="sm" onClick={handleGenerate} disabled={generating || selectedForGeneration.size === 0}>
                  {generating ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : null}
                  {generating ? t('invoices.generating') : t('common.save')}
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowConfirm(false)}>
                  {t('common.cancel')}
                </Button>
              </div>
            ) : (
              <Button className="bg-blue-600 hover:bg-blue-700 text-white" onClick={() => setShowConfirm(true)} disabled={selectedForGeneration.size === 0} data-testid="generate-invoices-button">
                <CheckCircle className="mr-2 h-4 w-4" />
                {t('invoices.generateInvoices')} ({selectedForGeneration.size}/{ungeneratedCount})
              </Button>
            )}
          </>
        )}

        <Button
          variant="outline"
          onClick={() => handleExport('pdf')}
          disabled={invoices.length === 0 || exportingFormat !== null}
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
                  <TableHead className="w-8">
                    {ungeneratedCount > 0 && (
                      <Checkbox
                        checked={selectedForGeneration.size === ungeneratedCount}
                        onCheckedChange={(checked) => {
                          setSelectedForGeneration(checked ? new Set(ungeneratedKeys) : new Set())
                        }}
                        aria-label="Select all"
                      />
                    )}
                  </TableHead>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>{t('invoices.invoiceNo')}</TableHead>
                  <TableHead>{t('invoices.status')}</TableHead>
                  <TableHead>{t('invoices.customer')}</TableHead>
                  <TableHead>{t('invoices.contract')}</TableHead>
                  <TableHead>{t('invoices.billingDate')}</TableHead>
                  <TableHead className="text-right">{t('invoices.netTotal')}</TableHead>
                  <TableHead className="text-right">{t('invoices.taxAmount')}</TableHead>
                  <TableHead className="text-right">{t('invoices.grossTotal')}</TableHead>
                  <TableHead className="w-10"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => {
                  const key = invoiceKey(invoice)
                  const record = recordByKey.get(key)
                  return (
                    <Fragment key={key}>
                      <TableRow
                        className="cursor-pointer hover:bg-muted/50"
                        onClick={() => toggleExpand(key)}
                        data-testid={`invoice-row-${invoice.contractId}`}
                      >
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          {!record && (
                            <Checkbox
                              checked={selectedForGeneration.has(key)}
                              onCheckedChange={(checked) => {
                                setSelectedForGeneration(prev => {
                                  const next = new Set(prev)
                                  if (checked) next.add(key)
                                  else next.delete(key)
                                  return next
                                })
                              }}
                              aria-label={`Select ${invoice.customerName}`}
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          {expandedInvoices.has(key) ? (
                            <ChevronDown className="h-4 w-4" />
                          ) : (
                            <ChevronRight className="h-4 w-4" />
                          )}
                        </TableCell>
                        <TableCell className="font-mono text-sm">
                          {record ? (
                            <Link
                              to={`/invoices/${record.id}`}
                              className="text-blue-600 hover:underline"
                              onClick={(e) => e.stopPropagation()}
                            >
                              {record.invoiceNumber}
                            </Link>
                          ) : '—'}
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
                        <TableCell onClick={(e) => e.stopPropagation()}>
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => handlePreview(invoice.contractId)}
                            title={t('invoices.previewInvoice')}
                            data-testid={`invoice-preview-${invoice.contractId}`}
                          >
                            <Eye className="h-4 w-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                      {expandedInvoices.has(key) && (
                        <TableRow>
                          <TableCell colSpan={11} className="bg-muted/30 p-0">
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

      {/* Invoice Preview Dialog */}
      <Dialog open={previewOpen} onOpenChange={setPreviewOpen}>
        <DialogContent className="max-w-4xl h-[90vh] flex flex-col">
          <DialogHeader>
            <DialogTitle>{t('invoices.previewInvoice')}</DialogTitle>
          </DialogHeader>
          {previewLoading ? (
            <div className="flex-1 flex items-center justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : previewHtml ? (
            <iframe
              srcDoc={previewHtml}
              className="flex-1 w-full border rounded"
              title={t('invoices.previewInvoice')}
            />
          ) : null}
        </DialogContent>
      </Dialog>
    </div>
  )
}
