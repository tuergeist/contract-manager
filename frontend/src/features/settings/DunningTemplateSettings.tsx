import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useMutation, useQuery } from '@apollo/client'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import {
  DUNNING_SETTINGS_QUERY,
  SAVE_DUNNING_SETTINGS,
  stageLabelKey,
  type DunningSettings,
  type DunningTemplateStage,
  type DunningTemplates,
} from '@/features/reminders/dunning'

type Language = 'de' | 'en'
const LANGUAGES: Language[] = ['de', 'en']
const STAGES = [0, 1, 2, 3]

const EMPTY_STAGE: DunningTemplateStage = { title: '', subject: '', body: '' }

// Same placeholders the backend uses in
// apps/invoices/dunning.py :: build_reminder_draft. Keep these in sync.
const DUNNING_PLACEHOLDERS = [
  '{invoice_number}',
  '{invoice_date}',
  '{due_date}',
  '{overdue_days}',
  '{amount}',
]

const SAMPLE_DATA: Record<string, string> = {
  invoice_number: 'INV-2026-001',
  invoice_date: '15.01.2026',
  due_date: '29.01.2026',
  overdue_days: '30',
  amount: '1190.00',
}

function renderPreview(template: string): string {
  try {
    return template.replace(/\{(\w+)\}/g, (match, key) => SAMPLE_DATA[key] ?? match)
  } catch {
    return template
  }
}

function buildTemplateState(settings: DunningSettings | null): Record<Language, Record<string, DunningTemplateStage>> {
  const result: Record<Language, Record<string, DunningTemplateStage>> = { de: {}, en: {} }
  for (const lang of LANGUAGES) {
    for (const stage of STAGES) {
      const src = settings?.templates?.[lang]?.[String(stage)]
      result[lang][String(stage)] = {
        title: src?.title ?? '',
        subject: src?.subject ?? '',
        body: src?.body ?? '',
      }
    }
  }
  return result
}

interface DunningTemplateSettingsProps {
  showHeader?: boolean
}

/**
 * Dunning email template editor.
 *
 * Mirrors EmailTemplateSettings (clickable placeholders + preview),
 * adds a per-stage editor (0–3) on top of the per-language selector,
 * and uses the same saveDunningSettings mutation — the non-template
 * fields are passed through unchanged so we don't clobber them.
 */
