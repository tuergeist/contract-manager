import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Link } from 'react-router-dom'
import {
  Loader2, FileText, Upload, X, Pencil, Plus,
  ArrowUp, ArrowDown, ArrowUpDown,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import {
  Popover, PopoverContent, PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command, CommandEmpty, CommandGroup, CommandInput, CommandItem, CommandList, CommandSeparator,
} from '@/components/ui/command'
import { usePersistedState } from '@/lib/usePersistedState'
import { formatDate, formatCurrency } from '@/lib/utils'
import { IncomingInvoiceDetail } from './IncomingInvoiceDetail'

// --- GraphQL ---

const INCOMING_INVOICES = gql`
  query IncomingInvoices($status: String, $search: String, $dateFrom: Date, $dateTo: Date, $sortBy: String, $sortOrder: String, $page: Int, $pageSize: Int) {
    incomingInvoices(status: $status, search: $search, dateFrom: $dateFrom, dateTo: $dateTo, sortBy: $sortBy, sortOrder: $sortOrder, page: $page, pageSize: $pageSize) {
      items {
        id
        supplierName
        invoiceNumber
        invoiceDate
        grossAmount
        currency
        extractionStatus
        counterpartyId
        counterpartyName
        originalFilename
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
      success error totalUploaded totalFailed
      results { filename success error }
    }
  }
`

const SEARCH_COUNTERPARTIES = gql`
  query SearchCounterpartiesForIncoming($search: String, $pageSize: Int) {
    counterparties(search: $search, pageSize: $pageSize) {
      items { id name iban }
    }
  }
`

const UPDATE_INCOMING_INVOICE = gql`
  mutation UpdateIncomingInvoiceCounterparty($input: UpdateIncomingInvoiceInput!) {
    updateIncomingInvoice(input: $input) {
      success error
      invoice { id counterpartyId counterpartyName }
    }
  }
`

// --- Status badge config ---

const statusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-800',
  extracting: 'bg-blue-100 text-blue-800',
  extracted: 'bg-green-100 text-green-800',
  extraction_failed: 'bg-red-100 text-red-800',
  confirmed: 'bg-emerald-100 text-emerald-800',
  matched: 'bg-purple-100 text-purple-800',
}

// --- Component ---

