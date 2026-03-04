import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2 } from 'lucide-react'

const AB_EMAIL_TEMPLATES_QUERY = gql`
  query ABEmailTemplates {
    abEmailTemplates {
      success
      error
      templates {
        language
        subject
        body
        isCustom
      }
    }
  }
`

const SET_AB_EMAIL_TEMPLATE = gql`
  mutation SetABEmailTemplate($input: SetABEmailTemplateInput!) {
    setAbEmailTemplate(input: $input) {
      success
      error
    }
  }
`

const AB_EMAIL_PLACEHOLDERS = [
  { key: '{order_confirmation_number}', label: 'Order Confirmation Number' },
  { key: '{customer_name}', label: 'Customer Name' },
  { key: '{contract_reference}', label: 'Contract Reference' },
  { key: '{personal_message}', label: 'Personal Message' },
  { key: '{company_name}', label: 'Company Name' },
]

const SAMPLE_DATA: Record<string, string> = {
  order_confirmation_number: 'AB-2026-001',
  customer_name: 'Acme Corp',
  contract_reference: 'Contract #12345',
  personal_message: 'Thank you for your order!',
  company_name: 'My Company GmbH',
}

function renderPreview(template: string): string {
  try {
    return template.replace(/\{(\w+)\}/g, (match, key) => SAMPLE_DATA[key] ?? match)
  } catch {
    return template
  }
}

interface ABEmailTemplateSettingsProps {
  showHeader?: boolean
}

export function ABEmailTemplateSettings({ showHeader = true }: ABEmailTemplateSettingsProps) {
  const { t } = useTranslation()
  const [lang, setLang] = useState<'de' | 'en'>('de')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('')
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, refetch } = useQuery(AB_EMAIL_TEMPLATES_QUERY)
  const [setEmailTemplate, { loading: saving }] = useMutation(SET_AB_EMAIL_TEMPLATE)

  useEffect(() => {
    const templates = data?.abEmailTemplates?.templates
    if (templates) {
      const tpl = templates.find((t: { language: string }) => t.language === lang)
      if (tpl) {
        setSubject(tpl.subject)
        setBody(tpl.body)
      }
    }
  }, [data, lang])

  const handleSave = async () => {
    setMessage(null)
    try {
      const result = await setEmailTemplate({
        variables: { input: { language: lang, subject, body } },
      })
      if (result.data?.setAbEmailTemplate?.success) {
        setMessage({ type: 'success', text: t('orderConfirmation.emailTemplate.saved') })
        refetch()
      } else {
        setMessage({ type: 'error', text: result.data?.setAbEmailTemplate?.error || t('orderConfirmation.emailTemplate.saveFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('orderConfirmation.emailTemplate.saveFailed') })
    }
  }

  const handleReset = async () => {
    setMessage(null)
    try {
      const result = await setEmailTemplate({
        variables: { input: { language: lang, subject: '', body: '' } },
      })
      if (result.data?.setAbEmailTemplate?.success) {
        setMessage({ type: 'success', text: t('orderConfirmation.emailTemplate.saved') })
        refetch()
      } else {
        setMessage({ type: 'error', text: result.data?.setAbEmailTemplate?.error || t('orderConfirmation.emailTemplate.saveFailed') })
      }
    } catch {
      setMessage({ type: 'error', text: t('orderConfirmation.emailTemplate.saveFailed') })
    }
  }

  return (
    <div className="space-y-6">
      {showHeader && (
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{t('orderConfirmation.emailTemplate.title')}</h1>
        </div>
      )}

      <div className="space-y-6">
        <section className="rounded-lg border bg-white p-6 space-y-4">
          {/* Language Tabs */}
          <div className="flex gap-1 border-b">
            {(['de', 'en'] as const).map((l) => {
              const tpl = data?.abEmailTemplates?.templates?.find(
                (t: { language: string }) => t.language === l
              )
              return (
                <button
                  key={l}
                  onClick={() => setLang(l)}
                  className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                    lang === l
                      ? 'border-blue-600 text-blue-600'
                      : 'border-transparent text-gray-500 hover:text-gray-700'
                  }`}
                >
                  {l.toUpperCase()}
                  {tpl?.isCustom && <span className="ml-1 text-xs text-blue-500">*</span>}
                </button>
              )
            })}
          </div>

          {/* Subject */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('orderConfirmation.emailTemplate.subject')}
            </label>
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Body */}
          <div>
            <label className="block text-sm font-medium text-gray-700">
              {t('orderConfirmation.emailTemplate.body')}
            </label>
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={8}
              className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
            />
          </div>

          {/* Placeholders */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('orderConfirmation.emailTemplate.placeholders')}
            </label>
            <div className="flex flex-wrap gap-1.5">
              {AB_EMAIL_PLACEHOLDERS.map((p) => (
                <span
                  key={p.key}
                  className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-700 cursor-pointer hover:bg-gray-200"
                  title={p.label}
                  onClick={() => setBody(prev => prev + p.key)}
                >
                  {p.key}
                </span>
              ))}
            </div>
          </div>

          {/* Preview */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              {t('settings.emailTemplate.preview')}
            </label>
            <div className="rounded-md border bg-gray-50 p-4">
              <div className="text-sm font-medium text-gray-900 mb-2">
                {renderPreview(subject)}
              </div>
              <div
                className="text-sm text-gray-700 prose prose-sm max-w-none"
                dangerouslySetInnerHTML={{ __html: renderPreview(body) }}
              />
            </div>
          </div>

          {/* Actions */}
          <div className="flex gap-2">
            <button
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('common.save')}
            </button>
            <button
              onClick={handleReset}
              disabled={saving}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              {t('settings.emailTemplate.resetToDefault')}
            </button>
          </div>

          {message && (
            <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
              {message.text}
            </p>
          )}
        </section>
      </div>
    </div>
  )
}
