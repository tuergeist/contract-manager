import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { Loader2, Mail, Eye, Send } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Checkbox } from '@/components/ui/checkbox'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog'

const PREVIEW_ORDER_CONFIRMATION = gql`
  mutation PreviewOrderConfirmationHtml(
    $contractId: ID!
    $personalMessage: String
    $includeMessageInPdf: Boolean
  ) {
    previewOrderConfirmationHtml(
      contractId: $contractId
      personalMessage: $personalMessage
      includeMessageInPdf: $includeMessageInPdf
    ) {
      html
      error
    }
  }
`

const CREATE_ORDER_CONFIRMATION = gql`
  mutation CreateOrderConfirmation(
    $contractId: ID!
    $personalMessage: String
    $includeMessageInPdf: Boolean
    $includeMessageInEmail: Boolean
    $additionalEmails: [String!]
  ) {
    createOrderConfirmation(
      contractId: $contractId
      personalMessage: $personalMessage
      includeMessageInPdf: $includeMessageInPdf
      includeMessageInEmail: $includeMessageInEmail
      additionalEmails: $additionalEmails
    ) {
      orderConfirmation {
        id
        orderConfirmationNumber
        status
      }
      success
      error
    }
  }
`

const SEND_ORDER_CONFIRMATION = gql`
  mutation SendOrderConfirmation($orderConfirmationId: ID!) {
    sendOrderConfirmation(orderConfirmationId: $orderConfirmationId) {
      orderConfirmation {
        id
        status
        sentAt
      }
      success
      error
    }
  }
`

interface OrderConfirmationDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  contractId: string
  /** If true, also triggers contract activation after AB creation */
  activationMode?: boolean
  onActivate?: () => Promise<void>
  onSuccess?: () => void
}

type Step = 'compose' | 'preview' | 'sending'

