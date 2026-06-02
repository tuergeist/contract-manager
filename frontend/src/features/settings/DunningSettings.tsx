import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useQuery, useMutation } from '@apollo/client'
import { Loader2, Bell } from 'lucide-react'
import { useAuth } from '@/lib/auth'
import {
  DUNNING_SETTINGS_QUERY,
  SAVE_DUNNING_SETTINGS,
  stageLabelKey,
  type DunningSettings as DunningSettingsType,
  type DunningTemplateStage,
} from '@/features/reminders/dunning'

interface DunningSettingsProps {
  showHeader?: boolean
}

type Language = 'de' | 'en'
const LANGUAGES: Language[] = ['de', 'en']
const STAGES = [0, 1, 2, 3]

const emptyStage: DunningTemplateStage = { title: '', subject: '', body: '' }

interface FormState {
  defaultPaymentTermDays: string
  overdueRedThresholdDays: string
  mahnfaehigThresholdDays: string
  interestRate: string
  defaultFeePerStage: Record<string, string>
  templates: Record<Language, Record<string, DunningTemplateStage>>
}

function buildInitialState(settings: DunningSettingsType | null): FormState {
  const templates: FormState['templates'] = { de: {}, en: {} }
  for (const lang of LANGUAGES) {
    for (const stage of STAGES) {
      const src = settings?.templates?.[lang]?.[String(stage)]
      templates[lang][String(stage)] = {
        title: src?.title ?? '',
        subject: src?.subject ?? '',
        body: src?.body ?? '',
      }
    }
  }
  const fees: Record<string, string> = {}
  for (const stage of STAGES) {
    fees[String(stage)] = settings?.defaultFeePerStage?.[String(stage)] ?? '0'
  }
  return {
    defaultPaymentTermDays: String(settings?.defaultPaymentTermDays ?? 14),
    overdueRedThresholdDays: String(settings?.overdueRedThresholdDays ?? 7),
    mahnfaehigThresholdDays: String(settings?.mahnfaehigThresholdDays ?? 14),
    interestRate: settings?.interestRate ?? '0',
    defaultFeePerStage: fees,
    templates,
  }
}

/**
 * Settings UI for the payment reminders / dunning (Mahnwesen) feature.
 * Editable only with the `reminders.settings` permission.
 */