export function DunningTemplateSettings({ showHeader = true }: DunningTemplateSettingsProps) {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const canEdit = hasPermission('reminders', 'settings')

  const [lang, setLang] = useState<Language>('de')
  const [stage, setStage] = useState<number>(0)
  const [templates, setTemplates] = useState<Record<Language, Record<string, DunningTemplateStage>>>(
    () => buildTemplateState(null),
  )
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null)

  const { data, loading, refetch } = useQuery<{ dunningSettings: DunningSettings | null }>(
    DUNNING_SETTINGS_QUERY,
  )
  const [save, { loading: saving }] = useMutation(SAVE_DUNNING_SETTINGS)

  useEffect(() => {
    if (data?.dunningSettings) {
      setTemplates(buildTemplateState(data.dunningSettings))
    }
  }, [data])

  const current = templates[lang][String(stage)] ?? EMPTY_STAGE
  const settings = data?.dunningSettings ?? null

  const updateField = (field: keyof DunningTemplateStage, value: string) => {
    setTemplates((prev) => ({
      ...prev,
      [lang]: {
        ...prev[lang],
        [String(stage)]: {
          ...(prev[lang][String(stage)] ?? EMPTY_STAGE),
          [field]: value,
        },
      },
    }))
  }

  const appendPlaceholder = (placeholder: string) => {
    updateField('body', current.body + placeholder)
  }

  const handleSave = async (templatesToSend?: DunningTemplates) => {
    if (!settings) return
    setMessage(null)
    try {
      const result = await save({
        variables: {
          input: {
            defaultPaymentTermDays: settings.defaultPaymentTermDays,
            overdueRedThresholdDays: settings.overdueRedThresholdDays,
            mahnfaehigThresholdDays: settings.mahnfaehigThresholdDays,
            interestRate: settings.interestRate,
            defaultFeePerStage: settings.defaultFeePerStage,
            templates: templatesToSend ?? templates,
          },
        },
        refetchQueries: ['DunningSettings'],
      })
      if (result.data?.saveDunningSettings?.success) {
        setMessage({ type: 'success', text: t('reminders.settings.saved') })
        refetch()
      } else {
        setMessage({
          type: 'error',
          text: result.data?.saveDunningSettings?.error || t('reminders.settings.saveFailed'),
        })
      }
    } catch {
      setMessage({ type: 'error', text: t('reminders.settings.saveFailed') })
    }
  }

  const handleReset = async () => {
    // Resetting means dropping the current language/stage entry so the
    // backend falls back to the built-in default template.
    const reset = {
      ...templates,
      [lang]: {
        ...templates[lang],
        [String(stage)]: { title: '', subject: '', body: '' },
      },
    }
    setTemplates(reset)
    await handleSave(reset)
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  return (
    <div className="space-y-6" data-testid="dunning-template-settings">
      {showHeader && (
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">{t('reminders.templates.title')}</h1>
          <p className="mt-1 text-sm text-gray-500">{t('reminders.templates.description')}</p>
        </div>
      )}

      <section className="rounded-lg border bg-white p-6 space-y-4">
        {/* Language tabs */}
        <div className="flex gap-1 border-b">
          {LANGUAGES.map((l) => (
            <button
              key={l}
              onClick={() => setLang(l)}
              className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                lang === l
                  ? 'border-blue-600 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700'
              }`}
              data-testid={`dunning-template-lang-${l}`}
            >
              {l.toUpperCase()}
            </button>
          ))}
        </div>

        {/* Stage selector */}
        <div className="inline-flex rounded-md border border-input">
          {STAGES.map((s) => (
            <button
              key={s}
              type="button"
              onClick={() => setStage(s)}
              className={`px-3 py-1.5 text-sm font-medium transition-colors first:rounded-l-md last:rounded-r-md ${
                stage === s
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-background text-muted-foreground hover:bg-muted'
              }`}
              data-testid={`dunning-template-stage-${s}`}
            >
              {t(stageLabelKey(s))}
            </button>
          ))}
        </div>

        {/* Title */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('reminders.settings.templateTitle')}
          </label>
          <input
            type="text"
            value={current.title}
            onChange={(e) => updateField('title', e.target.value)}
            disabled={!canEdit}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
            data-testid="dunning-template-title-input"
          />
        </div>

        {/* Subject */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('reminders.settings.templateSubject')}
          </label>
          <input
            type="text"
            value={current.subject}
            onChange={(e) => updateField('subject', e.target.value)}
            disabled={!canEdit}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
            data-testid="dunning-template-subject-input"
          />
        </div>

        {/* Body */}
        <div>
          <label className="block text-sm font-medium text-gray-700">
            {t('reminders.settings.templateBody')}
          </label>
          <textarea
            value={current.body}
            onChange={(e) => updateField('body', e.target.value)}
            rows={10}
            disabled={!canEdit}
            className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 text-sm font-mono shadow-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50"
            data-testid="dunning-template-body-input"
          />
        </div>

        {/* Placeholders */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('settings.emailTemplate.placeholders')}
          </label>
          <div className="flex flex-wrap gap-1.5">
            {DUNNING_PLACEHOLDERS.map((p) => (
              <span
                key={p}
                className="inline-flex items-center rounded bg-gray-100 px-2 py-0.5 text-xs font-mono text-gray-700 cursor-pointer hover:bg-gray-200"
                onClick={() => canEdit && appendPlaceholder(p)}
              >
                {p}
              </span>
            ))}
          </div>
        </div>

        {/* Preview */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            {t('settings.emailTemplate.preview')}
          </label>
          <div className="rounded-md border bg-gray-50 p-4 space-y-2">
            <div className="text-xs uppercase tracking-wide text-gray-500">
              {t('reminders.settings.templateTitle')}
            </div>
            <div className="text-sm font-semibold text-gray-900">
              {renderPreview(current.title)}
            </div>
            <div className="text-xs uppercase tracking-wide text-gray-500 pt-2">
              {t('reminders.settings.templateSubject')}
            </div>
            <div className="text-sm font-medium text-gray-900">
              {renderPreview(current.subject)}
            </div>
            <div className="text-xs uppercase tracking-wide text-gray-500 pt-2">
              {t('reminders.settings.templateBody')}
            </div>
            <div className="text-sm whitespace-pre-line text-gray-700">
              {renderPreview(current.body)}
            </div>
          </div>
        </div>

        {/* Actions */}
        {canEdit && (
          <div className="flex gap-2">
            <button
              onClick={() => handleSave()}
              disabled={saving || !settings}
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              data-testid="dunning-template-save-button"
            >
              {saving && <Loader2 className="h-4 w-4 animate-spin" />}
              {t('settings.emailTemplate.save')}
            </button>
            <button
              onClick={handleReset}
              disabled={saving || !settings}
              className="inline-flex items-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
              data-testid="dunning-template-reset-button"
            >
              {t('settings.emailTemplate.resetToDefault')}
            </button>
          </div>
        )}

        {message && (
          <p className={`text-sm ${message.type === 'success' ? 'text-green-600' : 'text-red-600'}`}>
            {message.text}
          </p>
        )}
      </section>
    </div>
  )
}