export function OrderConfirmationDialog({
  open,
  onOpenChange,
  contractId,
  activationMode = false,
  onActivate,
  onSuccess,
}: OrderConfirmationDialogProps) {
  const { t } = useTranslation()
  const [step, setStep] = useState<Step>('compose')
  const [personalMessage, setPersonalMessage] = useState('')
  const [includeInPdf, setIncludeInPdf] = useState(true)
  const [includeInEmail, setIncludeInEmail] = useState(true)
  const [additionalEmails, setAdditionalEmails] = useState('')
  const [previewHtml, setPreviewHtml] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const [previewMutation, { loading: previewing }] = useMutation(PREVIEW_ORDER_CONFIRMATION)
  const [createMutation, { loading: creating }] = useMutation(CREATE_ORDER_CONFIRMATION)
  const [sendMutation, { loading: sending }] = useMutation(SEND_ORDER_CONFIRMATION)

  const loading = previewing || creating || sending

  const parsedEmails = additionalEmails
    .split(/[,;\s]+/)
    .map((e) => e.trim())
    .filter((e) => e.includes('@'))

  const handlePreview = async () => {
    setError(null)
    try {
      const result = await previewMutation({
        variables: {
          contractId,
          personalMessage: personalMessage || undefined,
          includeMessageInPdf: includeInPdf,
        },
      })
      const data = result.data?.previewOrderConfirmationHtml
      if (data?.error) {
        setError(data.error)
      } else if (data?.html) {
        setPreviewHtml(data.html)
        setStep('preview')
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Preview failed')
    }
  }

  const handleSend = async () => {
    setError(null)
    setStep('sending')
    try {
      // If in activation mode, activate first
      if (activationMode && onActivate) {
        await onActivate()
      }

      // Create the AB
      const createResult = await createMutation({
        variables: {
          contractId,
          personalMessage: personalMessage || undefined,
          includeMessageInPdf: includeInPdf,
          includeMessageInEmail: includeInEmail,
          additionalEmails: parsedEmails.length > 0 ? parsedEmails : undefined,
        },
      })
      const createData = createResult.data?.createOrderConfirmation
      if (createData?.error) {
        setError(createData.error)
        setStep('preview')
        return
      }

      // Send the AB
      const abId = createData?.orderConfirmation?.id
      if (abId) {
        const sendResult = await sendMutation({
          variables: { orderConfirmationId: abId },
        })
        const sendData = sendResult.data?.sendOrderConfirmation
        if (sendData?.error) {
          setError(sendData.error)
          setStep('preview')
          return
        }
      }

      onSuccess?.()
      onOpenChange(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Send failed')
      setStep('preview')
    }
  }

  const handleSkip = async () => {
    if (activationMode && onActivate) {
      try {
        await onActivate()
        onSuccess?.()
        onOpenChange(false)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Activation failed')
      }
    } else {
      onOpenChange(false)
    }
  }

  const resetAndClose = (open: boolean) => {
    if (!open) {
      setStep('compose')
      setPersonalMessage('')
      setIncludeInPdf(true)
      setIncludeInEmail(true)
      setAdditionalEmails('')
      setPreviewHtml(null)
      setError(null)
    }
    onOpenChange(open)
  }

  return (
    <Dialog open={open} onOpenChange={resetAndClose}>
      <DialogContent className={step === 'preview' ? 'sm:max-w-4xl' : 'sm:max-w-lg'}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Mail className="h-5 w-5" />
            {t('orderConfirmation.dialog.title')}
          </DialogTitle>
        </DialogHeader>

        {error && (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-600">
            {error}
          </div>
        )}

        {step === 'compose' && (
          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>{t('orderConfirmation.personalMessage')}</Label>
              <Textarea
                value={personalMessage}
                onChange={(e) => setPersonalMessage(e.target.value)}
                placeholder={t('orderConfirmation.personalMessagePlaceholder')}
                rows={3}
              />
              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="include-pdf"
                    checked={includeInPdf}
                    onCheckedChange={(c) => setIncludeInPdf(!!c)}
                  />
                  <Label htmlFor="include-pdf" className="text-sm">
                    {t('orderConfirmation.includeInPdf')}
                  </Label>
                </div>
                <div className="flex items-center gap-2">
                  <Checkbox
                    id="include-email"
                    checked={includeInEmail}
                    onCheckedChange={(c) => setIncludeInEmail(!!c)}
                  />
                  <Label htmlFor="include-email" className="text-sm">
                    {t('orderConfirmation.includeInEmail')}
                  </Label>
                </div>
              </div>
            </div>

            <div className="space-y-2">
              <Label>{t('orderConfirmation.additionalEmails')}</Label>
              <Input
                value={additionalEmails}
                onChange={(e) => setAdditionalEmails(e.target.value)}
                placeholder={t('orderConfirmation.additionalEmailsPlaceholder')}
              />
              <p className="text-xs text-muted-foreground">
                {t('orderConfirmation.additionalEmailsHint')}
              </p>
            </div>
          </div>
        )}

        {step === 'preview' && previewHtml && (
          <div className="py-2">
            <iframe
              srcDoc={previewHtml}
              className="h-[500px] w-full rounded border"
              title="Order Confirmation Preview"
            />
          </div>
        )}

        {step === 'sending' && (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            <span className="ml-3 text-muted-foreground">{t('orderConfirmation.sending')}</span>
          </div>
        )}

        <DialogFooter className="gap-2">
          {step === 'compose' && (
            <>
              {activationMode && (
                <Button variant="outline" onClick={handleSkip} disabled={loading}>
                  {t('orderConfirmation.skipAndActivate')}
                </Button>
              )}
              <Button onClick={handlePreview} disabled={loading}>
                {previewing && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Eye className="mr-2 h-4 w-4" />
                {t('orderConfirmation.preview')}
              </Button>
            </>
          )}
          {step === 'preview' && (
            <>
              <Button variant="outline" onClick={() => setStep('compose')} disabled={loading}>
                {t('orderConfirmation.backToEdit')}
              </Button>
              <Button onClick={handleSend} disabled={loading}>
                {(creating || sending) && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                <Send className="mr-2 h-4 w-4" />
                {activationMode
                  ? t('orderConfirmation.sendAndActivate')
                  : t('orderConfirmation.send')}
              </Button>
            </>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
