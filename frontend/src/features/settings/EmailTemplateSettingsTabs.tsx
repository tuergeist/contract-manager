import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { EmailTemplateSettings } from '@/features/invoices/EmailTemplateSettings'
import { ABEmailTemplateSettings } from '@/features/contracts/ABEmailTemplateSettings'
import { SettingsCrossLink } from './SettingsCrossLink'

export function EmailTemplateSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/order-confirmation')) return 'order-confirmation'
    return 'invoice'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'order-confirmation':
        navigate('/settings/email-templates/order-confirmation')
        break
      default:
        navigate('/settings/email-templates')
    }
  }

  return (
    <div>
      <SettingsCrossLink
        text={t('settings.crossLink.numberingHint')}
        to="/settings/numbering"
        linkText={t('settings.crossLink.numbering')}
      />
      <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
        <TabsList className="mb-4">
          <TabsTrigger value="invoice">{t('settings.emailTemplates.invoice')}</TabsTrigger>
          <TabsTrigger value="order-confirmation">{t('settings.emailTemplates.orderConfirmation')}</TabsTrigger>
        </TabsList>

        <TabsContent value="invoice">
          <EmailTemplateSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="order-confirmation">
          <ABEmailTemplateSettings showHeader={false} />
        </TabsContent>
      </Tabs>
    </div>
  )
}
