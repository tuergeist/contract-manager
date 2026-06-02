import { useTranslation } from 'react-i18next'
import { Link } from 'react-router-dom'
import { FileText } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { formatDateTime } from '@/lib/utils'
import { stageLabelKey, type PaymentReminder } from './dunning'

interface PaymentReminderListProps {
  reminders: PaymentReminder[]
  /** When true, shows the invoice number / link for each reminder. */
  showInvoice?: boolean
}

/**
 * Renders a list of sent payment reminders. Used in the invoice detail
 * history as well as the customer / contract reminder sections.
 */
export function PaymentReminderList({ reminders, showInvoice = false }: PaymentReminderListProps) {
  const { t } = useTranslation()

  if (reminders.length === 0) {
    return (
      <div className="py-4 text-center text-sm text-muted-foreground" data-testid="reminder-list-empty">
        {t('reminders.noReminders')}
      </div>
    )
  }

  const sorted = [...reminders].sort((a, b) => {
    const da = a.sentAt || a.createdAt || ''
    const db = b.sentAt || b.createdAt || ''
    return db.localeCompare(da)
  })

  return (
    <div className="space-y-3" data-testid="reminder-list">
      {sorted.map((reminder) => (
        <div
          key={reminder.id}
          className="rounded border p-3 text-sm"
          data-testid={`reminder-row-${reminder.id}`}
        >
          <div className="flex items-center justify-between gap-2">
            <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200">
              {t(stageLabelKey(reminder.stage))}
            </Badge>
            <span className="text-xs text-muted-foreground" data-testid={`reminder-sent-at-${reminder.id}`}>
              {reminder.sentAt ? formatDateTime(reminder.sentAt) : t('reminders.notSent')}
            </span>
          </div>
          {showInvoice && (
            <div className="mt-1 text-xs text-muted-foreground">
              {t('reminders.forInvoice')}:{' '}
              <Link
                to={`/invoices/${reminder.invoiceRecordId}`}
                className="text-blue-600 hover:underline"
              >
                {reminder.invoiceNumber}
              </Link>
            </div>
          )}
          <div className="mt-1 font-medium">{reminder.title}</div>
          {reminder.pdfUrl && (
            <a
              href={reminder.pdfUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-flex items-center gap-1 text-xs text-blue-600 hover:underline"
              data-testid={`reminder-pdf-${reminder.id}`}
            >
              <FileText className="h-3 w-3" />
              {t('reminders.viewPdf')}
            </a>
          )}
        </div>
      ))}
    </div>
  )
}
