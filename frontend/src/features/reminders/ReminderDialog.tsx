import { useState, useEffect, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation } from '@apollo/client'
import { Loader2 } from 'lucide-react'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Label } from '@/components/ui/label'
import { formatCurrency } from '@/lib/utils'
import {
  CREATE_PAYMENT_REMINDER,
  SEND_PAYMENT_REMINDER,
  stageLabelKey,
  type PaymentReminderDraft,
} from './dunning'

interface ReminderDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  /** The InvoiceRecord id to create a reminder for. */
  invoiceRecordId: number | null
  /** Optional starting stage; defaults to the draft's suggested stage. */
  initialStage?: number
  /** Called after a reminder was successfully sent. */
  onSent?: () => void
}

/**
 * Dialog that creates a payment reminder draft, lets the user adjust
 * stage / text / fee+interest toggles and then dispatches the reminder.
 */
export function ReminderDialog({
  open,
  onOpenChange,
  invoiceRecordId,
  initialStage,
  onSent,
}: ReminderDialogProps) {
  const { t } = useTranslation()

  const [draft, setDraft] = useState<PaymentReminderDraft | null>(null)
  const [stage, setStage] = useState<number>(initialStage ?? 0)
  const [title, setTitle] = useState('')
  const [subject, setSubject] = useState('')
  const [bodyText, setBodyText] = useState('')
  const [includeFee, setIncludeFee] = useState(true)
  const [includeInterest, setIncludeInterest] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const [createReminder, { loading: creating }] = useMutation(CREATE_PAYMENT_REMINDER)
  const [sendReminder, { loading: sending }] = useMutation(SEND_PAYMENT_REMINDER)

  const applyDraft = useCallback((d: PaymentReminderDraft) => {
    setDraft(d)
    setStage(d.stage)
    setTitle(d.title)
    setSubject(d.subject)
    setBodyText(d.bodyText)
  }, [])

  // Load draft when the dialog opens.
  useEffect(() => {
    if (!open || invoiceRecordId == null) return
    let cancelled = false
    setError(null)
    setDraft(null)
    createReminder({
      variables: {
        invoiceRecordId,
        stage: initialStage ?? null,
      },
    })
      .then((res) => {
        if (cancelled) return
        const data = res.data?.createPaymentReminder
        if (data?.success && data.draft) {
          applyDraft(data.draft as PaymentReminderDraft)
        } else {
          setError(data?.error || t('reminders.draftFailed'))
        }
      })
      .catch(() => {
        if (!cancelled) setError(t('reminders.draftFailed'))
      })
    return () => {
      cancelled = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, invoiceRecordId])

  // Re-fetch the draft when the stage changes (refreshes fee / interest / text).
  const handleStageChange = async (value: string) => {
    const newStage = parseInt(value, 10)
    setStage(newStage)
    if (invoiceRecordId == null) return
    try {
      const res = await createReminder({
        variables: { invoiceRecordId, stage: newStage },
      })
      const data = res.data?.createPaymentReminder
      if (data?.success && data.draft) {
        applyDraft(data.draft as PaymentReminderDraft)
      }
    } catch {
      // keep previous draft on failure
    }
  }

  const handleSend = async () => {
    if (invoiceRecordId == null || !draft) return
    setError(null)
    try {
      const res = await sendReminder({
        variables: {
          invoiceRecordId,
          stage,
          language: draft.language,
          title,
          subject,
          bodyText,
          includeFee,
          includeInterest,
        },
      })
      const data = res.data?.sendPaymentReminder
      if (data?.success) {
        setToast({ type: 'success', message: t('reminders.sendSuccess') })
        setTimeout(() => setToast(null), 4000)
        onSent?.()
        onOpenChange(false)
      } else {
        setError(data?.error || t('reminders.sendFailed'))
      }
    } catch {
      setError(t('reminders.sendFailed'))
    }
  }

  const busy = creating || sending

  return (
    <>
      {toast && (
        <div
          className={`fixed right-4 top-4 z-[60] rounded-lg px-4 py-3 text-sm font-medium shadow-lg ${
            toast.type === 'success' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
          }`}
        >
          {toast.message}
        </div>
      )}
      <Dialog open={open} onOpenChange={onOpenChange}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto" data-testid="reminder-dialog">
          <DialogHeader>
            <DialogTitle>
              {draft
                ? t('reminders.dialogTitle', { invoice: draft.invoiceNumber })
                : t('reminders.dialogTitleGeneric')}
            </DialogTitle>
            <DialogDescription>{t('reminders.dialogDescription')}</DialogDescription>
          </DialogHeader>

          {creating && !draft ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : error && !draft ? (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-800">{error}</div>
          ) : draft ? (
            <div className="space-y-4 py-2">
              {/* Stage selector */}
              <div className="grid gap-2 sm:grid-cols-2">
                <div>
                  <Label className="mb-1 block text-sm font-medium">{t('reminders.stageLabel')}</Label>
                  <Select value={String(stage)} onValueChange={handleStageChange}>
                    <SelectTrigger data-testid="reminder-stage-select">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {[0, 1, 2, 3].map((s) => (
                        <SelectItem key={s} value={String(s)}>
                          {t(stageLabelKey(s))}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col justify-end">
                  <p className="text-xs text-muted-foreground">
                    {t('reminders.overdueDaysInfo', { days: draft.overdueDays })}
                  </p>
                </div>
              </div>

              {/* Title */}
              <div>
                <Label className="mb-1 block text-sm font-medium">{t('reminders.titleLabel')}</Label>
                <Input
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  data-testid="reminder-title-input"
                />
              </div>

              {/* Subject */}
              <div>
                <Label className="mb-1 block text-sm font-medium">{t('reminders.subjectLabel')}</Label>
                <Input
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  data-testid="reminder-subject-input"
                />
              </div>

              {/* Body */}
              <div>
                <Label className="mb-1 block text-sm font-medium">{t('reminders.bodyLabel')}</Label>
                <Textarea
                  value={bodyText}
                  onChange={(e) => setBodyText(e.target.value)}
                  rows={8}
                  data-testid="reminder-body-input"
                />
              </div>

              {/* Fee + interest toggles */}
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium">{t('reminders.feeLabel')}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatCurrency(draft.feeAmount)}
                    </p>
                  </div>
                  <Switch
                    checked={includeFee}
                    onCheckedChange={setIncludeFee}
                    data-testid="reminder-fee-switch"
                  />
                </div>
                <div className="flex items-center justify-between rounded-lg border p-3">
                  <div>
                    <p className="text-sm font-medium">{t('reminders.interestLabel')}</p>
                    <p className="text-xs text-muted-foreground">
                      {formatCurrency(draft.interestAmount)}
                      {draft.interestDays > 0 && (
                        <>
                          {' · '}
                          {t('reminders.interestDaysInfo', {
                            days: draft.interestDays,
                            rate: Number(draft.interestRate),
                          })}
                        </>
                      )}
                    </p>
                  </div>
                  <Switch
                    checked={includeInterest}
                    onCheckedChange={setIncludeInterest}
                    data-testid="reminder-interest-switch"
                  />
                </div>
              </div>

              {error && (
                <div className="rounded-lg bg-red-50 px-4 py-2 text-sm text-red-800">{error}</div>
              )}
            </div>
          ) : null}

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={busy}>
              {t('common.cancel')}
            </Button>
            <Button
              onClick={handleSend}
              disabled={busy || !draft}
              data-testid="reminder-send-button"
            >
              {sending && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              {t('reminders.sendButton')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  )
}
