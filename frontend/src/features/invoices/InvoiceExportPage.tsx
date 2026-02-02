import { useState, useMemo, Fragment } from 'react'
import { Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery } from '@apollo/client'
import { gql } from '@apollo/client'
import { format } from 'date-fns'
import { de, enUS } from 'date-fns/locale'
import { FileDown, FileSpreadsheet, Files, ChevronDown, ChevronRight } from 'lucide-react'

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

export function InvoiceExportPage() {
  const { t, i18n } = useTranslation()
  const locale = i18n.language === 'de' ? de : enUS

  // Default to current month
  const now = new Date()
  const [year, setYear] = useState(now.getFullYear())
  const [month, setMonth] = useState(now.getMonth() + 1)
  const [expandedInvoices, setExpandedInvoices] = useState<Set<number>>(new Set())
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)

  const { data, loading, error } = useQuery<{ invoicesForMonth: Invoice[] }>(
    INVOICES_FOR_MONTH,
    {
      variables: { year, month },
    }
  )

  const invoices = data?.invoicesForMonth ?? []

  // Calculate totals
  const totals = useMemo(() => {
    const totalAmount = invoices.reduce((sum, inv) => {
      const amount = Number(inv.totalAmount) || 0
      return sum + amount
    }, 0)
    return {
      count: invoices.length,
      totalAmount,
    }
  }, [invoices])

  // Generate year options (current year +/- 2 years)
  const yearOptions = useMemo(() => {
    const currentYear = new Date().getFullYear()
    return Array.from({ length: 5 }, (_, i) => currentYear - 2 + i)
  }, [])

  // Generate month options
  const monthOptions = useMemo(() => {
    return Array.from({ length: 12 }, (_, i) => ({
      value: i + 1,
      label: format(new Date(2000, i, 1), 'MMMM', { locale }),
    }))
  }, [locale])

  const toggleExpand = (contractId: number) => {
    setExpandedInvoices((prev) => {
      const next = new Set(prev)
      if (next.has(contractId)) {
        next.delete(contractId)
      } else {
        next.add(contractId)
      }
      return next
    })
  }

  const handleExport = async (exportFormat: 'pdf' | 'pdf-individual' | 'excel') => {
    setExportingFormat(exportFormat)
    try {
      const token = localStorage.getItem('auth_token')
      const response = await fetch(
        `/api/invoices/export/?year=${year}&month=${month}&format=${exportFormat}&language=${i18n.language}`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.error || 'Export failed')
      }

      // Get filename from Content-Disposition header or use default
      const contentDisposition = response.headers.get('Content-Disposition')
      let filename = `invoices-${year}-${String(month).padStart(2, '0')}`
      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/)
        if (match) {
          filename = match[1]
        }
      } else {
        // Add extension based on format
        if (exportFormat === 'pdf') filename += '.pdf'
        else if (exportFormat === 'pdf-individual') filename += '.zip'
        else filename += '.xlsx'
      }

      // Download the file
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
      // TODO: Show error toast
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

      {/* Month/Year Selector */}
      <Card>
        <CardHeader>
          <CardTitle>{t('invoices.export.selectPeriod')}</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <Select
              value={String(month)}
              onValueChange={(value) => setMonth(parseInt(value))}
            >
              <SelectTrigger className="w-40" data-testid="month-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {monthOptions.map((opt) => (
                  <SelectItem key={opt.value} value={String(opt.value)}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select
              value={String(year)}
              onValueChange={(value) => setYear(parseInt(value))}
            >
              <SelectTrigger className="w-28" data-testid="year-select">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {yearOptions.map((y) => (
                  <SelectItem key={y} value={String(y)}>
                    {y}
                  </SelectItem>
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
                <p className="text-sm text-muted-foreground">
                  {t('invoices.export.totalInvoices')}
                </p>
                <p className="text-2xl font-bold" data-testid="total-count">
                  {totals.count}
                </p>
              </div>
              <div>
                <p className="text-sm text-muted-foreground">
                  {t('invoices.export.totalAmount')}
                </p>
                <p className="text-2xl font-bold" data-testid="total-amount">
                  {formatCurrency(totals.totalAmount)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Export Buttons */}
      <div className="flex gap-3">
        <Button
          onClick={() => handleExport('pdf')}
          disabled={invoices.length === 0 || exportingFormat !== null}
          data-testid="export-pdf-button"
        >
          <FileDown className="mr-2 h-4 w-4" />
          {exportingFormat === 'pdf'
            ? t('invoices.export.exporting')
            : t('invoices.export.exportPdf')}
        </Button>
        <Button
          variant="outline"
          onClick={() => handleExport('pdf-individual')}
          disabled={invoices.length === 0 || exportingFormat !== null}
          data-testid="export-individual-pdfs-button"
        >
          <Files className="mr-2 h-4 w-4" />
          {exportingFormat === 'pdf-individual'
            ? t('invoices.export.exporting')
            : t('invoices.export.exportIndividualPdfs')}
        </Button>
        <Button
          variant="outline"
          onClick={() => handleExport('excel')}
          disabled={invoices.length === 0 || exportingFormat !== null}
          data-testid="export-excel-button"
        >
          <FileSpreadsheet className="mr-2 h-4 w-4" />
          {exportingFormat === 'excel'
            ? t('invoices.export.exporting')
            : t('invoices.export.exportExcel')}
        </Button>
      </div>

      {/* Invoice Preview Table */}
      <Card>
        <CardHeader>
          <CardTitle>{t('invoices.export.preview')}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="py-8 text-center text-muted-foreground">
              {t('common.loading')}
            </div>
          ) : error ? (
            <div className="py-8 text-center text-destructive">
              {t('common.error')}: {error.message}
            </div>
          ) : invoices.length === 0 ? (
            <div className="py-8 text-center text-muted-foreground" data-testid="no-invoices">
              {t('invoices.export.noInvoices')}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8"></TableHead>
                  <TableHead>{t('invoices.customer')}</TableHead>
                  <TableHead>{t('invoices.contract')}</TableHead>
                  <TableHead>{t('invoices.billingDate')}</TableHead>
                  <TableHead>{t('invoices.lineItems')}</TableHead>
                  <TableHead className="text-right">{t('invoices.total')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((invoice) => (
                  <Fragment key={invoice.contractId}>
                    <TableRow
                      key={invoice.contractId}
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
                      <TableCell>{invoice.lineItemCount}</TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(invoice.totalAmount)}
                      </TableCell>
                    </TableRow>
                    {expandedInvoices.has(invoice.contractId) && (
                      <TableRow>
                        <TableCell colSpan={6} className="bg-muted/30 p-0">
                          <Table>
                            <TableHeader>
                              <TableRow>
                                <TableHead className="pl-12">
                                  {t('invoices.product')}
                                </TableHead>
                                <TableHead className="text-center">
                                  {t('invoices.quantity')}
                                </TableHead>
                                <TableHead className="text-right">
                                  {t('invoices.unitPrice')}
                                </TableHead>
                                <TableHead className="text-right">
                                  {t('invoices.amount')}
                                </TableHead>
                              </TableRow>
                            </TableHeader>
                            <TableBody>
                              {invoice.lineItems.map((item) => (
                                <TableRow key={item.itemId}>
                                  <TableCell className="pl-12">
                                    {item.productName}
                                    {item.isProrated && (
                                      <span className="ml-2 text-xs text-muted-foreground">
                                        ({t('invoices.prorated')})
                                      </span>
                                    )}
                                    {item.isOneOff && (
                                      <span className="ml-2 text-xs text-muted-foreground">
                                        ({t('invoices.oneOff')})
                                      </span>
                                    )}
                                  </TableCell>
                                  <TableCell className="text-center">
                                    {item.quantity}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {formatCurrency(item.unitPrice)}
                                  </TableCell>
                                  <TableCell className="text-right">
                                    {formatCurrency(item.amount)}
                                  </TableCell>
                                </TableRow>
                              ))}
                            </TableBody>
                          </Table>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
