import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, gql } from '@apollo/client'
import { X, Loader2 } from 'lucide-react'

const UPDATE_PATTERN = gql`
  mutation UpdatePattern($input: UpdatePatternInput!) {
    updatePattern(input: $input) {
      success
      error
    }
  }
`

interface Pattern {
  id: number
  counterpartyName: string
  averageAmount: number
  frequency: string
  dayOfMonth: number | null
}

interface EditPatternModalProps {
  pattern: Pattern
  onClose: () => void
  onSave: () => void
}

const FREQUENCIES = ['monthly', 'quarterly', 'semi_annual', 'annual', 'irregular']

export function EditPatternModal({ pattern, onClose, onSave }: EditPatternModalProps) {
  const { t } = useTranslation()
  const [amount, setAmount] = useState(Math.abs(pattern.averageAmount).toString())
  const [frequency, setFrequency] = useState(pattern.frequency)
  const [dayOfMonth, setDayOfMonth] = useState(pattern.dayOfMonth?.toString() || '')
  const [error, setError] = useState<string | null>(null)

  const [updatePattern, { loading }] = useMutation(UPDATE_PATTERN)

  const handleSave = async () => {
    setError(null)

    const parsedAmount = parseFloat(amount)
    if (isNaN(parsedAmount) || parsedAmount <= 0) {
      setError(t('liquidity.invalidAmount'))
      return
    }

    const parsedDay = dayOfMonth ? parseInt(dayOfMonth, 10) : null
    if (parsedDay !== null && (parsedDay < 1 || parsedDay > 31)) {
      setError(t('liquidity.invalidDay'))
      return
    }

    // Preserve the sign of the original amount
    const finalAmount = pattern.averageAmount < 0 ? -parsedAmount : parsedAmount

    try {
      const result = await updatePattern({
        variables: {
          input: {
            id: pattern.id,
            amount: finalAmount,
            frequency,
            dayOfMonth: parsedDay,
          },
        },
      })

      if (result.data?.updatePattern?.success) {
        onSave()
      } else {
        setError(result.data?.updatePattern?.error || t('common.error'))
      }
    } catch {
      setError(t('common.error'))
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <div className="flex items-center justify-between">
          <h3 className="text-lg font-medium">{t('liquidity.editPattern')}</h3>
          <button onClick={onClose} className="rounded p-1 hover:bg-gray-100">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('liquidity.counterparty')}
            </label>
            <p className="mt-1 text-sm text-gray-900">{pattern.counterpartyName}</p>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('liquidity.amount')}
            </label>
            <div className="mt-1 flex items-center gap-2">
              <span className="text-gray-500">
                {pattern.averageAmount < 0 ? '-' : '+'}
              </span>
              <input
                type="number"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
                step="0.01"
                min="0"
                className="block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
              />
              <span className="text-gray-500">EUR</span>
            </div>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('liquidity.frequencyLabel')}
            </label>
            <select
              value={frequency}
              onChange={(e) => setFrequency(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            >
              {FREQUENCIES.map((f) => (
                <option key={f} value={f}>
                  {t(`liquidity.frequency.${f}`)}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('liquidity.dayOfMonthLabel')}
            </label>
            <input
              type="number"
              value={dayOfMonth}
              onChange={(e) => setDayOfMonth(e.target.value)}
              min="1"
              max="31"
              placeholder="15"
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {error && <p className="text-sm text-red-600">{error}</p>}
        </div>

        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="rounded-md border px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            {t('common.cancel')}
          </button>
          <button
            onClick={handleSave}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('common.save')}
          </button>
        </div>
      </div>
    </div>
  )
}
