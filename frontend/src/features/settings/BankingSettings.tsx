import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const BANKING_SETTINGS_QUERY = gql`
  query BankingSettings {
    bankingSettings {
      feeToleranceFixed
      feeTolerancePercent
      partialMatchThreshold
    }
  }
`

const SAVE_BANKING_SETTINGS = gql`
  mutation SaveBankingSettings(
    $feeToleranceFixed: Decimal!
    $feeTolerancePercent: Decimal!
    $partialMatchThreshold: Decimal
  ) {
    saveBankingSettings(
      feeToleranceFixed: $feeToleranceFixed
      feeTolerancePercent: $feeTolerancePercent
      partialMatchThreshold: $partialMatchThreshold
    ) {
      success
      error
    }
  }
`

export function BankingSettings() {
  const { t } = useTranslation()
  const [feeToleranceFixed, setFeeToleranceFixed] = useState('0')
  const [feeTolerancePercent, setFeeTolerancePercent] = useState('0')
  const [partialMatchThreshold, setPartialMatchThreshold] = useState('200')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data } = useQuery(BANKING_SETTINGS_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_BANKING_SETTINGS)

  useEffect(() => {
    const settings = data?.bankingSettings
    if (settings) {
      setFeeToleranceFixed(settings.feeToleranceFixed || '0')
      setFeeTolerancePercent(settings.feeTolerancePercent || '0')
      setPartialMatchThreshold(settings.partialMatchThreshold || '200')
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    try {
      const { data: result } = await saveSettings({
        variables: {
          feeToleranceFixed,
          feeTolerancePercent,
          partialMatchThreshold,
        },
      })
      if (result?.saveBankingSettings?.success) {
        setMessage({ type: 'success', text: t('settings.banking.saved') })
      } else {
        setMessage({ type: 'error', text: result?.saveBankingSettings?.error || t('settings.banking.saveFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.banking.saveFailed') })
    }
  }

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.banking.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.banking.description')}</p>

      <div className="mt-4 space-y-4">
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.banking.feeToleranceFixed')}</label>
            <input
              type="number"
              min="0"
              step="0.01"
              value={feeToleranceFixed}
              onChange={(e) => setFeeToleranceFixed(e.target.value)}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-gray-500">{t('settings.banking.feeToleranceFixedHint')}</p>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">{t('settings.banking.feeTolerancePercent')}</label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={feeTolerancePercent}
              onChange={(e) => setFeeTolerancePercent(e.target.value)}
              className={inputClass}
            />
            <p className="mt-1 text-xs text-gray-500">{t('settings.banking.feeTolerancePercentHint')}</p>
          </div>
        </div>

        <p className="text-xs text-gray-500 italic">
          {t('settings.banking.formulaHint')}
        </p>

        <div className="max-w-sm border-t pt-4">
          <label className="block text-sm font-medium text-gray-700">
            {t('settings.banking.partialMatchThreshold', { defaultValue: 'Partial-Match-Schwelle (EUR)' })}
          </label>
          <input
            type="number"
            min="0"
            step="1"
            value={partialMatchThreshold}
            onChange={(e) => setPartialMatchThreshold(e.target.value)}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-500">
            {t('settings.banking.partialMatchThresholdHint', {
              defaultValue:
                'Transaktionen mit nicht zugeordnetem Restbetrag über dieser Schwelle werden in der Banking-Liste markiert. Default: 200 EUR.',
            })}
          </p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('settings.banking.save')}
          </button>
        </div>

        {message && (
          <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {message.text}
          </p>
        )}
      </div>
    </div>
  )
}
