import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { EmailTemplateSettings } from '@/features/invoices/EmailTemplateSettings'
import { ABEmailTemplateSettings } from '@/features/contracts/ABEmailTemplateSettings'
import { DocumentEmailBccSettings } from './DocumentEmailBccSettings'
import { DunningTemplateSettings } from './DunningTemplateSettings'
import { SettingsCrossLink } from './SettingsCrossLink'

export function EmailTemplateSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/order-confirmation')) return 'order-confirmation'
    if (location.pathname.includes('/dunning')) return 'dunning'
    if (location.pathname.includes('/bcc')) return 'bcc'
    return 'invoice'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'order-confirmation':
        navigate('/settings/email-templates/order-confirmation')
        break
      case 'dunning':
        navigate('/settings/email-templates/dunning')
        break
      case 'bcc':
        navigate('/settings/email-templates/bcc')
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
          <TabsTrigger value="dunning">{t('settings.emailTemplates.dunning')}</TabsTrigger>
          <TabsTrigger value="bcc">{t('settings.emailTemplates.bcc')}</TabsTrigger>
        </TabsList>

        <TabsContent value="invoice">
          <EmailTemplateSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="order-confirmation">
          <ABEmailTemplateSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="dunning">
          <DunningTemplateSettings showHeader={false} />
        </TabsContent>

        <TabsContent value="bcc">
          <DocumentEmailBccSettings />
        </TabsContent>
      </Tabs>
    </div>
  )
}
