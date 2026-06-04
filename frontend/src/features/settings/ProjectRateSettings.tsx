import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const PS_RATE_AND_THRESHOLDS_QUERY = gql`
  query PsRateAndThresholds {
    psHourlyRate
    psRatioThresholds {
      amberMin
      yellowMin
      greenMin
    }
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

const SAVE_PS_RATIO_THRESHOLDS = gql`
  mutation SavePsRatioThresholds($amberMin: Float!, $yellowMin: Float!, $greenMin: Float!) {
    savePsRatioThresholds(amberMin: $amberMin, yellowMin: $yellowMin, greenMin: $greenMin) {
      success
      error
    }
  }
`

export function ProjectRateSettings() {
  const { t } = useTranslation()
  const [rate, setRate] = useState('160')
  const [amberMin, setAmberMin] = useState('1.0')
  const [yellowMin, setYellowMin] = useState('1.5')
  const [greenMin, setGreenMin] = useState('2.0')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, refetch } = useQuery(PS_RATE_AND_THRESHOLDS_QUERY)
  const [saveRate, { loading: savingRate }] = useMutation(SAVE_PS_HOURLY_RATE)
  const [saveThresholds, { loading: savingThresholds }] = useMutation(SAVE_PS_RATIO_THRESHOLDS)
  const saving = savingRate || savingThresholds

  useEffect(() => {
    if (data?.psHourlyRate != null) {
      setRate(String(data.psHourlyRate))
    }
    if (data?.psRatioThresholds) {
      setAmberMin(String(data.psRatioThresholds.amberMin))
      setYellowMin(String(data.psRatioThresholds.yellowMin))
      setGreenMin(String(data.psRatioThresholds.greenMin))
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    const rateNum = parseFloat(rate) || 0
    const amberNum = parseFloat(amberMin)
    const yellowNum = parseFloat(yellowMin)
    const greenNum = parseFloat(greenMin)

    if (Number.isNaN(amberNum) || Number.isNaN(yellowNum) || Number.isNaN(greenNum)) {
      setMessage({ type: 'error', text: t('settings.psRate.invalidThresholds') })
      return
    }
    if (!(amberNum < yellowNum && yellowNum < greenNum)) {
      setMessage({ type: 'error', text: t('settings.psRate.thresholdsNotIncreasing') })
      return
    }

    try {
      const [rateResult, thresholdResult] = await Promise.all([
        saveRate({ variables: { rate: rateNum } }),
        saveThresholds({
          variables: {
            amberMin: amberNum,
            yellowMin: yellowNum,
            greenMin: greenNum,
          },
        }),
      ])
      const rateOk = rateResult.data?.savePsHourlyRate?.success
      const thresholdsOk = thresholdResult.data?.savePsRatioThresholds?.success
      if (rateOk && thresholdsOk) {
        setMessage({ type: 'success', text: t('settings.psRate.saved') })
        refetch()
      } else {
        const err =
          rateResult.data?.savePsHourlyRate?.error ||
          thresholdResult.data?.savePsRatioThresholds?.error ||
          t('settings.psRate.saveFailed')
        setMessage({ type: 'error', text: err })
      }
    } catch {
      setMessage({ type: 'error', text: t('settings.psRate.saveFailed') })
    }
  }

  const inputClass =
    'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('settings.psRate.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('settings.psRate.description')}</p>

      <div className="mt-4 space-y-6">
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

        <div>
          <h3 className="text-sm font-medium text-gray-900">{t('settings.psRate.thresholdsTitle')}</h3>
          <p className="mt-1 text-xs text-gray-500">{t('settings.psRate.thresholdsDescription')}</p>
          <div className="mt-3 grid max-w-2xl grid-cols-1 gap-4 md:grid-cols-3">
            <div>
              <label className="block text-sm font-medium text-amber-700">
                {t('settings.psRate.amberMin')}
              </label>
              <input
                type="number"
                min="0"
                step="0.1"
                value={amberMin}
                onChange={(e) => setAmberMin(e.target.value)}
                className={inputClass}
                data-testid="ps-amber-min"
              />
              <p className="mt-1 text-xs text-gray-500">{t('settings.psRate.amberHint')}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-yellow-700">
                {t('settings.psRate.yellowMin')}
              </label>
              <input
                type="number"
                min="0"
                step="0.1"
                value={yellowMin}
                onChange={(e) => setYellowMin(e.target.value)}
                className={inputClass}
                data-testid="ps-yellow-min"
              />
              <p className="mt-1 text-xs text-gray-500">{t('settings.psRate.yellowHint')}</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-green-700">
                {t('settings.psRate.greenMin')}
              </label>
              <input
                type="number"
                min="0"
                step="0.1"
                value={greenMin}
                onChange={(e) => setGreenMin(e.target.value)}
                className={inputClass}
                data-testid="ps-green-min"
              />
              <p className="mt-1 text-xs text-gray-500">{t('settings.psRate.greenHint')}</p>
            </div>
          </div>
          <p className="mt-2 text-xs text-gray-500">
            {t('settings.psRate.thresholdsLegend', {
              amber: amberMin,
              yellow: yellowMin,
              green: greenMin,
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
