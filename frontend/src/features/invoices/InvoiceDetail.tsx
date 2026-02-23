import { useState } from 'react'
import { useParams, useNavigate, useSearchParams, Link } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Download,
  Mail,
  Ban,
  Loader2,
  FileText,
  CreditCard,
  Clock,
  Send,
  Eye,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { getToken } from '@/lib/auth'
import { formatCurrency, formatDate, formatDateTime } from '@/lib/utils'
import { ImportedInvoiceDetail } from './ImportedInvoiceDetail'

const INVOICE_RECORD_QUERY = gql`
  query InvoiceRecord($id: Int!) {
    invoiceRecord(id: $id) {
      id
      invoiceNumber
      contractId
      contractName
      customerId
      customerName
      billingDate
      invoiceDate
      periodStart
      periodEnd
      totalNet
      taxRate
      taxAmount
      totalGross
      status
      lineItemsSnapshot
      invoiceText
      pdfUrl
      isPaid
      paymentMatches {
        id
        transactionId
        transactionDate
        transactionAmount
        counterpartyName
        matchType
        confidence
        matchedAt
        matchedByName
        bookingText
        reference
        valueDate
        accountName
      }
      voidReason
      customerBillingEmails
      emailSentAt
      emailSentTo
      emailMessageId
    }
  }
`

const AUDIT_LOGS_QUERY = gql`
  query InvoiceAuditLogs($entityType: String, $entityId: Int, $first: Int) {
    auditLogs(entityType: $entityType, entityId: $entityId, first: $first) {
      edges {
        node {
          id
          action
          entityRepr
          userName
          changes {
            field
            oldValue
            newValue
          }
          timestamp
        }
      }
    }
  }
`

const SEND_INVOICE_EMAIL = gql`
  mutation SendInvoiceEmail($invoiceRecordId: ID!) {
    sendInvoiceEmail(invoiceRecordId: $invoiceRecordId) {
      success
      error
    }
  }
`

const VOID_INVOICE = gql`
  mutation VoidInvoice($invoiceId: Int!, $reason: String!) {
    voidInvoice(invoiceId: $invoiceId, reason: $reason) {
      success
      error
    }
  }
`

const GENERATE_INVOICE_PDF = gql`
  mutation GenerateInvoicePdf($invoiceId: Int!) {
    generateInvoicePdf(invoiceId: $invoiceId) {
      success
      error
    }
  }
`

interface PaymentMatch {
  id: number
  transactionId: number
  transactionDate: string
  transactionAmount: string
  counterpartyName: string
  matchType: string
  confidence: string
  matchedAt: string
  matchedByName: string | null
  bookingText: string
  reference: string
  valueDate: string | null
  accountName: string
}

interface LineItem {
  product_name: string
  description: string
  quantity: number
  unit_price: string | number
  amount: string | number
  is_prorated?: boolean
  is_one_off?: boolean
}

interface InvoiceRecord {
  id: number
  invoiceNumber: string
  contractId: number | null
  contractName: string
  customerId: number | null
  customerName: string
  billingDate: string
  invoiceDate: string
  periodStart: string
  periodEnd: string
  totalNet: string
  taxRate: string
  taxAmount: string
  totalGross: string
  status: string
  lineItemsSnapshot: LineItem[]
  invoiceText: string
  pdfUrl: string | null
  isPaid: boolean
  paymentMatches: PaymentMatch[]
  voidReason: string
  customerBillingEmails: string[]
  emailSentAt: string | null
  emailSentTo: string[]
  emailMessageId: string
}

interface AuditChange {
  field: string
  oldValue: string | null
  newValue: string | null
}

interface AuditEntry {
  id: number
  action: string
  entityRepr: string
  userName: string | null
  changes: AuditChange[]
  timestamp: string
}

function StatusBadge({ status, isPaid }: { status: string; isPaid?: boolean }) {
  const { t } = useTranslation()

  if (isPaid) {
    return (
      <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-2.5 py-1 text-sm font-medium text-green-800">
        <CheckCircle className="h-4 w-4" />
        {t('invoiceDetail.statusPaid')}
      </span>
    )
  }

  switch (status) {
    case 'finalized':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-1 text-sm font-medium text-blue-700">
          <CheckCircle className="h-4 w-4" />
          {t('invoices.statusFinalized')}
        </span>
      )
    case 'voided':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-red-50 px-2.5 py-1 text-sm font-medium text-red-700">
          <XCircle className="h-4 w-4" />
          {t('invoices.statusVoided')}
        </span>
      )
    case 'sent':
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-purple-50 px-2.5 py-1 text-sm font-medium text-purple-700">
          <Send className="h-4 w-4" />
          {t('invoiceDetail.statusSent')}
        </span>
      )
    default:
      return (
        <span className="inline-flex items-center gap-1 rounded-full bg-gray-100 px-2.5 py-1 text-sm font-medium text-gray-600">
          {status}
        </span>
      )
  }
}



