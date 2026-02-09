import { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useLocation } from 'react-router-dom'
import { useQuery, useMutation, gql } from '@apollo/client'
import { Loader2, Plus, X, Building2 } from 'lucide-react'

const COMPANY_LEGAL_DATA_QUERY = gql`
  query CompanyLegalData {
    companyLegalData {
      companyName
      street
      zipCode
      city
      country
      taxNumber
      vatId
      commercialRegisterCourt
      commercialRegisterNumber
      managingDirectors
      bankName
      iban
      bic
      phone
      email
      website
      shareCapital
      defaultTaxRate
    }
  }
`

const SAVE_COMPANY_LEGAL_DATA = gql`
  mutation SaveCompanyLegalData($input: CompanyLegalDataInput!) {
    saveCompanyLegalData(input: $input) {
      success
      error
      data {
        companyName
      }
    }
  }
`

interface FormData {
  companyName: string
  street: string
  zipCode: string
  city: string
  country: string
  taxNumber: string
  vatId: string
  commercialRegisterCourt: string
  commercialRegisterNumber: string
  managingDirectors: string[]
  bankName: string
  iban: string
  bic: string
  phone: string
  email: string
  website: string
  shareCapital: string
  defaultTaxRate: string
}

const emptyForm: FormData = {
  companyName: '',
  street: '',
  zipCode: '',
  city: '',
  country: 'Deutschland',
  taxNumber: '',
  vatId: '',
  commercialRegisterCourt: '',
  commercialRegisterNumber: '',
  managingDirectors: [''],
  bankName: '',
  iban: '',
  bic: '',
  phone: '',
  email: '',
  website: '',
  shareCapital: '',
  defaultTaxRate: '19.00',
}

interface CompanyDataSettingsProps {
  showHeader?: boolean
}

