import { useTranslation } from 'react-i18next'
import { useNavigate } from 'react-router-dom'
import { Building2, Palette, Layout, X } from 'lucide-react'

interface ExtractedData {
  legal_data: {
    company_name: string | null
    street: string | null
    zip_code: string | null
    city: string | null
    country: string | null
    tax_number: string | null
    vat_id: string | null
    commercial_register_court: string | null
    commercial_register_number: string | null
    managing_directors: string[] | null
    bank_name: string | null
    iban: string | null
    bic: string | null
    phone: string | null
    email: string | null
    website: string | null
    share_capital: string | null
    default_tax_rate: string | null
  }
  design: {
    accent_color: string | null
    header_text: string | null
    footer_text: string | null
  }
  layout: {
    logo_position: string | null
    footer_columns: number | null
    description: string | null
  }
}

interface ExtractionReviewPanelProps {
  data: ExtractedData
  onClose: () => void
  onApplyTemplate: (design: ExtractedData['design']) => void
}

function FieldRow({ label, value }: { label: string; value: string | null | undefined }) {
  const isNull = value === null || value === undefined || value === ''
  return (
    <div className="flex justify-between py-1.5 text-sm">
      <span className="text-gray-500">{label}</span>
      {isNull ? (
        <span className="italic text-gray-300">—</span>
      ) : (
        <span className="font-medium text-gray-900 text-right max-w-[60%]">{value}</span>
      )}
    </div>
  )
}

export function ExtractionReviewPanel({ data, onClose, onApplyTemplate }: ExtractionReviewPanelProps) {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const ld = data.legal_data
  const design = data.design
  const layout = data.layout

  const handleApplyCompanyData = () => {
    navigate('/settings/invoices', { state: { extractedLegalData: ld } })
  }

  const handleApplyTemplate = () => {
    onApplyTemplate(design)
  }

  return (
    <div className="rounded-lg border border-blue-200 bg-blue-50/50 p-5 space-y-5">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-semibold text-gray-900">{t('invoices.extraction.reviewTitle')}</h3>
        <button onClick={onClose} className="rounded p-1 text-gray-400 hover:bg-gray-200 hover:text-gray-600">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Legal Data Section */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Building2 className="h-4 w-4 text-gray-500" />
          <h4 className="text-sm font-semibold text-gray-700">{t('invoices.extraction.legalData')}</h4>
        </div>
        <div className="rounded-lg bg-white border p-4 divide-y divide-gray-100">
          <FieldRow label={t('invoices.companyData.companyName')} value={ld.company_name} />
          <FieldRow label={t('invoices.companyData.street')} value={ld.street} />
          <FieldRow label={t('invoices.companyData.zipCode')} value={ld.zip_code} />
          <FieldRow label={t('invoices.companyData.city')} value={ld.city} />
          <FieldRow label={t('invoices.companyData.country')} value={ld.country} />
          <FieldRow label={t('invoices.companyData.taxNumber')} value={ld.tax_number} />
          <FieldRow label={t('invoices.companyData.vatId')} value={ld.vat_id} />
          <FieldRow label={t('invoices.companyData.registerCourt')} value={ld.commercial_register_court} />
          <FieldRow label={t('invoices.companyData.registerNumber')} value={ld.commercial_register_number} />
          <FieldRow
            label={t('invoices.companyData.managingDirectors')}
            value={ld.managing_directors?.join(', ') || null}
          />
          <FieldRow label={t('invoices.companyData.bankName')} value={ld.bank_name} />
          <FieldRow label={t('invoices.companyData.iban')} value={ld.iban} />
          <FieldRow label={t('invoices.companyData.bic')} value={ld.bic} />
          <FieldRow label={t('invoices.companyData.phone')} value={ld.phone} />
          <FieldRow label={t('invoices.companyData.email')} value={ld.email} />
          <FieldRow label={t('invoices.companyData.website')} value={ld.website} />
          <FieldRow label={t('invoices.companyData.shareCapital')} value={ld.share_capital} />
          <FieldRow label={t('invoices.companyData.defaultTaxRate')} value={ld.default_tax_rate ? `${ld.default_tax_rate}%` : null} />
        </div>
        <button
          type="button"
          onClick={handleApplyCompanyData}
          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Building2 className="h-4 w-4" />
          {t('invoices.extraction.applyCompanyData')}
        </button>
      </section>

      {/* Design Section */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Palette className="h-4 w-4 text-gray-500" />
          <h4 className="text-sm font-semibold text-gray-700">{t('invoices.extraction.designData')}</h4>
        </div>
        <div className="rounded-lg bg-white border p-4 divide-y divide-gray-100">
          <div className="flex justify-between py-1.5 text-sm">
            <span className="text-gray-500">{t('invoices.template.accentColor')}</span>
            {design.accent_color ? (
              <div className="flex items-center gap-2">
                <div className="h-5 w-5 rounded border" style={{ backgroundColor: design.accent_color }} />
                <span className="font-mono text-sm text-gray-900">{design.accent_color}</span>
              </div>
            ) : (
              <span className="italic text-gray-300">—</span>
            )}
          </div>
          <FieldRow label={t('invoices.template.headerText')} value={design.header_text} />
          <FieldRow label={t('invoices.template.footerText')} value={design.footer_text} />
        </div>
        <button
          type="button"
          onClick={handleApplyTemplate}
          className="mt-3 inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <Palette className="h-4 w-4" />
          {t('invoices.extraction.applyTemplate')}
        </button>
      </section>

      {/* Layout Section */}
      <section>
        <div className="flex items-center gap-2 mb-3">
          <Layout className="h-4 w-4 text-gray-500" />
          <h4 className="text-sm font-semibold text-gray-700">{t('invoices.extraction.layoutData')}</h4>
        </div>
        <div className="rounded-lg bg-white border p-4 divide-y divide-gray-100">
          <FieldRow label={t('invoices.extraction.logoPosition')} value={layout.logo_position} />
          <FieldRow label={t('invoices.extraction.footerColumns')} value={layout.footer_columns?.toString() ?? null} />
          <FieldRow label={t('invoices.extraction.layoutDescription')} value={layout.description} />
        </div>
        <p className="mt-2 text-xs text-gray-400">{t('invoices.extraction.layoutHint')}</p>
      </section>
    </div>
  )
}
