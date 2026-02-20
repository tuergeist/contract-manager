import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Settings } from './Settings'
import { SmtpSettings } from './SmtpSettings'

export function IntegrationSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()

  const getActiveSubTab = () => {
    if (location.pathname.includes('/integrations/time-tracking')) return 'timeTracking'
    if (location.pathname.includes('/integrations/email')) return 'email'
    if (location.pathname.includes('/integrations/notifications')) return 'notifications'
    return 'hubspot'
  }

  const activeSubTab = getActiveSubTab()

  const handleSubTabChange = (value: string) => {
    switch (value) {
      case 'timeTracking':
        navigate('/settings/integrations/time-tracking')
        break
      case 'email':
        navigate('/settings/integrations/email')
        break
      case 'notifications':
        navigate('/settings/integrations/notifications')
        break
      default:
        navigate('/settings/integrations')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        <TabsTrigger value="hubspot">{t('settings.integrationTabs.hubspot')}</TabsTrigger>
        <TabsTrigger value="timeTracking">{t('settings.integrationTabs.timeTracking')}</TabsTrigger>
        <TabsTrigger value="email">{t('settings.integrationTabs.email')}</TabsTrigger>
        <TabsTrigger value="notifications">{t('settings.integrationTabs.notifications')}</TabsTrigger>
      </TabsList>

      <TabsContent value="hubspot">
        <Settings showHeader={false} section="hubspot" />
      </TabsContent>

      <TabsContent value="timeTracking">
        <Settings showHeader={false} section="timeTracking" />
      </TabsContent>

      <TabsContent value="email">
        <Settings showHeader={false} section="email" />
      </TabsContent>

      <TabsContent value="notifications">
        <SmtpSettings />
      </TabsContent>
    </Tabs>
  )
}
