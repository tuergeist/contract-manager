import { useState, useEffect, useRef } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useLazyQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Check, ExternalLink, ChevronsUpDown, PanelTopOpen, ChevronRight, GripHorizontal } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from '@/components/ui/sheet'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import { cn } from '@/lib/utils'

const MATCH_SUGGESTION = gql`
  query IncomingInvoiceMatchSuggestion($invoiceId: ID!) {
    incomingInvoiceMatchSuggestion(invoiceId: $invoiceId) {
      id
      entryDate
      amount
      currency
      counterparty { name }
    }
  }
`

const CONFIRM_AND_MATCH = gql`
  mutation ConfirmAndMatchIncoming($invoiceId: ID!, $transactionId: Int) {
    confirmAndMatchIncoming(invoiceId: $invoiceId, transactionId: $transactionId) {
      success
      error
      matchId
      invoice { id extractionStatus }
    }
  }
`

const INCOMING_INVOICE_DETAIL = gql`
  query IncomingInvoice($id: ID!) {
    incomingInvoice(id: $id) {
      id
      supplierName
      invoiceNumber
      invoiceDate
      dueDate
      netAmount
      vatAmount
      grossAmount
      currency
      originalFilename
      fileSize
      extractionStatus
      extractionError
      extractionConfidence
      sourceEmailSubject
      sourceEmailDate
      counterpartyId
      counterpartyName
      inboxName
      pdfUrl
      createdAt
    }
  }
`

const COUNTERPARTY_SEARCH = gql`
  query CounterpartySearch($search: String, $pageSize: Int!) {
    counterparties(search: $search, pageSize: $pageSize) {
      items { id name }
    }
  }
`

const UPDATE_INCOMING_INVOICE = gql`
  mutation UpdateIncomingInvoice($input: UpdateIncomingInvoiceInput!) {
    updateIncomingInvoice(input: $input) {
      success
      error
      invoice { id supplierName invoiceNumber extractionStatus counterpartyId counterpartyName }
    }
  }
`

const DELETE_INCOMING_INVOICE = gql`
  mutation DeleteIncomingInvoice($id: ID!) {
    deleteIncomingInvoice(id: $id) { success error }
  }
`

interface Props {
  id: string
  open: boolean
  onClose: () => void
  onUpdate: () => void
  pendingIds?: string[]
  onAllDone?: () => void
}

