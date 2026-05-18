import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const PS_HOURLY_RATE_QUERY = gql`
  query PsHourlyRate {
    psHourlyRate
  }
`

const SAVE_PS_HOURLY_RATE = gql`
  mutation SavePsHourlyRate($rate: Float!) {
    savePsHourlyRate(rate: $rate) {
      success
      error
    }
  }
`

export function ProjectRateSettings() {
  const { t } = useTranslation()
  const [rate, setRate] = useState('160')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data } = useQuery(PS_HOURLY_RATE_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_PS_HOURLY_RATE)

  useEffect(() => {
    if (data?.psHourlyRate != null) {
      setRate(String(data.psHourlyRate))
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    try {
      const { data: result } = await saveSettings({
        variables: { rate: parseFloat(rate) || 0 },
      })
      if (result?.savePsHourlyRate?.success) {
        setMessage({ type: 'success', text: t('settings.psRate.saved') })
      } else {
        setMessage({ type: 'error', text: result?.savePsHourlyRate?.error || t('settings.psRate.saveFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.psRate.saveFailed') })
    }
  }

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.psRate.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.psRate.description')}</p>

      <div className="mt-4 space-y-4">
        <div className="max-w-xs">
          <label className="block text-sm font-medium text-gray-700">{t('settings.psRate.rateLabel')}</label>
          <input
            type="number"
            min="0"
            step="1"
            value={rate}
            onChange={(e) => setRate(e.target.value)}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-500">{t('settings.psRate.rateHint')}</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('settings.psRate.save')}
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
