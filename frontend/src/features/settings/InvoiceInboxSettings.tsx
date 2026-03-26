import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Plus, Trash2, TestTube, Loader2, Mail, Pencil, Eye } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription, DialogFooter,
} from '@/components/ui/dialog'
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

const INVOICE_INBOXES = gql`
  query InvoiceInboxes {
    invoiceInboxes {
      id name inboxType host port username folder m365Mailbox isActive pollIntervalMinutes lastPolledAt useSsl
    }
  }
`

const CREATE_INBOX = gql`
  mutation CreateInvoiceInbox($input: CreateInvoiceInboxInput!) {
    createInvoiceInbox(input: $input) { success error inbox { id name } }
  }
`

const UPDATE_INBOX = gql`
  mutation UpdateInvoiceInbox($input: UpdateInvoiceInboxInput!) {
    updateInvoiceInbox(input: $input) { success error inbox { id name } }
  }
`

const DELETE_INBOX = gql`
  mutation DeleteInvoiceInbox($id: ID!) {
    deleteInvoiceInbox(id: $id) { success error }
  }
`

const TEST_CONNECTION = gql`
  mutation TestInvoiceInboxConnection($id: ID!) {
    testInvoiceInboxConnection(id: $id) { success message emailCount }
  }
`

const INBOX_EMAILS = gql`
  query InboxEmails($inboxId: ID!, $page: Int!, $pageSize: Int!) {
    incomingInvoices(inboxId: $inboxId, page: $page, pageSize: $pageSize) {
      items {
        id
        sourceEmailSubject
        sourceEmailDate
        originalFilename
        extractionStatus
        extractionError
        supplierName
        grossAmount
        currency
        createdAt
      }
      totalCount
      hasNextPage
    }
  }
`

interface InboxFormData {
  name: string; inboxType: string; host: string; port: number; username: string
  password: string; folder: string; useSsl: boolean; m365Mailbox: string
  isActive: boolean; pollIntervalMinutes: number
}

const defaultForm: InboxFormData = {
  name: '', inboxType: 'imap', host: '', port: 993, username: '', password: '',
  folder: 'INBOX', useSsl: true, m365Mailbox: '', isActive: true, pollIntervalMinutes: 15,
}

const STATUS_CONFIG: Record<string, { label: string; className: string }> = {
  pending: { label: 'Queued', className: 'bg-yellow-100 text-yellow-800' },
  extracting: { label: 'Processing', className: 'bg-blue-100 text-blue-800' },
  extracted: { label: 'Extracted', className: 'bg-green-100 text-green-800' },
  extraction_failed: { label: 'Failed', className: 'bg-red-100 text-red-800' },
  confirmed: { label: 'Confirmed', className: 'bg-emerald-100 text-emerald-800' },
  matched: { label: 'Matched', className: 'bg-purple-100 text-purple-800' },
}

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] || { label: status, className: 'bg-gray-100 text-gray-800' }
  return (
    <span className={cn('inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium', config.className)}>
      {config.label}
    </span>
  )
}

