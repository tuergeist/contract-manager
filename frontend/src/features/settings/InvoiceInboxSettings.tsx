import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Plus, Trash2, TestTube, Loader2, Mail, Pencil } from 'lucide-react'
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
    testInvoiceInboxConnection(id: $id) { success message }
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

export function InvoiceInboxSettings() {
  const { t } = useTranslation()
  const [showForm, setShowForm] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [form, setForm] = useState<InboxFormData>(defaultForm)
  const [deleteId, setDeleteId] = useState<string | null>(null)
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null)

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