export function CompanyDataSettings({ showHeader = true }: CompanyDataSettingsProps) {
  const { t } = useTranslation()
  const location = useLocation()
  const [form, setForm] = useState<FormData>(emptyForm)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [appliedExtraction, setAppliedExtraction] = useState(false)

  const { data, loading } = useQuery(COMPANY_LEGAL_DATA_QUERY)
  const [save, { loading: saving }] = useMutation(SAVE_COMPANY_LEGAL_DATA)

  useEffect(() => {
    if (data?.companyLegalData) {
      const d = data.companyLegalData
      setForm({
        companyName: d.companyName || '',
        street: d.street || '',
        zipCode: d.zipCode || '',
        city: d.city || '',
        country: d.country || 'Deutschland',
        taxNumber: d.taxNumber || '',
        vatId: d.vatId || '',
        commercialRegisterCourt: d.commercialRegisterCourt || '',
        commercialRegisterNumber: d.commercialRegisterNumber || '',
        managingDirectors: d.managingDirectors?.length ? d.managingDirectors : [''],
        bankName: d.bankName || '',
        iban: d.iban || '',
        bic: d.bic || '',
        phone: d.phone || '',
        email: d.email || '',
        website: d.website || '',
        shareCapital: d.shareCapital || '',
        defaultTaxRate: d.defaultTaxRate || '19.00',
      })
    }
  }, [data])

  // Apply extracted legal data from navigation state (only non-null values)
  useEffect(() => {
    const state = location.state as { extractedLegalData?: Record<string, unknown> } | null
    if (state?.extractedLegalData && !appliedExtraction) {
      setAppliedExtraction(true)
      const ld = state.extractedLegalData
      setForm(prev => ({
        companyName: (ld.company_name as string) || prev.companyName,
        street: (ld.street as string) || prev.street,
        zipCode: (ld.zip_code as string) || prev.zipCode,
        city: (ld.city as string) || prev.city,
        country: (ld.country as string) || prev.country,
        taxNumber: (ld.tax_number as string) || prev.taxNumber,
        vatId: (ld.vat_id as string) || prev.vatId,
        commercialRegisterCourt: (ld.commercial_register_court as string) || prev.commercialRegisterCourt,
        commercialRegisterNumber: (ld.commercial_register_number as string) || prev.commercialRegisterNumber,
        managingDirectors: (ld.managing_directors as string[])?.length
          ? (ld.managing_directors as string[])
          : prev.managingDirectors,
        bankName: (ld.bank_name as string) || prev.bankName,
        iban: (ld.iban as string) || prev.iban,
        bic: (ld.bic as string) || prev.bic,
        phone: (ld.phone as string) || prev.phone,
        email: (ld.email as string) || prev.email,
        website: (ld.website as string) || prev.website,
        shareCapital: (ld.share_capital as string) || prev.shareCapital,
        defaultTaxRate: (ld.default_tax_rate as string) || prev.defaultTaxRate,
      }))
      setToast({ type: 'success', message: t('invoices.extraction.appliedCompanyData') })
      setTimeout(() => setToast(null), 5000)
      // Clear the state so refresh doesn't re-apply
      window.history.replaceState({}, '')
    }
  }, [location.state, appliedExtraction, t])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const { data: result } = await save({
        variables: {
          input: {
            ...form,
            managingDirectors: form.managingDirectors.filter(d => d.trim()),
            defaultTaxRate: form.defaultTaxRate,
          },
        },
        refetchQueries: ['CompanyLegalData'],
      })
      if (result?.saveCompanyLegalData?.success) {
        setToast({ type: 'success', message: t('invoices.companyData.saved') })
      } else {
        setToast({ type: 'error', message: result?.saveCompanyLegalData?.error || t('invoices.companyData.saveFailed') })
      }
    } catch {
      setToast({ type: 'error', message: t('invoices.companyData.saveFailed') })
    }
    setTimeout(() => setToast(null), 3000)
  }

  const updateField = (field: keyof FormData, value: string) => {
    setForm(prev => ({ ...prev, [field]: value }))
  }

  const updateDirector = (index: number, value: string) => {
    setForm(prev => {
      const directors = [...prev.managingDirectors]
      directors[index] = value
      return { ...prev, managingDirectors: directors }
    })
  }

  const addDirector = () => {
    setForm(prev => ({ ...prev, managingDirectors: [...prev.managingDirectors, ''] }))
  }

  const removeDirector = (index: number) => {
    setForm(prev => ({
      ...prev,
      managingDirectors: prev.managingDirectors.filter((_, i) => i !== index),
    }))
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
    <div className="mx-auto max-w-3xl">
      {showHeader && (
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <Building2 className="h-6 w-6 text-gray-600" />
            <h1 className="text-2xl font-bold text-gray-900">{t('invoices.companyData.title')}</h1>
          </div>
          <p className="text-sm text-gray-500">{t('invoices.companyData.description')}</p>
        </div>
      )}

      {toast && (
        <div className={`mb-4 rounded-lg px-4 py-3 text-sm ${toast.type === 'success' ? 'bg-green-50 text-green-800' : 'bg-red-50 text-red-800'}`}>
          {toast.message}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Company Identification */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionCompany')}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={labelClass}>{t('invoices.companyData.companyName')} *</label>
              <input className={inputClass} value={form.companyName} onChange={e => updateField('companyName', e.target.value)} placeholder={t('invoices.companyData.companyNamePlaceholder')} required />
            </div>
            <div className="sm:col-span-2">
              <label className={labelClass}>{t('invoices.companyData.street')} *</label>
              <input className={inputClass} value={form.street} onChange={e => updateField('street', e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.zipCode')} *</label>
              <input className={inputClass} value={form.zipCode} onChange={e => updateField('zipCode', e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.city')} *</label>
              <input className={inputClass} value={form.city} onChange={e => updateField('city', e.target.value)} required />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.country')}</label>
              <input className={inputClass} value={form.country} onChange={e => updateField('country', e.target.value)} />
            </div>
          </div>
        </section>

        {/* Tax Information */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionTax')}</h2>
          <p className="mb-4 text-xs text-gray-500">{t('invoices.companyData.taxIdRequired')}</p>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>{t('invoices.companyData.taxNumber')}</label>
              <input className={inputClass} value={form.taxNumber} onChange={e => updateField('taxNumber', e.target.value)} placeholder={t('invoices.companyData.taxNumberPlaceholder')} />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.vatId')}</label>
              <input className={inputClass} value={form.vatId} onChange={e => updateField('vatId', e.target.value)} placeholder={t('invoices.companyData.vatIdPlaceholder')} />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.defaultTaxRate')}</label>
              <input className={inputClass} type="number" step="0.01" value={form.defaultTaxRate} onChange={e => updateField('defaultTaxRate', e.target.value)} />
            </div>
          </div>
        </section>

        {/* Commercial Register */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionRegister')}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>{t('invoices.companyData.registerCourt')} *</label>
              <input className={inputClass} value={form.commercialRegisterCourt} onChange={e => updateField('commercialRegisterCourt', e.target.value)} placeholder={t('invoices.companyData.registerCourtPlaceholder')} required />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.registerNumber')} *</label>
              <input className={inputClass} value={form.commercialRegisterNumber} onChange={e => updateField('commercialRegisterNumber', e.target.value)} placeholder={t('invoices.companyData.registerNumberPlaceholder')} required />
            </div>
          </div>
        </section>

        {/* Managing Directors */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-2 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionDirectors')}</h2>
          <p className="mb-4 text-xs text-gray-500">{t('invoices.companyData.managingDirectorsHint')}</p>
          <div className="space-y-2">
            {form.managingDirectors.map((director, i) => (
              <div key={i} className="flex gap-2">
                <input
                  className={inputClass}
                  value={director}
                  onChange={e => updateDirector(i, e.target.value)}
                  placeholder={`${t('invoices.companyData.managingDirectors')} ${i + 1}`}
                />
                {form.managingDirectors.length > 1 && (
                  <button type="button" onClick={() => removeDirector(i)} className="rounded p-2 text-gray-400 hover:bg-gray-100 hover:text-red-500">
                    <X className="h-4 w-4" />
                  </button>
                )}
              </div>
            ))}
            <button type="button" onClick={addDirector} className="flex items-center gap-1 text-sm text-blue-600 hover:text-blue-700">
              <Plus className="h-4 w-4" /> {t('invoices.companyData.addDirector')}
            </button>
          </div>
        </section>

        {/* Bank Details */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionBank')}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <label className={labelClass}>{t('invoices.companyData.bankName')}</label>
              <input className={inputClass} value={form.bankName} onChange={e => updateField('bankName', e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.iban')}</label>
              <input className={inputClass} value={form.iban} onChange={e => updateField('iban', e.target.value)} placeholder={t('invoices.companyData.ibanPlaceholder')} />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.bic')}</label>
              <input className={inputClass} value={form.bic} onChange={e => updateField('bic', e.target.value)} />
            </div>
          </div>
        </section>

        {/* Contact Information */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionContact')}</h2>
          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <label className={labelClass}>{t('invoices.companyData.phone')}</label>
              <input className={inputClass} value={form.phone} onChange={e => updateField('phone', e.target.value)} />
            </div>
            <div>
              <label className={labelClass}>{t('invoices.companyData.email')}</label>
              <input className={inputClass} type="email" value={form.email} onChange={e => updateField('email', e.target.value)} />
            </div>
            <div className="sm:col-span-2">
              <label className={labelClass}>{t('invoices.companyData.website')}</label>
              <input className={inputClass} value={form.website} onChange={e => updateField('website', e.target.value)} />
            </div>
          </div>
        </section>

        {/* Share Capital */}
        <section className="rounded-lg border bg-white p-6">
          <h2 className="mb-4 text-lg font-semibold text-gray-900">{t('invoices.companyData.sectionCapital')}</h2>
          <div>
            <label className={labelClass}>{t('invoices.companyData.shareCapital')}</label>
            <input className={inputClass} value={form.shareCapital} onChange={e => updateField('shareCapital', e.target.value)} placeholder={t('invoices.companyData.shareCapitalPlaceholder')} />
          </div>
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