function InboxDebugModal({ inboxId, inboxName, onClose }: { inboxId: string; inboxName: string; onClose: () => void }) {
  const { t } = useTranslation()
  const [page, setPage] = useState(1)
  const { data, loading } = useQuery(INBOX_EMAILS, {
    variables: { inboxId, page, pageSize: 30 },
    pollInterval: 5000,
  })

  const emails = data?.incomingInvoices?.items || []
  const totalCount = data?.incomingInvoices?.totalCount || 0
  const hasNextPage = data?.incomingInvoices?.hasNextPage || false

  return (
    <Dialog open onOpenChange={(open) => { if (!open) onClose() }}>
      <DialogContent className="max-w-4xl max-h-[80vh] flex flex-col">
        <DialogHeader>
          <DialogTitle>{inboxName} — Emails ({totalCount})</DialogTitle>
          <DialogDescription>Recent emails processed from this inbox. Auto-refreshes every 5s.</DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-auto min-h-0">
          {loading && emails.length === 0 ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : emails.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Mail className="mx-auto h-8 w-8 mb-2 opacity-50" />
              <p>No emails found in this inbox.</p>
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="sticky top-0 bg-white border-b">
                <tr className="text-left text-xs text-muted-foreground">
                  <th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Email Subject</th>
                  <th className="py-2 pr-3">Filename</th>
                  <th className="py-2 pr-3">Supplier</th>
                  <th className="py-2 pr-3 text-right">Amount</th>
                  <th className="py-2 pr-3">Email Date</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {emails.map((email: any) => (
                  <tr key={email.id} className="hover:bg-gray-50">
                    <td className="py-2 pr-3">
                      <StatusBadge status={email.extractionStatus} />
                    </td>
                    <td className="py-2 pr-3 max-w-[200px]">
                      <div className="truncate" title={email.sourceEmailSubject}>
                        {email.sourceEmailSubject || '—'}
                      </div>
                      {email.extractionStatus === 'extraction_failed' && email.extractionError && (
                        <div className="truncate text-xs text-red-500 mt-0.5" title={email.extractionError}>
                          {email.extractionError}
                        </div>
                      )}
                    </td>
                    <td className="py-2 pr-3 max-w-[150px]">
                      <div className="truncate text-xs" title={email.originalFilename}>{email.originalFilename}</div>
                    </td>
                    <td className="py-2 pr-3">{email.supplierName || '—'}</td>
                    <td className="py-2 pr-3 text-right tabular-nums">
                      {email.grossAmount ? `${Number(email.grossAmount).toLocaleString('de-DE', { minimumFractionDigits: 2 })} ${email.currency}` : '—'}
                    </td>
                    <td className="py-2 pr-3 text-xs text-muted-foreground whitespace-nowrap">
                      {email.sourceEmailDate ? new Date(email.sourceEmailDate).toLocaleString() : '—'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {totalCount > 30 && (
          <div className="flex items-center justify-between border-t pt-3">
            <span className="text-xs text-muted-foreground">
              Page {page} · {totalCount} total
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={() => setPage(p => p - 1)} disabled={page <= 1}>
                {t('common.back')}
              </Button>
              <Button variant="outline" size="sm" onClick={() => setPage(p => p + 1)} disabled={!hasNextPage}>
                Next
              </Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}

export function InvoiceInboxSettings() {
  const { t } = useTranslation()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<InboxFormData>(defaultForm)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string; emailCount?: number | null } | null>(null)
  const [debugInbox, setDebugInbox] = useState<{ id: string; name: string } | null>(null)

  const { data, loading, refetch } = useQuery(INVOICE_INBOXES)
  const [createInbox, { loading: creating }] = useMutation(CREATE_INBOX)
  const [updateInbox, { loading: updating }] = useMutation(UPDATE_INBOX)
  const [deleteInbox, { loading: deleting }] = useMutation(DELETE_INBOX)
  const [testConnection, { loading: testing }] = useMutation(TEST_CONNECTION)

  const inboxes = data?.invoiceInboxes || []

  const handleSave = async () => {
    const input = { ...form }
    if (editingId) {
      await updateInbox({ variables: { input: { id: editingId, ...input } } })
    } else {
      await createInbox({ variables: { input } })
    }
    setShowForm(false); setEditingId(null); setForm(defaultForm); refetch()
  }

  const handleEdit = (inbox: any) => {
    setForm({
      name: inbox.name, inboxType: inbox.inboxType, host: inbox.host, port: inbox.port,
      username: inbox.username, password: '', folder: inbox.folder, useSsl: inbox.useSsl,
      m365Mailbox: inbox.m365Mailbox, isActive: inbox.isActive, pollIntervalMinutes: inbox.pollIntervalMinutes,
    })
    setEditingId(inbox.id); setShowForm(true)
  }

  const handleDelete = async () => {
    if (!deleteId) return
    await deleteInbox({ variables: { id: deleteId } })
    setDeleteId(null); refetch()
  }

  const handleTest = async (id: string) => {
    setTestResult(null)
    const { data } = await testConnection({ variables: { id } })
    setTestResult(data?.testInvoiceInboxConnection)
  }

  if (loading) return <div className="flex items-center gap-2"><Loader2 className="h-4 w-4 animate-spin" />{t('common.loading')}</div>

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-medium">{t('incomingInvoices.inboxes.title')}</h3>
          <p className="text-sm text-muted-foreground">{t('incomingInvoices.inboxes.description')}</p>
        </div>
        <Button onClick={() => { setForm(defaultForm); setEditingId(null); setShowForm(true) }}>
          <Plus className="mr-1.5 h-4 w-4" />{t('incomingInvoices.inboxes.add')}
        </Button>
      </div>

      {inboxes.length === 0 ? (
        <div className="text-center py-8 text-muted-foreground">
          <Mail className="mx-auto h-10 w-10 mb-2 opacity-50" />
          <p>{t('incomingInvoices.inboxes.empty')}</p>
        </div>
      ) : (
        <div className="space-y-2">
          {inboxes.map((inbox: any) => (
            <div key={inbox.id} className="flex items-center justify-between border rounded-lg p-4">
              <div>
                <div className="font-medium">{inbox.name}</div>
                <div className="text-sm text-muted-foreground">
                  {inbox.inboxType === 'imap' ? `${inbox.host}:${inbox.port}` : inbox.m365Mailbox}
                  {' · '}{inbox.isActive ? t('common.active') : t('common.inactive')}
                  {inbox.lastPolledAt && ` · ${t('incomingInvoices.inboxes.lastPolled')}: ${new Date(inbox.lastPolledAt).toLocaleString()}`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setDebugInbox({ id: inbox.id, name: inbox.name })} title="View emails">
                  <Eye className="h-4 w-4" />
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleTest(inbox.id)} disabled={testing}>
                  {testing ? <Loader2 className="h-4 w-4 animate-spin" /> : <TestTube className="h-4 w-4" />}
                </Button>
                <Button variant="outline" size="sm" onClick={() => handleEdit(inbox)}><Pencil className="h-4 w-4" /></Button>
                <Button variant="outline" size="sm" onClick={() => setDeleteId(inbox.id)}><Trash2 className="h-4 w-4 text-destructive" /></Button>
              </div>
            </div>
          ))}
        </div>
      )}

      {testResult && (
        <div className={`p-3 rounded-lg text-sm ${testResult.success ? 'bg-green-50 text-green-700 dark:bg-green-950 dark:text-green-300' : 'bg-red-50 text-red-700 dark:bg-red-950 dark:text-red-300'}`}>
          {testResult.message}
        </div>
      )}

      {debugInbox && (
        <InboxDebugModal inboxId={debugInbox.id} inboxName={debugInbox.name} onClose={() => setDebugInbox(null)} />
      )}

      <Dialog open={showForm} onOpenChange={(open) => { if (!open) { setShowForm(false); setEditingId(null) } }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? t('incomingInvoices.inboxes.edit') : t('incomingInvoices.inboxes.add')}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div><Label>{t('common.name')}</Label><Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} /></div>
            <div>
              <Label>{t('incomingInvoices.inboxes.type')}</Label>
              <Select value={form.inboxType} onValueChange={(v) => setForm({ ...form, inboxType: v })}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="imap">IMAP</SelectItem>
                  <SelectItem value="m365">Microsoft 365</SelectItem>
                </SelectContent>
              </Select>
            </div>
            {form.inboxType === 'imap' ? (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <div><Label>{t('incomingInvoices.inboxes.host')}</Label><Input value={form.host} onChange={(e) => setForm({ ...form, host: e.target.value })} /></div>
                  <div><Label>{t('incomingInvoices.inboxes.port')}</Label><Input type="number" value={form.port} onChange={(e) => setForm({ ...form, port: parseInt(e.target.value) || 993 })} /></div>
                </div>
                <div><Label>{t('incomingInvoices.inboxes.username')}</Label><Input value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
                <div><Label>{t('incomingInvoices.inboxes.password')}</Label><Input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder={editingId ? t('incomingInvoices.inboxes.passwordUnchanged') : ''} /></div>
                <div><Label>{t('incomingInvoices.inboxes.folder')}</Label><Input value={form.folder} onChange={(e) => setForm({ ...form, folder: e.target.value })} /></div>
                <div className="flex items-center gap-2"><Switch checked={form.useSsl} onCheckedChange={(v) => setForm({ ...form, useSsl: v })} /><Label>SSL/TLS</Label></div>
              </>
            ) : (
              <div><Label>{t('incomingInvoices.inboxes.m365Mailbox')}</Label><Input value={form.m365Mailbox} onChange={(e) => setForm({ ...form, m365Mailbox: e.target.value })} placeholder="invoices@company.com" /></div>
            )}
            <div><Label>{t('incomingInvoices.inboxes.pollInterval')}</Label><Input type="number" value={form.pollIntervalMinutes} onChange={(e) => setForm({ ...form, pollIntervalMinutes: parseInt(e.target.value) || 15 })} /></div>
            <div className="flex items-center gap-2"><Switch checked={form.isActive} onCheckedChange={(v) => setForm({ ...form, isActive: v })} /><Label>{t('common.active')}</Label></div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setShowForm(false); setEditingId(null) }}>{t('common.cancel')}</Button>
            <Button onClick={handleSave} disabled={creating || updating || !form.name}>
              {(creating || updating) && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />}{t('common.save')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={!!deleteId} onOpenChange={(open) => { if (!open) setDeleteId(null) }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t('incomingInvoices.inboxes.deleteConfirmTitle')}</DialogTitle>
            <DialogDescription>{t('incomingInvoices.inboxes.deleteConfirmDescription')}</DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteId(null)}>{t('common.cancel')}</Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting && <Loader2 className="mr-1.5 h-4 w-4 animate-spin" />}{t('common.delete')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
