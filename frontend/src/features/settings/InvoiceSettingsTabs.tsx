import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { CompanyDataSettings } from '@/features/invoices/CompanyDataSettings'
import { NumberSchemeSettings } from '@/features/invoices/NumberSchemeSettings'
import { TemplateSettings } from '@/features/invoices/TemplateSettings'
import { ZugferdSettings } from '@/features/invoices/ZugferdSettings'

export function InvoiceSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  // Determine active sub-tab from URL
  const getActiveSubTab = () => {
    if (location.pathname.includes('/numbering')) return 'numbering'
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
        <TabsTrigger value="template">{t('invoices.template.title')}</TabsTrigger>
        <TabsTrigger value="zugferd">{t('invoices.zugferd.title')}</TabsTrigger>
      </TabsList>

      <TabsContent value="company">
        <CompanyDataSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="numbering">
        <NumberSchemeSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="template">
        <TemplateSettings showHeader={false} />
      </TabsContent>

      <TabsContent value="zugferd">
        <ZugferdSettings showHeader={false} />
      </TabsContent>
    </Tabs>
  )
}
