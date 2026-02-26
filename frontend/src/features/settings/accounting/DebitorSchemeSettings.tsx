import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const DEBITOR_SCHEME_QUERY = gql`
  query DebitorAccountScheme {
    debitorAccountScheme {
      prefix
      startNumber
      nextNumber
      endNumber
    }
  }
`

const UPDATE_DEBITOR_SCHEME = gql`
  mutation UpdateDebitorAccountScheme($input: DebitorAccountSchemeInput!) {
    updateDebitorAccountScheme(input: $input) {
      prefix
      startNumber
      nextNumber
      endNumber
    }
  }
`

export function DebitorSchemeSettings() {
  const { t } = useTranslation()
  const [prefix, setPrefix] = useState('')
  const [startNumber, setStartNumber] = useState('10000')
  const [nextNumber, setNextNumber] = useState('10001')
  const [endNumber, setEndNumber] = useState('69999')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, loading } = useQuery(DEBITOR_SCHEME_QUERY)
  const [updateScheme, { loading: saving }] = useMutation(UPDATE_DEBITOR_SCHEME)

  useEffect(() => {
    const scheme = data?.debitorAccountScheme
    if (scheme) {
      setPrefix(scheme.prefix || '')
      setStartNumber(String(scheme.startNumber))
      setNextNumber(String(scheme.nextNumber))
      setEndNumber(String(scheme.endNumber))
    }
  }, [data])

  const handleSave = async () => {
    setMessage(null)
    try {
      await updateScheme({
        variables: {
          input: {
            prefix,
            startNumber: parseInt(startNumber),
            nextNumber: parseInt(nextNumber),
            endNumber: parseInt(endNumber),
          },
        },
      })
      setMessage({ type: 'success', text: t('accounting.debitors.saved') })
    } catch {
      setMessage({ type: 'error', text: t('accounting.debitors.saveFailed') })
    }
  }

  const inputClass = 'mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500'

  if (loading) {
    return <div className="flex items-center gap-2 p-6 text-gray-500"><Loader2 className="h-4 w-4 animate-spin" />{t('common.loading')}</div>
  }

  return (
    <div className="rounded-lg border bg-white p-6">
      <h2 className="text-lg font-medium">{t('accounting.debitors.title')}</h2>
      <p className="mt-1 text-sm text-gray-500">{t('accounting.debitors.description')}</p>

      <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('accounting.debitors.prefix')}</label>
          <input
            type="text"
            value={prefix}
            onChange={(e) => setPrefix(e.target.value)}
            className={inputClass}
            placeholder={t('accounting.debitors.prefixPlaceholder')}
          />
          <p className="mt-1 text-xs text-gray-500">{t('accounting.debitors.prefixHint')}</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('accounting.debitors.startNumber')}</label>
          <input
            type="number"
            value={startNumber}
            onChange={(e) => setStartNumber(e.target.value)}
            className={inputClass}
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('accounting.debitors.nextNumber')}</label>
          <input
            type="number"
            value={nextNumber}
            onChange={(e) => setNextNumber(e.target.value)}
            className={inputClass}
          />
          <p className="mt-1 text-xs text-gray-500">{t('accounting.debitors.nextNumberHint')}</p>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700">{t('accounting.debitors.endNumber')}</label>
          <input
            type="number"
            value={endNumber}
            onChange={(e) => setEndNumber(e.target.value)}
            className={inputClass}
          />
        </div>
      </div>

      <div className="mt-4 rounded-md border border-gray-200 bg-gray-50 p-3">
        <p className="text-xs text-gray-600">{t('accounting.debitors.schemeHint')}</p>
      </div>

      <div className="mt-4 flex gap-2">
        <button
          onClick={handleSave}
          disabled={saving}
          className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {saving && <Loader2 className="h-4 w-4 animate-spin" />}
          {t('common.save')}
        </button>
      </div>

      {message && (
        <p className={`mt-3 text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
          {message.text}
        </p>
      )}
    </div>
  )
}
