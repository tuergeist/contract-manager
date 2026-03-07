import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { CompanyDataSettings } from '@/features/invoices/CompanyDataSettings'
import { TemplateSettings } from '@/features/invoices/TemplateSettings'
import { ZugferdSettings } from '@/features/invoices/ZugferdSettings'

export function DocumentSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/template')) return 'template'
    if (location.pathname.includes('/zugferd')) return 'zugferd'
    return 'company'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'template':
        navigate('/settings/documents/template')
        break
      case 'zugferd':
        navigate('/settings/documents/zugferd')
        break
      default:
        navigate('/settings/documents')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="company">{t('invoices.companyData.title')}</TabsTrigger>
        <TabsTrigger value="template">{t('invoices.template.title')}</TabsTrigger>
        <TabsTrigger value="zugferd">{t('invoices.zugferd.title')}</TabsTrigger>
      </TabsList>

      <TabsContent value="company">
        <CompanyDataSettings showHeader={false} />
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