export function InvoiceDetail() {
  const { id } = useParams<{ id: string }>()
  const [searchParams] = useSearchParams()
  const type = searchParams.get('type')

  if (type === 'imported') {
    return <ImportedInvoiceDetail id={Number(id!)} />
  }

  return <GeneratedInvoiceDetail id={Number(id!)} fallbackToImported={!type} />
}

function GeneratedInvoiceDetail({ id, fallbackToImported }: { id: number; fallbackToImported: boolean }) {
  const navigate = useNavigate()
  const { t } = useTranslation()
  const [showVoidDialog, setShowVoidDialog] = useState(false)
  const [voidReason, setVoidReason] = useState('')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const { data, loading, error, refetch } = useQuery<{ invoiceRecord: InvoiceRecord | null }>(
    INVOICE_RECORD_QUERY,
    { variables: { id } }
  )

  const { data: auditData } = useQuery(AUDIT_LOGS_QUERY, {
    variables: { entityType: 'invoice_record', entityId: id, first: 50 },
  })

  const [sendEmail, { loading: sendingEmail }] = useMutation(SEND_INVOICE_EMAIL)
  const [voidInvoice, { loading: voiding }] = useMutation(VOID_INVOICE)
  const [generatePdf, { loading: generatingPdf }] = useMutation(GENERATE_INVOICE_PDF)

  const record = data?.invoiceRecord
  const auditEntries: AuditEntry[] =
    auditData?.auditLogs?.edges?.map((e: { node: AuditEntry }) => e.node) || []

  const handleSendEmail = async () => {
    if (!record) return
    if (!confirm(t('invoices.sendEmailConfirm', { invoice: record.invoiceNumber }))) return
    try {
      const result = await sendEmail({ variables: { invoiceRecordId: String(record.id) } })
      if (result.data?.sendInvoiceEmail?.success) {
        setToast({ type: 'success', message: t('invoiceDetail.emailSent') })
        refetch()
      } else {
        setToast({
          type: 'error',
          message: result.data?.sendInvoiceEmail?.error || t('invoices.sendEmailFailed'),
        })
      }
    } catch {
      setToast({ type: 'error', message: t('invoices.sendEmailFailed') })
    }
  }

  const handleVoid = async () => {
    if (!record || !voidReason.trim()) return
    setShowVoidDialog(false)
    try {
      const result = await voidInvoice({ variables: { invoiceId: record.id, reason: voidReason.trim() } })
      if (result.data?.voidInvoice?.success) {
        setToast({ type: 'success', message: t('invoiceDetail.voided') })
        refetch()
      } else {
        setToast({
          type: 'error',
          message: result.data?.voidInvoice?.error || t('invoiceDetail.voidFailed'),
        })
      }
    } catch {
      setToast({ type: 'error', message: t('invoiceDetail.voidFailed') })
    }
  }

  const handleGeneratePdf = async () => {
    if (!record) return
    try {
      const result = await generatePdf({ variables: { invoiceId: record.id } })
      if (result.data?.generateInvoicePdf?.success) {
        setToast({ type: 'success', message: t('invoiceDetail.pdfQueued') })
        // Poll for PDF to appear
        const poll = setInterval(() => { refetch().then(({ data: d }) => { if (d?.invoiceRecord?.pdfUrl) clearInterval(poll) }) }, 2000)
        setTimeout(() => clearInterval(poll), 30000)
      } else {
        setToast({
          type: 'error',
          message: result.data?.generateInvoicePdf?.error || t('invoiceDetail.pdfGenerationFailed'),
        })
      }
    } catch {
      setToast({ type: 'error', message: t('invoiceDetail.pdfGenerationFailed') })
    }
  }

  // Auto-dismiss toast
  if (toast) {
    setTimeout(() => setToast(null), 4000)
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!loading && !record && fallbackToImported) {
    return <ImportedInvoiceDetail id={id} />
  }

  if (error || !record) {
    return (
      <div className="mx-auto max-w-4xl px-4 py-8">
        <button onClick={() => navigate(-1)} className="mb-4 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" />
          {t('common.back')}
        </button>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t('invoiceDetail.notFound')}
          </CardContent>
        </Card>
      </div>
    )
  }

  const canSendEmail = record.status === 'finalized' && record.pdfUrl
  const sendEmailDisabledReason = !canSendEmail
    ? record.status === 'voided'
      ? t('invoiceDetail.sendDisabledVoided')
      : record.status !== 'finalized'
        ? t('invoiceDetail.sendDisabledNotFinalized')
        : !record.pdfUrl
          ? t('invoiceDetail.sendDisabledNoPdf')
          : undefined
    : undefined
  const canVoid = record.status === 'finalized' && !record.emailSentAt

  // Build preview URL
  const previewHtmlUrl = record.contractId
    ? `/api/invoices/preview-html/?year=${new Date(record.billingDate).getFullYear()}&month=${new Date(record.billingDate).getMonth() + 1}&contract_id=${record.contractId}`
    : null

  // For PDF, fetch via auth endpoint
  const pdfViewUrl = record.pdfUrl
    ? `/api/invoices/${record.id}/pdf/`
    : null

  return (
    <div className="mx-auto max-w-7xl px-4 py-6">
      {/* Toast */}
      {toast && (
        <div
          className={`fixed right-4 top-4 z-50 rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
            toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}
        >
          {toast.message}
        </div>
      )}

      {/* Header */}
      <div className="mb-6">
        <button
          onClick={() => navigate(-1)}
          className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          {t('common.back')}
        </button>
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-2xl font-bold">{record.invoiceNumber}</h1>
            <div className="mt-1 flex items-center gap-3">
              <StatusBadge status={record.status} isPaid={record.isPaid} />
              {record.isPaid && record.status === 'finalized' && (
                <span className="text-sm text-muted-foreground">({t('invoices.statusFinalized')})</span>
              )}
              {record.status === 'voided' && record.voidReason && (
                <span className="text-sm text-muted-foreground">{record.voidReason}</span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2">
            {pdfViewUrl ? (
              <Button variant="outline" size="sm" asChild>
                <a
                  href={pdfViewUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                  onClick={async (e) => {
                    e.preventDefault()
                    const token = getToken()
                    const resp = await fetch(pdfViewUrl, {
                      headers: { Authorization: `Bearer ${token}` },
                    })
                    if (resp.ok) {
                      const blob = await resp.blob()
                      window.open(URL.createObjectURL(blob), '_blank')
                    }
                  }}
                >
                  <Download className="mr-1 h-4 w-4" />
                  {t('invoiceDetail.downloadPdf')}
                </a>
              </Button>
            ) : record.status === 'finalized' && (
              <Button variant="outline" size="sm" onClick={handleGeneratePdf} disabled={generatingPdf}>
                {generatingPdf ? (
                  <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                ) : (
                  <FileText className="mr-1 h-4 w-4" />
                )}
                {t('invoiceDetail.generatePdf')}
              </Button>
            )}
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span tabIndex={0}>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleSendEmail}
                      disabled={!canSendEmail || sendingEmail}
                    >
                      {sendingEmail ? (
                        <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                      ) : (
                        <Mail className="mr-1 h-4 w-4" />
                      )}
                      {t('invoices.sendEmail')}
                    </Button>
                  </span>
                </TooltipTrigger>
                {sendEmailDisabledReason ? (
                  <TooltipContent>
                    <p>{sendEmailDisabledReason}</p>
                  </TooltipContent>
                ) : record.customerBillingEmails.length > 0 ? (
                  <TooltipContent>
                    <p className="font-medium">{t('invoiceDetail.sendTo')}</p>
                    {record.customerBillingEmails.map((email) => (
                      <p key={email}>{email}</p>
                    ))}
                  </TooltipContent>
                ) : null}
              </Tooltip>
            </TooltipProvider>
            {canVoid && (
              <Button
                variant="destructive"
                size="sm"
                onClick={() => setShowVoidDialog(true)}
                disabled={voiding}
              >
                <Ban className="mr-1 h-4 w-4" />
                {t('invoiceDetail.void')}
              </Button>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main column */}
        <div className="space-y-6 lg:col-span-2">
          {/* Metadata */}
          <Card>
            <CardContent className="pt-6">
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoiceDetail.billingDate')}
                  </div>
                  <div className="mt-1 font-medium">{formatDate(record.billingDate)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoiceDetail.invoiceDate')}
                  </div>
                  <div className="mt-1 font-medium">{formatDate(record.invoiceDate)}</div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoiceDetail.period')}
                  </div>
                  <div className="mt-1 font-medium">
                    {formatDate(record.periodStart)} – {formatDate(record.periodEnd)}
                  </div>
                </div>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoiceDetail.customer')}
                  </div>
                  <div className="mt-1">
                    {record.customerId ? (
                      <Link to={`/customers/${record.customerId}`} className="font-medium text-blue-600 hover:underline">
                        {record.customerName}
                      </Link>
                    ) : (
                      <span className="font-medium">{record.customerName}</span>
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-xs font-medium uppercase text-muted-foreground">
                    {t('invoiceDetail.contract')}
                  </div>
                  <div className="mt-1">
                    {record.contractId ? (
                      <Link to={`/contracts/${record.contractId}`} className="font-medium text-blue-600 hover:underline">
                        {record.contractName}
                      </Link>
                    ) : (
                      <span className="font-medium">{record.contractName}</span>
                    )}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Amounts */}
          <Card>
            <CardContent className="pt-6">
              <div className="flex items-end justify-between">
                <div className="grid grid-cols-3 gap-8">
                  <div>
                    <div className="text-xs font-medium uppercase text-muted-foreground">{t('invoices.netTotal')}</div>
                    <div className="mt-1 text-lg font-semibold">{formatCurrency(record.totalNet)}</div>
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted-foreground">
                      {t('invoices.taxAmount')} ({Number(record.taxRate)}%)
                    </div>
                    <div className="mt-1 text-lg font-semibold">{formatCurrency(record.taxAmount)}</div>
                  </div>
                  <div>
                    <div className="text-xs font-medium uppercase text-muted-foreground">{t('invoices.grossTotal')}</div>
                    <div className="mt-1 text-xl font-bold">{formatCurrency(record.totalGross)}</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Line Items */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <FileText className="h-4 w-4" />
                {t('invoices.lineItems')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t('invoices.product')}</TableHead>
                    <TableHead className="text-right">{t('invoices.quantity')}</TableHead>
                    <TableHead className="text-right">{t('invoices.unitPrice')}</TableHead>
                    <TableHead className="text-right">{t('invoices.amount')}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {record.lineItemsSnapshot?.map((item, idx) => (
                    <TableRow key={idx}>
                      <TableCell>
                        <div className="font-medium">{item.product_name}</div>
                        {item.description && (
                          <div className="text-sm text-muted-foreground">{item.description}</div>
                        )}
                        <div className="flex gap-1 mt-0.5">
                          {item.is_prorated && (
                            <span className="text-xs text-amber-600">({t('invoices.prorated')})</span>
                          )}
                          {item.is_one_off && (
                            <span className="text-xs text-purple-600">({t('invoices.oneOff')})</span>
                          )}
                        </div>
                      </TableCell>
                      <TableCell className="text-right">{item.quantity}</TableCell>
                      <TableCell className="text-right">
                        {formatCurrency(item.unit_price)}
                      </TableCell>
                      <TableCell className="text-right font-medium">
                        {formatCurrency(item.amount)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {record.invoiceText && (
                <div className="mt-4 rounded border bg-muted/30 p-3 text-sm text-muted-foreground">
                  {record.invoiceText}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Content Preview */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Eye className="h-4 w-4" />
                {t('invoices.previewInvoice')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {pdfViewUrl ? (
                <PdfPreview recordId={record.id} />
              ) : previewHtmlUrl ? (
                <HtmlPreview url={previewHtmlUrl} />
              ) : (
                <div className="py-8 text-center text-sm text-muted-foreground">
                  {t('invoiceDetail.noPreview')}
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Payment Matches */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <CreditCard className="h-4 w-4" />
                {t('invoiceDetail.payments')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {record.paymentMatches.length > 0 ? (
                <div className="space-y-3">
                  {record.paymentMatches.map((match) => (
                    <div key={match.id} className="rounded border p-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">
                          {formatCurrency(match.transactionAmount)}
                        </span>
                        <span className="text-xs text-muted-foreground">
                          {formatDate(match.transactionDate)}
                          {match.valueDate && match.valueDate !== match.transactionDate && (
                            <> ({t('invoiceDetail.valueDate')}: {formatDate(match.valueDate)})</>
                          )}
                        </span>
                      </div>
                      <div className="mt-1 text-muted-foreground">{match.counterpartyName}</div>
                      {match.bookingText && (
                        <div className="mt-1 text-xs text-muted-foreground">{match.bookingText}</div>
                      )}
                      {match.reference && (
                        <div className="mt-1 font-mono text-xs text-muted-foreground">{match.reference}</div>
                      )}
                      <div className="mt-1 flex items-center gap-2 text-xs text-muted-foreground">
                        <span className="rounded bg-muted px-1.5 py-0.5">{match.matchType}</span>
                        <span>{Math.round(Number(match.confidence) * 100)}%</span>
                        {match.accountName && <span>{match.accountName}</span>}
                        {match.matchedByName && <span>by {match.matchedByName}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-sm text-muted-foreground">
                  {t('invoiceDetail.noPayments')}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Email History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Mail className="h-4 w-4" />
                {t('invoiceDetail.emailHistory')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {record.emailSentAt ? (
                <div className="space-y-2 text-sm">
                  <div className="flex items-center justify-between">
                    <span className="text-muted-foreground">{t('invoiceDetail.sentAt')}</span>
                    <span className="font-medium">{formatDateTime(record.emailSentAt)}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground">{t('invoiceDetail.sentTo')}</span>
                    <div className="mt-1 space-y-0.5">
                      {record.emailSentTo.map((email, i) => (
                        <div key={i} className="font-medium">{email}</div>
                      ))}
                    </div>
                  </div>
                  {record.emailMessageId && (
                    <div className="flex items-center justify-between">
                      <span className="text-muted-foreground">{t('invoiceDetail.messageId')}</span>
                      <span className="max-w-[180px] truncate font-mono text-xs">{record.emailMessageId}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="py-4 text-center text-sm text-muted-foreground">
                  {t('invoiceDetail.notSent')}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Audit History */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <Clock className="h-4 w-4" />
                {t('invoiceDetail.history')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {auditEntries.length > 0 ? (
                <div className="space-y-3">
                  {auditEntries.map((entry) => (
                    <div key={entry.id} className="border-l-2 border-muted pl-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium capitalize">{entry.action.toLowerCase()}</span>
                        <span className="text-xs text-muted-foreground">
                          {formatDateTime(entry.timestamp)}
                        </span>
                      </div>
                      {entry.userName && (
                        <div className="text-xs text-muted-foreground">{entry.userName}</div>
                      )}
                      {entry.changes?.length > 0 && (
                        <div className="mt-1 space-y-0.5">
                          {entry.changes.map((change, i) => (
                            <div key={i} className="text-xs text-muted-foreground">
                              <span className="font-medium">{change.field}</span>:{' '}
                              {change.oldValue && <span className="line-through">{change.oldValue}</span>}
                              {change.oldValue && change.newValue && ' → '}
                              {change.newValue && <span>{change.newValue}</span>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="py-4 text-center text-sm text-muted-foreground">
                  {t('invoiceDetail.noHistory')}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Void Confirmation Dialog */}
      <Dialog open={showVoidDialog} onOpenChange={(open) => { setShowVoidDialog(open); if (!open) setVoidReason('') }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('invoiceDetail.voidConfirmTitle')}</DialogTitle>
            <DialogDescription>
              {t('invoiceDetail.voidConfirmMessage', { invoice: record.invoiceNumber })}
            </DialogDescription>
          </DialogHeader>
          <div className="py-2">
            <label className="text-sm font-medium">{t('invoiceDetail.voidReasonLabel')}</label>
            <Textarea
              value={voidReason}
              onChange={(e) => setVoidReason(e.target.value)}
              placeholder={t('invoiceDetail.voidReasonPlaceholder')}
              className="mt-1"
              rows={3}
            />
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowVoidDialog(false); setVoidReason('') }}>
              {t('common.cancel')}
            </Button>
            <Button variant="destructive" onClick={handleVoid} disabled={!voidReason.trim()}>
              {t('invoiceDetail.void')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

/** Loads invoice PDF via authenticated fetch and displays in iframe */
function PdfPreview({ recordId }: { recordId: number }) {
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useState(() => {
    const token = getToken()
    fetch(`/api/invoices/${recordId}/pdf/`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((blob) => setBlobUrl(URL.createObjectURL(blob)))
      .catch(() => setBlobUrl(null))
      .finally(() => setLoading(false))
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!blobUrl) return null

  return <iframe src={blobUrl} className="h-[600px] w-full rounded border" title="Invoice PDF" />
}

/** Loads invoice HTML preview via authenticated fetch */
function HtmlPreview({ url }: { url: string }) {
  const [html, setHtml] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useState(() => {
    const token = getToken()
    fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.text() : Promise.reject()))
      .then(setHtml)
      .catch(() => setHtml(null))
      .finally(() => setLoading(false))
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (!html) return null

  return <iframe srcDoc={html} className="h-[600px] w-full rounded border" title="Invoice Preview" />
}
