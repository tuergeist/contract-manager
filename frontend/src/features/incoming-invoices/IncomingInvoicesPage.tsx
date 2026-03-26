import { useState, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, FileText, Search, Filter, Upload } from 'lucide-react'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
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
import { IncomingInvoiceDetail } from './IncomingInvoiceDetail'

const INCOMING_INVOICES = gql`
  query IncomingInvoices($status: String, $search: String, $dateFrom: Date, $dateTo: Date, $page: Int, $pageSize: Int) {
    incomingInvoices(status: $status, search: $search, dateFrom: $dateFrom, dateTo: $dateTo, page: $page, pageSize: $pageSize) {
      items {
        id
        supplierName
        invoiceNumber
        invoiceDate
        grossAmount
        currency
        extractionStatus
        counterpartyName
        originalFilename
        createdAt
      }
      totalCount
      page
      pageSize
      hasNextPage
    }
  }
`

const UPLOAD_INCOMING = gql`
  mutation UploadIncomingInvoices($files: [UploadIncomingInvoiceFileInput!]!) {
    uploadIncomingInvoices(files: $files) {
      success
      error
      totalUploaded
      totalFailed
      results { filename success error }
    }
  }
`

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-300',
  extracting: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-300',
  extracted: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-300',
  extraction_failed: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-300',
  confirmed: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-300',
  matched: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-300',
}

export function IncomingInvoicesPage() {
  const { t } = useTranslation()
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState<string>('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [uploadIncoming, { loading: uploading }] = useMutation(UPLOAD_INCOMING)
  const [uploadResult, setUploadResult] = useState<{ total: number; failed: number } | null>(null)

  const { data, loading, refetch } = useQuery(INCOMING_INVOICES, {
    variables: {
      status: status || undefined,
      search: search || undefined,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      page,
      pageSize: 50,
    },
  })

  const invoices = data?.incomingInvoices?.items || []
  const totalCount = data?.incomingInvoices?.totalCount || 0
  const hasNextPage = data?.incomingInvoices?.hasNextPage || false

  const handleFileUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return
    setUploadResult(null)

    const files: { fileContent: string; filename: string }[] = []
    for (const file of Array.from(fileList)) {
      if (!file.name.toLowerCase().endsWith('.pdf') && !file.name.toLowerCase().endsWith('.zip')) continue
      const buffer = await file.arrayBuffer()
      const base64 = btoa(
        new Uint8Array(buffer).reduce((data, byte) => data + String.fromCharCode(byte), '')
      )
      files.push({ fileContent: base64, filename: file.name })
    }

    if (files.length === 0) return

    const { data } = await uploadIncoming({ variables: { files } })
    const result = data?.uploadIncomingInvoices
    if (result) {
      setUploadResult({ total: result.totalUploaded, failed: result.totalFailed })
      refetch()
    }
    // Reset file input
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const formatAmount = (amount: string | null, currency: string) => {
    if (!amount) return '—'
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency }).format(parseFloat(amount))
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('incomingInvoices.title')}</h1>
        <div>
          <input
            ref={fileInputRef}
            type="file"
            accept=".pdf,.zip"
            multiple
            className="hidden"
            onChange={(e) => handleFileUpload(e.target.files)}
          />
          <Button onClick={() => fileInputRef.current?.click()} disabled={uploading}>
            {uploading ? <Loader2 className="mr-1.5 h-4 w-4 animate-spin" /> : <Upload className="mr-1.5 h-4 w-4" />}
            {t('incomingInvoices.upload')}
          </Button>
        </div>
      </div>

      {uploadResult && (
        <div className={`mb-4 p-3 rounded-lg text-sm ${uploadResult.failed > 0 ? 'bg-yellow-50 text-yellow-800' : 'bg-green-50 text-green-700'}`}>
          {uploadResult.total} invoice(s) uploaded{uploadResult.failed > 0 ? `, ${uploadResult.failed} failed` : ''}.
        </div>
      )}

      <div className="flex flex-wrap gap-3 mb-4">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder={t('incomingInvoices.searchPlaceholder')}
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            className="pl-9"
          />
        </div>
        <Select value={status} onValueChange={(v) => { setStatus(v === 'all' ? '' : v); setPage(1) }}>
          <SelectTrigger className="w-[180px]">
            <Filter className="mr-1.5 h-4 w-4" />
            <SelectValue placeholder={t('incomingInvoices.allStatuses')} />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">{t('incomingInvoices.allStatuses')}</SelectItem>
            <SelectItem value="pending">{t('incomingInvoices.status.pending')}</SelectItem>
            <SelectItem value="extracting">{t('incomingInvoices.status.extracting')}</SelectItem>
            <SelectItem value="extracted">{t('incomingInvoices.status.extracted')}</SelectItem>
            <SelectItem value="extraction_failed">{t('incomingInvoices.status.extractionFailed')}</SelectItem>
            <SelectItem value="confirmed">{t('incomingInvoices.status.confirmed')}</SelectItem>
            <SelectItem value="matched">{t('incomingInvoices.status.matched')}</SelectItem>
          </SelectContent>
        </Select>
        <Input type="date" value={dateFrom} onChange={(e) => { setDateFrom(e.target.value); setPage(1) }} className="w-[160px]" />
        <Input type="date" value={dateTo} onChange={(e) => { setDateTo(e.target.value); setPage(1) }} className="w-[160px]" />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : invoices.length === 0 ? (
        <div className="text-center py-12 text-muted-foreground">
          <FileText className="mx-auto h-12 w-12 mb-3 opacity-50" />
          <p className="text-lg font-medium">{t('incomingInvoices.empty')}</p>
          <p className="text-sm mt-1">{t('incomingInvoices.emptyDescription')}</p>
        </div>
      ) : (
        <>
          <div className="border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t('incomingInvoices.supplier')}</TableHead>
                  <TableHead>{t('incomingInvoices.invoiceNumber')}</TableHead>
                  <TableHead>{t('incomingInvoices.date')}</TableHead>
                  <TableHead className="text-right">{t('incomingInvoices.grossAmount')}</TableHead>
                  <TableHead>{t('incomingInvoices.statusLabel')}</TableHead>
                  <TableHead>{t('incomingInvoices.counterparty')}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invoices.map((inv: any) => (
                  <TableRow key={inv.id} className="cursor-pointer hover:bg-muted/50" onClick={() => setSelectedId(inv.id)}>
                    <TableCell className="font-medium">{inv.supplierName || inv.originalFilename}</TableCell>
                    <TableCell>{inv.invoiceNumber || '—'}</TableCell>
                    <TableCell>{inv.invoiceDate || '—'}</TableCell>
                    <TableCell className="text-right">{formatAmount(inv.grossAmount, inv.currency)}</TableCell>
                    <TableCell>
                      <Badge variant="secondary" className={statusColors[inv.extractionStatus] || ''}>
                        {t(`incomingInvoices.status.${inv.extractionStatus === 'extraction_failed' ? 'extractionFailed' : inv.extractionStatus}`)}
                      </Badge>
                    </TableCell>
                    <TableCell>{inv.counterpartyName || '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-muted-foreground">
              {t('common.showingOf', { count: invoices.length, total: totalCount })}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t('common.previous')}</Button>
              <Button variant="outline" size="sm" disabled={!hasNextPage} onClick={() => setPage(page + 1)}>{t('common.next')}</Button>
            </div>
          </div>
        </>
      )}

      {selectedId && (
        <IncomingInvoiceDetail id={selectedId} open={!!selectedId} onClose={() => setSelectedId(null)} onUpdate={() => refetch()} />
      )}
    </div>
  )
}