export function IncomingInvoiceDetail({ id, open, onClose, onUpdate, pendingIds = [], onAllDone }: Props) {
  const { t } = useTranslation()
  const [currentId, setCurrentId] = useState(id)

  // Reset to entry id when sheet opens with a new id
  useEffect(() => { setCurrentId(id) }, [id])

  const { data, loading } = useQuery(INCOMING_INVOICE_DETAIL, { variables: { id: currentId } })
  const { data: suggestionData, refetch: refetchSuggestion } = useQuery(MATCH_SUGGESTION, {
    variables: { invoiceId: currentId },
    skip: !currentId,
    fetchPolicy: 'network-only',
  })
  const [confirmAndMatch] = useMutation(CONFIRM_AND_MATCH)
  const matchSuggestion = suggestionData?.incomingInvoiceMatchSuggestion
  const [searchCounterparties, { data: cpData, loading: cpLoading }] = useLazyQuery(COUNTERPARTY_SEARCH)
  const [updateInvoice, { loading: updating }] = useMutation(UPDATE_INCOMING_INVOICE)
  const [deleteInvoice, { loading: deleting }] = useMutation(DELETE_INCOMING_INVOICE)

  const inv = data?.incomingInvoice
  const counterparties = cpData?.counterparties?.items || []
  const [form, setForm] = useState<any>({})
  const [cpOpen, setCpOpen] = useState(false)
  const [cpSearch, setCpSearch] = useState('')
  const [selectedCpName, setSelectedCpName] = useState('')

  useEffect(() => {
    if (inv) {
      setForm({
        supplierName: inv.supplierName || '',
        invoiceNumber: inv.invoiceNumber || '',
        invoiceDate: inv.invoiceDate || '',
        dueDate: inv.dueDate || '',
        netAmount: inv.netAmount || '',
        vatAmount: inv.vatAmount || '',
        grossAmount: inv.grossAmount || '',
        currency: inv.currency || 'EUR',
        counterpartyId: inv.counterpartyId || '',
      })
      setSelectedCpName(inv.counterpartyName || '')
    }
  }, [inv])

  // Search counterparties with debounce
  useEffect(() => {
    if (!cpOpen) return
    const timer = setTimeout(() => {
      searchCounterparties({ variables: { search: cpSearch || null, pageSize: 30 } })
    }, 200)
    return () => clearTimeout(timer)
  }, [cpSearch, cpOpen, searchCounterparties])

  // Pre-populate search with supplier name when opening
  const handleCpOpen = (isOpen: boolean) => {
    setCpOpen(isOpen)
    if (isOpen && !cpSearch && form.supplierName) {
      setCpSearch(form.supplierName)
    }
  }

  const handleSave = async (newStatus?: string) => {
    const input: any = {
      id: currentId,
      supplierName: form.supplierName,
      invoiceNumber: form.invoiceNumber,
      invoiceDate: form.invoiceDate || null,
      dueDate: form.dueDate || null,
      netAmount: form.netAmount || null,
      vatAmount: form.vatAmount || null,
      grossAmount: form.grossAmount || null,
      currency: form.currency,
      counterpartyId: form.counterpartyId || null,
    }
    if (newStatus) input.extractionStatus = newStatus
    await updateInvoice({ variables: { input } })
    onUpdate()
  }

  const handleConfirmAndMatch = async () => {
    // Save edits first, then confirm+match in one mutation
    await handleSave()
    await confirmAndMatch({
      variables: {
        invoiceId: currentId,
        transactionId: matchSuggestion ? parseInt(matchSuggestion.id) : null,
      },
    })
    onUpdate()
    refetchSuggestion()
    // Auto-advance if there's a next pending invoice
    const currentIdx = pendingIds.indexOf(currentId)
    const nextId = currentIdx >= 0 && currentIdx < pendingIds.length - 1
      ? pendingIds[currentIdx + 1] : null
    if (nextId) setCurrentId(nextId)
    else onAllDone ? onAllDone() : onClose()
  }

  const handleConfirmAndNext = async () => {
    await handleSave('confirmed')
    const currentIdx = pendingIds.indexOf(currentId)
    // Find next id, skipping the one we just confirmed
    const nextId = currentIdx >= 0 && currentIdx < pendingIds.length - 1
      ? pendingIds[currentIdx + 1]
      : null
    if (nextId) {
      setCurrentId(nextId)
    } else {
      onAllDone ? onAllDone() : onClose()
    }
  }

  const handleDelete = async () => {
    await deleteInvoice({ variables: { id: currentId } })
    onUpdate()
    onClose()
  }

  // PDF resize: persist user-chosen height to localStorage
  const pdfWrapperRef = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const wrapper = pdfWrapperRef.current
    if (!wrapper) return
    const stored = localStorage.getItem('cm:incoming:pdfHeight')
    if (stored) {
      const px = parseInt(stored, 10)
      if (!isNaN(px) && px > 200) wrapper.style.height = `${px}px`
    }
    const observer = new ResizeObserver(() => {
      const h = wrapper.clientHeight
      if (h > 200) localStorage.setItem('cm:incoming:pdfHeight', String(h))
    })
    observer.observe(wrapper)
    return () => observer.disconnect()
  }, [inv?.pdfUrl])

  // Cmd/Ctrl+Enter keyboard shortcut
  useEffect(() => {
    if (!open) return
    const handler = (e: KeyboardEvent) => {
      if (!(e.metaKey || e.ctrlKey) || e.key !== 'Enter') return
      const tag = (e.target as HTMLElement).tagName.toLowerCase()
      if (['input', 'textarea', 'select'].includes(tag)) return
      e.preventDefault()
      handleConfirmAndNext()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, currentId, pendingIds, form])

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <SheetContent className="w-full sm:max-w-3xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t('incomingInvoices.detail.title')}</SheetTitle>
        </SheetHeader>

        {loading || !inv ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : (
          <div className="space-y-6 mt-4">
            {inv.pdfUrl && (
              <div className="border rounded-lg overflow-hidden">
                <div className="flex items-center justify-between p-2 bg-muted gap-2">
                  <span className="text-sm font-medium truncate">{inv.originalFilename}</span>
                  <div className="flex items-center gap-1 shrink-0">
                    <Button
                      variant="ghost"
                      size="sm"
                      type="button"
                      title={t('incomingInvoices.detail.openPopup', 'In Popup öffnen')}
                      onClick={() => window.open(
                        inv.pdfUrl!,
                        'incoming-invoice-pdf',
                        'width=900,height=1100,resizable=yes,scrollbars=yes',
                      )}
                    >
                      <PanelTopOpen className="h-4 w-4" />
                    </Button>
                    <a href={inv.pdfUrl} target="_blank" rel="noopener noreferrer"
                       title={t('incomingInvoices.detail.openTab', 'In neuem Tab öffnen')}>
                      <Button variant="ghost" size="sm" type="button"><ExternalLink className="h-4 w-4" /></Button>
                    </a>
                  </div>
                </div>
                <div
                  ref={pdfWrapperRef}
                  className="relative w-full bg-white overflow-hidden"
                  style={{ resize: 'vertical', minHeight: '70vh', maxHeight: '90vh', height: '70vh' }}
                >
                  <iframe src={inv.pdfUrl} className="w-full h-full bg-white" title="PDF Preview" />
                  <div
                    className="pointer-events-none absolute bottom-0 left-1/2 -translate-x-1/2 flex items-center justify-center pb-0.5 text-gray-400"
                    title={t('incomingInvoices.detail.resizeHint', 'Höhe anpassen')}
                  >
                    <GripHorizontal className="h-3 w-6" />
                  </div>
                </div>
              </div>
            )}

            {inv.sourceEmailSubject && (
              <div className="text-sm text-muted-foreground">
                <span className="font-medium">{t('incomingInvoices.detail.emailSubject')}:</span> {inv.sourceEmailSubject}
                {inv.sourceEmailDate && <span> · {new Date(inv.sourceEmailDate).toLocaleString()}</span>}
              </div>
            )}

            {inv.extractionError && (
              <div className="p-3 bg-red-50 dark:bg-red-950 text-red-700 dark:text-red-300 rounded-lg text-sm">{inv.extractionError}</div>
            )}

            {(() => {
              const conf: Record<string, number> = inv.extractionConfidence || {}
              const isLow = (k: string) => conf[k] !== undefined && conf[k] < 0.8
              const lowCls = (k: string) => isLow(k) ? 'border-yellow-400 focus-visible:ring-yellow-300' : ''
              const lowTitle = (k: string) => isLow(k)
                ? t('incomingInvoices.detail.lowConfidence', 'AI ist unsicher — bitte prüfen ({{c}}%)', { c: Math.round((conf[k] || 0) * 100) })
                : undefined
              return (
            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>{t('incomingInvoices.supplier')}</Label>
                <Input className={lowCls('supplier_name')} title={lowTitle('supplier_name')} value={form.supplierName} onChange={(e) => setForm({ ...form, supplierName: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.invoiceNumber')}</Label>
                <Input className={lowCls('invoice_number')} title={lowTitle('invoice_number')} value={form.invoiceNumber} onChange={(e) => setForm({ ...form, invoiceNumber: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.currency')}</Label>
                <Input className={lowCls('currency')} title={lowTitle('currency')} value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.date')}</Label>
                <Input className={lowCls('invoice_date')} title={lowTitle('invoice_date')} type="date" value={form.invoiceDate} onChange={(e) => setForm({ ...form, invoiceDate: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.dueDate')}</Label>
                <Input className={lowCls('due_date')} title={lowTitle('due_date')} type="date" value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.netAmount')}</Label>
                <Input className={lowCls('net_amount')} title={lowTitle('net_amount')} type="number" step="0.01" value={form.netAmount} onChange={(e) => setForm({ ...form, netAmount: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.vatAmount')}</Label>
                <Input className={lowCls('vat_amount')} title={lowTitle('vat_amount')} type="number" step="0.01" value={form.vatAmount} onChange={(e) => setForm({ ...form, vatAmount: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.grossAmount')}</Label>
                <Input className={lowCls('gross_amount')} title={lowTitle('gross_amount')} type="number" step="0.01" value={form.grossAmount} onChange={(e) => setForm({ ...form, grossAmount: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.counterparty')}</Label>
                <Popover open={cpOpen} onOpenChange={handleCpOpen}>
                  <PopoverTrigger asChild>
                    <Button
                      variant="outline"
                      role="combobox"
                      className={cn('w-full justify-between font-normal', !form.counterpartyId && 'text-muted-foreground')}
                    >
                      <span className="truncate">{selectedCpName || '—'}</span>
                      <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
                    </Button>
                  </PopoverTrigger>
                  <PopoverContent className="w-[300px] p-0" align="start">
                    <Command shouldFilter={false}>
                      <CommandInput
                        placeholder={t('incomingInvoices.searchCounterparty')}
                        value={cpSearch}
                        onValueChange={setCpSearch}
                      />
                      <CommandList>
                        {cpLoading && (
                          <div className="flex justify-center py-3"><Loader2 className="h-4 w-4 animate-spin" /></div>
                        )}
                        <CommandEmpty>{cpLoading ? '' : t('common.noResults')}</CommandEmpty>
                        <CommandGroup>
                          <CommandItem
                            value="none"
                            onSelect={() => {
                              setForm({ ...form, counterpartyId: '' })
                              setSelectedCpName('')
                              setCpOpen(false)
                              setCpSearch('')
                            }}
                          >
                            <span className="text-muted-foreground">—</span>
                          </CommandItem>
                          {counterparties.map((cp: any) => (
                            <CommandItem
                              key={cp.id}
                              value={cp.id}
                              onSelect={() => {
                                setForm({ ...form, counterpartyId: cp.id })
                                setSelectedCpName(cp.name)
                                setCpOpen(false)
                                setCpSearch('')
                              }}
                            >
                              <Check className={cn('mr-2 h-4 w-4', form.counterpartyId === cp.id ? 'opacity-100' : 'opacity-0')} />
                              {cp.name}
                            </CommandItem>
                          ))}
                        </CommandGroup>
                      </CommandList>
                    </Command>
                  </PopoverContent>
                </Popover>
              </div>
            </div>
              )
            })()}

            <div className="flex items-center gap-2 pt-4 border-t">
              <Button onClick={() => handleSave()} disabled={updating}>
                {updating && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />}
                {t('common.save')}
              </Button>
              {inv.extractionStatus !== 'confirmed' && (
                <Button variant="outline" onClick={() => handleSave('confirmed')} disabled={updating}>
                  <Check className="mr-1.5 h-4 w-4" />
                  {t('incomingInvoices.detail.confirm')}
                </Button>
              )}
              {matchSuggestion && (
                <Button
                  variant="default"
                  onClick={handleConfirmAndMatch}
                  disabled={updating}
                  className="bg-emerald-600 hover:bg-emerald-700"
                  title={t('incomingInvoices.detail.confirmAndMatchHint', 'Bestätigen und passende Banktransaktion zuordnen')}
                >
                  <Check className="mr-1.5 h-4 w-4" />
                  {t('incomingInvoices.detail.confirmAndMatch', 'Bestätigen + Match')}
                  <span className="ml-1.5 text-xs opacity-80">
                    {new Date(matchSuggestion.entryDate).toLocaleDateString('de-DE', { day: '2-digit', month: '2-digit' })}
                    {' · '}
                    {new Intl.NumberFormat('de-DE', { style: 'currency', currency: matchSuggestion.currency || 'EUR' }).format(parseFloat(matchSuggestion.amount))}
                  </span>
                </Button>
              )}
              {pendingIds.length > 0 && (
                <Button
                  variant={pendingIds.indexOf(currentId) < pendingIds.length - 1 ? 'default' : 'outline'}
                  onClick={handleConfirmAndNext}
                  disabled={updating}
                  title="Cmd/Ctrl+Enter"
                >
                  {updating && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />}
                  {pendingIds.indexOf(currentId) < pendingIds.length - 1
                    ? <><Check className="mr-1.5 h-4 w-4" />{t('incomingInvoices.detail.confirmAndNext')}<ChevronRight className="ml-1 h-3.5 w-3.5" /></>
                    : <><Check className="mr-1.5 h-4 w-4" />{t('incomingInvoices.detail.confirmAndDone')}</>
                  }
                </Button>
              )}
              <div className="flex-1" />
              <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
                {deleting && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />}
                {t('common.delete')}
              </Button>
            </div>
          </div>
        )}
      </SheetContent>
    </Sheet>
  )
}
