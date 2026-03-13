import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Plus, X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

const DOCUMENT_EMAIL_BCC_QUERY = gql`
  query DocumentEmailBcc {
    documentEmailBcc {
      documentType
      recipients
    }
  }
`

const SET_DOCUMENT_EMAIL_BCC = gql`
  mutation SetDocumentEmailBcc($input: SetDocumentEmailBccInput!) {
    setDocumentEmailBcc(input: $input) {
      success
      error
    }
  }
`

const DOCUMENT_TYPES = ['invoice', 'storno', 'order_confirmation', 'offer'] as const

interface BccEntry {
  documentType: string
  recipients: string[]
}

export function DocumentEmailBccSettings() {
  const { t } = useTranslation()

  const { data, loading } = useQuery<{ documentEmailBcc: BccEntry[] }>(
    DOCUMENT_EMAIL_BCC_QUERY
  )

  const [setDocumentEmailBcc] = useMutation(SET_DOCUMENT_EMAIL_BCC, {
    refetchQueries: [{ query: DOCUMENT_EMAIL_BCC_QUERY }],
  })

  if (loading) {
    return (
      <div className="flex justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
      </div>
    )
  }

  const bccMap: Record<string, string[]> = {}
  for (const entry of data?.documentEmailBcc || []) {
    bccMap[entry.documentType] = entry.recipients
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">
        {t('settings.bcc.description')}
      </p>
      {DOCUMENT_TYPES.map((docType) => (
        <BccCard
          key={docType}
          documentType={docType}
          recipients={bccMap[docType] || []}
          onSave={(recipients) =>
            setDocumentEmailBcc({
              variables: { input: { documentType: docType, recipients } },
            })
          }
        />
      ))}
    </div>
  )
}

function BccCard({
  documentType,
  recipients,
  onSave,
}: {
  documentType: string
  recipients: string[]
  onSave: (recipients: string[]) => Promise<unknown>
}) {
  const { t } = useTranslation()
  const [emails, setEmails] = useState<string[]>(recipients)
  const [newEmail, setNewEmail] = useState('')
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)

  const handleAdd = () => {
    const trimmed = newEmail.trim().toLowerCase()
    if (trimmed && !emails.includes(trimmed)) {
      setEmails([...emails, trimmed])
      setNewEmail('')
      setDirty(true)
    }
  }

  const handleRemove = (email: string) => {
    setEmails(emails.filter((e) => e !== email))
    setDirty(true)
  }

  const handleSave = async () => {
    setSaving(true)
    await onSave(emails)
    setSaving(false)
    setDirty(false)
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">
          {t(`settings.bcc.docTypes.${documentType}`)}
        </CardTitle>
        <CardDescription>
          {t('settings.bcc.cardDescription')}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {emails.map((email) => (
            <div key={email} className="flex items-center gap-2">
              <span className="flex-1 rounded-md border bg-muted px-3 py-1.5 text-sm">
                {email}
              </span>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => handleRemove(email)}
                className="h-8 w-8 p-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          ))}
          <div className="flex items-center gap-2">
            <Input
              type="email"
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAdd())}
              placeholder={t('settings.bcc.addPlaceholder')}
              className="flex-1"
            />
            <Button
              variant="outline"
              size="sm"
              onClick={handleAdd}
              disabled={!newEmail.trim()}
            >
              <Plus className="mr-1 h-4 w-4" />
              {t('settings.bcc.add')}
            </Button>
          </div>
          {dirty && (
            <div className="flex justify-end pt-2">
              <Button size="sm" onClick={handleSave} disabled={saving}>
                {saving && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {t('settings.bcc.save')}
              </Button>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
