import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useLazyQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Check, ExternalLink, ChevronsUpDown } from 'lucide-react'
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
}

export function IncomingInvoiceDetail({ id, open, onClose, onUpdate }: Props) {
  const { t } = useTranslation()
  const { data, loading } = useQuery(INCOMING_INVOICE_DETAIL, { variables: { id } })
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
      id,
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

  const handleDelete = async () => {
    await deleteInvoice({ variables: { id } })
    onUpdate()
    onClose()
  }

  return (
    <Sheet open={open} onOpenChange={(o) => { if (!o) onClose() }}>
      <SheetContent className="w-full sm:max-w-2xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle>{t('incomingInvoices.detail.title')}</SheetTitle>
        </SheetHeader>

        {loading || !inv ? (
          <div className="flex justify-center py-8"><Loader2 className="h-6 w-6 animate-spin" /></div>
        ) : (
          <div className="space-y-6 mt-4">
            {inv.pdfUrl && (
              <div className="border rounded-lg overflow-hidden">
                <div className="flex items-center justify-between p-2 bg-muted">
                  <span className="text-sm font-medium">{inv.originalFilename}</span>
                  <a href={inv.pdfUrl} target="_blank" rel="noopener noreferrer">
                    <Button variant="ghost" size="sm"><ExternalLink className="h-4 w-4" /></Button>
                  </a>
                </div>
                <iframe src={inv.pdfUrl} className="w-full h-[300px]" title="PDF Preview" />
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

            <div className="grid grid-cols-2 gap-4">
              <div className="col-span-2">
                <Label>{t('incomingInvoices.supplier')}</Label>
                <Input value={form.supplierName} onChange={(e) => setForm({ ...form, supplierName: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.invoiceNumber')}</Label>
                <Input value={form.invoiceNumber} onChange={(e) => setForm({ ...form, invoiceNumber: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.currency')}</Label>
                <Input value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.date')}</Label>
                <Input type="date" value={form.invoiceDate} onChange={(e) => setForm({ ...form, invoiceDate: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.dueDate')}</Label>
                <Input type="date" value={form.dueDate} onChange={(e) => setForm({ ...form, dueDate: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.netAmount')}</Label>
                <Input type="number" step="0.01" value={form.netAmount} onChange={(e) => setForm({ ...form, netAmount: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.vatAmount')}</Label>
                <Input type="number" step="0.01" value={form.vatAmount} onChange={(e) => setForm({ ...form, vatAmount: e.target.value })} />
              </div>
              <div>
                <Label>{t('incomingInvoices.grossAmount')}</Label>
                <Input type="number" step="0.01" value={form.grossAmount} onChange={(e) => setForm({ ...form, grossAmount: e.target.value })} />
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
