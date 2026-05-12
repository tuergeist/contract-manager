import { useTranslation } from 'react-i18next'
import { useLocation, useNavigate } from 'react-router-dom'
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs'
import { Settings } from './Settings'
import { SmtpSettings } from './SmtpSettings'
import { McpSettings } from './McpSettings'
import { useAuth } from '@/lib/auth'

export function IntegrationSettingsTabs() {
  const { t } = useTranslation()
  const location = useLocation()
  const navigate = useNavigate()
  const { hasPermission } = useAuth()
  // Admin-only sub-tabs (tenant-wide integration configuration). API tab is per-user.
  const canManageIntegrations = hasPermission('settings', 'read')

  const getActiveSubTab = () => {
    if (location.pathname.includes('/integrations/time-tracking')) return 'timeTracking'
    if (location.pathname.includes('/integrations/email')) return 'email'
    if (location.pathname.includes('/integrations/notifications')) return 'notifications'
    if (location.pathname.includes('/integrations/api')) return 'api'
    return canManageIntegrations ? 'hubspot' : 'api'
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
      case 'api':
        navigate('/settings/integrations/api')
        break
      default:
        navigate('/settings/integrations')
    }
  }

  return (
    <Tabs value={activeSubTab} onValueChange={handleSubTabChange}>
      <TabsList className="mb-4">
        {canManageIntegrations && <TabsTrigger value="hubspot">{t('settings.integrationTabs.hubspot')}</TabsTrigger>}
        {canManageIntegrations && <TabsTrigger value="timeTracking">{t('settings.integrationTabs.timeTracking')}</TabsTrigger>}
        {canManageIntegrations && <TabsTrigger value="email">{t('settings.integrationTabs.email')}</TabsTrigger>}
        {canManageIntegrations && <TabsTrigger value="notifications">{t('settings.integrationTabs.notifications')}</TabsTrigger>}
        <TabsTrigger value="api">{t('settings.integrationTabs.api')}</TabsTrigger>
      </TabsList>

      {canManageIntegrations && (
        <TabsContent value="hubspot">
          <Settings showHeader={false} section="hubspot" />
        </TabsContent>
      )}

      {canManageIntegrations && (
        <TabsContent value="timeTracking">
          <Settings showHeader={false} section="timeTracking" />
        </TabsContent>
      )}

      {canManageIntegrations && (
        <TabsContent value="email">
          <Settings showHeader={false} section="email" />
        </TabsContent>
      )}

      {canManageIntegrations && (
        <TabsContent value="notifications">
          <SmtpSettings />
        </TabsContent>
      )}

      <TabsContent value="api">
        <McpSettings />
      </TabsContent>
    </Tabs>
  )
}