export function IncomingInvoicesPage() {
  const { t } = useTranslation()

  // Filters
  const [search, setSearch] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [status, setStatus] = useState<string>('all')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)

  // Sort (persisted)
  const [sortBy, setSortBy] = usePersistedState('cm:incoming:sortBy', 'created_at')
  const [sortOrder, setSortOrder] = usePersistedState('cm:incoming:sortOrder', 'desc')

  // UI state
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [editingInvId, setEditingInvId] = useState<string | null>(null)
  const [cpSearch, setCpSearch] = useState('')
  const [cpSearchDebounced, setCpSearchDebounced] = useState('')
  const [showCreateCp, setShowCreateCp] = useState(false)
  const [newCpName, setNewCpName] = useState('')
  const fileInputRef = useRef<HTMLInputElement>(null)
  // Bulk counterparty assign state
  const [bulkAssignPrompt, setBulkAssignPrompt] = useState<{
    supplierName: string
    counterpartyId: string
    counterpartyName: string
    otherIds: string[]
  } | null>(null)

  // Upload modal state
  const [uploadModalOpen, setUploadModalOpen] = useState(false)
  const [uploadFiles, setUploadFiles] = useState<{ name: string; status: 'pending' | 'uploading' | 'done' | 'skipped' | 'error'; error?: string }[]>([])
  const [uploadProgress, setUploadProgress] = useState({ current: 0, total: 0, done: false })

  // Debounce search
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(search), 300)
    return () => clearTimeout(timer)
  }, [search])

  // Debounce counterparty search
  useEffect(() => {
    const timer = setTimeout(() => setCpSearchDebounced(cpSearch), 200)
    return () => clearTimeout(timer)
  }, [cpSearch])

  // Queries
  const { data, loading, refetch } = useQuery(INCOMING_INVOICES, {
    variables: {
      status: status === 'all' ? undefined : status,
      search: debouncedSearch || undefined,
      dateFrom: dateFrom || undefined,
      dateTo: dateTo || undefined,
      sortBy,
      sortOrder,
      page,
      pageSize: 50,
    },
  })

  const { data: cpData } = useQuery(SEARCH_COUNTERPARTIES, {
    variables: { search: cpSearchDebounced || null, pageSize: 20 },
    skip: !editingInvId,
  })
  const searchedCps = cpData?.counterparties?.items ?? []

  // Mutations
  const [uploadIncoming] = useMutation(UPLOAD_INCOMING)
  const [updateInvoice, { loading: updatingCp }] = useMutation(UPDATE_INCOMING_INVOICE)

  const invoices = data?.incomingInvoices?.items || []
  const totalCount = data?.incomingInvoices?.totalCount || 0
  const hasNextPage = data?.incomingInvoices?.hasNextPage || false

  const hasActiveFilters = search || status !== 'all' || dateFrom || dateTo

  // --- Handlers ---

  const handleSort = (field: string) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder('desc')
    }
    setPage(1)
  }

  const getSortIcon = (field: string) => {
    if (sortBy !== field) return <ArrowUpDown className="h-3.5 w-3.5 text-gray-400" />
    return sortOrder === 'asc'
      ? <ArrowUp className="h-3.5 w-3.5" />
      : <ArrowDown className="h-3.5 w-3.5" />
  }

  const clearFilters = () => {
    setSearch('')
    setStatus('all')
    setDateFrom('')
    setDateTo('')
    setPage(1)
  }

  const handleFileUpload = async (fileList: FileList | null) => {
    if (!fileList || fileList.length === 0) return

    // Prepare file list
    const validFiles: { file: File; base64: string }[] = []
    for (const file of Array.from(fileList)) {
      if (!file.name.toLowerCase().endsWith('.pdf') && !file.name.toLowerCase().endsWith('.zip')) continue
      const buffer = await file.arrayBuffer()
      const base64 = btoa(new Uint8Array(buffer).reduce((d, byte) => d + String.fromCharCode(byte), ''))
      validFiles.push({ file, base64 })
    }
    if (validFiles.length === 0) return

    // Initialize modal
    const fileStates = validFiles.map(f => ({ name: f.file.name, status: 'pending' as const }))
    setUploadFiles(fileStates)
    setUploadProgress({ current: 0, total: validFiles.length, done: false })
    setUploadModalOpen(true)

    // Upload files one by one
    for (let i = 0; i < validFiles.length; i++) {
      const { file, base64 } = validFiles[i]
      setUploadFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'uploading' } : f))
      setUploadProgress(prev => ({ ...prev, current: i + 1 }))

      try {
        const { data } = await uploadIncoming({
          variables: { files: [{ fileContent: base64, filename: file.name }] },
        })
        const result = data?.uploadIncomingInvoices
        if (result?.success) {
          const firstResult = result.results?.[0]
          if (firstResult?.error === 'duplicate_skipped') {
            setUploadFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'skipped' } : f))
          } else {
            setUploadFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'done' } : f))
          }
        } else {
          const errorMsg = result?.results?.[0]?.error || result?.error || 'Upload failed'
          setUploadFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'error', error: errorMsg } : f))
        }
      } catch (e) {
        setUploadFiles(prev => prev.map((f, idx) => idx === i ? { ...f, status: 'error', error: e instanceof Error ? e.message : 'Upload failed' } : f))
      }
    }

    setUploadProgress(prev => ({ ...prev, done: true }))
    refetch()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const handleSelectCounterparty = async (invId: string, cpId: string) => {
    // Find the invoice being edited
    const inv = invoices.find((i: any) => i.id === invId)
    const supplierName = inv?.supplierName || ''
    const cpName = searchedCps.find((c: any) => c.id === cpId)?.name || ''

    // Update this invoice
    await updateInvoice({ variables: { input: { id: invId, counterpartyId: cpId } } })
    setEditingInvId(null)
    setCpSearch('')

    // Check if other invoices with the same supplier name have no counterparty
    if (supplierName) {
      const others = invoices.filter(
        (i: any) => i.id !== invId && i.supplierName === supplierName && !i.counterpartyId
      )
      if (others.length > 0) {
        setBulkAssignPrompt({
          supplierName,
          counterpartyId: cpId,
          counterpartyName: cpName,
          otherIds: others.map((i: any) => i.id),
        })
        return // don't refetch yet — wait for user decision
      }
    }

    refetch()
  }

  const handleBulkAssign = async (apply: boolean) => {
    if (apply && bulkAssignPrompt) {
      for (const invId of bulkAssignPrompt.otherIds) {
        await updateInvoice({
          variables: { input: { id: invId, counterpartyId: bulkAssignPrompt.counterpartyId } },
        })
      }
    }
    setBulkAssignPrompt(null)
    refetch()
  }

  const handleCreateAndSelectCounterparty = async (_invId: string) => {
    // For now, just close — creating counterparties requires a separate mutation
    // TODO: Add create counterparty flow if needed
    setShowCreateCp(false)
  }

  // --- Render ---

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{t('incomingInvoices.title')}</h1>
          {hasActiveFilters && (
            <button onClick={clearFilters} className="text-xs text-blue-600 hover:text-blue-800">
              {t('common.clearFilters', 'Clear filters')} <X className="inline h-3 w-3" />
            </button>
          )}
        </div>
        <div>
          <input ref={fileInputRef} type="file" accept=".pdf,.zip" multiple className="hidden" onChange={(e) => handleFileUpload(e.target.files)} />
          <Button onClick={() => fileInputRef.current?.click()} disabled={uploadModalOpen && !uploadProgress.done}>
            <Upload className="mr-1.5 h-4 w-4" />
            {t('incomingInvoices.upload')}
          </Button>
        </div>
      </div>

      {/* Upload Progress Modal */}
      <Dialog open={uploadModalOpen} onOpenChange={(open) => { if (uploadProgress.done) setUploadModalOpen(open) }}>
        <DialogContent className="max-w-2xl" onPointerDownOutside={(e) => { if (!uploadProgress.done) e.preventDefault() }}>
          <DialogHeader>
            <DialogTitle>
              {uploadProgress.done
                ? t('incomingInvoices.uploadComplete', 'Upload complete')
                : t('incomingInvoices.uploadProgress', 'Uploading invoices...')}
            </DialogTitle>
          </DialogHeader>

          {/* Progress bar */}
          <div className="space-y-3">
            <div className="flex items-center justify-between text-sm text-gray-600">
              <span>{uploadProgress.current} / {uploadProgress.total}</span>
              {!uploadProgress.done && (
                <span className="text-xs text-gray-400">{t('incomingInvoices.uploadStayHint', 'Please wait, do not close this dialog.')}</span>
              )}
            </div>
            <div className="h-2 w-full rounded-full bg-gray-100">
              <div
                className="h-2 rounded-full bg-blue-600 transition-all duration-300"
                style={{ width: `${uploadProgress.total > 0 ? (uploadProgress.current / uploadProgress.total) * 100 : 0}%` }}
              />
            </div>

            {/* File list */}
            <div className="max-h-[300px] overflow-y-auto space-y-1">
              {uploadFiles.map((f, i) => (
                <div key={i} className="flex items-center justify-between rounded px-2 py-1.5 text-sm">
                  <span className="truncate flex-1 mr-2">{f.name}</span>
                  {f.status === 'pending' && <span className="text-xs text-gray-400">{t('incomingInvoices.status.pending')}</span>}
                  {f.status === 'uploading' && <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600" />}
                  {f.status === 'done' && <span className="text-xs text-green-600">✓</span>}
                  {f.status === 'skipped' && <span className="text-xs text-gray-400">{t('incomingInvoices.duplicateSkipped', 'duplicate')}</span>}
                  {f.status === 'error' && (
                    <span className="text-xs text-red-600" title={f.error}>✗</span>
                  )}
                </div>
              ))}
            </div>

            {uploadProgress.done && (
              <div className="flex justify-end pt-2">
                <Button onClick={() => setUploadModalOpen(false)}>{t('common.close')}</Button>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Bulk counterparty assign prompt */}
      <Dialog open={!!bulkAssignPrompt} onOpenChange={(open) => { if (!open) handleBulkAssign(false) }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{t('incomingInvoices.bulkAssign.title', 'Apply to all?')}</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-600">
            {t('incomingInvoices.bulkAssign.message', {
              count: bulkAssignPrompt?.otherIds.length || 0,
              supplier: bulkAssignPrompt?.supplierName || '',
              counterparty: bulkAssignPrompt?.counterpartyName || '',
              defaultValue: `${bulkAssignPrompt?.otherIds.length} other invoice(s) from "${bulkAssignPrompt?.supplierName}" have no counterparty. Assign "${bulkAssignPrompt?.counterpartyName}" to all of them?`,
            })}
          </p>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => handleBulkAssign(false)}>
              {t('incomingInvoices.bulkAssign.no', 'No, just this one')}
            </Button>
            <Button onClick={() => handleBulkAssign(true)}>
              {t('incomingInvoices.bulkAssign.yes', 'Yes, apply to all')}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Filter card */}
      <div className="flex flex-wrap items-end gap-3 rounded-lg border bg-gray-50 p-3 mb-4">
        <div className="min-w-[200px] flex-1">
          <label className="mb-1 block text-xs font-medium text-gray-500">{t('common.search')}</label>
          <input
            type="text"
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1) }}
            placeholder={t('incomingInvoices.searchPlaceholder')}
            className="w-full rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="w-[150px]">
          <label className="mb-1 block text-xs font-medium text-gray-500">{t('incomingInvoices.statusLabel')}</label>
          <Select value={status} onValueChange={(v) => { setStatus(v); setPage(1) }}>
            <SelectTrigger className="h-8 text-sm">
              <SelectValue />
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
        </div>
        <div className="w-[130px]">
          <label className="mb-1 block text-xs font-medium text-gray-500">{t('incomingInvoices.dateFrom', 'From')}</label>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => { setDateFrom(e.target.value); setPage(1) }}
            className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
        <div className="w-[130px]">
          <label className="mb-1 block text-xs font-medium text-gray-500">{t('incomingInvoices.dateTo', 'To')}</label>
          <input
            type="date"
            value={dateTo}
            onChange={(e) => { setDateTo(e.target.value); setPage(1) }}
            className="w-full rounded-md border border-gray-300 bg-white px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* Table */}
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
          <div className="overflow-x-auto rounded-lg border bg-white">
            <table className="w-full table-fixed text-sm">
              <thead>
                <tr className="border-b bg-gray-50 text-left text-xs font-medium uppercase tracking-wide text-gray-500">
                  <th className="w-[10%] cursor-pointer whitespace-nowrap px-4 py-3" onClick={() => handleSort('invoice_date')}>
                    <span className="inline-flex items-center gap-1">
                      {t('incomingInvoices.date')}
                      {getSortIcon('invoice_date')}
                    </span>
                  </th>
                  <th className="w-[25%] cursor-pointer px-4 py-3" onClick={() => handleSort('supplier_name')}>
                    <span className="inline-flex items-center gap-1">
                      {t('incomingInvoices.supplier')}
                      {getSortIcon('supplier_name')}
                    </span>
                  </th>
                  <th className="w-[15%] cursor-pointer px-4 py-3" onClick={() => handleSort('invoice_number')}>
                    <span className="inline-flex items-center gap-1">
                      {t('incomingInvoices.invoiceNumber')}
                      {getSortIcon('invoice_number')}
                    </span>
                  </th>
                  <th className="w-[12%] cursor-pointer whitespace-nowrap px-4 py-3 text-right" onClick={() => handleSort('gross_amount')}>
                    <span className="inline-flex items-center justify-end gap-1">
                      {t('incomingInvoices.grossAmount')}
                      {getSortIcon('gross_amount')}
                    </span>
                  </th>
                  <th className="w-[10%] cursor-pointer px-4 py-3" onClick={() => handleSort('extraction_status')}>
                    <span className="inline-flex items-center gap-1">
                      {t('incomingInvoices.statusLabel')}
                      {getSortIcon('extraction_status')}
                    </span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {invoices.map((inv: any) => (
                  <tr
                    key={inv.id}
                    className="border-b cursor-pointer transition-colors hover:bg-blue-50/50"
                    onClick={() => setSelectedId(inv.id)}
                  >
                    <td className="whitespace-nowrap px-4 py-2.5 text-gray-600">
                      {formatDate(inv.invoiceDate)}
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-1">
                        <div className="min-w-0 flex-1 truncate font-medium text-gray-900">
                          {inv.counterpartyId ? (
                            <Link
                              to={`/banking/counterparty/${inv.counterpartyId}`}
                              onClick={(e) => e.stopPropagation()}
                              className="text-blue-600 hover:text-blue-800 hover:underline"
                            >
                              {inv.counterpartyName}
                            </Link>
                          ) : (
                            inv.supplierName || inv.originalFilename
                          )}
                        </div>
                        {inv.counterpartyName && inv.supplierName && inv.counterpartyName !== inv.supplierName && (
                          <span className="shrink-0 text-xs text-gray-400" title={inv.supplierName}>
                            ({inv.supplierName.slice(0, 20)})
                          </span>
                        )}
                        <Popover
                          open={editingInvId === inv.id}
                          onOpenChange={(open) => {
                            if (open) {
                              setEditingInvId(inv.id)
                              setCpSearch(inv.supplierName || '')
                              setShowCreateCp(false)
                              setNewCpName('')
                            } else {
                              setEditingInvId(null)
                            }
                          }}
                        >
                          <PopoverTrigger asChild>
                            <button
                              onClick={(e) => e.stopPropagation()}
                              className="flex-shrink-0 rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                              title={t('incomingInvoices.editCounterparty', 'Edit counterparty')}
                            >
                              <Pencil className="h-3.5 w-3.5" />
                            </button>
                          </PopoverTrigger>
                          <PopoverContent className="w-[300px] p-0" align="start" onClick={(e) => e.stopPropagation()}>
                            {showCreateCp ? (
                              <div className="p-3 space-y-3">
                                <div className="text-sm font-medium">{t('banking.createCounterparty', 'Create counterparty')}</div>
                                <input
                                  type="text"
                                  placeholder={t('banking.counterpartyName', 'Name')}
                                  value={newCpName}
                                  onChange={(e) => setNewCpName(e.target.value)}
                                  className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                                  autoFocus
                                />
                                <div className="flex gap-2">
                                  <button onClick={() => setShowCreateCp(false)} className="flex-1 rounded border px-3 py-1.5 text-sm hover:bg-gray-50">
                                    {t('common.cancel')}
                                  </button>
                                  <button
                                    onClick={() => handleCreateAndSelectCounterparty(inv.id)}
                                    disabled={!newCpName.trim()}
                                    className="flex-1 rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
                                  >
                                    {t('common.create')}
                                  </button>
                                </div>
                              </div>
                            ) : (
                              <Command shouldFilter={false}>
                                <CommandInput
                                  placeholder={t('incomingInvoices.searchCounterparty')}
                                  value={cpSearch}
                                  onValueChange={setCpSearch}
                                />
                                <CommandList>
                                  <CommandEmpty>{t('common.noResults')}</CommandEmpty>
                                  <CommandGroup>
                                    {searchedCps.map((cp: any) => (
                                      <CommandItem
                                        key={cp.id}
                                        value={cp.id}
                                        onSelect={() => handleSelectCounterparty(inv.id, cp.id)}
                                        disabled={updatingCp}
                                      >
                                        <div className="flex flex-col">
                                          <span>{cp.name}</span>
                                          {cp.iban && <span className="text-xs text-gray-400">{cp.iban}</span>}
                                        </div>
                                      </CommandItem>
                                    ))}
                                  </CommandGroup>
                                  <CommandSeparator />
                                  <CommandGroup>
                                    <CommandItem onSelect={() => setShowCreateCp(true)}>
                                      <Plus className="mr-2 h-4 w-4" />
                                      {t('banking.createNewCounterparty', 'Create new')}
                                    </CommandItem>
                                  </CommandGroup>
                                </CommandList>
                              </Command>
                            )}
                          </PopoverContent>
                        </Popover>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 text-gray-600">{inv.invoiceNumber || '—'}</td>
                    <td className="whitespace-nowrap px-4 py-2.5 text-right tabular-nums">
                      {formatCurrency(inv.grossAmount, { currency: inv.currency })}
                    </td>
                    <td className="px-4 py-2.5">
                      <Badge variant="secondary" className={statusColors[inv.extractionStatus] || ''}>
                        {t(`incomingInvoices.status.${inv.extractionStatus === 'extraction_failed' ? 'extractionFailed' : inv.extractionStatus}`)}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalCount > 10 && <div className="flex items-center justify-between mt-4">
            <span className="text-sm text-muted-foreground">
              {t('common.showingOf', { from: (page - 1) * 50 + 1, to: Math.min(page * 50, totalCount), total: totalCount })}
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t('common.pagination.previous')}</Button>
              <Button variant="outline" size="sm" disabled={!hasNextPage} onClick={() => setPage(page + 1)}>{t('common.pagination.next')}</Button>
            </div>
          </div>}
        </>
      )}

      {/* Detail sheet */}
      {selectedId && (
        <IncomingInvoiceDetail id={selectedId} open={!!selectedId} onClose={() => setSelectedId(null)} onUpdate={() => refetch()} />
      )}
    </div>
  )
}
