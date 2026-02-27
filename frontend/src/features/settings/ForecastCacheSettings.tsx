import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const FORECAST_CACHE_TTL_QUERY = gql`
  query ForecastCacheTtl {
    forecastCacheTtl
  }
`

const SAVE_FORECAST_CACHE_TTL = gql`
  mutation SaveForecastCacheTtl($minutes: Int!) {
    saveForecastCacheTtl(minutes: $minutes) {
      success
      error
    }
  }
`

export function ForecastCacheSettings() {
  const { t } = useTranslation()
  const [minutes, setMinutes] = useState('60')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data } = useQuery(FORECAST_CACHE_TTL_QUERY)
  const [saveSettings, { loading: saving }] = useMutation(SAVE_FORECAST_CACHE_TTL)

  useEffect(() => {
    if (data?.forecastCacheTtl != null) {
      setMinutes(String(data.forecastCacheTtl))
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    try {
      const { data: result } = await saveSettings({
        variables: { minutes: parseInt(minutes) || 60 },
      })
      if (result?.saveForecastCacheTtl?.success) {
        setMessage({ type: 'success', text: t('settings.forecastCache.saved') })
      } else {
        setMessage({ type: 'error', text: result?.saveForecastCacheTtl?.error || t('settings.forecastCache.saveFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.forecastCache.saveFailed') })
    }
  }

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.forecastCache.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.forecastCache.description')}</p>

      <div className="mt-4 space-y-4">
        <div className="max-w-xs">
          <label className="block text-sm font-medium text-gray-700">{t('settings.forecastCache.ttlLabel')}</label>
          <input
            type="number"
            min="1"
            step="1"
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-500">{t('settings.forecastCache.ttlHint')}</p>
        </div>

        <div className="flex gap-2">
          <button
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('settings.forecastCache.save')}
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
