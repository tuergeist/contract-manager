import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { CompanyDataSettings } from '@/features/invoices/CompanyDataSettings'
import { EmailTemplateSettings } from '@/features/invoices/EmailTemplateSettings'
import { NumberSchemeSettings } from '@/features/invoices/NumberSchemeSettings'
import { StornoNumberSchemeSettings } from '@/features/invoices/StornoNumberSchemeSettings'
import { TemplateSettings } from '@/features/invoices/TemplateSettings'
import { ZugferdSettings } from '@/features/invoices/ZugferdSettings'
import { OfferNumberSchemeSettings } from '@/features/offers/OfferNumberSchemeSettings'
import { ABNumberSchemeSettings } from '@/features/contracts/ABNumberSchemeSettings'
import { ABEmailTemplateSettings } from '@/features/contracts/ABEmailTemplateSettings'

export function InvoiceSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  // Determine active sub-tab from URL
  const getActiveSubTab = () => {
    if (location.pathname.includes('/ab-numbering')) return 'ab-numbering'
    if (location.pathname.includes('/ab-email-template')) return 'ab-email-template'
    if (location.pathname.includes('/offer-numbering')) return 'offer-numbering'
    if (location.pathname.includes('/storno-numbering')) return 'storno-numbering'
    if (location.pathname.includes('/numbering')) return 'numbering'
    if (location.pathname.includes('/email-template')) return 'email-template'
    if (location.pathname.includes('/template')) return 'template'
    if (location.pathname.includes('/zugferd')) return 'zugferd'
    return 'company'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'numbering':
        navigate('/settings/invoices/numbering')
        break
      case 'storno-numbering':
        navigate('/settings/invoices/storno-numbering')
        break
      case 'offer-numbering':
        navigate('/settings/invoices/offer-numbering')
        break
      case 'email-template':
        navigate('/settings/invoices/email-template')
        break
      case 'ab-numbering':
        navigate('/settings/invoices/ab-numbering')
        break
      case 'ab-email-template':
        navigate('/settings/invoices/ab-email-template')
        break
      case 'template':
        navigate('/settings/invoices/template')
        break
      case 'zugferd':
        navigate('/settings/invoices/zugferd')
        break
      default:
        navigate('/settings/invoices')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="company">{t('invoices.companyData.title')}</TabsTrigger>
        <TabsTrigger value="numbering">{t('invoices.numberScheme.title')}</TabsTrigger>
        <TabsTrigger value="storno-numbering">{t('invoices.stornoNumberScheme.title')}</TabsTrigger>
        <TabsTrigger value="offer-numbering">{t('offers.numberScheme.title')}</TabsTrigger>
        <TabsTrigger value="template">{t('invoices.template.title')}</TabsTrigger>
        <TabsTrigger value="email-template">{t('settings.emailTemplate.tabTitle')}</TabsTrigger>
        <TabsTrigger value="ab-numbering">{t('orderConfirmation.numberScheme.title')}</TabsTrigger>
        <TabsTrigger value="ab-email-template">{t('orderConfirmation.emailTemplate.title')}</TabsTrigger>
        <TabsTrigger value="zugferd">{t('invoices.zugferd.title')}</TabsTrigger>
      </TabsList>

      <TabsContent value="company">
        <CompanyDataSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="numbering">
        <NumberSchemeSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="storno-numbering">
        <StornoNumberSchemeSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="offer-numbering">
        <OfferNumberSchemeSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="template">
        <TemplateSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="email-template">
        <EmailTemplateSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="ab-numbering">
        <ABNumberSchemeSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="ab-email-template">
        <ABEmailTemplateSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="zugferd">
        <ZugferdSettings showHeader={false} />
      </TabsContent>
    </Tabs>
  )
}
