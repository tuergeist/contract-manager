import { Check } from 'lucide-react'
import { useTranslation } from 'react-i18next'

export type InvoiceDisplayStatus = 'voided' | 'paid' | 'dunning' | 'sent' | 'created'

export function getInvoiceDisplayStatus(status?: string, isPaid?: boolean): InvoiceDisplayStatus {
  if (status === 'voided') return 'voided'
  if (isPaid) return 'paid'
  if (status === 'dunning') return 'dunning'
  if (status === 'sent') return 'sent'
  return 'created'
}

const CONFIG: Record<InvoiceDisplayStatus, { colorSm: string; colorMd: string; translationKey: string }> = {
  voided: {
    colorSm: 'bg-gray-100 text-gray-600',
    colorMd: 'bg-gray-100 text-gray-600',
    translationKey: 'invoices.statusVoided',
  },
  paid: {
    colorSm: 'bg-green-100 text-green-800',
    colorMd: 'bg-green-100 text-green-800',
    translationKey: 'invoices.statusPaid',
  },
  dunning: {
    colorSm: 'bg-orange-100 text-orange-700',
    colorMd: 'bg-orange-100 text-orange-700',
    translationKey: 'invoices.statusDunning',
  },
  sent: {
    colorSm: 'bg-purple-50 text-purple-700',
    colorMd: 'bg-purple-50 text-purple-700',
    translationKey: 'invoices.statusSent',
  },
  created: {
    colorSm: 'bg-gray-50 text-gray-600',
    colorMd: 'bg-gray-100 text-gray-600',
    translationKey: 'invoices.statusFinalized',
  },
}

interface InvoiceStatusBadgeProps {
  status?: string
  isPaid?: boolean
  size?: 'sm' | 'md'
}

export function InvoiceStatusBadge({ status, isPaid, size = 'sm' }: InvoiceStatusBadgeProps) {
  const { t } = useTranslation()
  const displayStatus = getInvoiceDisplayStatus(status, isPaid)
  const config = CONFIG[displayStatus]
  const colorClass = size === 'md' ? config.colorMd : config.colorSm

  if (size === 'md') {
    return (
      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium ${colorClass}`}>
        {t(config.translationKey)}
      </span>
    )
  }

  return (
    <span className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${colorClass} w-fit`}>
      {t(config.translationKey)}
    </span>
  )
}

// Steps in the normal lifecycle
const NORMAL_STEPS: InvoiceDisplayStatus[] = ['created', 'sent', 'paid']

interface InvoiceStatusStepperProps {
  status?: string
  isPaid?: boolean
}

export function InvoiceStatusStepper({ status, isPaid }: InvoiceStatusStepperProps) {
  const { t } = useTranslation()
  const current = getInvoiceDisplayStatus(status, isPaid)

  // Voided and dunning are terminal/branch states — show as standalone badge
  if (current === 'voided' || current === 'dunning') {
    const steps: InvoiceDisplayStatus[] = current === 'dunning'
      ? ['created', 'sent', 'dunning']
      : ['created', 'voided']

    const currentIdx = steps.indexOf(current)

    return (
      <div className="flex items-center gap-1">
        {steps.map((step, i) => {
          const completed = i < currentIdx
          const active = i === currentIdx
          const config = CONFIG[step]

          return (
            <div key={step} className="flex items-center gap-1">
              {i > 0 && (
                <div className={`h-px w-5 ${completed || active ? 'bg-gray-400' : 'bg-gray-200'}`} />
              )}
              <span
                className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium ${
                  active
                    ? config.colorMd
                    : completed
                      ? 'bg-gray-100 text-gray-500'
                      : 'bg-gray-50 text-gray-300'
                }`}
              >
                {completed && <Check className="h-3.5 w-3.5" />}
                {t(config.translationKey)}
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  // Normal path: Created → Sent → Paid
  const currentIdx = NORMAL_STEPS.indexOf(current)

  return (
    <div className="flex items-center gap-1">
      {NORMAL_STEPS.map((step, i) => {
        const completed = i < currentIdx
        const active = i === currentIdx
        const config = CONFIG[step]

        return (
          <div key={step} className="flex items-center gap-1">
            {i > 0 && (
              <div className={`h-px w-5 ${completed || active ? 'bg-gray-400' : 'bg-gray-200'}`} />
            )}
            <span
              className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-sm font-medium ${
                active
                  ? config.colorMd
                  : completed
                    ? 'bg-gray-100 text-gray-500'
                    : 'bg-gray-50 text-gray-300'
              }`}
            >
              {completed && <Check className="h-3.5 w-3.5" />}
              {t(config.translationKey)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
