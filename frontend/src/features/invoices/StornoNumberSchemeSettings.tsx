import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Hash } from 'lucide-react'

const STORNO_NUMBER_SCHEME_QUERY = gql`
  query StornoNumberScheme {
    stornoNumberScheme {
      pattern
      nextCounter
      resetPeriod
      preview
    }
  }
`

const SAVE_STORNO_NUMBER_SCHEME = gql`
  mutation SaveStornoNumberScheme($input: InvoiceNumberSchemeInput!) {
    saveStornoNumberScheme(input: $input) {
      success
      error
      data {
        pattern
        nextCounter
        resetPeriod
        preview
      }
    }
  }
`

interface StornoNumberSchemeSettingsProps {
  showHeader?: boolean
}

export function StornoNumberSchemeSettings({ showHeader = true }: StornoNumberSchemeSettingsProps) {
  const { t } = useTranslation()
  const [pattern, setPattern] = useState('S-{YYYY}-{NNNN}')
  const [resetPeriod, setResetPeriod] = useState('yearly')
  const [nextCounter, setNextCounter] = useState<number | ''>('')
  const [preview, setPreview] = useState('')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const { data, loading } = useQuery(STORNO_NUMBER_SCHEME_QUERY)
  const [save, { loading: saving }] = useMutation(SAVE_STORNO_NUMBER_SCHEME)

  useEffect(() => {
    if (data?.stornoNumberScheme) {
      const s = data.stornoNumberScheme
      setPattern(s.pattern)
      setResetPeriod(s.resetPeriod)
      setNextCounter(s.nextCounter)
      setPreview(s.preview)
    }
  }, [data])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const variables: Record<string, unknown> = {
        input: {
          pattern,
          resetPeriod,
          ...(nextCounter !== '' ? { nextCounter: Number(nextCounter) } : {}),
        },
      }
      const { data: result } = await save({
        variables,
        refetchQueries: ['StornoNumberScheme'],
      })
      if (result?.saveStornoNumberScheme?.success) {
        setPreview(result.saveStornoNumberScheme.data.preview)
        setToast({ type: 'success', message: t('invoices.stornoNumberScheme.saved') })
      } else {
        setToast({ type: 'error', message: result?.saveStornoNumberScheme?.error || t('invoices.stornoNumberScheme.saveFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('invoices.stornoNumberScheme.saveFailed') })
    }
    setTimeout(() => setToast(null), 3000)
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const inputClass = "w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
  const labelClass = "block text-sm font-medium text-gray-700 mb-1"

  return (
    <div className="space-y-6">
      {showHeader && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Hash className="h-6 w-6 text-gray-600" />
            <h1 className="text-2xl font-bold text-gray-900">{t('invoices.stornoNumberScheme.title')}</h1>
          </div>
          <p className="text-sm text-gray-500">{t('invoices.stornoNumberScheme.description')}</p>
        </div>
      )}

      {toast && (
        <div className={`mb-4 rounded-lg px-4 py-3 text-sm ${toast.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {toast.message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-6">
        <section className="rounded-lg border bg-white p-6 space-y-5">
          <div>
            <label className={labelClass}>{t('invoices.numberScheme.pattern')}</label>
            <input
              className={`${inputClass} font-mono`}
              value={pattern}
              onChange={e => setPattern(e.target.value)}
              placeholder="e.g. S-{YYYY}-{NNNN}"
            />
            <p className="mt-1 text-xs text-gray-500">{t('invoices.numberScheme.patternHelp')}</p>
          </div>

          <div>
            <label className={labelClass}>{t('invoices.numberScheme.resetPeriod')}</label>
            <select className={inputClass} value={resetPeriod} onChange={e => setResetPeriod(e.target.value)}>
              <option value="yearly">{t('invoices.numberScheme.resetYearly')}</option>
              <option value="monthly">{t('invoices.numberScheme.resetMonthly')}</option>
              <option value="never">{t('invoices.numberScheme.resetNever')}</option>
            </select>
          </div>

          <div>
            <label className={labelClass}>{t('invoices.numberScheme.nextCounter')}</label>
            <input
              className={inputClass}
              type="number"
              min="1"
              value={nextCounter}
              onChange={e => setNextCounter(e.target.value ? Number(e.target.value) : '')}
            />
            <p className="mt-1 text-xs text-gray-500">{t('invoices.numberScheme.nextCounterHint')}</p>
          </div>

          {preview && (
            <div className="rounded-lg bg-gray-50 p-4">
              <p className="text-sm text-gray-600">{t('invoices.stornoNumberScheme.nextNumber')}</p>
              <p className="mt-1 text-lg font-mono font-bold text-gray-900">{preview}</p>
            </div>
          )}
        </section>

        <div className="flex justify-end">
          <button type="submit" disabled={saving} className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50">
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('common.save')}
          </button>
        </div>
      </form>
    </div>
  )
}