export function DunningSettings({ showHeader = true }: DunningSettingsProps) {
  const { t } = useTranslation()
  const { hasPermission } = useAuth()
  const canEdit = hasPermission('reminders', 'settings')

  const [form, setForm] = useState<FormState>(() => buildInitialState(null))
  const [activeLang, setActiveLang] = useState<Language>('de')
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const { data, loading } = useQuery<{ dunningSettings: DunningSettingsType | null }>(
    DUNNING_SETTINGS_QUERY
  )
  const [save, { loading: saving }] = useMutation(SAVE_DUNNING_SETTINGS)

  useEffect(() => {
    if (data?.dunningSettings) {
      setForm(buildInitialState(data.dunningSettings))
    }
  }, [data])

  const updateTemplate = (
    lang: Language,
    stage: number,
    field: keyof DunningTemplateStage,
    value: string
  ) => {
    setForm((prev) => ({
      ...prev,
      templates: {
        ...prev.templates,
        [lang]: {
          ...prev.templates[lang],
          [String(stage)]: {
            ...(prev.templates[lang][String(stage)] ?? emptyStage),
            [field]: value,
          },
        },
      },
    }))
  }

  const updateFee = (stage: number, value: string) => {
    setForm((prev) => ({
      ...prev,
      defaultFeePerStage: { ...prev.defaultFeePerStage, [String(stage)]: value },
    }))
  }

  const handleSave = async () => {
    try {
      const { data: result } = await save({
        variables: {
          input: {
            defaultPaymentTermDays: parseInt(form.defaultPaymentTermDays, 10) || 0,
            overdueRedThresholdDays: parseInt(form.overdueRedThresholdDays, 10) || 0,
            mahnfaehigThresholdDays: parseInt(form.mahnfaehigThresholdDays, 10) || 0,
            interestRate: form.interestRate || '0',
            defaultFeePerStage: form.defaultFeePerStage,
            templates: form.templates,
          },
        },
        refetchQueries: ['DunningSettings'],
      })
      if (result?.saveDunningSettings?.success) {
        setToast({ type: 'success', message: t('reminders.settings.saved') })
      } else {
        setToast({
          type: 'error',
          message: result?.saveDunningSettings?.error || t('reminders.settings.saveFailed'),
        })
      }
    } catch {
      setToast({ type: 'error', message: t('reminders.settings.saveFailed') })
    }
    setTimeout(() => setToast(null), 4000)
  }

  if (loading) {
    return (
      <div className="flex h-64 items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
      </div>
    )
  }

  const inputClass =
    'w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:bg-gray-50 disabled:text-gray-500'
  const labelClass = 'block text-sm font-medium text-gray-700 mb-1'

  return (
    <div className="space-y-6" data-testid="dunning-settings">
      {showHeader && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Bell className="h-6 w-6 text-gray-600" />
            <h1 className="text-2xl font-bold text-gray-900">{t('reminders.settings.title')}</h1>
          </div>
          <p className="text-sm text-gray-500">{t('reminders.settings.description')}</p>
        </div>
      )}

      {toast && (
        <div
          className={`rounded-lg px-4 py-3 text-sm ${
            toast.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'
          }`}
        >
          {toast.message}
        </div>
      )}

      {!canEdit && (
        <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-800">
          {t('reminders.settings.readonlyNotice')}
        </div>
      )}

      {/* Thresholds & interest */}
      <section className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          {t('reminders.settings.sectionThresholds')}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <label className={labelClass}>{t('reminders.settings.defaultPaymentTermDays')}</label>
            <input
              type="number"
              min={0}
              className={inputClass}
              disabled={!canEdit}
              value={form.defaultPaymentTermDays}
              onChange={(e) => setForm((p) => ({ ...p, defaultPaymentTermDays: e.target.value }))}
              data-testid="dunning-default-payment-term"
            />
            <p className="mt-1 text-xs text-gray-400">
              {t('reminders.settings.defaultPaymentTermDaysHint')}
            </p>
          </div>
          <div>
            <label className={labelClass}>{t('reminders.settings.overdueRedThresholdDays')}</label>
            <input
              type="number"
              min={0}
              className={inputClass}
              disabled={!canEdit}
              value={form.overdueRedThresholdDays}
              onChange={(e) => setForm((p) => ({ ...p, overdueRedThresholdDays: e.target.value }))}
              data-testid="dunning-overdue-red-threshold"
            />
            <p className="mt-1 text-xs text-gray-400">
              {t('reminders.settings.overdueRedThresholdDaysHint')}
            </p>
          </div>
          <div>
            <label className={labelClass}>{t('reminders.settings.mahnfaehigThresholdDays')}</label>
            <input
              type="number"
              min={0}
              className={inputClass}
              disabled={!canEdit}
              value={form.mahnfaehigThresholdDays}
              onChange={(e) => setForm((p) => ({ ...p, mahnfaehigThresholdDays: e.target.value }))}
              data-testid="dunning-mahnfaehig-threshold"
            />
            <p className="mt-1 text-xs text-gray-400">
              {t('reminders.settings.mahnfaehigThresholdDaysHint')}
            </p>
          </div>
          <div>
            <label className={labelClass}>{t('reminders.settings.interestRate')}</label>
            <input
              type="number"
              step="0.01"
              min={0}
              className={inputClass}
              disabled={!canEdit}
              value={form.interestRate}
              onChange={(e) => setForm((p) => ({ ...p, interestRate: e.target.value }))}
              data-testid="dunning-interest-rate"
            />
            <p className="mt-1 text-xs text-gray-400">{t('reminders.settings.interestRateHint')}</p>
          </div>
        </div>
      </section>

      {/* Fee per stage */}
      <section className="rounded-lg border bg-white p-6">
        <h2 className="mb-4 text-lg font-semibold text-gray-900">
          {t('reminders.settings.sectionFees')}
        </h2>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STAGES.map((stage) => (
            <div key={stage}>
              <label className={labelClass}>{t(stageLabelKey(stage))}</label>
              <input
                type="number"
                step="0.01"
                min={0}
                className={inputClass}
                disabled={!canEdit}
                value={form.defaultFeePerStage[String(stage)] ?? '0'}
                onChange={(e) => updateFee(stage, e.target.value)}
                data-testid={`dunning-fee-stage-${stage}`}
              />
            </div>
          ))}
        </div>
      </section>

      {/* Templates */}
      <section className="rounded-lg border bg-white p-6">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">
            {t('reminders.settings.sectionTemplates')}
          </h2>
          <div className="inline-flex rounded-md border border-input">
            {LANGUAGES.map((lang) => (
              <button
                key={lang}
                type="button"
                onClick={() => setActiveLang(lang)}
                className={`px-3 py-1.5 text-sm font-medium transition-colors first:rounded-l-md last:rounded-r-md ${
                  activeLang === lang
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-background text-muted-foreground hover:bg-muted'
                }`}
                data-testid={`dunning-lang-${lang}`}
              >
                {lang.toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="space-y-6">
          {STAGES.map((stage) => {
            const tpl = form.templates[activeLang][String(stage)] ?? emptyStage
            return (
              <div
                key={`${activeLang}-${stage}`}
                className="rounded-lg border p-4"
                data-testid={`dunning-template-${activeLang}-${stage}`}
              >
                <h3 className="mb-3 text-sm font-semibold text-gray-900">
                  {t(stageLabelKey(stage))}
                </h3>
                <div className="space-y-3">
                  <div>
                    <label className={labelClass}>{t('reminders.settings.templateTitle')}</label>
                    <input
                      className={inputClass}
                      disabled={!canEdit}
                      value={tpl.title}
                      onChange={(e) => updateTemplate(activeLang, stage, 'title', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>{t('reminders.settings.templateSubject')}</label>
                    <input
                      className={inputClass}
                      disabled={!canEdit}
                      value={tpl.subject}
                      onChange={(e) => updateTemplate(activeLang, stage, 'subject', e.target.value)}
                    />
                  </div>
                  <div>
                    <label className={labelClass}>{t('reminders.settings.templateBody')}</label>
                    <textarea
                      className={inputClass}
                      rows={5}
                      disabled={!canEdit}
                      value={tpl.body}
                      onChange={(e) => updateTemplate(activeLang, stage, 'body', e.target.value)}
                    />
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </section>

      {canEdit && (
        <div className="flex justify-end">
          <button
            type="button"
            onClick={handleSave}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-6 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="dunning-save-button"
          >
            {saving && <Loader2 className="h-4 w-4 animate-spin" />}
            {t('common.save')}
          </button>
        </div>
      )}
    </div>
  )
}
