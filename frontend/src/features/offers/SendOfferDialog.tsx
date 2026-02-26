import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { X, Plus, Send, Loader2 } from 'lucide-react'

const SEND_OFFER_EMAIL = gql`
  mutation SendOfferEmail($id: Int!, $recipients: [String!]!) {
    sendOfferEmail(id: $id, recipients: $recipients) {
      success
      error
      offer {
        id
        status
        emailSentAt
        emailSentTo
      }
    }
  }
`

interface SendOfferDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  offerId: number
  defaultRecipients: string[]
  onSent: () => void
}

export function SendOfferDialog({
  open,
  onOpenChange,
  offerId,
  defaultRecipients,
  onSent,
}: SendOfferDialogProps) {
  const { t } = useTranslation()
  const [recipients, setRecipients] = useState<string[]>([...defaultRecipients])
  const [newEmail, setNewEmail] = useState('')
  const [error, setError] = useState<string | null>(null)

  const [sendEmail, { loading }] = useMutation(SEND_OFFER_EMAIL)

  const handleAddRecipient = () => {
    const email = newEmail.trim()
    if (!email) return
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      setError(t('offers.send.invalidEmail'))
      return
    }
    if (recipients.includes(email)) {
      setError(t('offers.send.duplicateEmail'))
      return
    }
    setRecipients([...recipients, email])
    setNewEmail('')
    setError(null)
  }

  const handleRemoveRecipient = (email: string) => {
    setRecipients(recipients.filter((r) => r !== email))
  }

  const handleSend = async () => {
    if (recipients.length === 0) {
      setError(t('offers.send.noRecipients'))
      return
    }
    setError(null)
    const result = await sendEmail({
      variables: { id: offerId, recipients },
    })
    if (result.data?.sendOfferEmail?.success) {
      onOpenChange(false)
      onSent()
    } else {
      setError(result.data?.sendOfferEmail?.error || t('offers.send.sendFailed'))
    }
  }

  // Reset state when dialog opens
  const handleOpenChange = (isOpen: boolean) => {
    if (isOpen) {
      setRecipients([...defaultRecipients])
      setNewEmail('')
      setError(null)
    }
    onOpenChange(isOpen)
  }

  return (
    <Dialog open={open} onOpenChange={handleOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{t('offers.send.title')}</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <p className="text-sm text-gray-500">{t('offers.send.description')}</p>

          {/* Recipients list */}
          <div className="space-y-2">
            {recipients.map((email) => (
              <div key={email} className="flex items-center gap-2 text-sm bg-gray-50 rounded px-3 py-1.5">
                <span className="flex-1">{email}</span>
                <button
                  onClick={() => handleRemoveRecipient(email)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            ))}
          </div>

          {/* Add recipient */}
          <div className="flex gap-2">
            <Input
              value={newEmail}
              onChange={(e) => setNewEmail(e.target.value)}
              placeholder={t('offers.send.addEmailPlaceholder')}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  handleAddRecipient()
                }
              }}
            />
            <Button variant="outline" size="sm" onClick={handleAddRecipient}>
              <Plus className="w-4 h-4" />
            </Button>
          </div>

          {error && (
            <p className="text-sm text-red-600">{error}</p>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            {t('common.cancel')}
          </Button>
          <Button onClick={handleSend} disabled={loading || recipients.length === 0}>
            {loading ? (
              <Loader2 className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Send className="w-4 h-4 mr-2" />
            )}
            {t('offers.send.sendButton')}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
